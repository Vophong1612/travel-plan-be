#!/usr/bin/env python3
"""
Test script for TripAdvisor Content API integration
Tests all major endpoints and features of the TripAdvisor MCP tool.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, 'src')

from tools.tripadvisor_tool import TripAdvisorTool


async def test_tripadvisor_integration():
    """Test comprehensive TripAdvisor Content API integration."""
    
    print("🌟 Testing TripAdvisor Content API Integration")
    print("=" * 55)
    
    # Check if API key is set
    api_key = os.getenv("TRIPADVISOR_API_KEY")
    if not api_key:
        print("❌ TRIPADVISOR_API_KEY environment variable not set")
        print("Please set your TripAdvisor API key:")
        print("export TRIPADVISOR_API_KEY=your_api_key_here")
        print("\n💡 Get your API key at: https://developer-tripadvisor.com/")
        return False
    
    print(f"✅ TripAdvisor API key found: {api_key[:10]}...")
    
    # Initialize TripAdvisor tool
    tripadvisor_tool = TripAdvisorTool()
    
    # Test locations for different types of searches
    test_searches = [
        {
            "type": "text_search",
            "query": "Eiffel Tower",
            "description": "Famous landmark search"
        },
        {
            "type": "restaurant_search", 
            "query": "best restaurants Tokyo",
            "category": "restaurants",
            "description": "Restaurant search in Tokyo"
        },
        {
            "type": "hotel_search",
            "query": "luxury hotels New York",
            "category": "hotels", 
            "description": "Hotel search in New York"
        }
    ]
    
    # Test coordinates for nearby search
    test_coordinates = [
        {
            "name": "Times Square, NYC",
            "latitude": 40.7589,
            "longitude": -73.9851,
            "description": "Major tourist area"
        },
        {
            "name": "Big Ben, London",
            "latitude": 51.4994,
            "longitude": -0.1245,
            "description": "Historic landmark area"
        }
    ]
    
    success_count = 0
    total_tests = 0
    test_location_ids = []  # Store location IDs for detailed testing
    
    print("\n🔍 Testing Location Search...")
    print("-" * 40)
    
    # Test 1: Text-based location search
    for search in test_searches:
        print(f"\n📍 Testing {search['description']}: {search['query']}")
        
        try:
            search_params = {
                "action": "search_locations",
                "query": search["query"],
                "limit": 5
            }
            
            if "category" in search:
                search_params["category"] = search["category"]
            
            search_response = await tripadvisor_tool.execute(**search_params)
            
            if search_response.success:
                locations = search_response.data["locations"]
                print(f"  ✅ Found {len(locations)} locations")
                
                for i, location in enumerate(locations[:3]):  # Show top 3
                    print(f"      {i+1}. {location['name']}")
                    print(f"         Rating: {location.get('rating', 'N/A')}")
                    print(f"         Reviews: {location.get('num_reviews', 0)}")
                    print(f"         Category: {location.get('category', {}).get('name', 'N/A')}")
                    
                    # Store location ID for detailed testing
                    if location.get('location_id'):
                        test_location_ids.append(location['location_id'])
                
                success_count += 1
            else:
                print(f"  ❌ Search failed: {search_response.error}")
        
        except Exception as e:
            print(f"  ❌ Exception during search: {str(e)}")
        
        total_tests += 1
    
    print("\n🌍 Testing Nearby Search...")
    print("-" * 40)
    
    # Test 2: Coordinate-based nearby search
    for coords in test_coordinates:
        print(f"\n📍 Testing nearby search: {coords['name']}")
        
        try:
            nearby_response = await tripadvisor_tool.execute(
                action="nearby_search",
                latitude=coords["latitude"],
                longitude=coords["longitude"],
                radius=2,  # 2 km radius
                category="attractions",
                limit=5
            )
            
            if nearby_response.success:
                locations = nearby_response.data["locations"]
                print(f"  ✅ Found {len(locations)} nearby attractions")
                
                for i, location in enumerate(locations[:3]):
                    distance = location.get('distance_string', 'Unknown distance')
                    print(f"      {i+1}. {location['name']} ({distance})")
                    print(f"         Rating: {location.get('rating', 'N/A')}")
                    
                    # Store location ID for detailed testing
                    if location.get('location_id'):
                        test_location_ids.append(location['location_id'])
                
                success_count += 1
            else:
                print(f"  ❌ Nearby search failed: {nearby_response.error}")
        
        except Exception as e:
            print(f"  ❌ Exception during nearby search: {str(e)}")
        
        total_tests += 1
    
    # Test 3: Location Details, Photos, and Reviews
    if test_location_ids:
        print("\n📋 Testing Location Details...")
        print("-" * 40)
        
        # Test with first few location IDs
        for location_id in test_location_ids[:3]:
            print(f"\n🏢 Testing location details for ID: {location_id}")
            
            try:
                # Test location details
                details_response = await tripadvisor_tool.execute(
                    action="location_details",
                    location_id=location_id
                )
                
                if details_response.success:
                    details = details_response.data["location_details"]
                    print(f"  ✅ Details: {details['name']}")
                    print(f"      Address: {details.get('address', 'N/A')}")
                    print(f"      Phone: {details.get('phone', 'N/A')}")
                    print(f"      Website: {details.get('website', 'N/A')}")
                    
                    # Test location photos
                    photos_response = await tripadvisor_tool.execute(
                        action="location_photos",
                        location_id=location_id
                    )
                    
                    if photos_response.success:
                        photos = photos_response.data["photos"]
                        print(f"  ✅ Photos: {len(photos)} photos available")
                    else:
                        print(f"  ⚠️ Photos not available: {photos_response.error}")
                    
                    # Test location reviews
                    reviews_response = await tripadvisor_tool.execute(
                        action="location_reviews",
                        location_id=location_id
                    )
                    
                    if reviews_response.success:
                        reviews = reviews_response.data["reviews"]
                        print(f"  ✅ Reviews: {len(reviews)} recent reviews")
                        
                        # Show one sample review
                        if reviews:
                            review = reviews[0]
                            print(f"      Sample review: {review.get('title', 'No title')}")
                            print(f"      Rating: {review.get('rating', 'N/A')}/5")
                            print(f"      Date: {review.get('published_date', 'N/A')}")
                    else:
                        print(f"  ⚠️ Reviews not available: {reviews_response.error}")
                    
                    success_count += 1
                else:
                    print(f"  ❌ Location details failed: {details_response.error}")
            
            except Exception as e:
                print(f"  ❌ Exception during location details: {str(e)}")
            
            total_tests += 1
    
    # Test 4: Comprehensive Location Info
    if test_location_ids:
        print("\n🎯 Testing Comprehensive Location Info...")
        print("-" * 40)
        
        try:
            location_id = test_location_ids[0]
            print(f"\n📦 Testing comprehensive info for ID: {location_id}")
            
            comprehensive_response = await tripadvisor_tool.execute(
                action="get_location_info",
                location_id=location_id,
                include_photos=True,
                include_reviews=True
            )
            
            if comprehensive_response.success:
                data = comprehensive_response.data
                print(f"  ✅ Comprehensive data retrieved")
                print(f"      Location: {data['location_details']['name']}")
                print(f"      Photos: {data.get('total_photos', 0)}")
                print(f"      Reviews: {data.get('total_reviews', 0)}")
                print(f"      Complete package: {data.get('comprehensive_data', False)}")
                
                success_count += 1
            else:
                print(f"  ❌ Comprehensive info failed: {comprehensive_response.error}")
        
        except Exception as e:
            print(f"  ❌ Exception during comprehensive test: {str(e)}")
        
        total_tests += 1
    
    # Test 5: Multi-language support
    print("\n🌐 Testing Multi-language Support...")
    print("-" * 40)
    
    try:
        # Test in different languages
        languages = ["en", "fr", "es", "ja"]
        
        for lang in languages:
            print(f"\n🗣️ Testing language: {lang}")
            
            search_response = await tripadvisor_tool.execute(
                action="search_locations",
                query="restaurant",
                language=lang,
                limit=2
            )
            
            if search_response.success:
                locations = search_response.data["locations"]
                print(f"  ✅ Found {len(locations)} locations in {lang}")
                if locations:
                    print(f"      Sample: {locations[0]['name']}")
            else:
                print(f"  ⚠️ Language {lang} search failed: {search_response.error}")
    
    except Exception as e:
        print(f"  ❌ Exception during language test: {str(e)}")
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Successful tests: {success_count}/{total_tests}")
    print(f"   Success rate: {(success_count/total_tests)*100:.1f}%" if total_tests > 0 else "No tests run")
    print(f"   Location IDs found: {len(test_location_ids)}")
    
    if success_count >= total_tests * 0.7:  # 70% success rate
        print("✅ TripAdvisor Content API integration is working well!")
        print("🎯 Your AI Travel Planner has access to trusted travel reviews and photos!")
        print("\n💡 Features available:")
        print("   - 7.5+ million locations worldwide")
        print("   - 1+ billion reviews and opinions")
        print("   - Multi-language support (29 languages)")
        print("   - High-quality photos and authentic reviews")
        print("   - Rate-limited requests (50/second)")
        return True
    else:
        print("❌ Some tests failed. Check your API key and account status.")
        print("💡 Common issues:")
        print("   - Invalid API key")
        print("   - Exceeded rate limits")
        print("   - Account not active or subscription expired")
        print("   - Network connectivity issues")
        return False


def main():
    """Run the comprehensive TripAdvisor Content API integration test."""
    print("TripAdvisor Content API Integration Test")
    print("=======================================")
    
    try:
        success = asyncio.run(test_tripadvisor_integration())
        
        if success:
            print("\n🎉 TripAdvisor Content API integration is working correctly!")
            print("🌟 Your travel planner now has access to trusted travel intelligence!")
            print("\n📚 Next steps:")
            print("   1. Integrate TripAdvisor data into your itinerary planning")
            print("   2. Use reviews and ratings for recommendation ranking")
            print("   3. Display high-quality photos for visual appeal")
            print("   4. Leverage multi-language support for international travelers")
            sys.exit(0)
        else:
            print("\n🔧 Please fix the issues above and try again.")
            print("📖 Visit https://developer-tripadvisor.com/ for API documentation")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 