import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse


@dataclass
class TravelContext:
    """Central travel context object that gets enriched by each agent."""
    # User Intent Agent data
    destination: Optional[str] = None
    duration: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    food_preferences: List[str] = None
    activity_preferences: List[str] = None
    poi_preferences: List[str] = None
    travelers: int = 1
    transportation_style: Optional[str] = None
    budget_level: str = "mid-range"
    
    # Location & Weather Agent data
    validated_location_details: Optional[Dict[str, Any]] = None
    weather_data: Optional[Dict[str, Any]] = None
    
    # POI & Activity Agent data
    potential_pois: List[Dict[str, Any]] = None
    potential_activities: List[Dict[str, Any]] = None
    
    # Food Recommendation Agent data
    potential_restaurants: List[Dict[str, Any]] = None
    
    # Itinerary Generation Agent data
    proposed_itinerary: List[Dict[str, Any]] = None
    
    # Budget Estimation Agent data
    estimated_budget_breakdown: Optional[Dict[str, Any]] = None
    total_estimated_budget: float = 0.0
    daily_average_budget: float = 0.0
    
    def __post_init__(self):
        """Initialize lists if None."""
        if self.food_preferences is None:
            self.food_preferences = []
        if self.activity_preferences is None:
            self.activity_preferences = []
        if self.poi_preferences is None:
            self.poi_preferences = []
        if self.potential_pois is None:
            self.potential_pois = []
        if self.potential_activities is None:
            self.potential_activities = []
        if self.potential_restaurants is None:
            self.potential_restaurants = []
        if self.proposed_itinerary is None:
            self.proposed_itinerary = []


class UserIntentAgent(BaseAgent):
    """Agent responsible for parsing user queries and extracting travel intent."""
    
    def __init__(self):
        super().__init__(
            agent_id="user_intent",
            name="User Intent Extractor",
            description="Parses user queries to extract travel intent, destination, dates, preferences, and traveler information",
            tools=[]  # This agent uses AI for text processing, no external tools needed
        )
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant specializing in parsing user travel queries. Your goal is to extract key entities and preferences from the user's request to initialize a travel plan.

        Extract the following information from user messages:
        - destination: The primary city or region for travel
        - duration: Number of days (if not specified, infer from dates or assume 3-5 days)
        - start_date: Travel start date (if not specified, assume 30 days from today)
        - end_date: Travel end date (calculate from start_date + duration)
        - food_preferences: Specific cuisines, dietary restrictions, or meal types
        - activity_preferences: Types of activities (adventure, cultural, relaxing, shopping)
        - poi_preferences: Types of places of interest (museums, historical landmarks, parks, art galleries)
        - travelers: Number of travelers (default to 1 if not mentioned)
        - transportation_style: Preferred way to get around (walking, public transport, car, etc.)
        - budget_level: Categorize as 'budget', 'mid-range', or 'luxury' (default to 'mid-range')

        Always output structured JSON data for reliable parsing by other agents.
        If information is not explicitly mentioned, use reasonable defaults or leave as null.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the user intent agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "extract_user_intent":
            return await self._extract_user_intent(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _extract_user_intent(self, content: Dict[str, Any]) -> AgentResponse:
        """Extract user intent from natural language query."""
        try:
            user_query = content.get("user_query", "")
            
            if not user_query:
                return self._create_error_response("user_query is required")
            
            # Use AI to extract structured information from the user query
            extraction_prompt = f"""
            Extract travel information from this user message: "{user_query}"
            
            Today's date is {date.today().isoformat()} for reference when interpreting relative dates.
            
            Please identify and extract the following information:
            1. Destination (city/place name) - any location mentioned
            2. Duration (number of days) - look for patterns like "3-day", "5 days", "week", etc.
            3. Any specific dates mentioned
            4. Food preferences (cuisines, dietary restrictions, meal types)
            5. Activity preferences (adventure, cultural, relaxing, shopping, etc.)
            6. POI preferences (museums, landmarks, parks, galleries, etc.)
            7. Number of travelers
            8. Transportation preferences
            9. Budget level indicators
            
            If specific dates are not mentioned, assume the trip starts 30 days from today.
            If duration is not specified, assume 3 days.
            
            Return your response as valid JSON only, no additional text.
            """
            
            # Define the expected JSON schema
            schema = {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "The destination city or place name"
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Number of days for the trip",
                        "minimum": 1
                    },
                    "start_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string", 
                        "format": "date",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "food_preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of food preferences mentioned"
                    },
                    "activity_preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of activity preferences mentioned"
                    },
                    "poi_preferences": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of POI preferences mentioned"
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "Number of travelers",
                        "default": 1,
                        "minimum": 1
                    },
                    "transportation_style": {
                        "type": "string",
                        "description": "Preferred transportation method"
                    },
                    "budget_level": {
                        "type": "string",
                        "enum": ["budget", "mid-range", "luxury"],
                        "description": "Budget level if mentioned",
                        "default": "mid-range"
                    }
                },
                "required": ["destination"]
            }
            
            # Call AI to extract information
            extraction_result = await self.generate_ai_json_response(
                prompt=extraction_prompt,
                schema=schema
            )
            
            # Validate and create TravelContext
            travel_context = await self._create_travel_context(extraction_result)
            
            return self._create_success_response({
                "travel_context": travel_context.dict() if hasattr(travel_context, 'dict') else travel_context.__dict__,
                "extracted_info": extraction_result
            })
            
        except Exception as e:
            self.logger.error(f"Error extracting user intent: {str(e)}")
            return self._create_error_response(f"Failed to extract user intent: {str(e)}")
    
    async def _create_travel_context(self, extraction_result: Dict[str, Any]) -> TravelContext:
        """Create TravelContext from extraction result."""
        try:
            # Handle dates
            start_date = extraction_result.get("start_date")
            end_date = extraction_result.get("end_date")
            duration = extraction_result.get("duration", 3)
            
            # If we have dates, calculate duration
            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                duration = (end - start).days + 1
            # If we have start date and duration, calculate end date
            elif start_date and duration:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = start + timedelta(days=duration - 1)
                end_date = end.isoformat()
            # If we have duration but no dates, use defaults
            elif duration and not start_date:
                start = date.today() + timedelta(days=30)  # 30 days from today
                end = start + timedelta(days=duration - 1)
                start_date = start.isoformat()
                end_date = end.isoformat()
            # Default case
            else:
                start = date.today() + timedelta(days=30)
                end = start + timedelta(days=2)  # 3 days total
                start_date = start.isoformat()
                end_date = end.isoformat()
                duration = 3
            
            # Create TravelContext
            travel_context = TravelContext(
                destination=extraction_result.get("destination"),
                duration=duration,
                start_date=start_date,
                end_date=end_date,
                food_preferences=extraction_result.get("food_preferences", []),
                activity_preferences=extraction_result.get("activity_preferences", []),
                poi_preferences=extraction_result.get("poi_preferences", []),
                travelers=extraction_result.get("travelers", 1),
                transportation_style=extraction_result.get("transportation_style"),
                budget_level=extraction_result.get("budget_level", "mid-range")
            )
            
            return travel_context
            
        except Exception as e:
            self.logger.error(f"Error creating travel context: {str(e)}")
            raise 