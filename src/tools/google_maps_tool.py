import googlemaps
import requests
import base64
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import os
from src.tools.base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError
from src.config.settings import settings
from src.models.trip import Location


class GoogleMapsTool(BaseMCPTool):
    """
    Comprehensive Google Maps Platform MCP tool supporting:
    - Maps APIs (Places, Geocoding, Routes, Distance Matrix)
    - Environment APIs (Air Quality, Pollen, Solar)
    - Utility APIs (Time Zone, Elevation, Address Validation)
    - Static Maps and Street View
    """
    
    def __init__(self):
        super().__init__(
            name="google_maps",
            description="Comprehensive Google Maps Platform integration for location services, routing, places, and environmental data"
        )
        
        # Get API key from environment or settings
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY") or settings.get("GOOGLE_MAPS_API_KEY")
        
        if not self.api_key:
            self.logger.warning("Google Maps API key not found. Set GOOGLE_MAPS_API_KEY environment variable.")
        
        # Initialize Google Maps client
        self.gmaps = googlemaps.Client(key=self.api_key) if self.api_key else None
        
        # Base URLs for different APIs
        self.base_urls = {
            "places": "https://maps.googleapis.com/maps/api/place",
            "geocoding": "https://maps.googleapis.com/maps/api/geocode",
            "directions": "https://maps.googleapis.com/maps/api/directions",
            "distance_matrix": "https://maps.googleapis.com/maps/api/distancematrix",
            "elevation": "https://maps.googleapis.com/maps/api/elevation",
            "timezone": "https://maps.googleapis.com/maps/api/timezone",
            "static_maps": "https://maps.googleapis.com/maps/api/staticmap",
            "street_view": "https://maps.googleapis.com/maps/api/streetview",
            "address_validation": "https://addressvalidation.googleapis.com/v1:validateAddress",
            "air_quality": "https://airquality.googleapis.com/v1/currentConditions:lookup",
            "pollen": "https://pollen.googleapis.com/v1/forecast:lookup",
            "solar": "https://solar.googleapis.com/v1/buildingInsights:findClosest"
        }
        
        # Request session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Travel-Planner/1.0'
        })
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's comprehensive parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        # Core Location Services
                        "search_location", "geocode", "reverse_geocode", "address_validation",
                        
                        # Places API
                        "search_places", "find_nearby_places", "place_details", "place_photos",
                        "place_reviews", "place_autocomplete",
                        
                        # Routes & Navigation
                        "calculate_route", "calculate_travel_time", "optimize_route",
                        "distance_matrix", "snap_to_roads",
                        
                        # Geographic Data
                        "get_elevation", "get_timezone", "get_country_info",
                        
                        # Maps & Imagery
                        "generate_static_map", "get_street_view", "get_map_tile",
                        
                        # Environment APIs
                        "get_air_quality", "get_pollen_data", "get_solar_data"
                    ],
                    "description": "The Google Maps Platform action to perform"
                },
                
                # Location Parameters
                "query": {
                    "type": "string",
                    "description": "Search query for location or place name"
                },
                "address": {
                    "type": "string",
                    "description": "Address to validate or geocode"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate (-90 to 90)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate (-180 to 180)"
                },
                "place_id": {
                    "type": "string",
                    "description": "Google Places ID for specific place operations"
                },
                
                # Route Parameters
                "origin": {
                    "type": "string",
                    "description": "Origin location for routing"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location for routing"
                },
                "waypoints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of waypoints for routing"
                },
                "travel_mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "description": "Mode of transportation (default: driving)",
                    "default": "driving"
                },
                "route_preferences": {
                    "type": "string",
                    "enum": ["TRAFFIC_UNAWARE", "TRAFFIC_AWARE", "TRAFFIC_AWARE_OPTIMAL"],
                    "description": "Route calculation preferences",
                    "default": "TRAFFIC_AWARE"
                },
                "avoid": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["tolls", "highways", "ferries", "indoor"]
                    },
                    "description": "Route restrictions to avoid"
                },
                
                # Search Parameters
                "radius": {
                    "type": "integer",
                    "description": "Search radius in meters (default: 1000, max: 50000)",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 50000
                },
                "place_type": {
                    "type": "string",
                    "description": "Type of place to search for (restaurant, lodging, tourist_attraction, etc.)"
                },
                "keyword": {
                    "type": "string",
                    "description": "Keyword to match against place names and types"
                },
                "min_price": {
                    "type": "integer",
                    "description": "Minimum price level (0-4)",
                    "minimum": 0,
                    "maximum": 4
                },
                "max_price": {
                    "type": "integer",
                    "description": "Maximum price level (0-4)",
                    "minimum": 0,
                    "maximum": 4
                },
                "open_now": {
                    "type": "boolean",
                    "description": "Return only places that are open now"
                },
                
                # Map Parameters
                "map_size": {
                    "type": "string",
                    "description": "Map size for static maps (e.g., 640x640)",
                    "default": "640x640"
                },
                "zoom": {
                    "type": "integer",
                    "description": "Map zoom level (1-20)",
                    "default": 13,
                    "minimum": 1,
                    "maximum": 20
                },
                "map_type": {
                    "type": "string",
                    "enum": ["roadmap", "satellite", "terrain", "hybrid"],
                    "description": "Map type for static maps",
                    "default": "roadmap"
                },
                "markers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Markers to add to static map"
                },
                
                # General Parameters
                "language": {
                    "type": "string",
                    "description": "Language code for results (default: en)",
                    "default": "en"
                },
                "region": {
                    "type": "string",
                    "description": "Region code for biasing results (default: us)",
                    "default": "us"
                },
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial"],
                    "description": "Units for distance/speed (default: metric)",
                    "default": "metric"
                },
                "include_air_quality": {
                    "type": "boolean",
                    "description": "Include air quality data when available",
                    "default": False
                },
                "include_pollen": {
                    "type": "boolean",
                    "description": "Include pollen data when available",
                    "default": False
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific fields to return for place details"
                }
            },
            "required": ["action"]
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters for the specific action."""
        if not self.api_key:
            return False
            
        action = params.get("action")
        
        # Core location validation
        location_actions = ["search_location", "geocode", "address_validation"]
        if action in location_actions:
            return "query" in params or "address" in params
        
        # Coordinate-based actions
        coordinate_actions = ["reverse_geocode", "get_elevation", "get_timezone", "get_air_quality", "get_pollen_data"]
        if action in coordinate_actions:
            return "latitude" in params and "longitude" in params
        
        # Place-based actions
        place_actions = ["place_details", "place_photos", "place_reviews"]
        if action in place_actions:
            return "place_id" in params
        
        # Route-based actions
        route_actions = ["calculate_route", "calculate_travel_time", "distance_matrix"]
        if action in route_actions:
            return "origin" in params and "destination" in params
        
        # Search-based actions
        search_actions = ["search_places", "find_nearby_places", "place_autocomplete"]
        if action in search_actions:
            return ("latitude" in params and "longitude" in params) or "query" in params
        
        # Map generation actions
        map_actions = ["generate_static_map", "get_street_view"]
        if action in map_actions:
            return ("latitude" in params and "longitude" in params) or "query" in params
        
        return True
    
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the Google Maps Platform tool."""
        try:
            if not self.api_key:
                return self._handle_error("Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY environment variable.")
            
            action = kwargs.get("action")
            
            # Core Location Services
            if action == "search_location":
                return await self._search_location(kwargs)
            elif action == "geocode":
                return await self._geocode(kwargs)
            elif action == "reverse_geocode":
                return await self._reverse_geocode(kwargs)
            elif action == "address_validation":
                return await self._validate_address(kwargs)
            
            # Places API
            elif action == "search_places":
                return await self._search_places(kwargs)
            elif action == "find_nearby_places":
                return await self._find_nearby_places(kwargs)
            elif action == "place_details":
                return await self._get_place_details(kwargs)
            elif action == "place_photos":
                return await self._get_place_photos(kwargs)
            elif action == "place_reviews":
                return await self._get_place_reviews(kwargs)
            elif action == "place_autocomplete":
                return await self._place_autocomplete(kwargs)
            
            # Routes & Navigation
            elif action == "calculate_route":
                return await self._calculate_route(kwargs)
            elif action == "calculate_travel_time":
                return await self._calculate_travel_time(kwargs)
            elif action == "optimize_route":
                return await self._optimize_route(kwargs)
            elif action == "distance_matrix":
                return await self._distance_matrix(kwargs)
            elif action == "snap_to_roads":
                return await self._snap_to_roads(kwargs)
            
            # Geographic Data
            elif action == "get_elevation":
                return await self._get_elevation(kwargs)
            elif action == "get_timezone":
                return await self._get_timezone(kwargs)
            elif action == "get_country_info":
                return await self._get_country_info(kwargs)
            
            # Maps & Imagery
            elif action == "generate_static_map":
                return await self._generate_static_map(kwargs)
            elif action == "get_street_view":
                return await self._get_street_view(kwargs)
            elif action == "get_map_tile":
                return await self._get_map_tile(kwargs)
            
            # Environment APIs
            elif action == "get_air_quality":
                return await self._get_air_quality(kwargs)
            elif action == "get_pollen_data":
                return await self._get_pollen_data(kwargs)
            elif action == "get_solar_data":
                return await self._get_solar_data(kwargs)
            
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            return self._handle_error(f"Google Maps Platform error: {str(e)}")
    
    # Core Location Services
    
    async def _search_location(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Search for locations using Places API Text Search."""
        try:
            query = params.get("query", params.get("address", ""))
            language = params.get("language", "en")
            region = params.get("region", "us")
            
            places_result = self.gmaps.places(
                query=query,
                language=language,
                region=region
            )
            
            locations = []
            for place in places_result.get("results", []):
                location = self._format_place_result(place)
                locations.append(location)
            
            return self._handle_success({
                "query": query,
                "locations": locations,
                "total_results": len(locations)
            })
            
        except Exception as e:
            return self._handle_error(f"Location search failed: {str(e)}")
    
    async def _geocode(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Convert address to coordinates using Geocoding API."""
        try:
            query = params.get("query", params.get("address", ""))
            language = params.get("language", "en")
            region = params.get("region", "us")
            
            geocode_result = self.gmaps.geocode(
                query, 
                language=language,
                region=region
            )
            
            if not geocode_result:
                return self._handle_error("Location not found")
            
            locations = []
            for result in geocode_result:
                location = self._format_geocoding_result(result)
                locations.append(location)
            
            return self._handle_success({
                "query": query,
                "locations": locations,
                "total_results": len(locations)
            })
            
        except Exception as e:
            return self._handle_error(f"Geocoding failed: {str(e)}")
    
    async def _reverse_geocode(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Convert coordinates to address using Reverse Geocoding API."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            language = params.get("language", "en")
            
            reverse_geocode_result = self.gmaps.reverse_geocode(
                (latitude, longitude),
                language=language
            )
            
            if not reverse_geocode_result:
                return self._handle_error("No address found for coordinates")
            
            addresses = []
            for result in reverse_geocode_result:
                address = self._format_geocoding_result(result)
                addresses.append(address)
            
            return self._handle_success({
                "latitude": latitude,
                "longitude": longitude,
                "addresses": addresses,
                "total_results": len(addresses)
            })
            
        except Exception as e:
            return self._handle_error(f"Reverse geocoding failed: {str(e)}")
    
    async def _validate_address(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Validate and standardize address using Address Validation API."""
        try:
            address = params.get("address", params.get("query", ""))
            
            # Use Address Validation API
            payload = {
                "address": {
                    "addressLines": [address]
                },
                "enableUspsCass": True
            }
            
            response = await self._make_request(
                "POST", 
                self.base_urls["address_validation"],
                json=payload
            )
            
            if "result" in response:
                result = response["result"]
                
                return self._handle_success({
                    "original_address": address,
                    "validated_address": result.get("address", {}),
                    "validation_result": result.get("verdict", {}),
                    "geocode": result.get("geocode", {}),
                    "usps_data": result.get("uspsData", {})
                })
            else:
                return self._handle_error("Address validation failed")
            
        except Exception as e:
            return self._handle_error(f"Address validation failed: {str(e)}")
    
    # Places API
    
    async def _search_places(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Search for places using Places API."""
        try:
            query = params.get("query", "")
            place_type = params.get("place_type")
            language = params.get("language", "en")
            region = params.get("region", "us")
            
            # Use Places Text Search
            search_params = {
                "query": query,
                "language": language,
                "region": region
            }
            
            if place_type:
                search_params["type"] = place_type
            
            places_result = self.gmaps.places(**search_params)
            
            places = []
            for place in places_result.get("results", []):
                place_info = self._format_place_result(place)
                places.append(place_info)
            
            return self._handle_success({
                "query": query,
                "place_type": place_type,
                "places": places,
                "total_results": len(places)
            })
            
        except Exception as e:
            return self._handle_error(f"Places search failed: {str(e)}")
    
    async def _find_nearby_places(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Find nearby places using Places API Nearby Search."""
        try:
            # Get location coordinates
            location = await self._get_location_coordinates(params)
            if not location:
                return self._handle_error("Could not determine location")
            
            radius = params.get("radius", 1000)
            place_type = params.get("place_type")
            keyword = params.get("keyword")
            language = params.get("language", "en")
            open_now = params.get("open_now", False)
            min_price = params.get("min_price")
            max_price = params.get("max_price")
            
            # Search for nearby places
            search_params = {
                "location": location,
                "radius": radius,
                "language": language
            }
            
            if place_type:
                search_params["type"] = place_type
            if keyword:
                search_params["keyword"] = keyword
            if open_now:
                search_params["open_now"] = True
            if min_price is not None:
                search_params["min_price"] = min_price
            if max_price is not None:
                search_params["max_price"] = max_price
            
            places_result = self.gmaps.places_nearby(**search_params)
            
            places = []
            for place in places_result.get("results", []):
                place_info = self._format_place_result(place)
                places.append(place_info)
            
            return self._handle_success({
                "location": {
                    "latitude": location[0],
                    "longitude": location[1]
                },
                "radius": radius,
                "place_type": place_type,
                "keyword": keyword,
                "places": places,
                "total_results": len(places)
            })
            
        except Exception as e:
            return self._handle_error(f"Nearby places search failed: {str(e)}")
    
    async def _get_place_details(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get detailed information about a place."""
        try:
            place_id = params["place_id"]
            language = params.get("language", "en")
            fields = params.get("fields", [
                "name", "formatted_address", "geometry", "rating", "user_ratings_total",
                "price_level", "type", "opening_hours", "formatted_phone_number",
                "website", "reviews", "photo"
            ])
            
            place_details = self.gmaps.place(
                place_id=place_id,
                language=language,
                fields=fields
            )
            
            if "result" in place_details:
                place_info = self._format_place_details(place_details["result"])
                
                return self._handle_success({
                    "place_id": place_id,
                    "place_details": place_info
                })
            else:
                return self._handle_error("Place details not found")
            
        except Exception as e:
            return self._handle_error(f"Place details failed: {str(e)}")
    
    async def _get_place_photos(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get photos for a place."""
        try:
            place_id = params["place_id"]
            
            # First get place details to get photo references
            place_details = self.gmaps.place(
                place_id=place_id,
                fields=["photo"]
            )
            
            if "result" not in place_details or "photos" not in place_details["result"]:
                return self._handle_error("No photos found for this place")
            
            photos = []
            for photo in place_details["result"]["photos"]:
                photo_reference = photo["photo_reference"]
                
                # Generate photo URL
                photo_url = f"{self.base_urls['places']}/photo?photoreference={photo_reference}&maxwidth=800&key={self.api_key}"
                
                photos.append({
                    "photo_reference": photo_reference,
                    "width": photo.get("width", 800),
                    "height": photo.get("height", 600),
                    "photo_url": photo_url,
                    "attributions": photo.get("html_attributions", [])
                })
            
            return self._handle_success({
                "place_id": place_id,
                "photos": photos,
                "total_photos": len(photos)
            })
            
        except Exception as e:
            return self._handle_error(f"Place photos failed: {str(e)}")
    
    async def _get_place_reviews(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get reviews for a place."""
        try:
            place_id = params["place_id"]
            language = params.get("language", "en")
            
            place_details = self.gmaps.place(
                place_id=place_id,
                language=language,
                fields=["reviews", "rating", "user_ratings_total"]
            )
            
            if "result" not in place_details:
                return self._handle_error("Place not found")
            
            result = place_details["result"]
            
            return self._handle_success({
                "place_id": place_id,
                "overall_rating": result.get("rating"),
                "total_ratings": result.get("user_ratings_total"),
                "reviews": result.get("reviews", [])
            })
            
        except Exception as e:
            return self._handle_error(f"Place reviews failed: {str(e)}")
    
    async def _place_autocomplete(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get place predictions using Places Autocomplete."""
        try:
            query = params.get("query", "")
            language = params.get("language", "en")
            place_type = params.get("place_type")
            
            # Use Places Autocomplete
            autocomplete_result = self.gmaps.places_autocomplete(
                input_text=query,
                language=language,
                types=place_type
            )
            
            predictions = []
            for prediction in autocomplete_result:
                predictions.append({
                    "description": prediction["description"],
                    "place_id": prediction["place_id"],
                    "types": prediction["types"],
                    "structured_formatting": prediction.get("structured_formatting", {}),
                    "terms": prediction.get("terms", [])
                })
            
            return self._handle_success({
                "query": query,
                "predictions": predictions,
                "total_predictions": len(predictions)
            })
            
        except Exception as e:
            return self._handle_error(f"Places autocomplete failed: {str(e)}")
    
    # Routes & Navigation
    
    async def _calculate_route(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate detailed route using Directions API."""
        try:
            origin = params["origin"]
            destination = params["destination"]
            waypoints = params.get("waypoints", [])
            travel_mode = params.get("travel_mode", "driving")
            avoid = params.get("avoid", [])
            language = params.get("language", "en")
            units = params.get("units", "metric")
            
            # Calculate route
            directions_params = {
                "origin": origin,
                "destination": destination,
                "mode": travel_mode,
                "language": language,
                "units": units
            }
            
            if waypoints:
                directions_params["waypoints"] = waypoints
            if avoid:
                directions_params["avoid"] = "|".join(avoid)
            
            directions_result = self.gmaps.directions(**directions_params)
            
            if not directions_result:
                return self._handle_error("No route found")
            
            route = directions_result[0]
            leg = route["legs"][0]
            
            # Format route information
            route_info = {
                "summary": route.get("summary", ""),
                "distance": {
                    "text": leg["distance"]["text"],
                    "value_meters": leg["distance"]["value"]
                },
                "duration": {
                    "text": leg["duration"]["text"],
                    "value_seconds": leg["duration"]["value"]
                },
                "start_address": leg["start_address"],
                "end_address": leg["end_address"],
                "steps": []
            }
            
            # Add detailed steps
            for step in leg["steps"]:
                step_info = {
                    "instruction": step["html_instructions"],
                    "distance": step["distance"],
                    "duration": step["duration"],
                    "travel_mode": step["travel_mode"],
                    "start_location": step["start_location"],
                    "end_location": step["end_location"]
                }
                route_info["steps"].append(step_info)
            
            # Add polyline for route visualization
            if "overview_polyline" in route:
                route_info["polyline"] = route["overview_polyline"]["points"]
            
            return self._handle_success({
                "origin": origin,
                "destination": destination,
                "waypoints": waypoints,
                "travel_mode": travel_mode,
                "route": route_info
            })
            
        except Exception as e:
            return self._handle_error(f"Route calculation failed: {str(e)}")
    
    async def _calculate_travel_time(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate travel time using the newer Routes API v2."""
        try:
            origin = params["origin"]
            destination = params["destination"]
            travel_mode = params.get("travel_mode", "driving")
            
            # Convert travel_mode to Routes API format (according to official documentation)
            travel_mode_mapping = {
                "driving": "DRIVE",
                "walking": "WALK", 
                "bicycling": "BICYCLE",
                "transit": "TRANSIT"
            }
            route_travel_mode = travel_mode_mapping.get(travel_mode, "DRIVE")
            
            # Log the travel mode conversion for debugging
            self.logger.debug(f"Travel mode: {travel_mode} -> {route_travel_mode}")
            
            # Routes API v2 might need specific project setup, but attempt anyway
            
            # Use correct Routes API v2 URL
            routes_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
            
            # Build minimal request payload for Routes API v2
            # Detect if origin/destination are coordinates or addresses
            origin_waypoint = self._format_waypoint_for_routes_api(origin)
            destination_waypoint = self._format_waypoint_for_routes_api(destination)
            
            request_payload = {
                "origin": origin_waypoint,
                "destination": destination_waypoint,
                "travelMode": route_travel_mode
            }
            
            # Only include routingPreference for travel modes that support it
            # WALK and BICYCLE modes don't support routing preferences
            if route_travel_mode in ["DRIVE", "TRANSIT"]:
                request_payload["routingPreference"] = "TRAFFIC_AWARE"
            
            # Add optional parameters
            if params.get("language", "en") != "en":
                request_payload["languageCode"] = params.get("language", "en")
            
            # Set headers for Routes API v2 - use minimal field mask
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"
            }
            
            # Log the request for debugging
            self.logger.debug(f"Routes API request: {request_payload}")
            
            # Make request to Routes API
            response = await self._make_request(
                "POST", 
                routes_url, 
                json=request_payload, 
                headers=headers
            )
            
            if not response.get("routes"):
                return self._handle_error("No route found")
            
            route = response["routes"][0]
            
            # Extract duration and distance - handle different possible formats
            duration_seconds = 0
            distance_meters = 0
            
            # Try to get duration from route level
            if "duration" in route:
                duration_str = route["duration"]
                if duration_str.endswith('s'):
                    duration_seconds = int(duration_str[:-1])
                else:
                    # Try to parse as float and convert to int
                    try:
                        duration_seconds = int(float(duration_str))
                    except ValueError:
                        duration_seconds = 0
            
            # Try to get distance from route level
            if "distanceMeters" in route:
                distance_meters = route["distanceMeters"]
            
            # Fallback to legs if route-level data not available
            if duration_seconds == 0 or distance_meters == 0:
                legs = route.get("legs", [])
                if legs:
                    leg = legs[0]
                    if duration_seconds == 0 and "duration" in leg:
                        duration_str = leg["duration"]
                        if duration_str.endswith('s'):
                            duration_seconds = int(duration_str[:-1])
                        else:
                            try:
                                duration_seconds = int(float(duration_str))
                            except ValueError:
                                duration_seconds = 0
                    
                    if distance_meters == 0 and "distanceMeters" in leg:
                        distance_meters = leg["distanceMeters"]
            
            # Format response
            results = [{
                "origin": origin,
                "destination": destination,
                "distance": {
                    "text": f"{distance_meters / 1000:.1f} km" if distance_meters > 0 else "Unknown",
                    "value": distance_meters
                },
                "duration": {
                    "text": f"{duration_seconds // 60} min" if duration_seconds > 0 else "Unknown",
                    "value": duration_seconds
                },
                "travel_mode": travel_mode
            }]
            
            return self._handle_success({
                "travel_mode": travel_mode,
                "results": results,
                "total_pairs": len(results),
                "api_version": "routes_v2"
            })
            
        except Exception as e:
            # Fallback to legacy Distance Matrix API if Routes API fails
            self.logger.warning(f"Routes API failed: {str(e)}, falling back to Distance Matrix API")
            try:
                return await self._calculate_travel_time_legacy(params)
            except Exception as fallback_error:
                return self._handle_error(f"Travel time calculation failed: {str(e)}")
    
    def _format_waypoint_for_routes_api(self, location: str) -> Dict[str, Any]:
        """Format a location string as the correct waypoint type for Routes API v2."""
        # Check if the location looks like coordinates (lat,lng format)
        if self._is_coordinate_string(location):
            try:
                # Parse coordinates
                lat_str, lng_str = location.strip().split(',')
                latitude = float(lat_str.strip())
                longitude = float(lng_str.strip())
                
                # Return LatLng waypoint format
                waypoint = {
                    "location": {
                        "latLng": {
                            "latitude": latitude,
                            "longitude": longitude
                        }
                    }
                }
                self.logger.debug(f"Formatted '{location}' as LatLng waypoint: {waypoint}")
                return waypoint
                
            except (ValueError, IndexError):
                # If parsing fails, treat as address
                self.logger.debug(f"Failed to parse '{location}' as coordinates, using as address")
                pass
        
        # Return address waypoint format
        waypoint = {"address": location}
        self.logger.debug(f"Formatted '{location}' as address waypoint: {waypoint}")
        return waypoint
    
    def _is_coordinate_string(self, location: str) -> bool:
        """Check if a location string looks like coordinates (lat,lng)."""
        try:
            parts = location.strip().split(',')
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                # Check if coordinates are in valid ranges
                return -90 <= lat <= 90 and -180 <= lng <= 180
        except (ValueError, IndexError):
            pass
        return False
    
    async def _test_routes_api_basic(self, origin: str, destination: str) -> bool:
        """Test Routes API with the most basic request to verify it's working."""
        try:
            # Minimal test request with proper waypoint formatting
            test_payload = {
                "origin": self._format_waypoint_for_routes_api(origin),
                "destination": self._format_waypoint_for_routes_api(destination),
                "travelMode": "DRIVE"
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"
            }
            
            response = await self._make_request(
                "POST", 
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                json=test_payload, 
                headers=headers
            )
            
            return "routes" in response
        except Exception as e:
            self.logger.error(f"Routes API basic test failed: {str(e)}")
            return False
    
    async def _calculate_travel_time_legacy(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate travel time using legacy Distance Matrix API as fallback."""
        try:
            origin = params["origin"]
            destination = params["destination"]
            travel_mode = params.get("travel_mode", "driving")
            
            # Use legacy Distance Matrix API
            distance_result = self.gmaps.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode=travel_mode,
                units="metric" if params.get("units", "metric") == "metric" else "imperial",
                avoid=params.get("avoid", [])
            )
            
            if distance_result["status"] != "OK":
                return self._handle_error(f"Distance calculation failed: {distance_result['status']}")
            
            element = distance_result["rows"][0]["elements"][0]
            
            if element["status"] != "OK":
                return self._handle_error(f"Route not found: {element['status']}")
            
            # Format response to match Routes API format
            results = [{
                "origin": origin,
                "destination": destination,
                "distance": element["distance"],
                "duration": element["duration"],
                "travel_mode": travel_mode
            }]
            
            return self._handle_success({
                "travel_mode": travel_mode,
                "results": results,
                "total_pairs": len(results),
                "api_version": "distance_matrix_legacy"
            })
            
        except Exception as e:
            raise Exception(f"Legacy distance matrix calculation failed: {str(e)}")
    
    async def _optimize_route(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Optimize route with multiple waypoints."""
        try:
            origin = params["origin"]
            destination = params["destination"]
            waypoints = params.get("waypoints", [])
            travel_mode = params.get("travel_mode", "driving")
            
            if not waypoints:
                return self._handle_error("Waypoints required for route optimization")
            
            # Use waypoint optimization
            directions_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                waypoints=waypoints,
                optimize_waypoints=True,
                mode=travel_mode
            )
            
            if not directions_result:
                return self._handle_error("Route optimization failed")
            
            route = directions_result[0]
            
            # Get optimized waypoint order
            waypoint_order = route.get("waypoint_order", [])
            optimized_waypoints = [waypoints[i] for i in waypoint_order]
            
            # Calculate total distance and time
            total_distance = 0
            total_duration = 0
            
            for leg in route["legs"]:
                total_distance += leg["distance"]["value"]
                total_duration += leg["duration"]["value"]
            
            return self._handle_success({
                "origin": origin,
                "destination": destination,
                "original_waypoints": waypoints,
                "optimized_waypoints": optimized_waypoints,
                "waypoint_order": waypoint_order,
                "total_distance": {
                    "text": f"{total_distance / 1000:.1f} km",
                    "value_meters": total_distance
                },
                "total_duration": {
                    "text": f"{total_duration // 60} min",
                    "value_seconds": total_duration
                },
                "polyline": route.get("overview_polyline", {}).get("points", "")
            })
            
        except Exception as e:
            return self._handle_error(f"Route optimization failed: {str(e)}")
    
    async def _distance_matrix(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate distance matrix for multiple origins and destinations using Routes API."""
        try:
            origins = params.get("origins", [params.get("origin")])
            destinations = params.get("destinations", [params.get("destination")])
            travel_mode = params.get("travel_mode", "driving")
            
            # Convert travel_mode to Routes API format (according to official documentation)
            travel_mode_mapping = {
                "driving": "DRIVE",
                "walking": "WALK", 
                "bicycling": "BICYCLE",
                "transit": "TRANSIT"
            }
            route_travel_mode = travel_mode_mapping.get(travel_mode, "DRIVE")
            
            # Log the travel mode conversion for debugging
            self.logger.debug(f"Distance matrix travel mode: {travel_mode} -> {route_travel_mode}")
            
            # Use correct Routes API v2 URL for distance matrix
            routes_url = "https://routes.googleapis.com/distanceMatrix/v2:computeDistanceMatrix"
            
            # Build minimal request payload for distance matrix
            # Format origins and destinations with correct waypoint types
            formatted_origins = [self._format_waypoint_for_routes_api(origin) for origin in origins]
            formatted_destinations = [self._format_waypoint_for_routes_api(destination) for destination in destinations]
            
            request_payload = {
                "origins": formatted_origins,
                "destinations": formatted_destinations,
                "travelMode": route_travel_mode
            }
            
            # Only include routingPreference for travel modes that support it
            # WALK and BICYCLE modes don't support routing preferences
            if route_travel_mode in ["DRIVE", "TRANSIT"]:
                request_payload["routingPreference"] = "TRAFFIC_AWARE"
            
            # Add optional parameters
            if params.get("language", "en") != "en":
                request_payload["languageCode"] = params.get("language", "en")
            
            # Set headers with minimal field mask
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": "originIndex,destinationIndex,duration,distanceMeters,status"
            }
            
            # Make request
            response = await self._make_request(
                "POST", 
                routes_url, 
                json=request_payload, 
                headers=headers
            )
            
            # Format matrix results - handle different response formats
            matrix = []
            
            # Handle different response structures
            elements = response.get("elements", [])
            if not elements:
                # If no elements, try to get from direct response
                for i in range(len(origins)):
                    matrix_row = []
                    for j in range(len(destinations)):
                        matrix_row.append({
                            "status": "NOT_FOUND",
                            "error": "Route not found"
                        })
                    matrix.append(matrix_row)
            else:
                for i in range(len(origins)):
                    matrix_row = []
                    for j in range(len(destinations)):
                        # Find the corresponding result
                        result = None
                        for element in elements:
                            if element.get("originIndex") == i and element.get("destinationIndex") == j:
                                result = element
                                break
                        
                        if result and result.get("status") == "OK":
                            # Handle duration parsing
                            duration_seconds = 0
                            if "duration" in result:
                                duration_str = result["duration"]
                                if duration_str.endswith('s'):
                                    duration_seconds = int(duration_str[:-1])
                                else:
                                    try:
                                        duration_seconds = int(float(duration_str))
                                    except ValueError:
                                        duration_seconds = 0
                            
                            distance_meters = result.get("distanceMeters", 0)
                            
                            matrix_row.append({
                                "distance": {
                                    "text": f"{distance_meters / 1000:.1f} km" if distance_meters > 0 else "Unknown",
                                    "value": distance_meters
                                },
                                "duration": {
                                    "text": f"{duration_seconds // 60} min" if duration_seconds > 0 else "Unknown",
                                    "value": duration_seconds
                                },
                                "status": "OK"
                            })
                        else:
                            matrix_row.append({
                                "status": result.get("status", "NOT_FOUND") if result else "NOT_FOUND",
                                "error": "Route not found"
                            })
                    matrix.append(matrix_row)
            
            return self._handle_success({
                "origins": origins,
                "destinations": destinations,
                "travel_mode": travel_mode,
                "matrix": matrix,
                "api_version": "routes_v2"
            })
            
        except Exception as e:
            # Fallback to legacy Distance Matrix API if Routes API fails
            self.logger.warning(f"Routes API distance matrix failed: {str(e)}, falling back to Distance Matrix API")
            try:
                return await self._distance_matrix_legacy(params)
            except Exception as fallback_error:
                return self._handle_error(f"Distance matrix calculation failed: {str(e)}")
    
    async def _distance_matrix_legacy(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate distance matrix using legacy Distance Matrix API as fallback."""
        try:
            origins = params.get("origins", [params.get("origin")])
            destinations = params.get("destinations", [params.get("destination")])
            travel_mode = params.get("travel_mode", "driving")
            
            # Use legacy Distance Matrix API
            distance_result = self.gmaps.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=travel_mode,
                units="metric" if params.get("units", "metric") == "metric" else "imperial",
                avoid=params.get("avoid", [])
            )
            
            if distance_result["status"] != "OK":
                return self._handle_error(f"Distance matrix calculation failed: {distance_result['status']}")
            
            # Format matrix results
            matrix = []
            for i, row in enumerate(distance_result["rows"]):
                matrix_row = []
                for j, element in enumerate(row["elements"]):
                    if element["status"] == "OK":
                        matrix_row.append({
                            "distance": element["distance"],
                            "duration": element["duration"],
                            "status": "OK"
                        })
                    else:
                        matrix_row.append({
                            "status": element["status"],
                            "error": "Route not found"
                        })
                matrix.append(matrix_row)
            
            return self._handle_success({
                "origins": origins,
                "destinations": destinations,
                "travel_mode": travel_mode,
                "matrix": matrix,
                "api_version": "distance_matrix_legacy"
            })
            
        except Exception as e:
            raise Exception(f"Legacy distance matrix calculation failed: {str(e)}")
    
    async def _snap_to_roads(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Snap GPS coordinates to roads using Roads API."""
        try:
            # This would require the Roads API, which is part of Google Maps Platform
            # For now, return a placeholder response
            return self._handle_error("Roads API integration not yet implemented")
            
        except Exception as e:
            return self._handle_error(f"Snap to roads failed: {str(e)}")
    
    # Geographic Data
    
    async def _get_elevation(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get elevation data for locations."""
        try:
            locations = []
            
            if "latitude" in params and "longitude" in params:
                locations = [(params["latitude"], params["longitude"])]
            elif "locations" in params:
                locations = params["locations"]
            else:
                return self._handle_error("Coordinates required for elevation data")
            
            elevation_result = self.gmaps.elevation(locations)
            
            elevation_data = []
            for result in elevation_result:
                elevation_data.append({
                    "location": result["location"],
                    "elevation_meters": result["elevation"],
                    "resolution": result["resolution"]
                })
            
            return self._handle_success({
                "locations": locations,
                "elevation_data": elevation_data,
                "total_points": len(elevation_data)
            })
            
        except Exception as e:
            return self._handle_error(f"Elevation data failed: {str(e)}")
    
    async def _get_timezone(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get timezone information for a location."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            timestamp = params.get("timestamp", datetime.now().timestamp())
            
            timezone_result = self.gmaps.timezone(
                location=(latitude, longitude),
                timestamp=timestamp
            )
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "timestamp": timestamp,
                "timezone": {
                    "time_zone_id": timezone_result["timeZoneId"],
                    "time_zone_name": timezone_result["timeZoneName"],
                    "dst_offset": timezone_result["dstOffset"],
                    "raw_offset": timezone_result["rawOffset"]
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Timezone data failed: {str(e)}")
    
    async def _get_country_info(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get country information for a location."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            
            # Use reverse geocoding to get country info
            reverse_geocode_result = self.gmaps.reverse_geocode(
                (latitude, longitude)
            )
            
            if not reverse_geocode_result:
                return self._handle_error("No country information found")
            
            # Extract country information
            country_info = {}
            for result in reverse_geocode_result:
                for component in result.get("address_components", []):
                    if "country" in component["types"]:
                        country_info = {
                            "country_name": component["long_name"],
                            "country_code": component["short_name"],
                            "formatted_address": result["formatted_address"]
                        }
                        break
                if country_info:
                    break
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "country_info": country_info
            })
            
        except Exception as e:
            return self._handle_error(f"Country info failed: {str(e)}")
    
    # Maps & Imagery
    
    async def _generate_static_map(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Generate static map image."""
        try:
            # Get location
            location = await self._get_location_coordinates(params)
            if not location:
                return self._handle_error("Could not determine location")
            
            size = params.get("map_size", "640x640")
            zoom = params.get("zoom", 13)
            map_type = params.get("map_type", "roadmap")
            markers = params.get("markers", [])
            
            # Build static map URL
            map_url = f"{self.base_urls['static_maps']}?"
            map_url += f"center={location[0]},{location[1]}"
            map_url += f"&zoom={zoom}"
            map_url += f"&size={size}"
            map_url += f"&maptype={map_type}"
            
            # Add markers
            for marker in markers:
                map_url += f"&markers={marker}"
            
            map_url += f"&key={self.api_key}"
            
            return self._handle_success({
                "location": {
                    "latitude": location[0],
                    "longitude": location[1]
                },
                "map_url": map_url,
                "parameters": {
                    "size": size,
                    "zoom": zoom,
                    "map_type": map_type,
                    "markers": markers
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Static map generation failed: {str(e)}")
    
    async def _get_street_view(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get Street View imagery."""
        try:
            # Get location
            location = await self._get_location_coordinates(params)
            if not location:
                return self._handle_error("Could not determine location")
            
            size = params.get("map_size", "640x640")
            heading = params.get("heading", 0)
            pitch = params.get("pitch", 0)
            fov = params.get("fov", 90)
            
            # Build Street View URL
            street_view_url = f"{self.base_urls['street_view']}?"
            street_view_url += f"location={location[0]},{location[1]}"
            street_view_url += f"&size={size}"
            street_view_url += f"&heading={heading}"
            street_view_url += f"&pitch={pitch}"
            street_view_url += f"&fov={fov}"
            street_view_url += f"&key={self.api_key}"
            
            return self._handle_success({
                "location": {
                    "latitude": location[0],
                    "longitude": location[1]
                },
                "street_view_url": street_view_url,
                "parameters": {
                    "size": size,
                    "heading": heading,
                    "pitch": pitch,
                    "fov": fov
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Street View failed: {str(e)}")
    
    async def _get_map_tile(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get map tile information."""
        try:
            # This would require the Maps Tiles API
            return self._handle_error("Maps Tiles API integration not yet implemented")
            
        except Exception as e:
            return self._handle_error(f"Map tile failed: {str(e)}")
    
    # Environment APIs
    
    async def _get_air_quality(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get air quality data using Air Quality API."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            
            # Air Quality API request
            payload = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "includeLocalAqi": True,
                "includeHourlyPrediction": True,
                "includeDominantPollutant": True
            }
            
            response = await self._make_request(
                "POST",
                self.base_urls["air_quality"],
                json=payload
            )
            
            if "hourlyForecasts" in response:
                return self._handle_success({
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "air_quality": response
                })
            else:
                return self._handle_error("Air quality data not available")
            
        except Exception as e:
            return self._handle_error(f"Air quality data failed: {str(e)}")
    
    async def _get_pollen_data(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get pollen forecast data using Pollen API."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            
            # Pollen API request
            payload = {
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "days": 5
            }
            
            response = await self._make_request(
                "POST",
                self.base_urls["pollen"],
                json=payload
            )
            
            if "dailyInfo" in response:
                return self._handle_success({
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "pollen_forecast": response
                })
            else:
                return self._handle_error("Pollen data not available")
            
        except Exception as e:
            return self._handle_error(f"Pollen data failed: {str(e)}")
    
    async def _get_solar_data(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get solar potential data using Solar API."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            
            # Solar API request
            solar_url = f"{self.base_urls['solar']}?location.latitude={latitude}&location.longitude={longitude}&key={self.api_key}"
            
            response = await self._make_request("GET", solar_url)
            
            if "solarPotential" in response:
                return self._handle_success({
                    "location": {
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "solar_data": response
                })
            else:
                return self._handle_error("Solar data not available")
            
        except Exception as e:
            return self._handle_error(f"Solar data failed: {str(e)}")
    
    # Helper Methods
    
    async def _get_location_coordinates(self, params: Dict[str, Any]) -> Optional[tuple]:
        """Get coordinates from various location parameters."""
        if "latitude" in params and "longitude" in params:
            return (params["latitude"], params["longitude"])
        elif "query" in params:
            geocode_result = self.gmaps.geocode(params["query"])
            if geocode_result:
                location = geocode_result[0]["geometry"]["location"]
                return (location["lat"], location["lng"])
        return None
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            # Handle different API authentication methods
            if "headers" in kwargs and "X-Goog-Api-Key" in kwargs["headers"]:
                # Routes API uses header authentication
                pass
            elif "key" not in kwargs.get("params", {}) and "key" not in url:
                # Legacy APIs use query parameter authentication
                if "params" not in kwargs:
                    kwargs["params"] = {}
                kwargs["params"]["key"] = self.api_key
            
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            # Log the response details for debugging
            if hasattr(e, 'response') and e.response is not None:
                self.logger.error(f"API request failed with status {e.response.status_code}: {e.response.text}")
                if e.response.status_code == 400:
                    raise Exception(f"Bad Request - Check API request format: {e.response.text}")
                elif e.response.status_code == 401:
                    raise Exception(f"Unauthorized - Check API key: {e}")
                elif e.response.status_code == 403:
                    raise Exception(f"Forbidden - Check API permissions: {e}")
                else:
                    raise Exception(f"API request failed ({e.response.status_code}): {e.response.text}")
            else:
                raise Exception(f"API request failed: {e}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    def _format_place_result(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Format a place result from Google Maps API."""
        location = place.get("geometry", {}).get("location", {})
        
        return {
            "name": place.get("name", ""),
            "place_id": place.get("place_id", ""),
            "formatted_address": place.get("formatted_address", place.get("vicinity", "")),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "price_level": place.get("price_level"),
            "types": place.get("types", []),
            "business_status": place.get("business_status"),
            "opening_hours": self._format_opening_hours(place.get("opening_hours")),
            "photos": self._format_photos(place.get("photos", []))
        }
    
    def _format_place_details(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed place information."""
        location = place.get("geometry", {}).get("location", {})
        
        return {
            "name": place.get("name", ""),
            "place_id": place.get("place_id", ""),
            "formatted_address": place.get("formatted_address", ""),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("user_ratings_total"),
            "price_level": place.get("price_level"),
            "types": place.get("types", []),
            "business_status": place.get("business_status"),
            "formatted_phone_number": place.get("formatted_phone_number"),
            "international_phone_number": place.get("international_phone_number"),
            "website": place.get("website"),
            "url": place.get("url"),
            "utc_offset": place.get("utc_offset"),
            "opening_hours": self._format_opening_hours(place.get("opening_hours")),
            "reviews": place.get("reviews", []),
            "photos": self._format_photos(place.get("photos", []))
        }
    
    def _format_geocoding_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Format geocoding result."""
        location = result["geometry"]["location"]
        
        # Extract address components
        components = {}
        for component in result.get("address_components", []):
            for component_type in component["types"]:
                components[component_type] = {
                    "long_name": component["long_name"],
                    "short_name": component["short_name"]
                }
        
        return {
            "formatted_address": result["formatted_address"],
            "latitude": location["lat"],
            "longitude": location["lng"],
            "place_id": result["place_id"],
            "types": result["types"],
            "address_components": components,
            "geometry": result["geometry"]
        }
    
    def _format_opening_hours(self, opening_hours: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Format opening hours information."""
        if not opening_hours:
            return None
        
        return {
            "open_now": opening_hours.get("open_now"),
            "periods": opening_hours.get("periods", []),
            "weekday_text": opening_hours.get("weekday_text", [])
        }
    
    def _format_photos(self, photos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format photos information."""
        formatted_photos = []
        
        for photo in photos[:5]:  # Limit to 5 photos
            photo_url = f"{self.base_urls['places']}/photo?photoreference={photo.get('photo_reference')}&maxwidth=800&key={self.api_key}"
            
            formatted_photos.append({
                "photo_reference": photo.get("photo_reference"),
                "width": photo.get("width"),
                "height": photo.get("height"),
                "photo_url": photo_url,
                "attributions": photo.get("html_attributions", [])
            })
        
        return formatted_photos 