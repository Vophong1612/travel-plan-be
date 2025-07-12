import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.models.user import UserProfile, UserPreferences, TravelerInfo, Budget, TravelStyle, TravelPace, BudgetLevel, TravelerType


class ProfilerAgent(BaseAgent):
    """Agent responsible for user onboarding and profile building through conversational interactions."""
    
    def __init__(self):
        super().__init__(
            agent_id="profiler",
            name="Travel Profiler",
            description="Conducts conversational user onboarding to build detailed user profiles",
            tools=[]  # Profiler doesn't need external tools
        )
        
        # Onboarding question flow
        self.onboarding_questions = [
            {
                "id": "trip_goal",
                "question": "What's the main goal of your trip?",
                "type": "open_ended",
                "follow_up": "Tell me more about what you're hoping to experience."
            },
            {
                "id": "travel_style",
                "question": "How would you describe your travel style?",
                "type": "multiple_choice",
                "options": ["Adventure", "Cultural", "Relaxation", "Business", "Luxury", "Budget"],
                "follow_up": "What draws you to this style of travel?"
            },
            {
                "id": "pace_preference",
                "question": "Do you prefer a fast-paced itinerary with lots of activities, or a slower pace with more time to relax?",
                "type": "scale",
                "options": ["Slow and relaxed", "Moderate pace", "Fast-paced and active"]
            },
            {
                "id": "interests",
                "question": "What are your main interests and hobbies?",
                "type": "open_ended",
                "follow_up": "Are there any specific activities you always look for when traveling?"
            },
            {
                "id": "budget",
                "question": "What's your budget range for this trip?",
                "type": "multiple_choice",
                "options": ["Budget-conscious", "Mid-range", "Luxury"],
                "follow_up": "What's your daily spending comfort level?"
            },
            {
                "id": "group_info",
                "question": "Who are you traveling with?",
                "type": "multiple_choice",
                "options": ["Solo", "Couple", "Family", "Friends", "Business colleagues"]
            },
            {
                "id": "dietary_restrictions",
                "question": "Do you have any dietary restrictions or food preferences?",
                "type": "open_ended",
                "optional": True
            },
            {
                "id": "accessibility_needs",
                "question": "Do you have any accessibility requirements we should consider?",
                "type": "open_ended",
                "optional": True
            }
        ]
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are a friendly and insightful travel profiler. Your goal is to understand the user's travel DNA through natural conversation.
        
        Guidelines:
        1. Ask questions in a conversational, friendly tone
        2. Start broad and get more specific based on responses
        3. Show genuine interest in their answers
        4. Ask follow-up questions to dig deeper
        5. Synthesize responses into a structured profile
        6. Confirm understanding before finalizing
        
        Your mission is to create a comprehensive travel profile that will enable personalized trip planning.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the profiler agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "start_onboarding":
            return await self._start_onboarding(content)
        elif message_type == "process_response":
            return await self._process_user_response(content)
        elif message_type == "finalize_profile":
            return await self._finalize_profile(content)
        elif message_type == "update_profile":
            return await self._update_profile(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _start_onboarding(self, content: Dict[str, Any]) -> AgentResponse:
        """Start the user onboarding process."""
        user_id = content.get("user_id")
        if not user_id:
            return self._create_error_response("user_id is required")
        
        # Initialize onboarding state
        self.set_memory("user_id", user_id, scope="session")
        self.set_memory("current_question_index", 0, scope="session")
        self.set_memory("responses", {}, scope="session")
        self.set_memory("onboarding_complete", False, scope="session")
        
        # Get first question
        first_question = self.onboarding_questions[0]
        
        return self._create_success_response({
            "onboarding_started": True,
            "question": self._format_question(first_question),
            "progress": {
                "current": 1,
                "total": len(self.onboarding_questions)
            }
        })
    
    async def _process_user_response(self, content: Dict[str, Any]) -> AgentResponse:
        """Process user response to onboarding question."""
        user_response = content.get("response")
        if not user_response:
            return self._create_error_response("response is required")
        
        current_index = self.get_memory("current_question_index", scope="session", default=0)
        responses = self.get_memory("responses", scope="session", default={})
        
        if current_index >= len(self.onboarding_questions):
            return self._create_error_response("Onboarding already complete")
        
        # Store current response
        current_question = self.onboarding_questions[current_index]
        responses[current_question["id"]] = user_response
        self.set_memory("responses", responses, scope="session")
        
        # Process and validate response
        processed_response = await self._process_response(current_question, user_response)
        
        # Move to next question
        next_index = current_index + 1
        self.set_memory("current_question_index", next_index, scope="session")
        
        # Check if onboarding is complete
        if next_index >= len(self.onboarding_questions):
            return await self._complete_onboarding()
        
        # Get next question
        next_question = self.onboarding_questions[next_index]
        
        return self._create_success_response({
            "response_processed": True,
            "next_question": self._format_question(next_question),
            "progress": {
                "current": next_index + 1,
                "total": len(self.onboarding_questions)
            },
            "processed_response": processed_response
        })
    
    async def _complete_onboarding(self) -> AgentResponse:
        """Complete the onboarding process and generate profile."""
        responses = self.get_memory("responses", scope="session", default={})
        user_id = self.get_memory("user_id", scope="session")
        
        # Generate user profile from responses
        profile = await self._generate_profile_from_responses(user_id, responses)
        
        # Store in user memory
        self.set_memory("user_profile", profile.dict(), scope="user")
        self.set_memory("onboarding_complete", True, scope="session")
        
        return self._create_success_response({
            "onboarding_complete": True,
            "profile": profile.dict(),
            "confirmation_needed": True,
            "summary": await self._generate_profile_summary(profile)
        })
    
    async def _finalize_profile(self, content: Dict[str, Any]) -> AgentResponse:
        """Finalize the user profile after confirmation."""
        confirmed = content.get("confirmed", False)
        modifications = content.get("modifications", {})
        
        profile_data = self.get_memory("user_profile", scope="user")
        if not profile_data:
            return self._create_error_response("No profile found to finalize")
        
        if not confirmed:
            return self._create_error_response("Profile not confirmed by user")
        
        # Apply any modifications
        if modifications:
            profile_data = await self._apply_profile_modifications(profile_data, modifications)
        
        # Create final profile
        final_profile = UserProfile(**profile_data)
        
        # Store finalized profile
        self.set_memory("finalized_profile", final_profile.dict(), scope="user")
        
        return self._create_success_response({
            "profile_finalized": True,
            "profile": final_profile.dict(),
            "ready_for_planning": True
        })
    
    async def _update_profile(self, content: Dict[str, Any]) -> AgentResponse:
        """Update an existing user profile."""
        user_id = content.get("user_id")
        updates = content.get("updates", {})
        
        if not user_id or not updates:
            return self._create_error_response("user_id and updates are required")
        
        # Get existing profile
        existing_profile = self.get_memory("finalized_profile", scope="user")
        if not existing_profile:
            return self._create_error_response("No existing profile found")
        
        # Apply updates
        updated_profile_data = await self._apply_profile_modifications(existing_profile, updates)
        updated_profile = UserProfile(**updated_profile_data)
        
        # Store updated profile
        self.set_memory("finalized_profile", updated_profile.dict(), scope="user")
        
        return self._create_success_response({
            "profile_updated": True,
            "profile": updated_profile.dict()
        })
    
    def _format_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Format a question for presentation."""
        formatted = {
            "id": question["id"],
            "question": question["question"],
            "type": question["type"]
        }
        
        if "options" in question:
            formatted["options"] = question["options"]
        
        if "optional" in question:
            formatted["optional"] = question["optional"]
        
        return formatted
    
    async def _process_response(self, question: Dict[str, Any], response: str) -> Dict[str, Any]:
        """Process and validate a user response."""
        question_id = question["id"]
        question_type = question["type"]
        
        processed = {
            "question_id": question_id,
            "raw_response": response,
            "processed_value": response
        }
        
        # Process based on question type
        if question_type == "multiple_choice" and "options" in question:
            # Try to match response to options
            options = question["options"]
            matched_option = self._match_response_to_options(response, options)
            if matched_option:
                processed["processed_value"] = matched_option
                processed["confidence"] = "high"
            else:
                processed["confidence"] = "low"
                processed["note"] = "Response didn't match provided options"
        
        elif question_type == "scale":
            # Extract scale value
            scale_value = self._extract_scale_value(response, question.get("options", []))
            processed["processed_value"] = scale_value
        
        elif question_type == "open_ended":
            # Extract key information
            processed["keywords"] = self._extract_keywords(response)
            processed["sentiment"] = self._analyze_sentiment(response)
        
        return processed
    
    async def _generate_profile_from_responses(self, user_id: str, responses: Dict[str, str]) -> UserProfile:
        """Generate a UserProfile from onboarding responses."""
        # Extract travel style
        travel_style = []
        if "travel_style" in responses:
            style_response = responses["travel_style"]
            if "adventure" in style_response.lower():
                travel_style.append(TravelStyle.ADVENTURE)
            if "cultural" in style_response.lower():
                travel_style.append(TravelStyle.CULTURAL)
            if "relaxation" in style_response.lower():
                travel_style.append(TravelStyle.RELAXATION)
            if "business" in style_response.lower():
                travel_style.append(TravelStyle.BUSINESS)
            if "luxury" in style_response.lower():
                travel_style.append(TravelStyle.LUXURY)
            if "budget" in style_response.lower():
                travel_style.append(TravelStyle.BUDGET)
        
        # Extract pace preference
        pace = TravelPace.MODERATE
        if "pace_preference" in responses:
            pace_response = responses["pace_preference"].lower()
            if "slow" in pace_response:
                pace = TravelPace.SLOW
            elif "fast" in pace_response:
                pace = TravelPace.FAST
        
        # Extract interests
        interests = []
        if "interests" in responses:
            interests = self._extract_keywords(responses["interests"])
        
        # Extract budget
        budget_level = BudgetLevel.MID_RANGE
        if "budget" in responses:
            budget_response = responses["budget"].lower()
            if "budget" in budget_response:
                budget_level = BudgetLevel.BUDGET
            elif "luxury" in budget_response:
                budget_level = BudgetLevel.LUXURY
        
        # Extract group info
        travels_with = [TravelerType.SOLO]
        group_size = 1
        if "group_info" in responses:
            group_response = responses["group_info"].lower()
            if "couple" in group_response:
                travels_with = [TravelerType.COUPLE]
                group_size = 2
            elif "family" in group_response:
                travels_with = [TravelerType.FAMILY]
                group_size = 4  # Default family size
            elif "friends" in group_response:
                travels_with = [TravelerType.FRIENDS]
                group_size = 3  # Default friends group size
            elif "business" in group_response:
                travels_with = [TravelerType.BUSINESS]
        
        # Extract dietary restrictions
        dietary_restrictions = []
        if "dietary_restrictions" in responses and responses["dietary_restrictions"]:
            dietary_restrictions = [responses["dietary_restrictions"]]
        
        # Extract accessibility needs
        accessibility_needs = []
        if "accessibility_needs" in responses and responses["accessibility_needs"]:
            accessibility_needs = [responses["accessibility_needs"]]
        
        # Build profile
        preferences = UserPreferences(
            travel_style=travel_style,
            pace=pace,
            interests=interests,
            dietary_restrictions=dietary_restrictions if dietary_restrictions else None
        )
        
        traveler_info = TravelerInfo(
            group_size=group_size,
            travels_with=travels_with,
            accessibility_needs=accessibility_needs if accessibility_needs else None
        )
        
        budget = Budget(
            level=budget_level,
            currency="USD"
        )
        
        return UserProfile(
            user_id=user_id,
            preferences=preferences,
            traveler_info=traveler_info,
            budget=budget
        )
    
    async def _generate_profile_summary(self, profile: UserProfile) -> str:
        """Generate a human-readable summary of the profile."""
        summary_parts = []
        
        # Travel style
        if profile.preferences.travel_style:
            styles = [style.value for style in profile.preferences.travel_style]
            summary_parts.append(f"Travel style: {', '.join(styles)}")
        
        # Pace
        summary_parts.append(f"Pace: {profile.preferences.pace.value}")
        
        # Group info
        group_info = f"{profile.traveler_info.group_size} "
        if profile.traveler_info.travels_with:
            group_types = [t.value for t in profile.traveler_info.travels_with]
            group_info += f"({', '.join(group_types)})"
        summary_parts.append(f"Group: {group_info}")
        
        # Budget
        summary_parts.append(f"Budget: {profile.budget.level.value}")
        
        # Interests
        if profile.preferences.interests:
            interests = ', '.join(profile.preferences.interests[:3])  # Top 3 interests
            summary_parts.append(f"Interests: {interests}")
        
        return "; ".join(summary_parts)
    
    async def _apply_profile_modifications(self, profile_data: Dict[str, Any], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Apply modifications to a profile."""
        # Deep copy to avoid modifying original
        import copy
        modified_profile = copy.deepcopy(profile_data)
        
        # Apply modifications
        for key, value in modifications.items():
            if "." in key:
                # Handle nested keys like "preferences.pace"
                parts = key.split(".")
                current = modified_profile
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                modified_profile[key] = value
        
        return modified_profile
    
    def _match_response_to_options(self, response: str, options: List[str]) -> Optional[str]:
        """Match a response to available options."""
        response_lower = response.lower()
        
        for option in options:
            if option.lower() in response_lower or response_lower in option.lower():
                return option
        
        return None
    
    def _extract_scale_value(self, response: str, options: List[str]) -> str:
        """Extract scale value from response."""
        response_lower = response.lower()
        
        for option in options:
            if option.lower() in response_lower:
                return option
        
        # Default to middle option
        return options[len(options) // 2] if options else "moderate"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text response."""
        # Simple keyword extraction
        import re
        
        # Remove common words and punctuation
        common_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "i", "me", "my", "you", "your"}
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        
        # Return unique keywords
        return list(set(keywords))
    
    def _analyze_sentiment(self, text: str) -> str:
        """Simple sentiment analysis."""
        positive_words = {"love", "enjoy", "great", "amazing", "wonderful", "fantastic", "excited", "passion", "favorite"}
        negative_words = {"hate", "dislike", "terrible", "awful", "boring", "stressful", "avoid"}
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral" 