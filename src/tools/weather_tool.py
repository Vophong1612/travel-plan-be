import requests
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
import os
from src.tools.base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError
from src.config.settings import settings


class WeatherTool(BaseMCPTool):
    """Weather MCP tool using OpenWeatherMap One Call API 3.0 for comprehensive weather information."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="Get current weather, forecasts, historical data, and weather alerts using OpenWeatherMap One Call API 3.0"
        )
        
        # Get API key from settings
        self.api_key = os.getenv("OPENWEATHER_API_KEY") or settings.get("OPENWEATHER_API_KEY")
        
        if not self.api_key:
            self.logger.warning("OpenWeatherMap API key not found. Set OPENWEATHER_API_KEY environment variable.")
        
        # API URLs
        self.onecall_api_url = "https://api.openweathermap.org/data/3.0/onecall"
        self.geocoding_api_url = "https://api.openweathermap.org/geo/1.0/direct"
        self.reverse_geocoding_api_url = "https://api.openweathermap.org/geo/1.0/reverse"
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AI-Travel-Planner/1.0'
        })
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["current_weather", "weather_forecast", "hourly_forecast", "weather_alerts", "weather_overview"],
                    "description": "The weather action to perform"
                },
                "location": {
                    "type": "string",
                    "description": "Location name (city, state, country)"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate (-90 to 90)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate (-180 to 180)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days (1-8, default: 7)",
                    "default": 7,
                    "minimum": 1,
                    "maximum": 8
                },
                "hours": {
                    "type": "integer",
                    "description": "Number of forecast hours (1-48, default: 24)",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 48
                },
                "units": {
                    "type": "string",
                    "enum": ["standard", "metric", "imperial"],
                    "description": "Units of measurement (default: metric)",
                    "default": "metric"
                },
                "lang": {
                    "type": "string",
                    "description": "Language code for weather descriptions (default: en)",
                    "default": "en"
                },
                "exclude": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["current", "minutely", "hourly", "daily", "alerts"]
                    },
                    "description": "Parts of the weather data to exclude"
                }
            },
            "required": ["action"]
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters for the specific action."""
        if not self.api_key:
            return False
            
        action = params.get("action")
        
        # Must have either location or coordinates
        has_location = "location" in params
        has_coordinates = "latitude" in params and "longitude" in params
        
        if not (has_location or has_coordinates):
            return False
        
        # Validate specific action requirements
        if action in ["current_weather", "weather_forecast", "hourly_forecast", "weather_alerts", "weather_overview"]:
            return True
        
        return False
    
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the weather tool."""
        try:
            if not self.api_key:
                return self._handle_error("OpenWeatherMap API key not configured. Please set OPENWEATHER_API_KEY environment variable.")
            
            action = kwargs.get("action")
            
            # Get coordinates if location is provided
            if "location" in kwargs and not ("latitude" in kwargs and "longitude" in kwargs):
                coords = await self._geocode_location(kwargs["location"])
                if not coords:
                    return self._handle_error("Could not find location coordinates")
                kwargs["latitude"] = coords["latitude"]
                kwargs["longitude"] = coords["longitude"]
                kwargs["location_info"] = coords
            
            if action == "current_weather":
                return await self._get_current_weather(kwargs)
            elif action == "weather_forecast":
                return await self._get_weather_forecast(kwargs)
            elif action == "hourly_forecast":
                return await self._get_hourly_forecast(kwargs)
            elif action == "weather_alerts":
                return await self._get_weather_alerts(kwargs)
            elif action == "weather_overview":
                return await self._get_weather_overview(kwargs)
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            return self._handle_error(str(e))
    
    async def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        """Geocode location name to coordinates using OpenWeatherMap Geocoding API."""
        try:
            params = {
                "q": location,
                "limit": 1,
                "appid": self.api_key
            }
            
            response = await self._make_request("GET", self.geocoding_api_url, params=params)
            
            if response and len(response) > 0:
                result = response[0]
                return {
                    "latitude": result["lat"],
                    "longitude": result["lon"],
                    "name": result["name"],
                    "country": result.get("country", ""),
                    "state": result.get("state", ""),
                    "local_names": result.get("local_names", {})
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Geocoding failed: {str(e)}")
            return None
    
    async def _get_current_weather(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get current weather conditions using One Call API 3.0."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            units = params.get("units", "metric")
            lang = params.get("lang", "en")
            
            api_params = {
                "lat": latitude,
                "lon": longitude,
                "exclude": "minutely,hourly,daily,alerts",
                "units": units,
                "lang": lang,
                "appid": self.api_key
            }
            
            response = await self._make_request("GET", self.onecall_api_url, params=api_params)
            
            if "current" not in response:
                return self._handle_error("No current weather data available")
            
            current = response["current"]
            
            # Process current weather data
            current_weather = {
                "dt": current["dt"],
                "timestamp": datetime.fromtimestamp(current["dt"]).isoformat(),
                "sunrise": datetime.fromtimestamp(current["sunrise"]).isoformat(),
                "sunset": datetime.fromtimestamp(current["sunset"]).isoformat(),
                "temperature": current["temp"],
                "feels_like": current["feels_like"],
                "pressure": current["pressure"],
                "humidity": current["humidity"],
                "dew_point": current["dew_point"],
                "uvi": current["uvi"],
                "clouds": current["clouds"],
                "visibility": current.get("visibility", 0),
                "wind_speed": current["wind_speed"],
                "wind_deg": current["wind_deg"],
                "wind_gust": current.get("wind_gust", 0),
                "weather": current["weather"]
            }
            
            # Add rain and snow data if available
            if "rain" in current:
                current_weather["rain"] = current["rain"]
            if "snow" in current:
                current_weather["snow"] = current["snow"]
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response["timezone"],
                    "timezone_offset": response["timezone_offset"]
                },
                "current_weather": current_weather,
                "units": self._get_units_description(units)
            })
            
        except Exception as e:
            return self._handle_error(f"Current weather request failed: {str(e)}")
    
    async def _get_weather_forecast(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get daily weather forecast using One Call API 3.0."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            days = min(params.get("days", 7), 8)  # OpenWeatherMap supports max 8 days
            units = params.get("units", "metric")
            lang = params.get("lang", "en")
            
            api_params = {
                "lat": latitude,
                "lon": longitude,
                "exclude": "current,minutely,hourly,alerts",
                "units": units,
                "lang": lang,
                "appid": self.api_key
            }
            
            response = await self._make_request("GET", self.onecall_api_url, params=api_params)
            
            if "daily" not in response:
                return self._handle_error("No daily forecast data available")
            
            daily_forecast = response["daily"][:days]
            
            forecast_days = []
            for day in daily_forecast:
                day_data = {
                    "dt": day["dt"],
                    "date": datetime.fromtimestamp(day["dt"]).date().isoformat(),
                    "sunrise": datetime.fromtimestamp(day["sunrise"]).isoformat(),
                    "sunset": datetime.fromtimestamp(day["sunset"]).isoformat(),
                    "moonrise": datetime.fromtimestamp(day["moonrise"]).isoformat() if day.get("moonrise") else None,
                    "moonset": datetime.fromtimestamp(day["moonset"]).isoformat() if day.get("moonset") else None,
                    "moon_phase": day["moon_phase"],
                    "summary": day.get("summary", ""),
                    "temperature": day["temp"],
                    "feels_like": day["feels_like"],
                    "pressure": day["pressure"],
                    "humidity": day["humidity"],
                    "dew_point": day["dew_point"],
                    "wind_speed": day["wind_speed"],
                    "wind_deg": day["wind_deg"],
                    "wind_gust": day.get("wind_gust", 0),
                    "weather": day["weather"],
                    "clouds": day["clouds"],
                    "pop": day["pop"],  # Probability of precipitation
                    "uvi": day["uvi"]
                }
                
                # Add precipitation data if available
                if "rain" in day:
                    day_data["rain"] = day["rain"]
                if "snow" in day:
                    day_data["snow"] = day["snow"]
                
                forecast_days.append(day_data)
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response["timezone"],
                    "timezone_offset": response["timezone_offset"]
                },
                "forecast_days": forecast_days,
                "units": self._get_units_description(units)
            })
            
        except Exception as e:
            return self._handle_error(f"Weather forecast request failed: {str(e)}")
    
    async def _get_hourly_forecast(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get hourly weather forecast using One Call API 3.0."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            hours = min(params.get("hours", 24), 48)  # OpenWeatherMap supports max 48 hours
            units = params.get("units", "metric")
            lang = params.get("lang", "en")
            
            api_params = {
                "lat": latitude,
                "lon": longitude,
                "exclude": "current,minutely,daily,alerts",
                "units": units,
                "lang": lang,
                "appid": self.api_key
            }
            
            response = await self._make_request("GET", self.onecall_api_url, params=api_params)
            
            if "hourly" not in response:
                return self._handle_error("No hourly forecast data available")
            
            hourly_forecast = response["hourly"][:hours]
            
            forecast_hours = []
            for hour in hourly_forecast:
                hour_data = {
                    "dt": hour["dt"],
                    "timestamp": datetime.fromtimestamp(hour["dt"]).isoformat(),
                    "temperature": hour["temp"],
                    "feels_like": hour["feels_like"],
                    "pressure": hour["pressure"],
                    "humidity": hour["humidity"],
                    "dew_point": hour["dew_point"],
                    "uvi": hour["uvi"],
                    "clouds": hour["clouds"],
                    "visibility": hour.get("visibility", 0),
                    "wind_speed": hour["wind_speed"],
                    "wind_deg": hour["wind_deg"],
                    "wind_gust": hour.get("wind_gust", 0),
                    "weather": hour["weather"],
                    "pop": hour["pop"]  # Probability of precipitation
                }
                
                # Add precipitation data if available
                if "rain" in hour:
                    hour_data["rain"] = hour["rain"]
                if "snow" in hour:
                    hour_data["snow"] = hour["snow"]
                
                forecast_hours.append(hour_data)
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response["timezone"],
                    "timezone_offset": response["timezone_offset"]
                },
                "forecast_hours": forecast_hours,
                "units": self._get_units_description(units)
            })
            
        except Exception as e:
            return self._handle_error(f"Hourly forecast request failed: {str(e)}")
    
    async def _get_weather_alerts(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get weather alerts using One Call API 3.0."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            units = params.get("units", "metric")
            lang = params.get("lang", "en")
            
            api_params = {
                "lat": latitude,
                "lon": longitude,
                "exclude": "current,minutely,hourly,daily",
                "units": units,
                "lang": lang,
                "appid": self.api_key
            }
            
            response = await self._make_request("GET", self.onecall_api_url, params=api_params)
            
            alerts = []
            if "alerts" in response:
                for alert in response["alerts"]:
                    alert_data = {
                        "sender_name": alert["sender_name"],
                        "event": alert["event"],
                        "start": datetime.fromtimestamp(alert["start"]).isoformat(),
                        "end": datetime.fromtimestamp(alert["end"]).isoformat(),
                        "description": alert["description"],
                        "tags": alert.get("tags", [])
                    }
                    alerts.append(alert_data)
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response.get("timezone", ""),
                    "timezone_offset": response.get("timezone_offset", 0)
                },
                "alerts": alerts,
                "alert_count": len(alerts)
            })
            
        except Exception as e:
            return self._handle_error(f"Weather alerts request failed: {str(e)}")
    
    async def _get_weather_overview(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get weather overview with AI-powered summary."""
        try:
            # Get both current weather and forecast for comprehensive overview
            current_response = await self._get_current_weather(params)
            forecast_response = await self._get_weather_forecast({**params, "days": 3})
            
            if not current_response.success or not forecast_response.success:
                return self._handle_error("Could not retrieve weather data for overview")
            
            current_data = current_response.data
            forecast_data = forecast_response.data
            
            # Create weather overview
            overview = {
                "location": current_data["location"],
                "current_conditions": {
                    "temperature": current_data["current_weather"]["temperature"],
                    "condition": current_data["current_weather"]["weather"][0]["description"],
                    "humidity": current_data["current_weather"]["humidity"],
                    "wind_speed": current_data["current_weather"]["wind_speed"]
                },
                "today_forecast": forecast_data["forecast_days"][0] if forecast_data["forecast_days"] else None,
                "three_day_outlook": forecast_data["forecast_days"][:3],
                "summary": self._generate_weather_summary(current_data["current_weather"], forecast_data["forecast_days"][:3])
            }
            
            return self._handle_success(overview)
            
        except Exception as e:
            return self._handle_error(f"Weather overview request failed: {str(e)}")
    
    def _generate_weather_summary(self, current: Dict[str, Any], forecast: List[Dict[str, Any]]) -> str:
        """Generate a human-readable weather summary."""
        try:
            current_condition = current["weather"][0]["description"]
            current_temp = current["temperature"]
            
            summary = f"Currently {current_condition} with temperature at {current_temp}°. "
            
            if forecast:
                today = forecast[0]
                temp_range = f"{today['temperature']['min']}° to {today['temperature']['max']}°"
                summary += f"Today's range: {temp_range}. "
                
                if today.get("rain"):
                    summary += f"Rain expected: {today['rain']}mm. "
                
                if len(forecast) > 1:
                    tomorrow = forecast[1]
                    tomorrow_condition = tomorrow["weather"][0]["description"]
                    summary += f"Tomorrow: {tomorrow_condition}."
            
            return summary
            
        except Exception as e:
            return f"Weather summary unavailable: {str(e)}"
    
    def _get_units_description(self, units: str) -> Dict[str, str]:
        """Get units description for the response."""
        if units == "metric":
            return {
                "temperature": "°C",
                "wind_speed": "m/s",
                "pressure": "hPa",
                "visibility": "m"
            }
        elif units == "imperial":
            return {
                "temperature": "°F",
                "wind_speed": "mph",
                "pressure": "hPa",
                "visibility": "m"
            }
        else:  # standard
            return {
                "temperature": "K",
                "wind_speed": "m/s",
                "pressure": "hPa",
                "visibility": "m"
            }
    
    async def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise Exception("Invalid API key or unauthorized access")
            elif response.status_code == 404:
                raise Exception("Location not found")
            elif response.status_code == 429:
                raise Exception("API rate limit exceeded")
            elif 500 <= response.status_code < 600:
                raise Exception("OpenWeatherMap service temporarily unavailable")
            else:
                raise Exception(f"API request failed: {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
        except ValueError as e:
            raise Exception(f"Invalid JSON response: {e}") 