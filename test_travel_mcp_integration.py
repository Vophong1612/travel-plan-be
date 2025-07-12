#!/usr/bin/env python3
"""
Test script for Travel MCP Tool integration
"""
import asyncio
import json
from src.tools.travel_mcp_tool import TravelMCPTool


async def test_travel_mcp_tool():
    """Test the Travel MCP Tool functionality."""
    print("🧪 Testing Travel MCP Tool Integration")
    print("=" * 50)
    
    # Initialize the travel tool
    travel_tool = TravelMCPTool()
    
    # Test 1: Currency conversion
    print("\n💰 Testing Currency Conversion...")
    try:
        response = await travel_tool.execute(
            action="convert_currency",
            from_currency="USD",
            to_currency="EUR",
            amount=1000
        )
        print(f"✅ Currency conversion: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Currency conversion failed: {str(e)}")
    
    # Test 2: Weather forecast
    print("\n🌤️ Testing Weather Forecast...")
    try:
        response = await travel_tool.execute(
            action="get_weather_forecast",
            location="Paris"
        )
        print(f"✅ Weather forecast: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Weather forecast failed: {str(e)}")
    
    # Test 3: City information
    print("\n🏙️ Testing City Information...")
    try:
        response = await travel_tool.execute(
            action="get_city_info",
            city_name="Tokyo"
        )
        print(f"✅ City info: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ City info failed: {str(e)}")
    
    # Test 4: Budget calculation
    print("\n💳 Testing Budget Calculation...")
    try:
        response = await travel_tool.execute(
            action="calculate_trip_budget",
            destination="London",
            days=7,
            travelers=2,
            budget_level="medium"
        )
        print(f"✅ Budget calculation: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Budget calculation failed: {str(e)}")
    
    # Test 5: Accommodation search (will use mock data)
    print("\n🏨 Testing Accommodation Search...")
    try:
        response = await travel_tool.execute(
            action="search_accommodation",
            location="New York",
            check_in_date="2025-07-01",
            check_out_date="2025-07-05",
            guests=2,
            rooms=1
        )
        print(f"✅ Accommodation search: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Accommodation search failed: {str(e)}")
    
    # Test 6: Flight search (would need API keys)
    print("\n✈️ Testing Flight Search...")
    try:
        response = await travel_tool.execute(
            action="search_flights",
            origin="JFK",
            destination="CDG",
            departure_date="2025-07-01",
            return_date="2025-07-05",
            adults=2,
            cabin_class="economy"
        )
        print(f"✅ Flight search: {response.success}")
        if response.success:
            print(f"   Result: Found {len(response.data.get('flights', []))} flights")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Flight search failed: {str(e)}")
    
    # Test 7: Get airport info
    print("\n🛫 Testing Airport Information...")
    try:
        response = await travel_tool.execute(
            action="get_airport_info",
            airport_code="JFK"
        )
        print(f"✅ Airport info: {response.success}")
        if response.success:
            print(f"   Result: {response.data}")
        else:
            print(f"   Error: {response.error}")
    except Exception as e:
        print(f"❌ Airport info failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 Travel MCP Tool Integration Test Complete!")


async def test_tool_schema():
    """Test the Travel MCP Tool schema."""
    print("\n📋 Testing Travel MCP Tool Schema...")
    travel_tool = TravelMCPTool()
    schema = travel_tool.get_schema()
    
    print(f"✅ Schema loaded successfully")
    print(f"   Actions available: {len(schema['properties']['action']['enum'])}")
    print(f"   Actions: {', '.join(schema['properties']['action']['enum'])}")
    
    # Validate schema structure
    required_fields = ["action"]
    missing_fields = [field for field in required_fields if field not in schema.get("required", [])]
    
    if not missing_fields:
        print("✅ Schema validation passed")
    else:
        print(f"❌ Schema validation failed: Missing required fields: {missing_fields}")


def main():
    """Run all tests."""
    print("🚀 Starting Travel MCP Tool Integration Tests")
    
    # Test schema
    asyncio.run(test_tool_schema())
    
    # Test functionality
    asyncio.run(test_travel_mcp_tool())


if __name__ == "__main__":
    main() 