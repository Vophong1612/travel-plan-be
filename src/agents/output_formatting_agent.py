import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class OutputFormattingAgent(BaseAgent):
    """Agent responsible for formatting the final JSON response for the /chat endpoint."""
    
    def __init__(self):
        super().__init__(
            agent_id="output_formatting",
            name="Output Formatter",
            description="Formats final JSON response including markdown message and structured trip details",
            tools=[]  # This agent uses formatting logic, no external tools needed
        )
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant specializing in formatting travel plan outputs.
        
        Your tasks:
        1. Create a comprehensive markdown message with trip overview, daily itinerary, and budget summary
        2. Format structured trip details for the backend API
        3. Extract and organize user preferences and trip information
        4. Ensure all data is properly formatted and complete
        
        The output should be user-friendly, well-organized, and contain all necessary trip information.
        Use markdown tables and formatting for clear presentation.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the output formatting agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "format_final_output":
            return await self._format_final_output(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _format_final_output(self, content: Dict[str, Any]) -> AgentResponse:
        """Format the final output for the /chat endpoint."""
        try:
            # Get travel context
            travel_context_data = content.get("travel_context")
            if not travel_context_data:
                return self._create_error_response("travel_context is required")
            
            # Recreate TravelContext object
            travel_context = TravelContext(**travel_context_data)
            
            # Generate unique trip ID
            trip_id = f"trip_{travel_context.travelers}_{int(datetime.utcnow().timestamp())}"
            
            # Create the final JSON response
            final_response = {
                "success": True,
                "message": await self._generate_markdown_message(travel_context),
                "trip_id": trip_id,
                "extracted_info": self._create_extracted_info(travel_context),
                "trip_details": self._create_trip_details(travel_context, trip_id),
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return self._create_success_response({
                "final_response": final_response
            })
            
        except Exception as e:
            self.logger.error(f"Error formatting final output: {str(e)}")
            return self._create_error_response(f"Failed to format final output: {str(e)}")
    
    async def _generate_markdown_message(self, travel_context: TravelContext) -> str:
        """Generate the markdown message for the response."""
        try:
            destination = travel_context.destination or "Your Destination"
            duration = travel_context.duration or 1
            start_date = travel_context.start_date or "TBD"
            end_date = travel_context.end_date or "TBD"
            total_budget = travel_context.total_estimated_budget or 0
            daily_budget = travel_context.daily_average_budget or 0
            
            # Build markdown message
            message_parts = []
            
            # Header
            message_parts.append(f"Great! I've planned your {duration}-day trip to {destination}. Here's your complete travel plan:\n")
            
            # Trip Overview
            message_parts.append("## 🌍 Trip Overview\n")
            message_parts.append("| **Field** | **Details** |")
            message_parts.append("|-----------|-------------|")
            message_parts.append(f"| **Destination** | {destination} |")
            message_parts.append(f"| **Duration** | {duration} days |")
            message_parts.append(f"| **Start Date** | {start_date} |")
            message_parts.append(f"| **End Date** | {end_date} |")
            message_parts.append("| **Status** | Planned |")
            message_parts.append(f"| **Created** | {datetime.utcnow().isoformat()} |")
            message_parts.append("")
            
            # Daily Itinerary
            message_parts.append("## 📅 Daily Itinerary\n")
            
            if travel_context.proposed_itinerary:
                for day in travel_context.proposed_itinerary:
                    day_index = day.get("day_index", 1)
                    theme = day.get("theme", "City Exploration")
                    activities = day.get("activities", [])
                    
                    message_parts.append(f"### Day {day_index}: {theme}\n")
                    message_parts.append("<div style='overflow-x: auto;'>\n")
                    message_parts.append("| **Time** | **Activity** | **Location** | **Cost** |")
                    message_parts.append("|----------|-------------|-------------|----------|")
                    
                    for activity in activities:
                        time = self._format_activity_time(activity)
                        name = activity.get("name", "Unknown Activity")
                        location = activity.get("location", {}).get("name", name)
                        cost = self._format_cost(activity.get("cost", 0))
                        
                        message_parts.append(f"| {time} | {name} | {location} | {cost} |")
                    
                    message_parts.append("\n\n</div>\n")
            else:
                message_parts.append("No detailed itinerary available.\n")
            
            # Budget Summary
            message_parts.append("## 💰 Budget Summary\n")
            message_parts.append("| **Category** | **Amount** |")
            message_parts.append("|-------------|------------|")
            message_parts.append(f"| **Estimated Total** | USD {total_budget:.2f} |")
            message_parts.append(f"| **Daily Average** | USD {daily_budget:.2f} |")
            message_parts.append("")
            
            # Travel Preferences
            message_parts.append("## 👤 Your Travel Preferences\n")
            message_parts.append("| **Preference** | **Details** |")
            message_parts.append("|---------------|-------------|")
            
            # Format travel style
            travel_style = "Unknown"
            if hasattr(travel_context, 'activity_preferences') and travel_context.activity_preferences:
                travel_style = ", ".join(travel_context.activity_preferences[:3])
            
            message_parts.append(f"| **Travel Style** | {travel_style} |")
            message_parts.append("| **Pace** | Moderate |")
            message_parts.append(f"| **Group Size** | {travel_context.travelers} |")
            message_parts.append(f"| **Budget Level** | {travel_context.budget_level.title()} |")
            message_parts.append("")
            
            # Additional Notes
            message_parts.append("## 📝 Additional Notes\n")
            message_parts.append("| **Category** | **Details** |")
            message_parts.append("|-------------|-------------|")
            
            # Add weather info if available
            if travel_context.weather_data and not travel_context.weather_data.get("error"):
                message_parts.append("| **Weather** | Check daily forecasts for each day |")
            
            message_parts.append("")
            message_parts.append("---")
            message_parts.append("🎯 **Your trip is ready!** Would you like me to make any adjustments to your itinerary, budget, or preferences?")
            
            return "\n".join(message_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating markdown message: {str(e)}")
            return f"I've planned your trip to {travel_context.destination or 'your destination'}. Please see the trip details below."
    
    def _create_extracted_info(self, travel_context: TravelContext) -> Dict[str, Any]:
        """Create the extracted_info section."""
        return {
            "destination": travel_context.destination,
            "start_date": travel_context.start_date,
            "end_date": travel_context.end_date,
            "duration_days": travel_context.duration,
            "food_preferences": travel_context.food_preferences or [],
            "activities": travel_context.activity_preferences or [],
            "travelers": travel_context.travelers,
            "budget_level": travel_context.budget_level,
            "accommodation_preferences": [],  # Not in current scope
            "transportation_preferences": [],  # Not in current scope
            "other_preferences": travel_context.poi_preferences or []
        }
    
    def _create_trip_details(self, travel_context: TravelContext, trip_id: str) -> Dict[str, Any]:
        """Create the trip_details section."""
        return {
            "user_id": "1",  # Default user ID - would come from auth in real app
            "destination": travel_context.destination,
            "start_date": travel_context.start_date,
            "end_date": travel_context.end_date,
            "duration_days": travel_context.duration,
            "user_profile": self._create_user_profile(travel_context),
            "itinerary": self._format_itinerary_for_output(travel_context),
            "extracted_preferences": self._create_extracted_info(travel_context),
            "status": "planned",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "trip_id": trip_id
        }
    
    def _create_user_profile(self, travel_context: TravelContext) -> Dict[str, Any]:
        """Create the user_profile section."""
        return {
            "user_id": "1",
            "preferences": {
                "travel_style": travel_context.activity_preferences or ["cultural"],
                "pace": "moderate",
                "interests": travel_context.poi_preferences or [],
                "dietary_restrictions": None,
                "accommodation_preferences": None,
                "transport_preferences": None,
                "activity_preferences": travel_context.activity_preferences
            },
            "traveler_info": {
                "group_size": travel_context.travelers,
                "travels_with": ["solo"] if travel_context.travelers == 1 else ["group"],
                "ages": None,
                "accessibility_needs": None
            },
            "budget": {
                "level": travel_context.budget_level,
                "currency": "USD",
                "daily_max": travel_context.daily_average_budget,
                "total_max": travel_context.total_estimated_budget
            }
        }
    
    def _format_itinerary_for_output(self, travel_context: TravelContext) -> List[Dict[str, Any]]:
        """Format the itinerary for the output structure."""
        if not travel_context.proposed_itinerary:
            return []
        
        formatted_itinerary = []
        
        for day in travel_context.proposed_itinerary:
            # Format activities for this day
            formatted_activities = []
            
            for activity in day.get("activities", []):
                formatted_activity = {
                    "id": activity.get("id"),
                    "name": activity.get("name"),
                    "type": activity.get("type"),
                    "description": activity.get("description"),
                    "location": activity.get("location", {}),
                    "start_time": activity.get("start_time"),
                    "end_time": activity.get("end_time"),
                    "duration_minutes": activity.get("duration_minutes"),
                    "cost": activity.get("cost"),
                    "currency": activity.get("currency", "USD"),
                    "booking_url": activity.get("booking_url"),
                    "booking_reference": activity.get("booking_reference"),
                    "rating": activity.get("rating"),
                    "review_count": activity.get("review_count"),
                    "opening_hours": activity.get("opening_hours"),
                    "contact_info": activity.get("contact_info"),
                    "travel_time_from_previous": activity.get("travel_time_from_previous"),
                    "travel_mode": activity.get("travel_mode"),
                    "created_at": activity.get("created_at"),
                    "source": activity.get("source")
                }
                formatted_activities.append(formatted_activity)
            
            # Get weather forecast for this day
            weather_forecast = self._format_weather_forecast(day.get("weather_forecast", {}), travel_context.weather_data)
            
            formatted_day = {
                "day_index": day.get("day_index"),
                "date": day.get("date"),
                "theme": day.get("theme"),
                "status": day.get("status", "pending_confirmation"),
                "activities": formatted_activities,
                "total_cost": day.get("total_cost", 0),
                "total_duration_minutes": day.get("total_duration_minutes", 0),
                "travel_distance_km": day.get("travel_distance_km"),
                "weather_forecast": weather_forecast,
                "special_considerations": day.get("special_considerations"),
                "user_feedback": day.get("user_feedback"),
                "revision_count": day.get("revision_count", 0),
                "created_at": day.get("created_at"),
                "confirmed_at": day.get("confirmed_at")
            }
            
            formatted_itinerary.append(formatted_day)
        
        return formatted_itinerary
    
    def _format_weather_forecast(self, day_weather: Dict[str, Any], full_weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format weather forecast for a day."""
        if not full_weather_data or full_weather_data.get("error"):
            return {}
        
        # Use the full weather data structure from the design document example
        return {
            "location": full_weather_data.get("location", {}),
            "forecast_days": full_weather_data.get("forecast", []),
            "units": full_weather_data.get("units", {
                "temperature": "°C",
                "wind_speed": "m/s",
                "pressure": "hPa",
                "visibility": "m"
            })
        }
    
    def _format_activity_time(self, activity: Dict[str, Any]) -> str:
        """Format activity time for display."""
        start_time = activity.get("start_time")
        if start_time:
            try:
                # Parse ISO format and extract time
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                return dt.strftime("%H:%M")
            except:
                return "TBD"
        return "TBD"
    
    def _format_cost(self, cost: Optional[float]) -> str:
        """Format cost for display."""
        if cost is None or cost <= 0:
            return "Free"
        return f"USD {cost:.2f}" 