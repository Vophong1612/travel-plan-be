import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class POIActivityAgent(BaseAgent):
    """Agent responsible for discovering Points of Interest and activities."""
    
    def __init__(self):
        super().__init__(
            agent_id="poi_activity",
            name="POI & Activity Discovery",
            description="Identifies and curates relevant Points of Interest and activities using Google Maps",
            tools=["google_maps"]
        )
        
        # Mapping user preferences to Google Maps place types
        self.poi_type_mapping = {
            "museums": ["museum", "art_gallery"],
            "art": ["art_gallery", "museum"],
            "history": ["museum", "historical_site"],
            "historical": ["museum", "historical_site"],
            "landmarks": ["tourist_attraction", "point_of_interest"],
            "parks": ["park", "amusement_park"],
            "nature": ["park", "zoo", "aquarium"],
            "architecture": ["tourist_attraction", "church", "synagogue", "hindu_temple"],
            "culture": ["museum", "art_gallery", "cultural_center"],
            "galleries": ["art_gallery"],
            "monuments": ["tourist_attraction", "cemetery"]
        }
        
        self.activity_type_mapping = {
            "adventure": ["amusement_park", "zoo", "aquarium", "park"],
            "outdoor": ["park", "zoo", "amusement_park"],
            "entertainment": ["amusement_park", "movie_theater", "night_club"],
            "shopping": ["shopping_mall", "clothing_store", "electronics_store"],
            "cultural": ["museum", "art_gallery", "cultural_center"],
            "relaxing": ["spa", "park", "beauty_salon"],
            "sports": ["gym", "stadium"],
            "nightlife": ["bar", "night_club"],
            "music": ["music_venue", "night_club"]
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant specializing in discovering points of interest and activities.
        
        Your tasks:
        1. Identify relevant POIs based on user preferences and validated location
        2. Discover activities suitable for the weather conditions and user interests
        3. Use Google Maps to gather detailed information including ratings, reviews, and hours
        4. Structure data for use by the itinerary generation agent
        
        Consider weather conditions when recommending outdoor vs indoor activities.
        Prioritize highly-rated venues and authentic local experiences.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the POI & activity agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "discover_pois_activities":
            return await self._discover_pois_activities(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _discover_pois_activities(self, content: Dict[str, Any]) -> AgentResponse:
        """Discover POIs and activities for the travel context."""
        try:
            # Get travel context
            travel_context_data = content.get("travel_context")
            if not travel_context_data:
                return self._create_error_response("travel_context is required")
            
            # Recreate TravelContext object
            travel_context = TravelContext(**travel_context_data)
            
            if not travel_context.validated_location_details:
                return self._create_error_response("validated_location_details is required in travel_context")
            
            # Get coordinates for nearby searches
            coordinates = travel_context.validated_location_details.get("coordinates", {})
            latitude = coordinates.get("latitude")
            longitude = coordinates.get("longitude")
            
            if not latitude or not longitude:
                return self._create_error_response("Location coordinates are required")
            
            # Discover POIs
            pois = await self._discover_pois(travel_context, latitude, longitude)
            
            # Discover Activities
            activities = await self._discover_activities(travel_context, latitude, longitude)
            
            # Update travel context
            travel_context.potential_pois = pois
            travel_context.potential_activities = activities
            
            return self._create_success_response({
                "travel_context": travel_context.__dict__,
                "discovery_summary": {
                    "pois_found": len(pois),
                    "activities_found": len(activities),
                    "top_pois": [poi.get("name") for poi in pois[:3]],
                    "top_activities": [activity.get("name") for activity in activities[:3]]
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error discovering POIs and activities: {str(e)}")
            return self._create_error_response(f"Failed to discover POIs and activities: {str(e)}")
    
    async def _discover_pois(self, travel_context: TravelContext, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Discover Points of Interest based on user preferences."""
        pois = []
        
        try:
            # Get place types to search for based on user preferences
            place_types = self._get_poi_place_types(travel_context.poi_preferences)
            
            # If no specific preferences, use default popular tourist attractions
            if not place_types:
                place_types = ["tourist_attraction", "museum", "park"]
            
            # Search for each place type
            for place_type in place_types:
                try:
                    places_response = await self.use_tool(
                        "google_maps",
                        action="find_nearby_places",
                        latitude=latitude,
                        longitude=longitude,
                        place_type=place_type,
                        radius=10000  # 10km radius
                    )
                    
                    if places_response.success:
                        places = places_response.data.get("places", [])
                        for place in places[:5]:  # Top 5 per category
                            poi = await self._format_poi(place, "poi")
                            if poi and self._is_suitable_poi(poi, travel_context):
                                pois.append(poi)
                
                except Exception as e:
                    self.logger.warning(f"Error searching for {place_type}: {str(e)}")
                    continue
            
            # Remove duplicates and sort by rating
            pois = self._deduplicate_and_sort(pois)
            
            self.logger.info(f"Discovered {len(pois)} POIs")
            return pois[:15]  # Limit to top 15
            
        except Exception as e:
            self.logger.error(f"Error discovering POIs: {str(e)}")
            return []
    
    async def _discover_activities(self, travel_context: TravelContext, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Discover activities based on user preferences and weather."""
        activities = []
        
        try:
            # Get place types for activities
            place_types = self._get_activity_place_types(travel_context.activity_preferences)
            
            # Consider weather conditions
            weather_data = travel_context.weather_data or {}
            if self._is_bad_weather(weather_data):
                # Filter out outdoor activities in bad weather
                place_types = [pt for pt in place_types if pt not in ["park", "amusement_park", "zoo"]]
                # Add indoor alternatives
                place_types.extend(["shopping_mall", "museum", "movie_theater"])
            
            # If no specific preferences, use defaults
            if not place_types:
                place_types = ["amusement_park", "shopping_mall", "spa"]
            
            # Search for each place type
            for place_type in place_types:
                try:
                    places_response = await self.use_tool(
                        "google_maps",
                        action="find_nearby_places",
                        latitude=latitude,
                        longitude=longitude,
                        place_type=place_type,
                        radius=15000  # 15km radius for activities
                    )
                    
                    if places_response.success:
                        places = places_response.data.get("places", [])
                        for place in places[:5]:  # Top 5 per category
                            activity = await self._format_poi(place, "activity")
                            if activity and self._is_suitable_activity(activity, travel_context):
                                activities.append(activity)
                
                except Exception as e:
                    self.logger.warning(f"Error searching for {place_type} activities: {str(e)}")
                    continue
            
            # Remove duplicates and sort by rating
            activities = self._deduplicate_and_sort(activities)
            
            self.logger.info(f"Discovered {len(activities)} activities")
            return activities[:10]  # Limit to top 10
            
        except Exception as e:
            self.logger.error(f"Error discovering activities: {str(e)}")
            return []
    
    async def _format_poi(self, place: Dict[str, Any], poi_type: str) -> Optional[Dict[str, Any]]:
        """Format a place into POI/activity structure."""
        try:
            # Estimate cost based on place type and price level
            cost = self._estimate_cost(place, poi_type)
            
            # Determine activity type
            activity_type = self._determine_activity_type(place, poi_type)
            
            formatted_poi = {
                "id": place.get("place_id", f"{poi_type}_{datetime.utcnow().timestamp()}"),
                "name": place.get("name", "Unknown"),
                "type": activity_type,
                "description": self._generate_description(place),
                "location": {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("formatted_address", place.get("vicinity", "")),
                    "latitude": place.get("geometry", {}).get("location", {}).get("lat") or place.get("latitude"),
                    "longitude": place.get("geometry", {}).get("location", {}).get("lng") or place.get("longitude"),
                    "place_id": place.get("place_id"),
                    "country": None,  # Could be extracted from address components
                    "city": None
                },
                "start_time": None,  # Will be set by itinerary agent
                "end_time": None,
                "duration_minutes": self._estimate_duration(place, activity_type),
                "cost": cost,
                "currency": "USD",
                "booking_url": None,
                "booking_reference": None,
                "rating": place.get("rating"),
                "review_count": place.get("user_ratings_total"),
                "opening_hours": self._format_opening_hours(place.get("opening_hours")),
                "contact_info": self._extract_contact_info(place),
                "travel_time_from_previous": None,  # Will be calculated by itinerary agent
                "travel_mode": None,
                "created_at": datetime.utcnow().isoformat(),
                "source": "google_maps"
            }
            
            return formatted_poi
            
        except Exception as e:
            self.logger.error(f"Error formatting POI: {str(e)}")
            return None
    
    def _get_poi_place_types(self, poi_preferences: List[str]) -> List[str]:
        """Get Google Maps place types for POI preferences."""
        place_types = set()
        
        for preference in poi_preferences:
            pref_lower = preference.lower()
            for keyword, types in self.poi_type_mapping.items():
                if keyword in pref_lower:
                    place_types.update(types)
        
        return list(place_types)
    
    def _get_activity_place_types(self, activity_preferences: List[str]) -> List[str]:
        """Get Google Maps place types for activity preferences."""
        place_types = set()
        
        for preference in activity_preferences:
            pref_lower = preference.lower()
            for keyword, types in self.activity_type_mapping.items():
                if keyword in pref_lower:
                    place_types.update(types)
        
        return list(place_types)
    
    def _is_bad_weather(self, weather_data: Dict[str, Any]) -> bool:
        """Check if weather conditions are bad for outdoor activities."""
        if weather_data.get("error"):
            return False  # Unknown weather, don't filter
        
        # Check current weather
        current = weather_data.get("current_weather", {})
        condition = current.get("condition", "").lower()
        
        if "rain" in condition or "storm" in condition or "snow" in condition:
            return True
        
        # Check forecast
        forecast = weather_data.get("forecast", [])
        if forecast:
            # Check first day of forecast
            first_day = forecast[0]
            weather_info = first_day.get("weather", [])
            if weather_info:
                main_condition = weather_info[0].get("main", "").lower()
                if "rain" in main_condition or "storm" in main_condition:
                    return True
        
        return False
    
    def _is_suitable_poi(self, poi: Dict[str, Any], travel_context: TravelContext) -> bool:
        """Check if POI is suitable for the user."""
        # Basic rating filter
        rating = poi.get("rating")
        if rating and rating < 3.5:
            return False
        
        # Budget filter
        cost = poi.get("cost", 0)
        budget_level = travel_context.budget_level
        
        if budget_level == "budget" and cost > 25:
            return False
        elif budget_level == "luxury" and cost < 10:
            return False
        
        return True
    
    def _is_suitable_activity(self, activity: Dict[str, Any], travel_context: TravelContext) -> bool:
        """Check if activity is suitable for the user."""
        # Basic rating filter
        rating = activity.get("rating")
        if rating and rating < 3.0:
            return False
        
        # Budget filter
        cost = activity.get("cost", 0)
        budget_level = travel_context.budget_level
        
        if budget_level == "budget" and cost > 40:
            return False
        elif budget_level == "luxury" and cost < 20:
            return False
        
        return True
    
    def _deduplicate_and_sort(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and sort by rating."""
        # Remove duplicates by place_id
        seen_ids = set()
        unique_items = []
        
        for item in items:
            place_id = item.get("location", {}).get("place_id")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_items.append(item)
            elif not place_id:  # No place_id, check by name
                name = item.get("name", "").lower()
                if name not in [i.get("name", "").lower() for i in unique_items]:
                    unique_items.append(item)
        
        # Sort by rating (descending)
        unique_items.sort(key=lambda x: x.get("rating", 0), reverse=True)
        
        return unique_items
    
    def _estimate_cost(self, place: Dict[str, Any], poi_type: str) -> float:
        """Estimate cost for a place."""
        price_level = place.get("price_level")
        
        # Base estimates by type
        base_costs = {
            "poi": {"museum": 15, "park": 0, "tourist_attraction": 10},
            "activity": {"amusement_park": 35, "shopping_mall": 0, "spa": 50}
        }
        
        # Get place types
        place_types = place.get("types", [])
        
        # Find matching type
        cost = 0
        for place_type in place_types:
            if place_type in base_costs.get(poi_type, {}):
                cost = base_costs[poi_type][place_type]
                break
        
        # Adjust by price level if available
        if price_level is not None:
            multipliers = {0: 0, 1: 0.5, 2: 1.0, 3: 1.5, 4: 2.0}
            cost *= multipliers.get(price_level, 1.0)
        
        return cost
    
    def _determine_activity_type(self, place: Dict[str, Any], poi_type: str) -> str:
        """Determine activity type from place data."""
        place_types = place.get("types", [])
        
        # Map Google place types to our activity types
        type_mapping = {
            "museum": "cultural",
            "art_gallery": "cultural",
            "park": "outdoor",
            "amusement_park": "entertainment",
            "shopping_mall": "shopping",
            "restaurant": "dining",
            "tourist_attraction": "sightseeing",
            "spa": "entertainment",
            "zoo": "outdoor",
            "aquarium": "cultural"
        }
        
        for place_type in place_types:
            if place_type in type_mapping:
                return type_mapping[place_type]
        
        # Default based on poi_type
        return "sightseeing" if poi_type == "poi" else "entertainment"
    
    def _estimate_duration(self, place: Dict[str, Any], activity_type: str) -> int:
        """Estimate duration in minutes for an activity."""
        duration_map = {
            "cultural": 120,    # 2 hours for museums
            "sightseeing": 90,  # 1.5 hours for attractions
            "outdoor": 180,     # 3 hours for parks
            "entertainment": 150, # 2.5 hours for entertainment
            "shopping": 120,    # 2 hours for shopping
            "dining": 90        # 1.5 hours for dining
        }
        
        return duration_map.get(activity_type, 120)
    
    def _generate_description(self, place: Dict[str, Any]) -> str:
        """Generate a description for the place."""
        name = place.get("name", "Unknown")
        types = place.get("types", [])
        
        if "museum" in types:
            return f"Explore {name}, a cultural institution with exhibits and collections"
        elif "park" in types:
            return f"Enjoy outdoor time at {name}, a beautiful park area"
        elif "tourist_attraction" in types:
            return f"Visit {name}, a popular tourist destination"
        else:
            return f"Experience {name}"
    
    def _format_opening_hours(self, opening_hours: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Format opening hours data."""
        if not opening_hours:
            return None
        
        return {
            "open_now": opening_hours.get("open_now"),
            "periods": opening_hours.get("periods", []),
            "weekday_text": opening_hours.get("weekday_text", [])
        }
    
    def _extract_contact_info(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract contact information from place data."""
        contact_info = {}
        
        if place.get("formatted_phone_number"):
            contact_info["phone"] = place["formatted_phone_number"]
        
        if place.get("website"):
            contact_info["website"] = place["website"]
        
        return contact_info if contact_info else None 