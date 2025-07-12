# MCP Tools for AI Travel Planner Backend

This document lists all available MCP (Model Context Protocol) tools for the AI Travel Planner backend, organized by category.

## Core MCP Tools Implemented

### 1. Google Maps Tool (`google_maps`)
**Description:** Comprehensive location services using Google Maps API
**Actions:**
- `search_location` - Search for locations by name
- `calculate_travel_time` - Calculate travel time between two locations
- `find_nearby_places` - Find points of interest near a location
- `geocode` - Convert addresses to coordinates
- `reverse_geocode` - Convert coordinates to addresses

**Use Cases:**
- Finding restaurants, attractions, hotels
- Calculating travel times between activities
- Geocoding user input locations
- Route optimization

### 2. Weather Tool (`weather`) 
**Description:** Weather information using Open-Meteo API
**Actions:**
- `current_weather` - Get current weather conditions
- `weather_forecast` - Get daily weather forecast (1-16 days)
- `hourly_forecast` - Get hourly weather forecast (1-168 hours)
- `weather_alerts` - Get weather alerts and warnings

**Use Cases:**
- Planning outdoor activities based on weather
- Alerting users to weather disruptions
- Suggesting indoor alternatives during bad weather

### 3. Travel MCP Tool (`travel_mcp_tool`)
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
tool_registry.register(TravelMCPTool())
tool_registry.register(FlightTool())
tool_registry.register(AccommodationTool())
tool_registry.register(EventsTool())
```

### Agent Tool Access
Each agent in the multi-agent system has access to specific tools:

#### Itinerary Agent Tools:
- `google_maps` - Location and POI search
- `weather` - Weather forecasting
- `travel_mcp_tool` - Comprehensive travel services
- `flight_search` - Flight options
- `accommodation_search` - Hotel/lodging options
- `events_search` - Local events and attractions

#### Monitor Agent Tools:
- `weather` - Weather alerts
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
# Google Maps
GOOGLE_MAPS_API_KEY=your_google_maps_key

# Weather (Open-Meteo - no key required)
# Weather tool uses free Open-Meteo API

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
      "args": ["-m", "src.tools.weather_tool"]
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
# Itinerary Agent using tools
async def generate_itinerary(self, location: str, date: date):
    # Get weather forecast
    weather_response = await self.tools.execute_tool(
        "weather",
        action="weather_forecast",
        location=location,
        days=1
    )
    
    # Find nearby restaurants
    places_response = await self.tools.execute_tool(
        "google_maps",
        action="find_nearby_places",
        query=location,
        place_type="restaurant",
        radius=2000
    )
    
    # Search for local events
    events_response = await self.tools.execute_tool(
        "events_search",
        location=location,
        date=date.isoformat()
    )
    
    return self.create_itinerary(weather_response, places_response, events_response)
```

### Monitor Agent Example:
```python
# Monitor Agent checking for disruptions
async def monitor_trip(self, trip_id: str):
    trip = await self.get_trip(trip_id)
    
    # Check weather alerts
    weather_alerts = await self.tools.execute_tool(
        "weather",
        action="weather_alerts",
        latitude=trip.current_location.latitude,
        longitude=trip.current_location.longitude
    )
    
    # Check flight status
    if trip.has_flights:
        flight_status = await self.tools.execute_tool(
            "flight_status",
            flight_number=trip.current_flight.number,
            date=trip.current_flight.date
        )
    
    return self.process_disruptions(weather_alerts, flight_status)
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