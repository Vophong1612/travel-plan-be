# MCP Tools for AI Travel Planner Backend

This document lists all available MCP (Model Context Protocol) tools for the AI Travel Planner backend, organized by category.

## Core MCP Tools Implemented

### 1. Google Maps Tool (`google_maps`)
**Description:** Comprehensive Google Maps Platform integration supporting all major APIs
**Actions:**
- **Core Location Services:**
  - `search_location` - Search for locations by name
  - `geocode` - Convert addresses to coordinates
  - `reverse_geocode` - Convert coordinates to addresses
  - `address_validation` - Validate and standardize addresses
  
- **Places API:**
  - `search_places` - Search for places with advanced filters
  - `find_nearby_places` - Find POIs near a location
  - `place_details` - Get detailed place information
  - `place_photos` - Get place photos and imagery
  - `place_reviews` - Get place reviews and ratings
  - `place_autocomplete` - Get place predictions for autocomplete
  
- **Routes & Navigation:**
  - `calculate_route` - Calculate detailed routes with turn-by-turn directions
  - `calculate_travel_time` - Calculate travel times with traffic data
  - `optimize_route` - Optimize routes with multiple waypoints
  - `distance_matrix` - Calculate distance/time matrices
  - `snap_to_roads` - Snap GPS coordinates to roads
  
- **Geographic Data:**
  - `get_elevation` - Get elevation data for locations
  - `get_timezone` - Get timezone information
  - `get_country_info` - Get country information for locations
  
- **Maps & Imagery:**
  - `generate_static_map` - Generate static map images
  - `get_street_view` - Get Street View imagery
  - `get_map_tile` - Get map tiles for custom implementations
  
- **Environment APIs:**
  - `get_air_quality` - Get air quality data and forecasts
  - `get_pollen_data` - Get pollen forecasts
  - `get_solar_data` - Get solar potential data

**Use Cases:**
- Comprehensive location intelligence and mapping
- Advanced route planning and optimization
- Environmental data for health-conscious travelers
- Rich place information with photos and reviews
- Address validation for booking accuracy
- Static maps and Street View for visual context

### 2. Weather Tool (`weather`) 
**Description:** Comprehensive weather information using OpenWeatherMap One Call API 3.0
**Actions:**
- `current_weather` - Get current weather conditions with detailed metrics
- `weather_forecast` - Get daily weather forecast (1-8 days)
- `hourly_forecast` - Get hourly weather forecast (1-48 hours)
- `weather_alerts` - Get official weather alerts and warnings
- `weather_overview` - Get AI-powered weather summary with current conditions and 3-day outlook

**Use Cases:**
- Planning outdoor activities based on weather
- Alerting users to weather disruptions and official warnings
- Suggesting indoor alternatives during bad weather
- Comprehensive weather analysis for travel planning

### 3. TripAdvisor Tool (`tripadvisor`)
**Description:** Access TripAdvisor's trusted database of 7.5+ million locations and 1+ billion reviews
**Actions:**
- **Location Search:**
  - `search_locations` - Search for hotels, restaurants, attractions by query
  - `nearby_search` - Find locations near specific coordinates
  
- **Location Intelligence:**
  - `location_details` - Get comprehensive location information
  - `location_photos` - Get up to 5 high-quality photos per location
  - `location_reviews` - Get up to 5 recent reviews per location
  - `get_location_info` - Get complete location package (details + photos + reviews)

**Features:**
- 29 language support for global travelers
- Trusted reviews and ratings from real travelers
- High-quality location photos
- Price level indicators and ranking data
- Category filtering (hotels, restaurants, attractions, vacation_rentals)
- Radius-based nearby search (1-25 km)
- Rate limiting compliance (50 requests/second)

**Use Cases:**
- Finding top-rated restaurants and attractions
- Getting authentic traveler reviews and photos
- Location-based recommendations for itinerary planning
- Price level filtering for budget-conscious travelers
- Multi-language content for international trips
- Trusted source validation for travel recommendations

### 4. Travel MCP Tool (`travel_mcp_tool`)
**Description:** Comprehensive travel services including flight search, accommodation, weather, and currency exchange
**Actions:**
- `search_flights` - Search for flights using Amadeus API
- `search_accommodation` - Search for hotels and accommodations
- `get_weather_forecast` - Get weather forecast for destinations
- `convert_currency` - Convert between currencies
- `get_airport_info` - Get airport information by code
- `get_city_info` - Get city information and travel recommendations
- `calculate_trip_budget` - Calculate estimated trip budget

**Use Cases:**
- Comprehensive flight search and booking
- Hotel and accommodation discovery
- Currency conversion for international travel
- Budget planning and cost estimation
- Airport and city information lookup
- Weather-based travel recommendations

## Additional MCP Tools Available for Integration

### 3. Flight Planning Tools

#### Flight Planner MCP Server (`@salamentic/google-flights-mcp`)
**Description:** Flight search and booking using fast-flights API
**Features:**
- Search one-way and round-trip flights
- Create comprehensive travel plans
- Get airport code information
- Flight search templates

#### Find Flights MCP Server (`ravinahp/find-flights-mcp`)
**Description:** Flight search using Duffel API
**Features:**
- Detailed flight information
- Flexible search parameters
- Various flight types support

#### Amadeus MCP Server (`privilegemendes/amadeus-mcp`)
**Description:** Flight search and analysis using Amadeus API
**Features:**
- Flight search and price analysis
- Best travel deals
- Multi-city trip planning

### 4. Weather Tools

#### Weather MCP Server (`danielshih/weather-mcp`)
**Description:** Real-time weather using Open-Meteo API
**Features:**
- Current weather for any city
- Historical weather data
- Timezone-specific datetime information
- No API key required

**Note:** Our implemented weather tool uses OpenWeatherMap One Call API 3.0 instead, which provides more comprehensive weather data including official alerts.

### 5. Event and Entertainment Tools

#### MCP Live Events Server (`mmmaaatttttt/mcp-live-events`)
**Description:** Real-time concert and event data using Ticketmaster API
**Features:**
- Concert and event information
- Real-time availability
- Dynamic event data fetching

### 6. Travel Services

#### LumbreTravel MCP Server (`lumile/lumbre-travel-mcp`)
**Description:** Travel program management using LumbreTravel API
**Features:**
- Travel program management
- Activity booking
- Travel entity management

## MCP Tool Integration Architecture

### Tool Registry System
```python
from src.tools.base_mcp_tool import tool_registry

# Register all tools
tool_registry.register(GoogleMapsTool())
tool_registry.register(WeatherTool())
tool_registry.register(TripAdvisorTool())
tool_registry.register(TravelMCPTool())
tool_registry.register(FlightTool())
tool_registry.register(AccommodationTool())
tool_registry.register(EventsTool())
```

### Agent Tool Access
Each agent in the multi-agent system has access to specific tools:

#### Itinerary Agent Tools:
- `google_maps` - Comprehensive location services, route planning, place details, environmental data
- `weather` - Weather forecasting and alerts
- `tripadvisor` - Trusted reviews, photos, and location intelligence from real travelers
- `travel_mcp_tool` - Comprehensive travel services
- `flight_search` - Flight options
- `accommodation_search` - Hotel/lodging options
- `events_search` - Local events and attractions

#### Monitor Agent Tools:
- `weather` - Weather alerts and forecasts
- `google_maps` - Air quality monitoring, traffic data, route disruptions
- `flight_status` - Flight delay monitoring
- `traffic_updates` - Real-time traffic data
- `venue_status` - Venue closure alerts

## Custom MCP Tools Implementation Plan

### 1. Flight Search Tool (`flight_search`)
**Amadeus API Integration**
```python
class FlightSearchTool(BaseMCPTool):
    def __init__(self):
        super().__init__(
            name="flight_search",
            description="Search for flights using Amadeus API"
        )
        self.amadeus = AmadeusClient()
    
    async def execute(self, **kwargs):
        # Implementation for flight search
        pass
```

### 2. Accommodation Tool (`accommodation_search`)
**Booking.com API Integration**
```python
class AccommodationTool(BaseMCPTool):
    def __init__(self):
        super().__init__(
            name="accommodation_search", 
            description="Search for hotels and accommodations"
        )
        self.booking_api = BookingAPIClient()
```

### 3. Local Events Tool (`events_search`)
**Ticketmaster API Integration**
```python
class EventsTool(BaseMCPTool):
    def __init__(self):
        super().__init__(
            name="events_search",
            description="Search for local events and attractions"
        )
        self.ticketmaster = TicketmasterClient()
```

### 4. Flight Status Monitor (`flight_status`)
**Real-time Flight Tracking**
```python
class FlightStatusTool(BaseMCPTool):
    def __init__(self):
        super().__init__(
            name="flight_status",
            description="Monitor flight status and delays"
        )
        self.flight_tracker = FlightTrackerClient()
```

## Tool Configuration

### Environment Variables Required:
```bash
# Google Maps Platform (enable required APIs in Google Cloud Console)
GOOGLE_MAPS_API_KEY=your_google_maps_key
# Required APIs: Maps JavaScript API, Places API, Geocoding API, Directions API,
# Distance Matrix API, Elevation API, Time Zone API, Static Maps API, Street View API
# Optional APIs: Address Validation API, Air Quality API, Pollen API, Solar API

# Weather (OpenWeatherMap One Call API 3.0)
OPENWEATHER_API_KEY=your_openweather_api_key

# TripAdvisor Content API
TRIPADVISOR_API_KEY=your_tripadvisor_api_key

# Travel MCP Tool APIs
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret
BOOKING_COM_API_KEY=your_booking_com_key
EXCHANGE_RATES_API_KEY=your_exchange_rates_key

# Flight APIs
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret

# Accommodation
BOOKING_API_KEY=your_booking_key

# Events
TICKETMASTER_API_KEY=your_ticketmaster_key
```

### MCP Server Configuration:
```json
{
  "mcpServers": {
    "google-maps": {
      "command": "python",
      "args": ["-m", "src.tools.google_maps_tool"],
      "env": {
        "GOOGLE_MAPS_API_KEY": "${GOOGLE_MAPS_API_KEY}"
      }
    },
    "weather": {
      "command": "python", 
      "args": ["-m", "src.tools.weather_tool"],
      "env": {
        "OPENWEATHER_API_KEY": "${OPENWEATHER_API_KEY}"
      }
    },
    "tripadvisor": {
      "command": "python",
      "args": ["-m", "src.tools.tripadvisor_tool"],
      "env": {
        "TRIPADVISOR_API_KEY": "${TRIPADVISOR_API_KEY}"
      }
    },
    "flight-planner": {
      "command": "npx",
      "args": ["-y", "@salamentic/google-flights-mcp"]
    }
  }
}
```

## Usage Examples

### In Agent Code:
```python
# Itinerary Agent using comprehensive tools
async def generate_itinerary(self, location: str, date: date):
    # Get weather forecast
    weather_response = await self.tools.execute_tool(
        "weather",
        action="weather_forecast",
        location=location,
        days=1
    )
    
    # Get location coordinates for detailed queries
    geocode_response = await self.tools.execute_tool(
        "google_maps",
        action="geocode",
        query=location
    )
    
    if geocode_response.success:
        coords = geocode_response.data["locations"][0]
        lat, lng = coords["latitude"], coords["longitude"]
        
        # Find nearby restaurants with detailed information
        places_response = await self.tools.execute_tool(
            "google_maps",
            action="find_nearby_places",
            latitude=lat,
            longitude=lng,
            place_type="restaurant",
            radius=2000,
            open_now=True
        )
        
        # Get air quality data for health-conscious travelers
        air_quality_response = await self.tools.execute_tool(
            "google_maps",
            action="get_air_quality",
            latitude=lat,
            longitude=lng
        )
        
        # Calculate optimized route for multiple attractions
        attractions = await self.tools.execute_tool(
            "google_maps",
            action="find_nearby_places",
            latitude=lat,
            longitude=lng,
            place_type="tourist_attraction",
            radius=5000
        )
        
        # Generate static map for visual context
        map_response = await self.tools.execute_tool(
            "google_maps",
            action="generate_static_map",
            latitude=lat,
            longitude=lng,
            zoom=13,
            map_type="roadmap"
        )
    
         return self.create_comprehensive_itinerary(
         weather_response, places_response, air_quality_response, 
         attractions, map_response
     )

# Enhanced Itinerary Agent with TripAdvisor integration
async def create_detailed_itinerary(self, location: str, preferences: dict):
    # Get highly-rated restaurants with authentic reviews
    restaurants_response = await self.tools.execute_tool(
        "tripadvisor",
        action="search_locations",
        query=f"restaurants in {location}",
        category="restaurants",
        language=preferences.get("language", "en"),
        limit=10
    )
    
    # Get detailed information including photos and reviews
    if restaurants_response.success:
        restaurant_details = []
        for restaurant in restaurants_response.data["locations"][:5]:
            location_id = restaurant["location_id"]
            
            # Get comprehensive info with photos and reviews
            details_response = await self.tools.execute_tool(
                "tripadvisor",
                action="get_location_info",
                location_id=location_id,
                include_photos=True,
                include_reviews=True
            )
            
            if details_response.success:
                restaurant_details.append(details_response.data)
    
    # Find top attractions with trusted reviews
    attractions_response = await self.tools.execute_tool(
        "tripadvisor",
        action="nearby_search",
        latitude=lat,
        longitude=lng,
        category="attractions",
        radius=10,
        limit=15
    )
    
    return self.build_trust_based_itinerary(
        restaurant_details, attractions_response.data, preferences
    )
```

### Monitor Agent Example:
```python
# Monitor Agent checking for comprehensive disruptions
async def monitor_trip(self, trip_id: str):
    trip = await self.get_trip(trip_id)
    lat, lng = trip.current_location.latitude, trip.current_location.longitude
    
    # Check weather alerts
    weather_alerts = await self.tools.execute_tool(
        "weather",
        action="weather_alerts",
        latitude=lat,
        longitude=lng
    )
    
    # Check air quality for health alerts
    air_quality = await self.tools.execute_tool(
        "google_maps",
        action="get_air_quality",
        latitude=lat,
        longitude=lng
    )
    
    # Check pollen data for allergy-sensitive travelers
    pollen_data = await self.tools.execute_tool(
        "google_maps",
        action="get_pollen_data",
        latitude=lat,
        longitude=lng
    )
    
    # Check current traffic conditions for route disruptions
    if trip.has_planned_routes:
        traffic_conditions = await self.tools.execute_tool(
            "google_maps",
            action="calculate_travel_time",
            origin=trip.current_location.address,
            destination=trip.next_destination.address,
            travel_mode="driving"
        )
    
    # Check flight status
    if trip.has_flights:
        flight_status = await self.tools.execute_tool(
            "flight_status",
            flight_number=trip.current_flight.number,
            date=trip.current_flight.date
        )
    
    return self.process_comprehensive_disruptions(
        weather_alerts, air_quality, pollen_data, 
        traffic_conditions, flight_status
    )
```

## Tool Performance Optimization

### Caching Strategy:
- Weather data: Cache for 1 hour
- Location data: Cache for 24 hours
- Flight prices: Cache for 15 minutes
- Event data: Cache for 6 hours

### Rate Limiting:
- Google Maps: 1000 requests/day (free tier)
- Amadeus: 1000 requests/month (free tier)
- Open-Meteo: No rate limits
- Ticketmaster: 5000 requests/day

### Error Handling:
- Automatic retries with exponential backoff
- Fallback to alternative APIs when primary fails
- Graceful degradation of service quality

## Future Tool Integrations

### Planned Additions:
1. **Restaurant Reservation Tool** - OpenTable API integration
2. **Ground Transportation Tool** - Uber/Lyft API integration
3. **Currency Exchange Tool** - Real-time exchange rates
4. **Translation Tool** - Google Translate API integration
5. **Travel Insurance Tool** - Insurance comparison and booking
6. **Local Transportation Tool** - Public transit information

### Advanced Features:
1. **Real-time Pricing Tool** - Dynamic pricing monitoring
2. **Review Aggregation Tool** - TripAdvisor/Yelp integration
3. **Photo Search Tool** - Instagram/Google Photos integration
4. **Local Guide Tool** - Local expert recommendations
5. **Accessibility Tool** - Accessibility information for venues

This comprehensive MCP tool ecosystem provides the AI Travel Planner with robust external service integrations while maintaining flexibility and scalability through the standardized MCP protocol. 