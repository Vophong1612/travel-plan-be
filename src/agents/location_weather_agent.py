import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class LocationWeatherAgent(BaseAgent):
    """Agent responsible for validating destinations and retrieving weather data."""
    
    def __init__(self):
        super().__init__(
            agent_id="location_weather",
            name="Location & Weather Validator",
            description="Validates destination using Google Maps and retrieves weather forecasts",
            tools=["google_maps", "weather"]
        )
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant responsible for validating locations and retrieving weather data.
        
        Your tasks:
        1. Validate the destination using Google Maps to get precise coordinates and official name
        2. Retrieve detailed weather forecast for the destination and travel dates
        3. Enrich the travel context with validated location details and weather data
        
        Use real-time data from your tools to provide accurate, up-to-date information.
        Always validate location coordinates before retrieving weather data.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the location & weather agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "validate_and_enrich":
            return await self._validate_and_enrich(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _validate_and_enrich(self, content: Dict[str, Any]) -> AgentResponse:
        """Validate location and enrich with weather data."""
        try:
            # Get travel context
            travel_context_data = content.get("travel_context")
            if not travel_context_data:
                return self._create_error_response("travel_context is required")
            
            # Recreate TravelContext object
            travel_context = TravelContext(**travel_context_data)
            
            if not travel_context.destination:
                return self._create_error_response("destination is required in travel_context")
            
            # Step 1: Validate destination using Google Maps
            location_details = await self._validate_destination(travel_context.destination)
            if not location_details:
                return self._create_error_response(f"Could not validate destination: {travel_context.destination}")
            
            # Step 2: Get weather data
            weather_data = await self._get_weather_data(
                location_details, 
                travel_context.start_date, 
                travel_context.duration
            )
            
            # Step 3: Update travel context
            travel_context.validated_location_details = location_details
            travel_context.weather_data = weather_data
            
            return self._create_success_response({
                "travel_context": travel_context.__dict__,
                "location_validation": {
                    "validated": True,
                    "original_query": travel_context.destination,
                    "validated_name": location_details.get("name"),
                    "coordinates": location_details.get("coordinates")
                },
                "weather_summary": self._generate_weather_summary(weather_data)
            })
            
        except Exception as e:
            self.logger.error(f"Error validating and enriching: {str(e)}")
            return self._create_error_response(f"Failed to validate and enrich: {str(e)}")
    
    async def _validate_destination(self, destination: str) -> Optional[Dict[str, Any]]:
        """Validate destination using Google Maps API."""
        try:
            # Search for the destination
            search_response = await self.use_tool(
                "google_maps",
                action="search_location",
                query=destination
            )
            
            if not search_response.success:
                self.logger.warning(f"Google Maps search failed: {search_response.error}")
                return None
            
            locations = search_response.data.get("locations", [])
            if not locations:
                self.logger.warning(f"No locations found for: {destination}")
                return None
            
            # Take the first (most relevant) result
            location = locations[0]
            
            # Extract and structure location details
            location_details = {
                "name": location.get("name", destination),
                "formatted_address": location.get("formatted_address", ""),
                "coordinates": {
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude")
                },
                "place_id": location.get("place_id"),
                "types": location.get("types", []),
                "country": self._extract_country(location.get("address_components", [])),
                "city": self._extract_city(location.get("address_components", []))
            }
            
            self.logger.info(f"Successfully validated destination: {location_details['name']}")
            return location_details
            
        except Exception as e:
            self.logger.error(f"Error validating destination: {str(e)}")
            return None
    
    async def _get_weather_data(self, location_details: Dict[str, Any], start_date: str, duration: int) -> Dict[str, Any]:
        """Get weather data for the location and dates."""
        try:
            coordinates = location_details.get("coordinates", {})
            latitude = coordinates.get("latitude")
            longitude = coordinates.get("longitude")
            
            if not latitude or not longitude:
                self.logger.warning("No coordinates available for weather data")
                return {"error": "No coordinates available"}
            
            # Calculate how many days ahead the trip starts
            if start_date:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                days_ahead = (start - date.today()).days
            else:
                days_ahead = 30  # Default
            
            # Get weather forecast
            if days_ahead < 0:
                # Trip is in the past, get current weather only
                weather_response = await self.use_tool(
                    "weather",
                    action="current_weather",
                    location=f"{latitude},{longitude}"
                )
            else:
                # Get forecast for the trip period
                weather_response = await self.use_tool(
                    "weather",
                    action="weather_forecast",
                    location=f"{latitude},{longitude}",
                    days=min(days_ahead + duration, 16)  # API limits
                )
            
            if weather_response.success:
                weather_data = weather_response.data
                
                # Enrich weather data with location information
                weather_data["location"] = {
                    "name": location_details.get("name"),
                    "latitude": latitude,
                    "longitude": longitude,
                    "country": location_details.get("country"),
                    "city": location_details.get("city")
                }
                
                # Add travel-specific insights
                weather_data["travel_insights"] = self._generate_travel_insights(weather_data, duration)
                
                return weather_data
            else:
                self.logger.warning(f"Weather API failed: {weather_response.error}")
                return {"error": f"Weather data unavailable: {weather_response.error}"}
                
        except Exception as e:
            self.logger.error(f"Error getting weather data: {str(e)}")
            return {"error": str(e)}
    
    def _extract_country(self, address_components: List[Dict[str, Any]]) -> Optional[str]:
        """Extract country from Google Maps address components."""
        for component in address_components:
            if "country" in component.get("types", []):
                return component.get("long_name")
        return None
    
    def _extract_city(self, address_components: List[Dict[str, Any]]) -> Optional[str]:
        """Extract city from Google Maps address components."""
        for component in address_components:
            types = component.get("types", [])
            if "locality" in types or "administrative_area_level_1" in types:
                return component.get("long_name")
        return None
    
    def _generate_weather_summary(self, weather_data: Dict[str, Any]) -> str:
        """Generate a human-readable weather summary."""
        if weather_data.get("error"):
            return f"Weather data unavailable: {weather_data['error']}"
        
        try:
            current = weather_data.get("current_weather", {})
            forecast = weather_data.get("forecast", [])
            
            if current:
                temp = current.get("temperature", "N/A")
                condition = current.get("condition", "").title()
                summary = f"Current: {temp}°C, {condition}"
            else:
                summary = "Current weather unavailable"
            
            if forecast:
                avg_temp = sum(day.get("temperature", {}).get("max", 0) for day in forecast[:3]) / min(len(forecast), 3)
                summary += f". Expected average: {avg_temp:.1f}°C for trip period"
            
            return summary
            
        except Exception as e:
            return f"Weather summary generation failed: {str(e)}"
    
    def _generate_travel_insights(self, weather_data: Dict[str, Any], duration: int) -> Dict[str, Any]:
        """Generate travel-specific weather insights."""
        insights = {
            "clothing_recommendations": [],
            "activity_suggestions": [],
            "weather_alerts": []
        }
        
        try:
            forecast = weather_data.get("forecast", [])
            if not forecast:
                return insights
            
            # Analyze temperature range
            temps = []
            conditions = []
            precipitation_days = 0
            
            for day in forecast[:duration]:
                temp_data = day.get("temperature", {})
                if temp_data.get("max"):
                    temps.append(temp_data["max"])
                if temp_data.get("min"):
                    temps.append(temp_data["min"])
                
                weather_info = day.get("weather", [])
                if weather_info:
                    condition = weather_info[0].get("main", "").lower()
                    conditions.append(condition)
                    if "rain" in condition or "snow" in condition:
                        precipitation_days += 1
            
            # Generate clothing recommendations
            if temps:
                max_temp = max(temps)
                min_temp = min(temps)
                
                if max_temp > 25:
                    insights["clothing_recommendations"].append("Light, breathable clothing")
                if min_temp < 10:
                    insights["clothing_recommendations"].append("Warm layers and jacket")
                if precipitation_days > 0:
                    insights["clothing_recommendations"].append("Waterproof jacket or umbrella")
            
            # Generate activity suggestions
            if precipitation_days > duration / 2:
                insights["activity_suggestions"].append("Plan indoor activities")
            else:
                insights["activity_suggestions"].append("Great weather for outdoor exploration")
            
            # Weather alerts
            if precipitation_days > 0:
                insights["weather_alerts"].append(f"Expect rain on {precipitation_days} out of {duration} days")
            
        except Exception as e:
            insights["error"] = f"Could not generate insights: {str(e)}"
        
        return insights 