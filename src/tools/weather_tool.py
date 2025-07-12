import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
from src.tools.base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError


class WeatherTool(BaseMCPTool):
    """Weather MCP tool using Open-Meteo API for weather information."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="Get current weather conditions, forecasts, and historical weather data"
        )
        
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)
        
        # API URLs
        self.weather_api_url = "https://api.open-meteo.com/v1/forecast"
        self.geocoding_api_url = "https://geocoding-api.open-meteo.com/v1/search"
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["current_weather", "weather_forecast", "hourly_forecast", "weather_alerts"],
                    "description": "The weather action to perform"
                },
                "location": {
                    "type": "string",
                    "description": "Location name (city, address, etc.)"
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude coordinate"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude coordinate"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days (1-16, default: 7)",
                    "default": 7,
                    "minimum": 1,
                    "maximum": 16
                },
                "hours": {
                    "type": "integer",
                    "description": "Number of forecast hours (1-168, default: 24)",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 168
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the forecast (default: auto)",
                    "default": "auto"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature units (default: celsius)",
                    "default": "celsius"
                },
                "include_alerts": {
                    "type": "boolean",
                    "description": "Include weather alerts if available (default: true)",
                    "default": True
                }
            },
            "required": ["action"]
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters for the specific action."""
        action = params.get("action")
        
        # Must have either location or coordinates
        has_location = "location" in params
        has_coordinates = "latitude" in params and "longitude" in params
        
        if not (has_location or has_coordinates):
            return False
        
        # Validate specific action requirements
        if action in ["current_weather", "weather_forecast", "hourly_forecast", "weather_alerts"]:
            return True
        
        return False
    
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the weather tool."""
        try:
            action = kwargs.get("action")
            
            # Get coordinates if location is provided
            if "location" in kwargs and not ("latitude" in kwargs and "longitude" in kwargs):
                coords = await self._geocode_location(kwargs["location"])
                if not coords:
                    return self._handle_error("Could not find location coordinates")
                kwargs["latitude"] = coords["latitude"]
                kwargs["longitude"] = coords["longitude"]
            
            if action == "current_weather":
                return await self._get_current_weather(kwargs)
            elif action == "weather_forecast":
                return await self._get_weather_forecast(kwargs)
            elif action == "hourly_forecast":
                return await self._get_hourly_forecast(kwargs)
            elif action == "weather_alerts":
                return await self._get_weather_alerts(kwargs)
            else:
                return self._handle_error(f"Unknown action: {action}")
                
        except Exception as e:
            return self._handle_error(str(e))
    
    async def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        """Geocode location name to coordinates."""
        try:
            params = {
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            
            response = await self._make_request("GET", self.geocoding_api_url, params=params)
            
            if "results" in response and response["results"]:
                result = response["results"][0]
                return {
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "name": result["name"],
                    "country": result.get("country", ""),
                    "timezone": result.get("timezone", "auto")
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Geocoding failed: {str(e)}")
            return None
    
    async def _get_current_weather(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get current weather conditions."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            units = params.get("units", "celsius")
            timezone = params.get("timezone", "auto")
            
            # Define weather parameters
            current_params = [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "is_day", "precipitation", "rain", "showers", "snowfall",
                "weather_code", "cloud_cover", "pressure_msl", "surface_pressure",
                "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"
            ]
            
            api_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": current_params,
                "timezone": timezone,
                "temperature_unit": units,
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm"
            }
            
            responses = self.openmeteo.weather_api(self.weather_api_url, params=api_params)
            response = responses[0]
            
            # Current weather data
            current = response.Current()
            
            current_weather = {
                "temperature": current.Variables(0).Value(),
                "relative_humidity": current.Variables(1).Value(),
                "apparent_temperature": current.Variables(2).Value(),
                "is_day": bool(current.Variables(3).Value()),
                "precipitation": current.Variables(4).Value(),
                "rain": current.Variables(5).Value(),
                "showers": current.Variables(6).Value(),
                "snowfall": current.Variables(7).Value(),
                "weather_code": int(current.Variables(8).Value()),
                "cloud_cover": current.Variables(9).Value(),
                "pressure_msl": current.Variables(10).Value(),
                "surface_pressure": current.Variables(11).Value(),
                "wind_speed": current.Variables(12).Value(),
                "wind_direction": current.Variables(13).Value(),
                "wind_gusts": current.Variables(14).Value(),
                "time": datetime.fromtimestamp(current.Time()).isoformat()
            }
            
            # Add weather description
            current_weather["condition"] = self._get_weather_description(current_weather["weather_code"])
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response.Timezone().decode('utf-8')
                },
                "current_weather": current_weather,
                "units": {
                    "temperature": "°C" if units == "celsius" else "°F",
                    "wind_speed": "km/h",
                    "precipitation": "mm"
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Current weather request failed: {str(e)}")
    
    async def _get_weather_forecast(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get daily weather forecast."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            days = params.get("days", 7)
            units = params.get("units", "celsius")
            timezone = params.get("timezone", "auto")
            
            # Define daily forecast parameters
            daily_params = [
                "weather_code", "temperature_2m_max", "temperature_2m_min",
                "apparent_temperature_max", "apparent_temperature_min",
                "precipitation_sum", "rain_sum", "showers_sum", "snowfall_sum",
                "precipitation_hours", "precipitation_probability_max",
                "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant",
                "sunrise", "sunset", "uv_index_max"
            ]
            
            api_params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": daily_params,
                "timezone": timezone,
                "forecast_days": days,
                "temperature_unit": units,
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm"
            }
            
            responses = self.openmeteo.weather_api(self.weather_api_url, params=api_params)
            response = responses[0]
            
            # Daily forecast data
            daily = response.Daily()
            
            forecast_days = []
            for i in range(days):
                day_data = {
                    "date": datetime.fromtimestamp(daily.Time()[i]).date().isoformat(),
                    "weather_code": int(daily.Variables(0).ValuesAsNumpy()[i]),
                    "temperature_max": daily.Variables(1).ValuesAsNumpy()[i],
                    "temperature_min": daily.Variables(2).ValuesAsNumpy()[i],
                    "apparent_temperature_max": daily.Variables(3).ValuesAsNumpy()[i],
                    "apparent_temperature_min": daily.Variables(4).ValuesAsNumpy()[i],
                    "precipitation_sum": daily.Variables(5).ValuesAsNumpy()[i],
                    "rain_sum": daily.Variables(6).ValuesAsNumpy()[i],
                    "showers_sum": daily.Variables(7).ValuesAsNumpy()[i],
                    "snowfall_sum": daily.Variables(8).ValuesAsNumpy()[i],
                    "precipitation_hours": daily.Variables(9).ValuesAsNumpy()[i],
                    "precipitation_probability_max": daily.Variables(10).ValuesAsNumpy()[i],
                    "wind_speed_max": daily.Variables(11).ValuesAsNumpy()[i],
                    "wind_gusts_max": daily.Variables(12).ValuesAsNumpy()[i],
                    "wind_direction_dominant": daily.Variables(13).ValuesAsNumpy()[i],
                    "sunrise": datetime.fromtimestamp(daily.Variables(14).ValuesAsNumpy()[i]).isoformat(),
                    "sunset": datetime.fromtimestamp(daily.Variables(15).ValuesAsNumpy()[i]).isoformat(),
                    "uv_index_max": daily.Variables(16).ValuesAsNumpy()[i]
                }
                
                # Add weather description
                day_data["condition"] = self._get_weather_description(day_data["weather_code"])
                forecast_days.append(day_data)
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response.Timezone().decode('utf-8')
                },
                "forecast_days": forecast_days,
                "units": {
                    "temperature": "°C" if units == "celsius" else "°F",
                    "wind_speed": "km/h",
                    "precipitation": "mm"
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Weather forecast request failed: {str(e)}")
    
    async def _get_hourly_forecast(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get hourly weather forecast."""
        try:
            latitude = params["latitude"]
            longitude = params["longitude"]
            hours = params.get("hours", 24)
            units = params.get("units", "celsius")
            timezone = params.get("timezone", "auto")
            
            # Define hourly forecast parameters
            hourly_params = [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation_probability", "precipitation", "rain", "showers", "snowfall",
                "weather_code", "cloud_cover", "visibility", "wind_speed_10m",
                "wind_direction_10m", "wind_gusts_10m", "is_day"
            ]
            
            api_params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": hourly_params,
                "timezone": timezone,
                "forecast_hours": hours,
                "temperature_unit": units,
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm"
            }
            
            responses = self.openmeteo.weather_api(self.weather_api_url, params=api_params)
            response = responses[0]
            
            # Hourly forecast data
            hourly = response.Hourly()
            
            forecast_hours = []
            for i in range(hours):
                hour_data = {
                    "time": datetime.fromtimestamp(hourly.Time()[i]).isoformat(),
                    "temperature": hourly.Variables(0).ValuesAsNumpy()[i],
                    "relative_humidity": hourly.Variables(1).ValuesAsNumpy()[i],
                    "apparent_temperature": hourly.Variables(2).ValuesAsNumpy()[i],
                    "precipitation_probability": hourly.Variables(3).ValuesAsNumpy()[i],
                    "precipitation": hourly.Variables(4).ValuesAsNumpy()[i],
                    "rain": hourly.Variables(5).ValuesAsNumpy()[i],
                    "showers": hourly.Variables(6).ValuesAsNumpy()[i],
                    "snowfall": hourly.Variables(7).ValuesAsNumpy()[i],
                    "weather_code": int(hourly.Variables(8).ValuesAsNumpy()[i]),
                    "cloud_cover": hourly.Variables(9).ValuesAsNumpy()[i],
                    "visibility": hourly.Variables(10).ValuesAsNumpy()[i],
                    "wind_speed": hourly.Variables(11).ValuesAsNumpy()[i],
                    "wind_direction": hourly.Variables(12).ValuesAsNumpy()[i],
                    "wind_gusts": hourly.Variables(13).ValuesAsNumpy()[i],
                    "is_day": bool(hourly.Variables(14).ValuesAsNumpy()[i])
                }
                
                # Add weather description
                hour_data["condition"] = self._get_weather_description(hour_data["weather_code"])
                forecast_hours.append(hour_data)
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": response.Timezone().decode('utf-8')
                },
                "forecast_hours": forecast_hours,
                "units": {
                    "temperature": "°C" if units == "celsius" else "°F",
                    "wind_speed": "km/h",
                    "precipitation": "mm"
                }
            })
            
        except Exception as e:
            return self._handle_error(f"Hourly forecast request failed: {str(e)}")
    
    async def _get_weather_alerts(self, params: Dict[str, Any]) -> MCPToolResponse:
        """Get weather alerts for the location."""
        try:
            # Open-Meteo doesn't provide weather alerts directly
            # This is a placeholder for potential integration with other services
            # or parsing of severe weather conditions from forecast data
            
            latitude = params["latitude"]
            longitude = params["longitude"]
            
            # For now, analyze current and forecast conditions for potential alerts
            current_weather = await self._get_current_weather(params)
            
            alerts = []
            
            if current_weather.success:
                weather_data = current_weather.data["current_weather"]
                
                # Check for severe weather conditions
                if weather_data["wind_speed"] > 50:  # Strong wind
                    alerts.append({
                        "type": "wind",
                        "severity": "high",
                        "title": "Strong Wind Warning",
                        "description": f"Wind speed: {weather_data['wind_speed']} km/h"
                    })
                
                if weather_data["precipitation"] > 20:  # Heavy rain
                    alerts.append({
                        "type": "precipitation",
                        "severity": "medium",
                        "title": "Heavy Rain Warning",
                        "description": f"Heavy precipitation: {weather_data['precipitation']} mm"
                    })
                
                if weather_data["temperature"] < -10:  # Extreme cold
                    alerts.append({
                        "type": "temperature",
                        "severity": "high",
                        "title": "Extreme Cold Warning",
                        "description": f"Temperature: {weather_data['temperature']}°C"
                    })
                
                if weather_data["temperature"] > 40:  # Extreme heat
                    alerts.append({
                        "type": "temperature",
                        "severity": "high",
                        "title": "Extreme Heat Warning",
                        "description": f"Temperature: {weather_data['temperature']}°C"
                    })
            
            return self._handle_success({
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "alerts": alerts,
                "alert_count": len(alerts)
            })
            
        except Exception as e:
            return self._handle_error(f"Weather alerts request failed: {str(e)}")
    
    def _get_weather_description(self, weather_code: int) -> str:
        """Convert weather code to human-readable description."""
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        return weather_codes.get(weather_code, f"Unknown weather code: {weather_code}") 