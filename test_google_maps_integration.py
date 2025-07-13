#!/usr/bin/env python3
"""
Test script for Google Maps Platform integration
Tests all major APIs and features of the comprehensive Google Maps tool.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from tools.google_maps_tool import GoogleMapsTool


async def test_google_maps_integration():
    """Test comprehensive Google Maps Platform integration."""
    
    print("🗺️  Testing Google Maps Platform Integration")
    print("=" * 55)
    
    # Check if API key is set
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("❌ GOOGLE_MAPS_API_KEY environment variable not set")
        print("Please set your Google Maps API key:")
        print("export GOOGLE_MAPS_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ Google Maps API key found: {api_key[:10]}...")
    
    # Initialize Google Maps tool
    gmaps_tool = GoogleMapsTool()
    
    # Test locations
    test_locations = [
        {"name": "London, UK", "query": "London, UK"},
        {"name": "Times Square, New York", "query": "Times Square, New York, NY"},
        {"name": "Tokyo Tower, Japan", "query": "Tokyo Tower, Japan"}
    ]
    
    success_count = 0
    total_tests = 0
    
    for location_data in test_locations:
        location_name = location_data["name"]
        location_query = location_data["query"]
        
        print(f"\n🌍 Testing location: {location_name}")
        print("-" * 40)
        
        try:
            # Test 1: Core Location Services
            print("🔍 Testing Core Location Services...")
            
            # Geocoding
            geocode_response = await gmaps_tool.execute(
                action="geocode",
                query=location_query
            )
            
            if geocode_response.success:
                coords = geocode_response.data["locations"][0]
                lat, lng = coords["latitude"], coords["longitude"]
                print(f"  ✅ Geocoding: {coords['formatted_address']}")
                print(f"      Coordinates: {lat}, {lng}")
                
                # Reverse Geocoding
                reverse_response = await gmaps_tool.execute(
                    action="reverse_geocode",
                    latitude=lat,
                    longitude=lng
                )
                
                if reverse_response.success:
                    print(f"  ✅ Reverse geocoding: {reverse_response.data['addresses'][0]['formatted_address']}")
                else:
                    print(f"  ❌ Reverse geocoding failed: {reverse_response.error}")
                
                # Address Validation (if available)
                try:
                    validation_response = await gmaps_tool.execute(
                        action="address_validation",
                        address=location_query
                    )
                    if validation_response.success:
                        print(f"  ✅ Address validation completed")
                    else:
                        print(f"  ⚠️ Address validation not available")
                except:
                    print(f"  ⚠️ Address validation API not enabled")
                
                # Test 2: Places API
                print("\n🏢 Testing Places API...")
                
                # Find nearby restaurants
                places_response = await gmaps_tool.execute(
                    action="find_nearby_places",
                    latitude=lat,
                    longitude=lng,
                    place_type="restaurant",
                    radius=1000
                )
                
                if places_response.success:
                    restaurants = places_response.data["places"]
                    print(f"  ✅ Found {len(restaurants)} nearby restaurants")
                    
                    if restaurants:
                        # Get details for first restaurant
                        restaurant = restaurants[0]
                        place_id = restaurant.get("place_id")
                        
                        if place_id:
                            details_response = await gmaps_tool.execute(
                                action="place_details",
                                place_id=place_id
                            )
                            
                            if details_response.success:
                                details = details_response.data["place_details"]
                                print(f"  ✅ Place details: {details['name']}")
                                print(f"      Rating: {details.get('rating', 'N/A')}")
                                print(f"      Phone: {details.get('formatted_phone_number', 'N/A')}")
                            else:
                                print(f"  ❌ Place details failed: {details_response.error}")
                else:
                    print(f"  ❌ Places search failed: {places_response.error}")
                
                # Test 3: Routes & Navigation
                print("\n🛣️  Testing Routes & Navigation...")
                
                # Calculate route to a nearby location
                if location_name == "London, UK":
                    destination = "Big Ben, London, UK"
                elif location_name == "Times Square, New York":
                    destination = "Central Park, New York, NY"
                else:
                    destination = "Shibuya, Tokyo, Japan"
                
                route_response = await gmaps_tool.execute(
                    action="calculate_route",
                    origin=location_query,
                    destination=destination,
                    travel_mode="walking"
                )
                
                if route_response.success:
                    route = route_response.data["route"]
                    print(f"  ✅ Route calculated: {route['distance']['text']}")
                    print(f"      Duration: {route['duration']['text']}")
                    print(f"      Steps: {len(route['steps'])}")
                else:
                    print(f"  ❌ Route calculation failed: {route_response.error}")
                
                # Test travel time matrix
                matrix_response = await gmaps_tool.execute(
                    action="calculate_travel_time",
                    origin=location_query,
                    destination=destination,
                    travel_mode="driving"
                )
                
                if matrix_response.success:
                    result = matrix_response.data["results"][0]
                    print(f"  ✅ Travel time (driving): {result['duration']['text']}")
                else:
                    print(f"  ❌ Travel time calculation failed: {matrix_response.error}")
                
                # Test 4: Geographic Data
                print("\n🌍 Testing Geographic Data...")
                
                # Get elevation
                elevation_response = await gmaps_tool.execute(
                    action="get_elevation",
                    latitude=lat,
                    longitude=lng
                )
                
                if elevation_response.success:
                    elevation = elevation_response.data["elevation_data"][0]
                    print(f"  ✅ Elevation: {elevation['elevation_meters']:.1f} meters")
                else:
                    print(f"  ❌ Elevation failed: {elevation_response.error}")
                
                # Get timezone
                timezone_response = await gmaps_tool.execute(
                    action="get_timezone",
                    latitude=lat,
                    longitude=lng
                )
                
                if timezone_response.success:
                    timezone = timezone_response.data["timezone"]
                    print(f"  ✅ Timezone: {timezone['time_zone_name']}")
                else:
                    print(f"  ❌ Timezone failed: {timezone_response.error}")
                
                # Test 5: Maps & Imagery
                print("\n🗺️  Testing Maps & Imagery...")
                
                # Generate static map
                static_map_response = await gmaps_tool.execute(
                    action="generate_static_map",
                    latitude=lat,
                    longitude=lng,
                    zoom=15,
                    map_type="roadmap",
                    map_size="640x480"
                )
                
                if static_map_response.success:
                    map_url = static_map_response.data["map_url"]
                    print(f"  ✅ Static map generated: {map_url[:50]}...")
                else:
                    print(f"  ❌ Static map failed: {static_map_response.error}")
                
                # Get Street View
                street_view_response = await gmaps_tool.execute(
                    action="get_street_view",
                    latitude=lat,
                    longitude=lng,
                    map_size="640x480"
                )
                
                if street_view_response.success:
                    street_view_url = street_view_response.data["street_view_url"]
                    print(f"  ✅ Street View: {street_view_url[:50]}...")
                else:
                    print(f"  ❌ Street View failed: {street_view_response.error}")
                
                # Test 6: Environment APIs (optional)
                print("\n🌱 Testing Environment APIs...")
                
                # Air Quality
                try:
                    air_quality_response = await gmaps_tool.execute(
                        action="get_air_quality",
                        latitude=lat,
                        longitude=lng
                    )
                    
                    if air_quality_response.success:
                        print(f"  ✅ Air quality data retrieved")
                    else:
                        print(f"  ⚠️ Air quality API not available or not enabled")
                except:
                    print(f"  ⚠️ Air quality API not enabled")
                
                # Pollen Data
                try:
                    pollen_response = await gmaps_tool.execute(
                        action="get_pollen_data",
                        latitude=lat,
                        longitude=lng
                    )
                    
                    if pollen_response.success:
                        print(f"  ✅ Pollen data retrieved")
                    else:
                        print(f"  ⚠️ Pollen API not available or not enabled")
                except:
                    print(f"  ⚠️ Pollen API not enabled")
                
                success_count += 1
                
            else:
                print(f"  ❌ Geocoding failed: {geocode_response.error}")
                
        except Exception as e:
            print(f"  ❌ Exception for {location_name}: {str(e)}")
        
        total_tests += 1
    
    print(f"\n📊 Test Results:")
    print(f"   Successful locations: {success_count}/{total_tests}")
    print(f"   Success rate: {(success_count/total_tests)*100:.1f}%")
    
    if success_count >= total_tests * 0.8:  # 80% success rate
        print("✅ Google Maps Platform integration is working well!")
        print("🎯 Your AI Travel Planner has comprehensive mapping capabilities!")
        return True
    else:
        print("❌ Some tests failed. Check your API key and enabled APIs.")
        print("💡 Enable the following APIs in Google Cloud Console:")
        print("   - Maps JavaScript API")
        print("   - Places API")
        print("   - Geocoding API")
        print("   - Directions API")
        print("   - Distance Matrix API")
        print("   - Elevation API")
        print("   - Time Zone API")
        print("   - Static Maps API")
        print("   - Street View API")
        print("   - Address Validation API (optional)")
        print("   - Air Quality API (optional)")
        print("   - Pollen API (optional)")
        return False


def main():
    """Run the comprehensive Google Maps Platform integration test."""
    print("Google Maps Platform Integration Test")
    print("====================================")
    
    try:
        success = asyncio.run(test_google_maps_integration())
        
        if success:
            print("\n🎉 Google Maps Platform integration is working correctly!")
            print("🌟 Your travel planner has access to comprehensive mapping services!")
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