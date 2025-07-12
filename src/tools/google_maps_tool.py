import googlemaps
from typing import Dict, Any, List, Optional, Union
from src.tools.base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError
from src.config.settings import settings
from src.models.trip import Location


class GoogleMapsTool(BaseMCPTool):
    """Google Maps MCP tool for location data, travel times, and POI search."""
    
    def __init__(self):
        super().__init__(
            name="google_maps",
            description="Search for locations, calculate travel times, and find points of interest using Google Maps"
        )
        self.gmaps = googlemaps.Client(key=settings.google_maps_api_key)
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search_location", "calculate_travel_time", "find_nearby_places", "geocode", "reverse_geocode"],
                    "description": "The action to perform"
                },
                "query": {
                    "type": "string",
                    "description": "Search query for location or place name"
                },
                "origin": {
                    "type": "string",
                    "description": "Origin location for travel time calculation"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location for travel time calculation"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in meters (default: 1000)",
                    "default": 1000
                },
                "place_type": {
                    "type": "string",
                    "description": "Type of place to search for (e.g., restaurant, tourist_attraction, lodging)"
                },
                "travel_mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "description": "Mode of transportation (default: driving)",
                    "default": "driving"
                },
                "language": {
                    "type": "string",
                    "description": "Language for results (default: en)",
                    "default": "en"
                }
            },
            "required": ["action"]
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters for the specific action."""
        action = params.get("action")
        
        if action == "search_location":
            return "query" in params
        elif action == "calculate_travel_time":
            return "origin" in params and "destination" in params
        elif action == "find_nearby_places":
            return ("latitude" in params and "longitude" in params) or "query" in params
        elif action in ["geocode", "reverse_geocode"]:
            if action == "geocode":
                return "query" in params
            else:
                return "latitude" in params and "longitude" in params
        
        return False
    
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the Google Maps tool."""
        try:
            action = kwargs.get("action")
            
            if action == "search_location":
                return await self._search_location(kwargs)
            elif action == "calculate_travel_time":
                return await self._calculate_travel_time(kwargs)
            elif action == "find_nearby_places":
                return await self._find_nearby_places(kwargs)
            elif action == "geocode":
                return await self._geocode(kwargs)
            elif action == "reverse_geocode":
                return await self._reverse_geocode(kwargs)
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            return self._handle_error(str(e))
    
    async def _search_location(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Search for a location by query."""
        query = params["query"]
        language = params.get("language", "en")
        
        try:
            # Use Places API to search for locations
            places_result = self.gmaps.places(
                query=query,
                language=language
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
    
    async def _calculate_travel_time(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Calculate travel time between two locations."""
        origin = params["origin"]
        destination = params["destination"]
        travel_mode = params.get("travel_mode", "driving")
        
        try:
            # Get distance matrix
            matrix_result = self.gmaps.distance_matrix(
                origins=[origin],
                destinations=[destination],
                mode=travel_mode,
                units="metric"
            )
            
            if matrix_result["rows"]:
                element = matrix_result["rows"][0]["elements"][0]
                
                if element["status"] == "OK":
                    return self._handle_success({
                        "origin": origin,
                        "destination": destination,
                        "travel_mode": travel_mode,
                        "distance": {
                            "text": element["distance"]["text"],
                            "value_meters": element["distance"]["value"]
                        },
                        "duration": {
                            "text": element["duration"]["text"],
                            "value_seconds": element["duration"]["value"]
                        }
                    })
                else:
                    return self._handle_error(f"Route calculation failed: {element['status']}")
            else:
                return self._handle_error("No route found")
                
        except Exception as e:
            return self._handle_error(f"Travel time calculation failed: {str(e)}")
    
    async def _find_nearby_places(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Find nearby places of interest."""
        try:
            # Determine location
            if "latitude" in params and "longitude" in params:
                location = (params["latitude"], params["longitude"])
            else:
                # Geocode the query first
                geocode_result = self.gmaps.geocode(params["query"])
                if not geocode_result:
                    return self._handle_error("Could not find location")
                location = geocode_result[0]["geometry"]["location"]
                location = (location["lat"], location["lng"])
            
            radius = params.get("radius", 1000)
            place_type = params.get("place_type")
            language = params.get("language", "en")
            
            # Search for nearby places
            places_result = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                type=place_type,
                language=language
            )
            
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
                "places": places,
                "total_results": len(places)
            })
            
        except Exception as e:
            return self._handle_error(f"Nearby places search failed: {str(e)}")
    
    async def _geocode(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Convert address to coordinates."""
        query = params["query"]
        language = params.get("language", "en")
        
        try:
            geocode_result = self.gmaps.geocode(query, language=language)
            
            if not geocode_result:
                return self._handle_error("Location not found")
            
            locations = []
            for result in geocode_result:
                location = {
                    "formatted_address": result["formatted_address"],
                    "latitude": result["geometry"]["location"]["lat"],
                    "longitude": result["geometry"]["location"]["lng"],
                    "place_id": result["place_id"],
                    "types": result["types"]
                }
                
                # Extract address components
                components = {}
                for component in result.get("address_components", []):
                    for component_type in component["types"]:
                        components[component_type] = component["long_name"]
                
                location["address_components"] = components
                locations.append(location)
            
            return self._handle_success({
                "query": query,
                "locations": locations
            })
            
        except Exception as e:
            return self._handle_error(f"Geocoding failed: {str(e)}")
    
    async def _reverse_geocode(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Convert coordinates to address."""
        latitude = params["latitude"]
        longitude = params["longitude"]
        language = params.get("language", "en")
        
        try:
            reverse_geocode_result = self.gmaps.reverse_geocode(
                (latitude, longitude),
                language=language
            )
            
            if not reverse_geocode_result:
                return self._handle_error("No address found for coordinates")
            
            addresses = []
            for result in reverse_geocode_result:
                address = {
                    "formatted_address": result["formatted_address"],
                    "place_id": result["place_id"],
                    "types": result["types"]
                }
                
                # Extract address components
                components = {}
                for component in result.get("address_components", []):
                    for component_type in component["types"]:
                        components[component_type] = component["long_name"]
                
                address["address_components"] = components
                addresses.append(address)
            
            return self._handle_success({
                "latitude": latitude,
                "longitude": longitude,
                "addresses": addresses
            })
            
        except Exception as e:
            return self._handle_error(f"Reverse geocoding failed: {str(e)}")
    
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
            "opening_hours": {
                "open_now": place.get("opening_hours", {}).get("open_now"),
                "weekday_text": place.get("opening_hours", {}).get("weekday_text", [])
            } if place.get("opening_hours") else None,
            "photos": [
                {
                    "photo_reference": photo.get("photo_reference"),
                    "width": photo.get("width"),
                    "height": photo.get("height")
                }
                for photo in place.get("photos", [])[:3]  # Limit to 3 photos
            ]
        } 