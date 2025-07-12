import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import httpx
import asyncio
from dataclasses import dataclass

from .base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError


@dataclass
class FlightSearchParams:
    """Parameters for flight search."""
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    infants: int = 0
    cabin_class: str = "economy"
    currency: str = "USD"
    max_results: int = 10


@dataclass
class AccommodationSearchParams:
    """Parameters for accommodation search."""
    location: str
    check_in_date: str
    check_out_date: str
    guests: int = 1
    rooms: int = 1
    currency: str = "USD"
    max_results: int = 10


@dataclass
class CurrencyExchangeParams:
    """Parameters for currency exchange."""
    from_currency: str
    to_currency: str
    amount: float


class TravelMCPTool(BaseMCPTool):
    """Comprehensive Travel MCP Tool for flights, hotels, weather, and currency."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="travel_mcp_tool",
            description="Comprehensive travel tool for flights, accommodation, weather, and currency exchange",
            **kwargs
        )
        
        # API Configuration
        self.amadeus_api_key = kwargs.get("amadeus_api_key", "")
        self.amadeus_secret = kwargs.get("amadeus_secret", "")
        self.booking_com_api_key = kwargs.get("booking_com_api_key", "")
        self.exchange_rates_api_key = kwargs.get("exchange_rates_api_key", "")
        
        # API endpoints
        self.amadeus_base_url = "https://test.api.amadeus.com"
        self.booking_base_url = "https://booking-com.p.rapidapi.com"
        self.exchange_rates_url = "https://api.exchangerate-api.com/v4/latest"
        
        # Cache for access tokens
        self.amadeus_token = None
        self.token_expires_at = None
        
    async def execute(self, action: str, **kwargs) -> MCPToolResponse:
        """Execute travel-related actions."""
        try:
            if action == "search_flights":
                return await self._search_flights(**kwargs)
            elif action == "search_accommodation":
                return await self._search_accommodation(**kwargs)
            elif action == "get_weather_forecast":
                return await self._get_weather_forecast(**kwargs)
            elif action == "convert_currency":
                return await self._convert_currency(**kwargs)
            elif action == "get_airport_info":
                return await self._get_airport_info(**kwargs)
            elif action == "get_city_info":
                return await self._get_city_info(**kwargs)
            elif action == "calculate_trip_budget":
                return await self._calculate_trip_budget(**kwargs)
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            self.logger.error(f"Error executing travel action {action}: {str(e)}")
            return self._handle_error(f"Travel tool error: {str(e)}")
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "search_flights",
                        "search_accommodation",
                        "get_weather_forecast",
                        "convert_currency",
                        "get_airport_info",
                        "get_city_info",
                        "calculate_trip_budget"
                    ],
                    "description": "The travel action to perform"
                },
                "origin": {
                    "type": "string",
                    "description": "Origin airport code or city name"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport code or city name"
                },
                "departure_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Departure date in YYYY-MM-DD format"
                },
                "return_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Return date in YYYY-MM-DD format (optional)"
                },
                "location": {
                    "type": "string",
                    "description": "Location name for accommodation or weather"
                },
                "check_in_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Check-in date in YYYY-MM-DD format"
                },
                "check_out_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Check-out date in YYYY-MM-DD format"
                },
                "adults": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 9,
                    "description": "Number of adult passengers"
                },
                "children": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 9,
                    "description": "Number of children"
                },
                "guests": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Number of guests for accommodation"
                },
                "rooms": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "description": "Number of rooms"
                },
                "cabin_class": {
                    "type": "string",
                    "enum": ["economy", "premium_economy", "business", "first"],
                    "description": "Flight cabin class"
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code (USD, EUR, GBP, etc.)"
                },
                "from_currency": {
                    "type": "string",
                    "description": "Source currency code"
                },
                "to_currency": {
                    "type": "string",
                    "description": "Target currency code"
                },
                "amount": {
                    "type": "number",
                    "description": "Amount to convert"
                },
                "airport_code": {
                    "type": "string",
                    "description": "IATA airport code"
                },
                "city_name": {
                    "type": "string",
                    "description": "City name for information"
                }
            },
            "required": ["action"]
        }
    
    async def _get_amadeus_token(self) -> str:
        """Get Amadeus API access token."""
        if self.amadeus_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.amadeus_token
        
        if not self.amadeus_api_key or not self.amadeus_secret:
            raise MCPToolError("Amadeus API credentials not configured")
        
        try:
            response = await self._make_request(
                "POST",
                f"{self.amadeus_base_url}/v1/security/oauth2/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.amadeus_api_key,
                    "client_secret": self.amadeus_secret
                }
            )
            
            self.amadeus_token = response["access_token"]
            expires_in = response.get("expires_in", 3600)
            self.token_expires_at = datetime.now().timestamp() + expires_in - 60  # 1 minute buffer
            
            return self.amadeus_token
            
        except Exception as e:
            raise MCPToolError(f"Failed to get Amadeus token: {str(e)}")
    
    async def _search_flights(self, **kwargs) -> MCPToolResponse:
        """Search for flights using Amadeus API."""
        try:
            params = FlightSearchParams(**{k: v for k, v in kwargs.items() if v is not None})
            
            # Get access token
            token = await self._get_amadeus_token()
            
            # Build search parameters
            search_params = {
                "originLocationCode": params.origin,
                "destinationLocationCode": params.destination,
                "departureDate": params.departure_date,
                "adults": params.adults,
                "currencyCode": params.currency,
                "max": params.max_results
            }
            
            if params.return_date:
                search_params["returnDate"] = params.return_date
            
            if params.children > 0:
                search_params["children"] = params.children
            
            if params.infants > 0:
                search_params["infants"] = params.infants
            
            # Map cabin class
            cabin_mapping = {
                "economy": "ECONOMY",
                "premium_economy": "PREMIUM_ECONOMY", 
                "business": "BUSINESS",
                "first": "FIRST"
            }
            search_params["travelClass"] = cabin_mapping.get(params.cabin_class, "ECONOMY")
            
            # Make API request
            response = await self._make_request(
                "GET",
                f"{self.amadeus_base_url}/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params=search_params
            )
            
            # Process and format results
            flights = []
            for offer in response.get("data", []):
                flight_info = {
                    "id": offer["id"],
                    "price": {
                        "total": offer["price"]["total"],
                        "currency": offer["price"]["currency"]
                    },
                    "itineraries": [],
                    "travelerPricings": offer.get("travelerPricings", [])
                }
                
                for itinerary in offer.get("itineraries", []):
                    segments = []
                    for segment in itinerary.get("segments", []):
                        segments.append({
                            "departure": {
                                "iataCode": segment["departure"]["iataCode"],
                                "at": segment["departure"]["at"]
                            },
                            "arrival": {
                                "iataCode": segment["arrival"]["iataCode"],
                                "at": segment["arrival"]["at"]
                            },
                            "carrierCode": segment["carrierCode"],
                            "flightNumber": segment["number"],
                            "aircraft": segment.get("aircraft", {}),
                            "duration": segment.get("duration", "")
                        })
                    
                    flight_info["itineraries"].append({
                        "duration": itinerary.get("duration", ""),
                        "segments": segments
                    })
                
                flights.append(flight_info)
            
            return self._handle_success({
                "flights": flights,
                "search_params": params.__dict__,
                "total_results": len(flights)
            })
            
        except Exception as e:
            self.logger.error(f"Flight search error: {str(e)}")
            return self._handle_error(f"Flight search failed: {str(e)}")
    
    async def _search_accommodation(self, **kwargs) -> MCPToolResponse:
        """Search for accommodation using Booking.com API."""
        try:
            params = AccommodationSearchParams(**{k: v for k, v in kwargs.items() if v is not None})
            
            if not self.booking_com_api_key:
                # Fallback to mock data for development
                return self._handle_success({
                    "accommodations": [
                        {
                            "id": "mock_hotel_1",
                            "name": f"Hotel in {params.location}",
                            "rating": 4.2,
                            "price": {
                                "total": 120.0,
                                "currency": params.currency,
                                "per_night": 60.0
                            },
                            "address": f"123 Main St, {params.location}",
                            "amenities": ["WiFi", "Pool", "Gym"],
                            "photos": ["https://example.com/hotel1.jpg"],
                            "review_score": 8.5,
                            "review_count": 1250
                        }
                    ],
                    "search_params": params.__dict__,
                    "total_results": 1,
                    "note": "Mock data - configure Booking.com API key for live results"
                })
            
            # Real API implementation would go here
            headers = {
                "X-RapidAPI-Key": self.booking_com_api_key,
                "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
            }
            
            search_params = {
                "query": params.location,
                "checkin_date": params.check_in_date,
                "checkout_date": params.check_out_date,
                "adults": params.guests,
                "room_number": params.rooms,
                "currency": params.currency,
                "locale": "en-gb"
            }
            
            response = await self._make_request(
                "GET",
                f"{self.booking_base_url}/v1/hotels/search",
                headers=headers,
                params=search_params
            )
            
            # Process results (implementation depends on actual API response format)
            accommodations = []
            for hotel in response.get("result", []):
                accommodations.append({
                    "id": hotel.get("hotel_id"),
                    "name": hotel.get("hotel_name"),
                    "rating": hotel.get("class"),
                    "price": {
                        "total": hotel.get("min_total_price"),
                        "currency": hotel.get("currency_code")
                    },
                    "address": hotel.get("address"),
                    "review_score": hotel.get("review_score"),
                    "review_count": hotel.get("review_nr")
                })
            
            return self._handle_success({
                "accommodations": accommodations,
                "search_params": params.__dict__,
                "total_results": len(accommodations)
            })
            
        except Exception as e:
            self.logger.error(f"Accommodation search error: {str(e)}")
            return self._handle_error(f"Accommodation search failed: {str(e)}")
    
    async def _get_weather_forecast(self, location: str, **kwargs) -> MCPToolResponse:
        """Get weather forecast for a location."""
        try:
            # Use OpenWeatherMap API or similar
            # For now, return mock data
            return self._handle_success({
                "location": location,
                "current": {
                    "temperature": 22.5,
                    "condition": "Partly Cloudy",
                    "humidity": 65,
                    "wind_speed": 12.5,
                    "wind_direction": "SW"
                },
                "forecast": [
                    {
                        "date": "2024-01-15",
                        "temperature_high": 25,
                        "temperature_low": 18,
                        "condition": "Sunny",
                        "precipitation_chance": 10
                    },
                    {
                        "date": "2024-01-16",
                        "temperature_high": 23,
                        "temperature_low": 16,
                        "condition": "Partly Cloudy",
                        "precipitation_chance": 30
                    }
                ]
            })
            
        except Exception as e:
            self.logger.error(f"Weather forecast error: {str(e)}")
            return self._handle_error(f"Weather forecast failed: {str(e)}")
    
    async def _convert_currency(self, **kwargs) -> MCPToolResponse:
        """Convert currency using exchange rate API."""
        try:
            params = CurrencyExchangeParams(**{k: v for k, v in kwargs.items() if v is not None})
            
            # Get exchange rates
            response = await self._make_request(
                "GET",
                f"{self.exchange_rates_url}/{params.from_currency}"
            )
            
            rates = response.get("rates", {})
            if params.to_currency not in rates:
                return self._handle_error(f"Currency {params.to_currency} not found")
            
            exchange_rate = rates[params.to_currency]
            converted_amount = params.amount * exchange_rate
            
            return self._handle_success({
                "from_currency": params.from_currency,
                "to_currency": params.to_currency,
                "original_amount": params.amount,
                "converted_amount": round(converted_amount, 2),
                "exchange_rate": exchange_rate,
                "timestamp": response.get("date")
            })
            
        except Exception as e:
            self.logger.error(f"Currency conversion error: {str(e)}")
            return self._handle_error(f"Currency conversion failed: {str(e)}")
    
    async def _get_airport_info(self, airport_code: str, **kwargs) -> MCPToolResponse:
        """Get airport information."""
        try:
            # Use Amadeus API to get airport info
            token = await self._get_amadeus_token()
            
            response = await self._make_request(
                "GET",
                f"{self.amadeus_base_url}/v1/reference-data/locations",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "subType": "AIRPORT",
                    "keyword": airport_code
                }
            )
            
            airports = []
            for airport in response.get("data", []):
                airports.append({
                    "iataCode": airport["iataCode"],
                    "name": airport["name"],
                    "city": airport.get("address", {}).get("cityName"),
                    "country": airport.get("address", {}).get("countryName"),
                    "timezone": airport.get("timeZoneOffset"),
                    "geoCode": airport.get("geoCode")
                })
            
            return self._handle_success({
                "airports": airports,
                "search_term": airport_code
            })
            
        except Exception as e:
            self.logger.error(f"Airport info error: {str(e)}")
            return self._handle_error(f"Airport info failed: {str(e)}")
    
    async def _get_city_info(self, city_name: str, **kwargs) -> MCPToolResponse:
        """Get city information and travel recommendations."""
        try:
            # Mock implementation - in a real scenario, this would use a travel API
            return self._handle_success({
                "city": city_name,
                "country": "Country Name",
                "timezone": "UTC+2",
                "best_time_to_visit": "Spring (March-May) and Fall (September-November)",
                "attractions": [
                    "Famous landmarks",
                    "Museums",
                    "Parks and gardens"
                ],
                "transportation": {
                    "public_transport": "Excellent metro and bus system",
                    "taxi_apps": ["Uber", "Local Taxi App"],
                    "rental_cars": "Available at airports and city centers"
                },
                "currency": "Local Currency",
                "languages": ["English", "Local Language"],
                "emergency_numbers": {
                    "police": "Emergency Number",
                    "medical": "Emergency Number"
                }
            })
            
        except Exception as e:
            self.logger.error(f"City info error: {str(e)}")
            return self._handle_error(f"City info failed: {str(e)}")
    
    async def _calculate_trip_budget(self, **kwargs) -> MCPToolResponse:
        """Calculate estimated trip budget."""
        try:
            destination = kwargs.get("destination", "Unknown")
            days = kwargs.get("days", 7)
            travelers = kwargs.get("travelers", 1)
            budget_level = kwargs.get("budget_level", "medium")  # low, medium, high
            
            # Mock budget calculation
            daily_rates = {
                "low": {"accommodation": 50, "food": 30, "activities": 20, "local_transport": 15},
                "medium": {"accommodation": 100, "food": 60, "activities": 50, "local_transport": 25},
                "high": {"accommodation": 200, "food": 120, "activities": 100, "local_transport": 40}
            }
            
            rates = daily_rates.get(budget_level, daily_rates["medium"])
            
            budget_breakdown = {}
            total_budget = 0
            
            for category, daily_rate in rates.items():
                category_total = daily_rate * days * travelers
                budget_breakdown[category] = {
                    "daily_rate": daily_rate,
                    "total": category_total
                }
                total_budget += category_total
            
            return self._handle_success({
                "destination": destination,
                "days": days,
                "travelers": travelers,
                "budget_level": budget_level,
                "budget_breakdown": budget_breakdown,
                "total_budget": total_budget,
                "currency": "USD",
                "notes": [
                    "Prices are estimates and may vary by season and location",
                    "Flight costs not included - use flight search for accurate pricing",
                    "Consider booking accommodations in advance for better rates"
                ]
            })
            
        except Exception as e:
            self.logger.error(f"Budget calculation error: {str(e)}")
            return self._handle_error(f"Budget calculation failed: {str(e)}") 