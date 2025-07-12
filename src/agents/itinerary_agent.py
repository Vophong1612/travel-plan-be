import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.models.trip import ItineraryDay, Activity, Location, ActivityType
from src.models.user import UserProfile
from src.tools import MCPToolResponse


@dataclass
class ItineraryRequest:
    """Request structure for itinerary generation."""
    user_profile: UserProfile
    destination: str
    date: date
    day_index: int
    constraints: Optional[Dict[str, Any]] = None
    revision_feedback: Optional[str] = None


class ItineraryAgent(BaseAgent):
    """Agent responsible for generating detailed, feasible daily itineraries."""
    
    def __init__(self):
        super().__init__(
            agent_id="itinerary",
            name="Itinerary Planner",
            description="Generates detailed daily itineraries using real-time data and user preferences",
            tools=["google_maps", "weather"]
        )
        
        # Activity type preferences mapping
        self.activity_type_mapping = {
            "history": [ActivityType.CULTURAL, ActivityType.SIGHTSEEING],
            "food": [ActivityType.DINING],
            "adventure": [ActivityType.OUTDOOR],
            "culture": [ActivityType.CULTURAL],
            "art": [ActivityType.CULTURAL, ActivityType.SIGHTSEEING],
            "music": [ActivityType.ENTERTAINMENT],
            "shopping": [ActivityType.SHOPPING],
            "nightlife": [ActivityType.ENTERTAINMENT],
            "nature": [ActivityType.OUTDOOR],
            "architecture": [ActivityType.SIGHTSEEING],
            "photography": [ActivityType.SIGHTSEEING, ActivityType.OUTDOOR]
        }
        
        # Place type mapping for Google Maps
        self.place_types = {
            ActivityType.DINING: ["restaurant", "cafe", "food"],
            ActivityType.SIGHTSEEING: ["tourist_attraction", "museum", "park"],
            ActivityType.CULTURAL: ["museum", "art_gallery", "historical_site"],
            ActivityType.ENTERTAINMENT: ["entertainment", "amusement_park", "nightclub"],
            ActivityType.SHOPPING: ["shopping_mall", "store"],
            ActivityType.OUTDOOR: ["park", "hiking_area", "beach"],
            ActivityType.ACCOMMODATION: ["lodging"],
            ActivityType.TRANSPORT: ["transit_station"]
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an expert travel planner. Your goal is to create optimal daily itineraries that are:
        1. Personalized to the user's preferences and travel style
        2. Logically sequenced with feasible travel times
        3. Weather-appropriate and contextually aware
        4. Budget-conscious and realistic
        5. Locally relevant with authentic experiences
        
        When creating itineraries:
        - Use real-time data from your tools
        - Consider travel time between activities
        - Account for opening hours and availability
        - Match activities to user interests and pace
        - Include a mix of must-see attractions and local experiences
        - Plan for meals at appropriate times
        - Consider weather conditions and seasonal factors
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the itinerary agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "generate_itinerary":
            return await self._generate_itinerary(content)
        elif message_type == "revise_itinerary":
            return await self._revise_itinerary(content)
        elif message_type == "get_activity_suggestions":
            return await self._get_activity_suggestions(content)
        elif message_type == "calculate_travel_times":
            return await self._calculate_travel_times(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _generate_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Generate a complete daily itinerary."""
        try:
            # Parse request
            request = await self._parse_itinerary_request(content)
            
            # Get weather forecast for the day
            weather_info = await self._get_weather_for_date(request.destination, request.date)
            
            # Get location information
            location_info = await self._get_location_info(request.destination)
            
            # Generate activity suggestions based on user profile
            activity_suggestions = await self._generate_activity_suggestions(
                request.user_profile, 
                request.destination, 
                request.date,
                weather_info,
                location_info
            )
            
            # Create optimized itinerary
            itinerary = await self._create_optimized_itinerary(
                request, 
                activity_suggestions, 
                weather_info
            )
            
            return self._create_success_response({
                "itinerary": itinerary.dict(),
                "weather_info": weather_info,
                "generation_context": {
                    "user_profile_summary": await self._get_profile_summary(request.user_profile),
                    "constraints_applied": request.constraints,
                    "total_activities": len(itinerary.activities),
                    "estimated_cost": itinerary.total_cost
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error generating itinerary: {str(e)}")
            return self._create_error_response(f"Failed to generate itinerary: {str(e)}")
    
    async def _revise_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Revise an existing itinerary based on feedback."""
        try:
            # Parse revision request
            request = await self._parse_itinerary_request(content)
            existing_itinerary = content.get("existing_itinerary")
            
            if not existing_itinerary:
                return self._create_error_response("existing_itinerary is required for revision")
            
            # Analyze feedback
            feedback_analysis = await self._analyze_revision_feedback(
                request.revision_feedback, 
                existing_itinerary
            )
            
            # Apply revisions
            revised_itinerary = await self._apply_revisions(
                existing_itinerary, 
                feedback_analysis, 
                request
            )
            
            return self._create_success_response({
                "revised_itinerary": revised_itinerary.dict(),
                "revision_summary": feedback_analysis,
                "changes_made": await self._get_revision_changes(existing_itinerary, revised_itinerary)
            })
            
        except Exception as e:
            self.logger.error(f"Error revising itinerary: {str(e)}")
            return self._create_error_response(f"Failed to revise itinerary: {str(e)}")
    
    async def _get_activity_suggestions(self, content: Dict[str, Any]) -> AgentResponse:
        """Get activity suggestions for a location."""
        try:
            destination = content.get("destination")
            activity_type = content.get("activity_type")
            user_preferences = content.get("user_preferences", {})
            
            if not destination:
                return self._create_error_response("destination is required")
            
            # Get location-based suggestions
            suggestions = await self._find_activities_by_type(
                destination, 
                activity_type, 
                user_preferences
            )
            
            return self._create_success_response({
                "destination": destination,
                "activity_type": activity_type,
                "suggestions": suggestions
            })
            
        except Exception as e:
            self.logger.error(f"Error getting activity suggestions: {str(e)}")
            return self._create_error_response(f"Failed to get activity suggestions: {str(e)}")
    
    async def _calculate_travel_times(self, content: Dict[str, Any]) -> AgentResponse:
        """Calculate travel times between activities."""
        try:
            activities = content.get("activities", [])
            travel_mode = content.get("travel_mode", "driving")
            
            if len(activities) < 2:
                return self._create_error_response("At least 2 activities required")
            
            # Calculate travel times between consecutive activities
            travel_times = []
            for i in range(len(activities) - 1):
                current = activities[i]
                next_activity = activities[i + 1]
                
                travel_time = await self._get_travel_time(
                    current.get("location"),
                    next_activity.get("location"),
                    travel_mode
                )
                
                travel_times.append({
                    "from": current.get("name"),
                    "to": next_activity.get("name"),
                    "travel_time_minutes": travel_time,
                    "travel_mode": travel_mode
                })
            
            return self._create_success_response({
                "travel_times": travel_times,
                "total_travel_time": sum(t["travel_time_minutes"] for t in travel_times)
            })
            
        except Exception as e:
            self.logger.error(f"Error calculating travel times: {str(e)}")
            return self._create_error_response(f"Failed to calculate travel times: {str(e)}")
    
    async def _parse_itinerary_request(self, content: Dict[str, Any]) -> ItineraryRequest:
        """Parse and validate itinerary request."""
        user_profile_data = content.get("user_profile")
        if not user_profile_data:
            raise ValueError("user_profile is required")
        
        user_profile = UserProfile(**user_profile_data) if isinstance(user_profile_data, dict) else user_profile_data
        
        destination = content.get("destination")
        if not destination:
            raise ValueError("destination is required")
        
        date_str = content.get("date")
        if not date_str:
            raise ValueError("date is required")
        
        # Parse date
        if isinstance(date_str, str):
            trip_date = datetime.fromisoformat(date_str).date()
        else:
            trip_date = date_str
        
        return ItineraryRequest(
            user_profile=user_profile,
            destination=destination,
            date=trip_date,
            day_index=content.get("day_index", 1),
            constraints=content.get("constraints"),
            revision_feedback=content.get("revision_feedback")
        )
    
    async def _get_weather_for_date(self, destination: str, target_date: date) -> Dict[str, Any]:
        """Get weather forecast for a specific date."""
        try:
            # Calculate days from today
            days_ahead = (target_date - date.today()).days
            
            if days_ahead < 0:
                # Historical weather (simplified)
                weather_response = await self.use_tool(
                    "weather",
                    action="current_weather",
                    location=destination
                )
            else:
                # Future weather forecast
                weather_response = await self.use_tool(
                    "weather",
                    action="weather_forecast",
                    location=destination,
                    days=min(days_ahead + 1, 16)  # Open-Meteo limit
                )
            
            if weather_response.success:
                return weather_response.data
            else:
                self.logger.warning(f"Weather API failed: {weather_response.error}")
                return {"error": "Weather data unavailable"}
                
        except Exception as e:
            self.logger.error(f"Error getting weather: {str(e)}")
            return {"error": str(e)}
    
    async def _get_location_info(self, destination: str) -> Dict[str, Any]:
        """Get general location information."""
        try:
            location_response = await self.use_tool(
                "google_maps",
                action="search_location",
                query=destination
            )
            
            if location_response.success and location_response.data.get("locations"):
                return location_response.data["locations"][0]
            else:
                self.logger.warning(f"Location search failed: {location_response.error}")
                return {"error": "Location data unavailable"}
                
        except Exception as e:
            self.logger.error(f"Error getting location info: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_activity_suggestions(self, 
                                           user_profile: UserProfile, 
                                           destination: str, 
                                           target_date: date,
                                           weather_info: Dict[str, Any],
                                           location_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate activity suggestions based on user profile and conditions."""
        suggestions = []
        
        # Determine activity types based on user interests
        preferred_activity_types = self._get_preferred_activity_types(user_profile)
        
        # Get suggestions for each activity type
        for activity_type in preferred_activity_types:
            try:
                type_suggestions = await self._find_activities_by_type(
                    destination, 
                    activity_type, 
                    user_profile.preferences.dict()
                )
                suggestions.extend(type_suggestions)
            except Exception as e:
                self.logger.error(f"Error finding activities for {activity_type}: {str(e)}")
                continue
        
        # Note: Travel MCP tool removed - relying on Google Maps for activity suggestions
        
        # Filter based on weather conditions
        if weather_info and not weather_info.get("error"):
            suggestions = self._filter_by_weather(suggestions, weather_info)
        
        # Sort by relevance score
        suggestions = self._score_and_sort_suggestions(suggestions, user_profile)
        
        return suggestions[:20]  # Limit to top 20 suggestions
    

    
    async def _find_activities_by_type(self, 
                                     destination: str, 
                                     activity_type: ActivityType, 
                                     user_preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find activities of a specific type in the destination."""
        suggestions = []
        
        # Get place types for this activity type
        place_types = self.place_types.get(activity_type, ["tourist_attraction"])
        
        for place_type in place_types:
            try:
                places_response = await self.use_tool(
                    "google_maps",
                    action="find_nearby_places",
                    query=destination,
                    place_type=place_type,
                    radius=5000  # 5km radius
                )
                
                if places_response.success:
                    places = places_response.data.get("places", [])
                    for place in places:
                        suggestion = {
                            "name": place.get("name", ""),
                            "type": activity_type.value,
                            "location": {
                                "name": place.get("name", ""),
                                "address": place.get("formatted_address", ""),
                                "latitude": place.get("latitude"),
                                "longitude": place.get("longitude"),
                                "place_id": place.get("place_id")
                            },
                            "rating": place.get("rating"),
                            "price_level": place.get("price_level"),
                            "opening_hours": place.get("opening_hours"),
                            "types": place.get("types", []),
                            "photos": place.get("photos", [])
                        }
                        suggestions.append(suggestion)
                        
            except Exception as e:
                self.logger.error(f"Error finding {place_type} places: {str(e)}")
                continue
        
        return suggestions
    
    async def _create_optimized_itinerary(self, 
                                        request: ItineraryRequest, 
                                        activity_suggestions: List[Dict[str, Any]],
                                        weather_info: Dict[str, Any]) -> ItineraryDay:
        """Create an optimized daily itinerary."""
        # Determine number of activities based on user pace
        pace = request.user_profile.preferences.pace
        if pace.value == "slow":
            max_activities = 3
        elif pace.value == "fast":
            max_activities = 7
        else:
            max_activities = 5
        
        # Select activities
        selected_activities = activity_suggestions[:max_activities]
        
        # Create activities with timing
        activities = []
        current_time = datetime.combine(request.date, datetime.min.time().replace(hour=9))  # Start at 9 AM
        
        for i, suggestion in enumerate(selected_activities):
            # Calculate duration based on activity type
            duration = self._estimate_activity_duration(suggestion["type"])
            
            # Create activity
            activity = Activity(
                id=f"activity_{request.day_index}_{i+1}",
                name=suggestion["name"],
                type=ActivityType(suggestion["type"]),
                description=f"Visit {suggestion['name']}",
                location=Location(**suggestion["location"]),
                start_time=current_time,
                end_time=current_time + timedelta(minutes=duration),
                duration_minutes=duration,
                rating=suggestion.get("rating"),
                source="google_maps"
            )
            
            # Add travel time from previous activity
            if i > 0:
                travel_time = await self._get_travel_time(
                    activities[i-1].location,
                    activity.location,
                    "walking"
                )
                activity.travel_time_from_previous = travel_time
                activity.travel_mode = "walking"
            
            activities.append(activity)
            
            # Move to next time slot (including travel time)
            travel_time = activity.travel_time_from_previous or 0
            current_time = activity.end_time + timedelta(minutes=travel_time + 30)  # 30 min buffer
        
        # Create daily theme
        theme = self._generate_daily_theme(activities, request.user_profile)
        
        # Calculate totals
        total_cost = sum(a.cost for a in activities if a.cost)
        total_duration = sum(a.duration_minutes for a in activities if a.duration_minutes)
        
        # Create itinerary day
        itinerary_day = ItineraryDay(
            day_index=request.day_index,
            date=request.date,
            theme=theme,
            activities=activities,
            total_cost=total_cost,
            total_duration_minutes=total_duration,
            weather_forecast=weather_info
        )
        
        return itinerary_day
    
    def _get_preferred_activity_types(self, user_profile: UserProfile) -> List[ActivityType]:
        """Get preferred activity types based on user profile."""
        preferred_types = []
        
        # Map user interests to activity types
        for interest in user_profile.preferences.interests:
            interest_lower = interest.lower()
            for keyword, types in self.activity_type_mapping.items():
                if keyword in interest_lower:
                    preferred_types.extend(types)
        
        # Add default types based on travel style
        for style in user_profile.preferences.travel_style:
            if style.value == "cultural":
                preferred_types.extend([ActivityType.CULTURAL, ActivityType.SIGHTSEEING])
            elif style.value == "adventure":
                preferred_types.extend([ActivityType.OUTDOOR])
            elif style.value == "relaxation":
                preferred_types.extend([ActivityType.DINING])
        
        # Always include dining
        preferred_types.append(ActivityType.DINING)
        
        # Remove duplicates and return
        return list(set(preferred_types))
    
    def _filter_by_weather(self, suggestions: List[Dict[str, Any]], weather_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter suggestions based on weather conditions."""
        if weather_info.get("error"):
            return suggestions
        
        # Get weather conditions
        current_weather = weather_info.get("current_weather", {})
        condition = current_weather.get("condition", "").lower()
        precipitation = current_weather.get("precipitation", 0)
        
        # Filter outdoor activities if weather is bad
        if precipitation > 5 or "rain" in condition or "storm" in condition:
            filtered = []
            for suggestion in suggestions:
                if suggestion["type"] in ["outdoor"]:
                    # Skip outdoor activities in bad weather
                    continue
                filtered.append(suggestion)
            return filtered
        
        return suggestions
    
    def _score_and_sort_suggestions(self, suggestions: List[Dict[str, Any]], user_profile: UserProfile) -> List[Dict[str, Any]]:
        """Score and sort suggestions based on user preferences."""
        for suggestion in suggestions:
            score = 0
            
            # Rating score
            if suggestion.get("rating"):
                score += suggestion["rating"] * 10
            
            # Price level alignment
            price_level = suggestion.get("price_level", 2)
            if user_profile.budget.level.value == "budget" and price_level <= 2:
                score += 20
            elif user_profile.budget.level.value == "luxury" and price_level >= 3:
                score += 20
            elif user_profile.budget.level.value == "mid-range" and price_level == 2:
                score += 20
            
            # Interest alignment
            suggestion_types = suggestion.get("types", [])
            for interest in user_profile.preferences.interests:
                if any(interest.lower() in t.lower() for t in suggestion_types):
                    score += 15
            
            suggestion["relevance_score"] = score
        
        # Sort by relevance score
        return sorted(suggestions, key=lambda x: x.get("relevance_score", 0), reverse=True)
    
    async def _get_travel_time(self, origin: Location, destination: Location, mode: str = "walking") -> int:
        """Get travel time between two locations."""
        try:
            travel_response = await self.use_tool(
                "google_maps",
                action="calculate_travel_time",
                origin=f"{origin.latitude},{origin.longitude}",
                destination=f"{destination.latitude},{destination.longitude}",
                travel_mode=mode
            )
            
            if travel_response.success:
                duration = travel_response.data.get("duration", {})
                return duration.get("value_seconds", 0) // 60  # Convert to minutes
            else:
                self.logger.warning(f"Travel time calculation failed: {travel_response.error}")
                return 30  # Default 30 minutes
                
        except Exception as e:
            self.logger.error(f"Error calculating travel time: {str(e)}")
            return 30  # Default 30 minutes
    
    def _estimate_activity_duration(self, activity_type: str) -> int:
        """Estimate activity duration in minutes."""
        duration_map = {
            "dining": 90,
            "sightseeing": 120,
            "cultural": 150,
            "outdoor": 180,
            "entertainment": 120,
            "shopping": 90,
            "accommodation": 60,
            "transport": 30
        }
        return duration_map.get(activity_type, 120)
    
    def _generate_daily_theme(self, activities: List[Activity], user_profile: UserProfile) -> str:
        """Generate a theme for the day based on activities."""
        activity_types = [a.type.value for a in activities]
        
        if "cultural" in activity_types and "sightseeing" in activity_types:
            return "Cultural Exploration"
        elif "outdoor" in activity_types:
            return "Nature & Adventure"
        elif "dining" in activity_types and len([a for a in activities if a.type == ActivityType.DINING]) > 1:
            return "Culinary Discovery"
        elif "entertainment" in activity_types:
            return "Entertainment & Nightlife"
        else:
            return "City Discovery"
    
    async def _analyze_revision_feedback(self, feedback: str, existing_itinerary: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze revision feedback and determine what changes to make."""
        # Simple feedback analysis (could be enhanced with NLP)
        feedback_lower = feedback.lower()
        
        analysis = {
            "feedback": feedback,
            "changes_requested": []
        }
        
        # Common feedback patterns
        if "restaurant" in feedback_lower or "food" in feedback_lower or "dining" in feedback_lower:
            analysis["changes_requested"].append("change_dining")
        
        if "outdoor" in feedback_lower or "indoor" in feedback_lower:
            analysis["changes_requested"].append("change_activity_type")
        
        if "time" in feedback_lower or "schedule" in feedback_lower:
            analysis["changes_requested"].append("adjust_timing")
        
        if "expensive" in feedback_lower or "cheap" in feedback_lower or "budget" in feedback_lower:
            analysis["changes_requested"].append("adjust_budget")
        
        if "more" in feedback_lower or "add" in feedback_lower:
            analysis["changes_requested"].append("add_activities")
        
        if "less" in feedback_lower or "remove" in feedback_lower:
            analysis["changes_requested"].append("remove_activities")
        
        return analysis
    
    async def _apply_revisions(self, existing_itinerary: Dict[str, Any], feedback_analysis: Dict[str, Any], request: ItineraryRequest) -> ItineraryDay:
        """Apply revisions to an existing itinerary."""
        # For now, regenerate the itinerary with feedback constraints
        # In a more sophisticated version, we would make targeted changes
        
        # Add feedback as constraints
        constraints = request.constraints or {}
        constraints["revision_feedback"] = feedback_analysis
        
        # Create new request with constraints
        revision_request = ItineraryRequest(
            user_profile=request.user_profile,
            destination=request.destination,
            date=request.date,
            day_index=request.day_index,
            constraints=constraints
        )
        
        # Generate new itinerary
        weather_info = await self._get_weather_for_date(request.destination, request.date)
        location_info = await self._get_location_info(request.destination)
        
        activity_suggestions = await self._generate_activity_suggestions(
            request.user_profile,
            request.destination,
            request.date,
            weather_info,
            location_info
        )
        
        return await self._create_optimized_itinerary(revision_request, activity_suggestions, weather_info)
    
    async def _get_revision_changes(self, old_itinerary: Dict[str, Any], new_itinerary: ItineraryDay) -> List[str]:
        """Get a list of changes made during revision."""
        changes = []
        
        old_activities = old_itinerary.get("activities", [])
        new_activities = new_itinerary.activities
        
        # Compare activity counts
        if len(new_activities) != len(old_activities):
            changes.append(f"Changed number of activities from {len(old_activities)} to {len(new_activities)}")
        
        # Compare activity types
        old_types = [a.get("type") for a in old_activities]
        new_types = [a.type.value for a in new_activities]
        
        if old_types != new_types:
            changes.append("Changed activity types")
        
        # Compare specific activities
        old_names = [a.get("name") for a in old_activities]
        new_names = [a.name for a in new_activities]
        
        added = set(new_names) - set(old_names)
        removed = set(old_names) - set(new_names)
        
        if added:
            changes.append(f"Added: {', '.join(added)}")
        
        if removed:
            changes.append(f"Removed: {', '.join(removed)}")
        
        return changes
    
    async def _get_profile_summary(self, user_profile: UserProfile) -> str:
        """Get a summary of the user profile for context."""
        return f"Travel style: {', '.join([s.value for s in user_profile.preferences.travel_style])}, " \
               f"Pace: {user_profile.preferences.pace.value}, " \
               f"Budget: {user_profile.budget.level.value}, " \
               f"Group size: {user_profile.traveler_info.group_size}" 