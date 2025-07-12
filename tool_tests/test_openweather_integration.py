#!/usr/bin/env python3
"""
Test script for OpenWeatherMap integration
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from tools.weather_tool import WeatherTool


async def test_openweather_integration():
    """Test OpenWeatherMap integration."""
    
    print("🌤️  Testing OpenWeatherMap Integration")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        print("❌ OPENWEATHER_API_KEY environment variable not set")
        print("Please set your OpenWeatherMap API key:")
        print("export OPENWEATHER_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ OpenWeatherMap API key found: {api_key[:10]}...")
    
    # Initialize weather tool
    weather_tool = WeatherTool()
    
    # Test data
    test_locations = [
        "Ho Chi Minh, Vietnam",
        "Paris, France", 
        "Tokyo, Japan",
        "New York, USA"
    ]
    
    success_count = 0
    
    for location in test_locations:
        print(f"\n🌍 Testing weather for: {location}")
        try:
            # Test current weather
            current_response = await weather_tool.execute(
                action="current_weather",
                location=location
            )
            
            if current_response.success:
                weather_data = current_response.data
                current = weather_data["current_weather"]
                print(f"  ✅ Current weather: {current['weather'][0]['description']}")
                print(f"     Temperature: {current['temperature']}°C")
                print(f"     Humidity: {current['humidity']}%")
                print(f"     Wind: {current['wind_speed']} m/s")
                
                # Test weather forecast
                forecast_response = await weather_tool.execute(
                    action="weather_forecast",
                    location=location,
                    days=3
                )
                
                if forecast_response.success:
                    forecast_data = forecast_response.data
                    print(f"  ✅ 3-day forecast retrieved")
                    print(f"     Days: {len(forecast_data['forecast_days'])}")
                    
                    # Test weather overview
                    overview_response = await weather_tool.execute(
                        action="weather_overview",
                        location=location
                    )
                    
                    if overview_response.success:
                        overview_data = overview_response.data
                        print(f"  ✅ Weather overview: {overview_data['summary']}")
                        success_count += 1
                    else:
                        print(f"  ❌ Weather overview failed: {overview_response.error}")
                else:
                    print(f"  ❌ Weather forecast failed: {forecast_response.error}")
            else:
                print(f"  ❌ Current weather failed: {current_response.error}")
                
        except Exception as e:
            print(f"  ❌ Exception for {location}: {str(e)}")
    
    print(f"\n📊 Test Results:")
    print(f"   Successful locations: {success_count}/{len(test_locations)}")
    
    if success_count == len(test_locations):
        print("✅ All OpenWeatherMap integration tests passed!")
        print("🎯 Your AI Travel Planner is ready to use OpenWeatherMap!")
        return True
    else:
        print("❌ Some tests failed. Check your API key and network connection.")
        return False


def main():
    """Run the integration test."""
    print("OpenWeatherMap Integration Test")
    print("==============================")
    
    try:
        success = asyncio.run(test_openweather_integration())
        
        if success:
            print("\n🎉 OpenWeatherMap integration is working correctly!")
            sys.exit(0)
        else:
            print("\n🔧 Please fix the issues above and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 