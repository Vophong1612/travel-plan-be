import requests
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import os
from src.tools.base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError
from src.config.settings import settings


class TripAdvisorTool(BaseMCPTool):
    """
    TripAdvisor Content API MCP tool providing access to:
    - 7.5+ million locations worldwide
    - 1+ billion reviews and opinions
    - High-quality location photos
    - Comprehensive location details
    - Multi-language support (29 languages)
    """
    
    def __init__(self):
        super().__init__(
            name="tripadvisor",
            description="Access TripAdvisor's trusted database of locations, reviews, photos, and travel recommendations"
        )
        
        # Get API key from environment or settings
        self.api_key = os.getenv("TRIPADVISOR_API_KEY") or settings.get("TRIPADVISOR_API_KEY")
        
        if not self.api_key:
            self.logger.warning("TripAdvisor API key not found. Set TRIPADVISOR_API_KEY environment variable.")
        
        # API Configuration
        self.base_url = "https://api.content.tripadvisor.com/api/v1"
        self.max_requests_per_second = 50  # TripAdvisor rate limit
        self.request_interval = 1.0 / self.max_requests_per_second  # 0.02 seconds between requests
        
        # Request session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Travel-Planner/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        
        # Supported languages (29 languages as per TripAdvisor)
        self.supported_languages = [
            'en', 'ar', 'cs', 'da', 'de', 'el', 'es', 'fi', 'fr', 'he', 'hu', 'id',
            'it', 'ja', 'ko', 'ms', 'nl', 'no', 'pl', 'pt', 'ru', 'sk', 'sv', 'th',
            'tr', 'uk', 'vi', 'zh', 'zh-TW'
        ]
        
        # Location categories supported by TripAdvisor
        self.location_categories = [
            'hotels', 'restaurants', 'attractions', 'vacation_rentals',
            'flights', 'cruises', 'car_rental', 'travel_guides'
        ]
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "search_locations", "nearby_search", "location_details",
                        "location_photos", "location_reviews", "get_location_info"
                    ],
                    "description": "The TripAdvisor action to perform"
                },
                
                # Search Parameters
                "query": {
                    "type": "string",
                    "description": "Search query for locations (hotels, restaurants, attractions)"
                },
                "searchQuery": {
                    "type": "string", 
                    "description": "Alternative parameter name for search query"
                },
                "category": {
                    "type": "string",
                    "enum": ["hotels", "restaurants", "attractions", "vacation_rentals"],
                    "description": "Category of locations to search for"
                },
                
                # Location Parameters
                "locationId": {
                    "type": "string",
                    "description": "TripAdvisor location ID for specific operations"
                },
                "location_id": {
                    "type": "string",
                    "description": "Alternative parameter name for location ID"
                },
                
                # Geographic Parameters
                "latitude": {
                    "type": "number",
                    "description": "Latitude for nearby search (-90 to 90)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude for nearby search (-180 to 180)"
                },
                "latLong": {
                    "type": "string",
                    "description": "Latitude and longitude as comma-separated string (e.g., '40.7128,-74.0060')"
                },
                
                # Search Filters
                "radius": {
                    "type": "number",
                    "description": "Search radius in kilometers (1-25, default: 10)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 25
                },
                "radiusUnit": {
                    "type": "string",
                    "enum": ["km", "mi"],
                    "description": "Unit for radius (default: km)",
                    "default": "km"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-30, default: 20)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 30
                },
                
                # Localization
                "language": {
                    "type": "string",
                    "enum": [
                        "en", "ar", "cs", "da", "de", "el", "es", "fi", "fr", "he", "hu", "id",
                        "it", "ja", "ko", "ms", "nl", "no", "pl", "pt", "ru", "sk", "sv", "th",
                        "tr", "uk", "vi", "zh", "zh-TW"
                    ],
                    "description": "Language code for results (default: en)",
                    "default": "en"
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code for pricing (e.g., USD, EUR, JPY)",
                    "default": "USD"
                },
                
                # Content Filters
                "include_reviews": {
                    "type": "boolean",
                    "description": "Include up to 5 reviews per location (default: true)",
                    "default": True
                },
                "include_photos": {
                    "type": "boolean", 
                    "description": "Include up to 5 photos per location (default: true)",
                    "default": True
                },
                "min_rating": {
                    "type": "number",
                    "description": "Minimum rating filter (1.0-5.0)",
                    "minimum": 1.0,
                    "maximum": 5.0
                },
                "max_price_level": {
                    "type": "integer",
                    "description": "Maximum price level (1-4, where 4 is most expensive)",
                    "minimum": 1,
                    "maximum": 4
                },
                
                # Sorting and Ranking
                "sort": {
                    "type": "string",
                    "enum": ["relevance", "distance", "rating", "popularity"],
                    "description": "Sort order for results (default: relevance)",
                    "default": "relevance"
                }
            },
            "required": ["action"]
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters for the specific action."""
        if not self.api_key:
            return False
            
        action = params.get("action")
        
        # Search actions require query or location
        if action in ["search_locations"]:
            return "query" in params or "searchQuery" in params
        
        # Nearby search requires coordinates
        elif action == "nearby_search":
            has_coords = ("latitude" in params and "longitude" in params) or "latLong" in params
            return has_coords
        
        # Location-specific actions require location ID
        elif action in ["location_details", "location_photos", "location_reviews", "get_location_info"]:
            return "locationId" in params or "location_id" in params
        
        return True
    
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the TripAdvisor tool."""
        try:
            if not self.api_key:
                return self._handle_error("TripAdvisor API key not configured. Please set TRIPADVISOR_API_KEY environment variable.")
            
            action = kwargs.get("action")
            
            if action == "search_locations":
                return await self._search_locations(kwargs)
            elif action == "nearby_search":
                return await self._nearby_search(kwargs)
            elif action == "location_details":
                return await self._location_details(kwargs)
            elif action == "location_photos":
                return await self._location_photos(kwargs)
            elif action == "location_reviews":
                return await self._location_reviews(kwargs)
            elif action == "get_location_info":
                return await self._get_location_info(kwargs)
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            return self._handle_error(f"TripAdvisor API error: {str(e)}")
    
    async def _search_locations(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Search for locations by query."""
        try:
            # Get search parameters
            query = params.get("query") or params.get("searchQuery", "")
            if not query:
                return self._handle_error("Search query is required")
            
            language = params.get("language", "en")
            category = params.get("category")
            limit = params.get("limit", 20)
            
            # Build API endpoint
            endpoint = f"{self.base_url}/location/search"
            
            # Build query parameters
            api_params = {
                "key": self.api_key,
                "searchQuery": query,
                "language": language
            }
            
            if category:
                api_params["category"] = category
            if limit:
                api_params["limit"] = min(limit, 30)  # TripAdvisor max limit
            
            # Make API request with rate limiting
            response_data = await self._make_request("GET", endpoint, params=api_params)
            
            # Process results
            locations = []
            if "data" in response_data:
                for location in response_data["data"]:
                    location_info = self._format_location_result(location)
                    locations.append(location_info)
            
            return self._handle_success({
                "query": query,
                "category": category,
                "language": language,
                "locations": locations,
                "total_results": len(locations),
                "search_metadata": {
                    "search_type": "text_search",
                    "api_version": "v1",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Location search failed: {str(e)}")
    
    async def _nearby_search(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Search for locations near coordinates."""
        try:
            # Get coordinates
            if "latLong" in params:
                lat_long = params["latLong"]
                try:
                    lat, lng = map(float, lat_long.split(','))
                except:
                    return self._handle_error("Invalid latLong format. Use 'latitude,longitude'")
            else:
                lat = params.get("latitude")
                lng = params.get("longitude")
                if lat is None or lng is None:
                    return self._handle_error("Latitude and longitude are required")
                lat_long = f"{lat},{lng}"
            
            # Get other parameters
            language = params.get("language", "en")
            category = params.get("category")
            radius = params.get("radius", 10)
            radius_unit = params.get("radiusUnit", "km")
            limit = params.get("limit", 20)
            
            # Build API endpoint
            endpoint = f"{self.base_url}/location/nearby_search"
            
            # Build query parameters
            api_params = {
                "key": self.api_key,
                "latLong": lat_long,
                "language": language,
                "radius": radius,
                "radiusUnit": radius_unit
            }
            
            if category:
                api_params["category"] = category
            if limit:
                api_params["limit"] = min(limit, 30)
            
            # Make API request
            response_data = await self._make_request("GET", endpoint, params=api_params)
            
            # Process results
            locations = []
            if "data" in response_data:
                for location in response_data["data"]:
                    location_info = self._format_location_result(location)
                    locations.append(location_info)
            
            return self._handle_success({
                "coordinates": {"latitude": lat, "longitude": lng},
                "radius": f"{radius} {radius_unit}",
                "category": category,
                "language": language,
                "locations": locations,
                "total_results": len(locations),
                "search_metadata": {
                    "search_type": "nearby_search",
                    "center_point": lat_long,
                    "search_radius": f"{radius}{radius_unit}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Nearby search failed: {str(e)}")
    
    async def _location_details(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get detailed information about a specific location."""
        try:
            # Get location ID
            location_id = params.get("locationId") or params.get("location_id")
            if not location_id:
                return self._handle_error("Location ID is required")
            
            language = params.get("language", "en")
            currency = params.get("currency", "USD")
            
            # Build API endpoint
            endpoint = f"{self.base_url}/location/{location_id}/details"
            
            # Build query parameters
            api_params = {
                "key": self.api_key,
                "language": language,
                "currency": currency
            }
            
            # Make API request
            response_data = await self._make_request("GET", endpoint, params=api_params)
            
            # Process location details
            if "data" in response_data:
                location_details = self._format_location_details(response_data["data"])
                
                return self._handle_success({
                    "location_id": location_id,
                    "language": language,
                    "currency": currency,
                    "location_details": location_details,
                    "data_source": "tripadvisor_content_api",
                    "retrieved_at": datetime.utcnow().isoformat()
                })
            else:
                return self._handle_error("Location details not found")
            
        except Exception as e:
            return self._handle_error(f"Location details failed: {str(e)}")
    
    async def _location_photos(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get photos for a specific location."""
        try:
            # Get location ID
            location_id = params.get("locationId") or params.get("location_id")
            if not location_id:
                return self._handle_error("Location ID is required")
            
            language = params.get("language", "en")
            
            # Build API endpoint
            endpoint = f"{self.base_url}/location/{location_id}/photos"
            
            # Build query parameters
            api_params = {
                "key": self.api_key,
                "language": language
            }
            
            # Make API request
            response_data = await self._make_request("GET", endpoint, params=api_params)
            
            # Process photos
            photos = []
            if "data" in response_data:
                for photo_data in response_data["data"]:
                    photo_info = self._format_photo_result(photo_data)
                    photos.append(photo_info)
            
            return self._handle_success({
                "location_id": location_id,
                "language": language,
                "photos": photos,
                "total_photos": len(photos),
                "max_photos_per_api": 5,  # TripAdvisor limit
                "photo_source": "tripadvisor_content_api"
            })
            
        except Exception as e:
            return self._handle_error(f"Location photos failed: {str(e)}")
    
    async def _location_reviews(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get reviews for a specific location."""
        try:
            # Get location ID
            location_id = params.get("locationId") or params.get("location_id")
            if not location_id:
                return self._handle_error("Location ID is required")
            
            language = params.get("language", "en")
            
            # Build API endpoint  
            endpoint = f"{self.base_url}/location/{location_id}/reviews"
            
            # Build query parameters
            api_params = {
                "key": self.api_key,
                "language": language
            }
            
            # Make API request
            response_data = await self._make_request("GET", endpoint, params=api_params)
            
            # Process reviews
            reviews = []
            if "data" in response_data:
                for review_data in response_data["data"]:
                    review_info = self._format_review_result(review_data)
                    reviews.append(review_info)
            
            return self._handle_success({
                "location_id": location_id,
                "language": language,
                "reviews": reviews,
                "total_reviews": len(reviews),
                "max_reviews_per_api": 5,  # TripAdvisor limit
                "review_source": "tripadvisor_content_api"
            })
            
        except Exception as e:
            return self._handle_error(f"Location reviews failed: {str(e)}")
    
    async def _get_location_info(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get comprehensive location information (details + photos + reviews)."""
        try:
            location_id = params.get("locationId") or params.get("location_id")
            if not location_id:
                return self._handle_error("Location ID is required")
            
            language = params.get("language", "en")
            include_photos = params.get("include_photos", True)
            include_reviews = params.get("include_reviews", True)
            
            # Get location details (always included)
            details_response = await self._location_details({
                "location_id": location_id,
                "language": language
            })
            
            if not details_response.success:
                return details_response
            
            result = {
                "location_id": location_id,
                "language": language,
                "location_details": details_response.data["location_details"]
            }
            
            # Get photos if requested
            if include_photos:
                photos_response = await self._location_photos({
                    "location_id": location_id,
                    "language": language
                })
                
                if photos_response.success:
                    result["photos"] = photos_response.data["photos"]
                    result["total_photos"] = photos_response.data["total_photos"]
                else:
                    result["photos"] = []
                    result["photos_error"] = photos_response.error
            
            # Get reviews if requested
            if include_reviews:
                reviews_response = await self._location_reviews({
                    "location_id": location_id,
                    "language": language
                })
                
                if reviews_response.success:
                    result["reviews"] = reviews_response.data["reviews"]
                    result["total_reviews"] = reviews_response.data["total_reviews"]
                else:
                    result["reviews"] = []
                    result["reviews_error"] = reviews_response.error
            
            result["comprehensive_data"] = True
            result["data_source"] = "tripadvisor_content_api"
            result["retrieved_at"] = datetime.utcnow().isoformat()
            
            return self._handle_success(result)
            
        except Exception as e:
            return self._handle_error(f"Comprehensive location info failed: {str(e)}")
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        try:
            # Rate limiting - ensure we don't exceed 50 requests per second
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            
            if time_since_last_request < self.request_interval:
                sleep_time = self.request_interval - time_since_last_request
                await asyncio.sleep(sleep_time)
            
            self.last_request_time = time.time()
            
            # Make request
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Invalid API key or unauthorized access")
            elif response.status_code == 403:
                raise Exception("API access forbidden - check billing or subscription")
            elif response.status_code == 404:
                raise Exception("Location not found")
            elif response.status_code == 429:
                raise Exception("Rate limit exceeded - too many requests")
            elif 500 <= response.status_code < 600:
                raise Exception("TripAdvisor service temporarily unavailable")
            else:
                raise Exception(f"API request failed: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    def _format_location_result(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """Format a location result from TripAdvisor API."""
        return {
            "location_id": location.get("location_id"),
            "name": location.get("name", ""),
            "description": location.get("description", ""),
            "category": {
                "name": location.get("category", {}).get("name", ""),
                "localized_name": location.get("category", {}).get("localized_name", "")
            },
            "subcategory": location.get("subcategory", []),
            "address_obj": location.get("address_obj", {}),
            "address": location.get("address", ""),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "rating": location.get("rating"),
            "num_reviews": location.get("num_reviews", 0),
            "ranking_data": location.get("ranking_data", {}),
            "price_level": location.get("price_level"),
            "web_url": location.get("web_url", ""),
            "photo": self._format_photo_result(location.get("photo", {})) if location.get("photo") else None,
            "is_closed": location.get("is_closed", False),
            "open_now_text": location.get("open_now_text", ""),
            "timezone": location.get("timezone", ""),
            "distance": location.get("distance"),
            "distance_string": location.get("distance_string", "")
        }
    
    def _format_location_details(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """Format detailed location information."""
        details = self._format_location_result(location)
        
        # Add additional detail-specific fields
        details.update({
            "description": location.get("description", ""),
            "web_url": location.get("web_url", ""),
            "write_review": location.get("write_review", ""),
            "ancestors": location.get("ancestors", []),
            "cuisine": location.get("cuisine", []),
            "dietary_restrictions": location.get("dietary_restrictions", []),
            "establishment_types": location.get("establishment_types", []),
            "trip_types": location.get("trip_types", []),
            "awards": location.get("awards", []),
            "location_string": location.get("location_string", ""),
            "doubleclick_zone": location.get("doubleclick_zone", ""),
            "preferred_map_engine": location.get("preferred_map_engine", ""),
            "phone": location.get("phone", ""),
            "website": location.get("website", ""),
            "email": location.get("email", ""),
            "address_obj": location.get("address_obj", {}),
            "hours": location.get("hours", {}),
            "features": location.get("features", [])
        })

        # --- Begin: Category-specific details enhancement ---
        category = details.get("category", {}).get("name")

        if category == "restaurants":
            details["restaurant_info"] = {
                "price_level": details.get("price_level"),
                "cuisine": details.get("cuisine", []),
                "dietary_restrictions": details.get("dietary_restrictions", []),
                # The following are speculative fields based on common restaurant data.
                # The .get() method ensures no errors if they don't exist in the API response.
                "reservations": location.get("reservations", {}),
                "menu_url": location.get("menu_url")
            }

        if category == "attractions":
            subcategories = [sub.get('name', '').lower() for sub in details.get("subcategory", [])]
            attraction_type = [subcat.get('name') for subcat in details.get("subcategory", []) if subcat.get('name')]
            
            is_museum = "museums" in subcategories
            is_landmark = "landmarks & points of interest" in subcategories or "historic sites" in subcategories

            details["attraction_info"] = {
                # Speculative fields based on common attraction data.
                "suggested_duration": location.get("suggested_duration"),
                "ticket_info": location.get("ticket_info"),
                "attraction_type": attraction_type,
                "is_museum": is_museum,
                "is_landmark": is_landmark
            }
        # --- End: Category-specific details enhancement ---

        return details
    
    def _format_photo_result(self, photo: Dict[str, Any]) -> Dict[str, Any]:
        """Format a photo result from TripAdvisor API."""
        if not photo:
            return {}
        
        return {
            "id": photo.get("id"),
            "is_blessed": photo.get("is_blessed", False),
            "caption": photo.get("caption", ""),
            "published_date": photo.get("published_date", ""),
            "images": {
                "small": photo.get("images", {}).get("small", {}),
                "thumbnail": photo.get("images", {}).get("thumbnail", {}),
                "original": photo.get("images", {}).get("original", {}),
                "large": photo.get("images", {}).get("large", {}),
                "medium": photo.get("images", {}).get("medium", {})
            },
            "album": photo.get("album", ""),
            "source": photo.get("source", {}),
            "user": photo.get("user", {})
        }
    
    def _format_review_result(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Format a review result from TripAdvisor API."""
        return {
            "id": review.get("id"),
            "url": review.get("url", ""),
            "location_id": review.get("location_id"),
            "lang": review.get("lang"),
            "published_date": review.get("published_date", ""),
            "published_platform": review.get("published_platform", ""),
            "rating": review.get("rating"),
            "helpful_votes": review.get("helpful_votes", 0),
            "is_machine_translated": review.get("is_machine_translated", False),
            "title": review.get("title", ""),
            "text": review.get("text", ""),
            "user": {
                "username": review.get("user", {}).get("username", ""),
                "user_location": review.get("user", {}).get("user_location", {}),
                "avatar": review.get("user", {}).get("avatar", {})
            },
            "trip_type": review.get("trip_type", ""),
            "travel_date": review.get("travel_date", ""),
            "helpful_vote_count": review.get("helpful_vote_count", 0),
            "photos": [self._format_photo_result(photo) for photo in review.get("photos", [])]
        }
    
    def get_cached_location_id(self, location_identifier: str) -> Optional[str]:
        """
        Get cached location ID if available.
        Note: According to TripAdvisor caching policy, only location_id can be cached.
        """
        # This would integrate with your caching system
        # Only location_id is allowed to be cached per TripAdvisor policy
        return None  # Implement based on your caching strategy
    
    def cache_location_id(self, location_identifier: str, location_id: str) -> None:
        """
        Cache location ID for performance improvement.
        Note: Only location_id can be cached per TripAdvisor policy.
        """
        # This would integrate with your caching system
        # Only location_id is allowed to be cached per TripAdvisor policy
        pass  # Implement based on your caching strategy 