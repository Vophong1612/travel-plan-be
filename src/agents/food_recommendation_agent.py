import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class FoodRecommendationAgent(BaseAgent):
    """Agent responsible for discovering restaurants and food experiences."""
    
    def __init__(self):
        super().__init__(
            agent_id="food_recommendation",
            name="Food & Restaurant Discovery",
            description="Recommends restaurants and food experiences using Google Maps",
            tools=["google_maps"]
        )
        
        # Mapping food preferences to search terms and place types
        self.cuisine_mapping = {
            "italian": ["italian_restaurant"],
            "chinese": ["chinese_restaurant"],
            "japanese": ["japanese_restaurant"], 
            "french": ["french_restaurant"],
            "mexican": ["mexican_restaurant"],
            "indian": ["indian_restaurant"],
            "thai": ["thai_restaurant"],
            "american": ["american_restaurant"],
            "mediterranean": ["mediterranean_restaurant"],
            "seafood": ["seafood_restaurant"],
            "vegetarian": ["vegetarian_restaurant"],
            "vegan": ["vegetarian_restaurant"],
            "pizza": ["pizza_restaurant"],
            "sushi": ["sushi_restaurant"],
            "bbq": ["barbecue_restaurant"],
            "steakhouse": ["steak_house"],
            "fast food": ["fast_food_restaurant"],
            "cafe": ["cafe"],
            "bakery": ["bakery"],
            "fine dining": ["fine_dining_restaurant"]
        }
        
        # Meal type classifications
        self.meal_types = {
            "breakfast": ["cafe", "bakery", "breakfast_restaurant"],
            "lunch": ["restaurant", "cafe", "fast_food_restaurant"],
            "dinner": ["restaurant", "fine_dining_restaurant"],
            "snacks": ["cafe", "bakery", "fast_food_restaurant"],
            "dessert": ["bakery", "ice_cream_shop"]
        }
        
        # Budget level price filters
        self.budget_price_filters = {
            "budget": [0, 1, 2],      # $ and $$
            "mid-range": [1, 2, 3],   # $$ and $$$
            "luxury": [3, 4]          # $$$ and $$$$
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an AI assistant specializing in food and restaurant recommendations.
        
        Your tasks:
        1. Discover restaurants that match user food preferences and budget
        2. Find dining options near POIs for convenient meal planning
        3. Include various meal types (breakfast, lunch, dinner) as needed
        4. Use Google Maps to gather ratings, reviews, and pricing information
        5. Consider dietary restrictions and special requirements
        
        Prioritize highly-rated restaurants with good reviews.
        Ensure variety in cuisine types and price ranges within budget constraints.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the food recommendation agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "discover_restaurants":
            return await self._discover_restaurants(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _discover_restaurants(self, content: Dict[str, Any]) -> AgentResponse:
        """Discover restaurants for the travel context."""
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
            
            # Discover restaurants
            restaurants = await self._discover_restaurants_by_preferences(travel_context, latitude, longitude)
            
            # Update travel context
            travel_context.potential_restaurants = restaurants
            
            return self._create_success_response({
                "travel_context": travel_context.__dict__,
                "restaurant_summary": {
                    "restaurants_found": len(restaurants),
                    "top_restaurants": [restaurant.get("name") for restaurant in restaurants[:5]],
                    "cuisine_variety": self._get_cuisine_variety(restaurants),
                    "price_range": self._get_price_range_summary(restaurants)
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error discovering restaurants: {str(e)}")
            return self._create_error_response(f"Failed to discover restaurants: {str(e)}")
    
    async def _discover_restaurants_by_preferences(self, travel_context: TravelContext, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Discover restaurants based on user food preferences."""
        restaurants = []
        
        try:
            # Get restaurant search terms based on preferences
            search_terms = self._get_restaurant_search_terms(travel_context.food_preferences)
            
            # If no specific preferences, use general restaurant search
            if not search_terms:
                search_terms = ["restaurant"]
            
            # Search for restaurants by cuisine/type
            for search_term in search_terms:
                try:
                    # Search for restaurants
                    if search_term in ["restaurant", "cafe", "bakery"]:
                        # Use place type search for general categories
                        places_response = await self.use_tool(
                            "google_maps",
                            action="find_nearby_places",
                            latitude=latitude,
                            longitude=longitude,
                            place_type=search_term,
                            radius=8000  # 8km radius
                        )
                    else:
                        # Use text search for specific cuisines
                        places_response = await self.use_tool(
                            "google_maps",
                            action="search_places",
                            query=f"{search_term} near {travel_context.validated_location_details.get('name')}",
                            location=f"{latitude},{longitude}",
                            radius=8000
                        )
                    
                    if places_response.success:
                        places = places_response.data.get("places", [])
                        for place in places[:8]:  # Top 8 per category
                            restaurant = await self._format_restaurant(place)
                            if restaurant and self._is_suitable_restaurant(restaurant, travel_context):
                                restaurants.append(restaurant)
                
                except Exception as e:
                    self.logger.warning(f"Error searching for {search_term}: {str(e)}")
                    continue
            
            # Add restaurants near POIs if available
            if travel_context.potential_pois:
                poi_restaurants = await self._find_restaurants_near_pois(travel_context)
                restaurants.extend(poi_restaurants)
            
            # Ensure we have variety in meal types
            restaurants = await self._ensure_meal_variety(restaurants, travel_context, latitude, longitude)
            
            # Remove duplicates and sort by rating
            restaurants = self._deduplicate_and_sort(restaurants)
            
            self.logger.info(f"Discovered {len(restaurants)} restaurants")
            return restaurants[:20]  # Limit to top 20
            
        except Exception as e:
            self.logger.error(f"Error discovering restaurants: {str(e)}")
            return []
    
    async def _find_restaurants_near_pois(self, travel_context: TravelContext) -> List[Dict[str, Any]]:
        """Find restaurants near discovered POIs."""
        restaurants = []
        
        try:
            # Take top 3 POIs to find nearby restaurants
            top_pois = travel_context.potential_pois[:3]
            
            for poi in top_pois:
                poi_location = poi.get("location", {})
                poi_lat = poi_location.get("latitude")
                poi_lng = poi_location.get("longitude")
                
                if poi_lat and poi_lng:
                    # Search for restaurants near this POI
                    places_response = await self.use_tool(
                        "google_maps",
                        action="find_nearby_places",
                        latitude=poi_lat,
                        longitude=poi_lng,
                        place_type="restaurant",
                        radius=1000  # 1km around POI
                    )
                    
                    if places_response.success:
                        places = places_response.data.get("places", [])
                        for place in places[:3]:  # Top 3 per POI
                            restaurant = await self._format_restaurant(place)
                            if restaurant and self._is_suitable_restaurant(restaurant, travel_context):
                                restaurants.append(restaurant)
        
        except Exception as e:
            self.logger.warning(f"Error finding restaurants near POIs: {str(e)}")
        
        return restaurants
    
    async def _ensure_meal_variety(self, restaurants: List[Dict[str, Any]], travel_context: TravelContext, latitude: float, longitude: float) -> List[Dict[str, Any]]:
        """Ensure variety in meal types (breakfast, lunch, dinner)."""
        try:
            # Check what meal types we have
            existing_meal_types = set()
            for restaurant in restaurants:
                meal_type = self._classify_meal_type(restaurant)
                if meal_type:
                    existing_meal_types.add(meal_type)
            
            # Ensure we have options for all meal types
            needed_meal_types = {"breakfast", "lunch", "dinner"} - existing_meal_types
            
            for meal_type in needed_meal_types:
                place_types = self.meal_types.get(meal_type, ["restaurant"])
                
                for place_type in place_types:
                    try:
                        places_response = await self.use_tool(
                            "google_maps",
                            action="find_nearby_places",
                            latitude=latitude,
                            longitude=longitude,
                            place_type=place_type,
                            radius=5000  # 5km radius
                        )
                        
                        if places_response.success:
                            places = places_response.data.get("places", [])
                            for place in places[:3]:  # Add a few options
                                restaurant = await self._format_restaurant(place)
                                if restaurant and self._is_suitable_restaurant(restaurant, travel_context):
                                    restaurant["meal_type"] = meal_type  # Tag the meal type
                                    restaurants.append(restaurant)
                                    break  # Just need one good option per type
                    
                    except Exception as e:
                        self.logger.warning(f"Error finding {meal_type} options: {str(e)}")
                        continue
        
        except Exception as e:
            self.logger.warning(f"Error ensuring meal variety: {str(e)}")
        
        return restaurants
    
    async def _format_restaurant(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Format a place into restaurant structure."""
        try:
            # Estimate cost based on price level
            cost = self._estimate_restaurant_cost(place)
            
            # Determine cuisine type
            cuisine_type = self._determine_cuisine_type(place)
            
            formatted_restaurant = {
                "id": place.get("place_id", f"restaurant_{datetime.utcnow().timestamp()}"),
                "name": place.get("name", "Unknown Restaurant"),
                "type": "dining",
                "description": self._generate_restaurant_description(place, cuisine_type),
                "location": {
                    "name": place.get("name", "Unknown Restaurant"),
                    "address": place.get("formatted_address", place.get("vicinity", "")),
                    "latitude": place.get("geometry", {}).get("location", {}).get("lat") or place.get("latitude"),
                    "longitude": place.get("geometry", {}).get("location", {}).get("lng") or place.get("longitude"),
                    "place_id": place.get("place_id"),
                    "country": None,
                    "city": None
                },
                "start_time": None,  # Will be set by itinerary agent
                "end_time": None,
                "duration_minutes": self._estimate_dining_duration(place),
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
                "source": "google_maps",
                "cuisine_type": cuisine_type,
                "price_level": place.get("price_level")
            }
            
            return formatted_restaurant
            
        except Exception as e:
            self.logger.error(f"Error formatting restaurant: {str(e)}")
            return None
    
    def _get_restaurant_search_terms(self, food_preferences: List[str]) -> List[str]:
        """Get search terms based on food preferences."""
        search_terms = set()
        
        for preference in food_preferences:
            pref_lower = preference.lower()
            for cuisine, terms in self.cuisine_mapping.items():
                if cuisine in pref_lower:
                    search_terms.update(terms)
        
        return list(search_terms)
    
    def _is_suitable_restaurant(self, restaurant: Dict[str, Any], travel_context: TravelContext) -> bool:
        """Check if restaurant is suitable for the user."""
        # Basic rating filter
        rating = restaurant.get("rating")
        if rating and rating < 3.0:
            return False
        
        # Price level filter based on budget
        price_level = restaurant.get("price_level")
        if price_level is not None:
            budget_levels = self.budget_price_filters.get(travel_context.budget_level, [1, 2, 3])
            if price_level not in budget_levels:
                return False
        
        # Cost filter as backup
        cost = restaurant.get("cost", 0)
        budget_level = travel_context.budget_level
        
        if budget_level == "budget" and cost > 30:
            return False
        elif budget_level == "luxury" and cost < 25:
            return False
        
        return True
    
    def _deduplicate_and_sort(self, restaurants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and sort by rating."""
        # Remove duplicates by place_id
        seen_ids = set()
        unique_restaurants = []
        
        for restaurant in restaurants:
            place_id = restaurant.get("location", {}).get("place_id")
            if place_id and place_id not in seen_ids:
                seen_ids.add(place_id)
                unique_restaurants.append(restaurant)
            elif not place_id:  # No place_id, check by name
                name = restaurant.get("name", "").lower()
                if name not in [r.get("name", "").lower() for r in unique_restaurants]:
                    unique_restaurants.append(restaurant)
        
        # Sort by rating (descending), then by review count
        unique_restaurants.sort(
            key=lambda x: (x.get("rating", 0), x.get("review_count", 0)), 
            reverse=True
        )
        
        return unique_restaurants
    
    def _estimate_restaurant_cost(self, place: Dict[str, Any]) -> float:
        """Estimate cost per person for a restaurant."""
        price_level = place.get("price_level")
        
        # Base cost estimates by price level
        price_estimates = {
            0: 8,   # Very inexpensive
            1: 15,  # Inexpensive
            2: 25,  # Moderate
            3: 45,  # Expensive
            4: 80   # Very expensive
        }
        
        if price_level is not None:
            return price_estimates.get(price_level, 25)
        
        # Default moderate pricing if no price level
        return 25
    
    def _determine_cuisine_type(self, place: Dict[str, Any]) -> str:
        """Determine cuisine type from place data."""
        place_types = place.get("types", [])
        name = place.get("name", "").lower()
        
        # Check place types first
        cuisine_type_mapping = {
            "chinese_restaurant": "Chinese",
            "italian_restaurant": "Italian",
            "japanese_restaurant": "Japanese",
            "french_restaurant": "French",
            "mexican_restaurant": "Mexican",
            "indian_restaurant": "Indian",
            "thai_restaurant": "Thai",
            "american_restaurant": "American",
            "mediterranean_restaurant": "Mediterranean",
            "seafood_restaurant": "Seafood",
            "pizza_restaurant": "Pizza",
            "sushi_restaurant": "Sushi",
            "barbecue_restaurant": "BBQ",
            "steak_house": "Steakhouse",
            "fast_food_restaurant": "Fast Food",
            "cafe": "Cafe",
            "bakery": "Bakery"
        }
        
        for place_type in place_types:
            if place_type in cuisine_type_mapping:
                return cuisine_type_mapping[place_type]
        
        # Try to infer from name
        name_keywords = {
            "pizza": "Pizza",
            "sushi": "Sushi",
            "chinese": "Chinese",
            "italian": "Italian",
            "mexican": "Mexican",
            "thai": "Thai",
            "indian": "Indian",
            "cafe": "Cafe",
            "bakery": "Bakery"
        }
        
        for keyword, cuisine in name_keywords.items():
            if keyword in name:
                return cuisine
        
        return "International"
    
    def _classify_meal_type(self, restaurant: Dict[str, Any]) -> Optional[str]:
        """Classify restaurant by meal type."""
        name = restaurant.get("name", "").lower()
        cuisine = restaurant.get("cuisine_type", "").lower()
        
        # Breakfast indicators
        if any(word in name for word in ["breakfast", "brunch", "cafe", "bakery", "coffee"]):
            return "breakfast"
        
        if cuisine in ["cafe", "bakery"]:
            return "breakfast"
        
        # Fast food typically good for lunch
        if "fast food" in cuisine.lower():
            return "lunch"
        
        # Fine dining typically dinner
        price_level = restaurant.get("price_level", 2)
        if price_level >= 3:
            return "dinner"
        
        # Default to lunch/dinner
        return "lunch"
    
    def _estimate_dining_duration(self, place: Dict[str, Any]) -> int:
        """Estimate dining duration in minutes."""
        place_types = place.get("types", [])
        price_level = place.get("price_level", 2)
        
        # Fast food or cafes are quicker
        if any(t in place_types for t in ["fast_food_restaurant", "cafe"]):
            return 45
        
        # Fine dining takes longer
        if price_level >= 3:
            return 120
        
        # Regular restaurants
        return 90
    
    def _generate_restaurant_description(self, place: Dict[str, Any], cuisine_type: str) -> str:
        """Generate a description for the restaurant."""
        name = place.get("name", "Unknown Restaurant")
        rating = place.get("rating")
        
        description = f"Enjoy {cuisine_type} cuisine at {name}"
        
        if rating and rating >= 4.5:
            description += ", a highly-rated local favorite"
        elif rating and rating >= 4.0:
            description += ", a well-reviewed restaurant"
        
        return description
    
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
    
    def _get_cuisine_variety(self, restaurants: List[Dict[str, Any]]) -> List[str]:
        """Get list of cuisine types found."""
        cuisines = set()
        for restaurant in restaurants:
            cuisine = restaurant.get("cuisine_type")
            if cuisine:
                cuisines.add(cuisine)
        return list(cuisines)
    
    def _get_price_range_summary(self, restaurants: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get price range summary."""
        price_counts = {"budget": 0, "moderate": 0, "expensive": 0}
        
        for restaurant in restaurants:
            cost = restaurant.get("cost", 0)
            if cost <= 20:
                price_counts["budget"] += 1
            elif cost <= 40:
                price_counts["moderate"] += 1
            else:
                price_counts["expensive"] += 1
        
        return price_counts 