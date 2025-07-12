# AI Travel Planner - Phase 2 Backend Implementation

A complete agentic AI travel planning system built with Google Gemini API, MCP tools, and modern backend architecture.

## 🚀 Phase 2 Features Completed

### ✅ Multi-Agent System
- **Orchestrator Agent**: Manages end-to-end trip planning workflow
- **Profiler Agent**: Conducts conversational user onboarding 
- **Itinerary Agent**: Generates detailed daily itineraries using real-time data
- **Critique Agent**: Reviews itineraries for quality assurance
- **Monitor Agent**: Real-time trip monitoring for disruptions

### ✅ Database Integration
- **Firestore**: Persistent storage for user profiles and trip data
- **Redis**: Session management, caching, and agent memory
- **Unified Database Manager**: Seamless integration with caching layer

### ✅ MCP Tool Integration
- **Google Maps Tool**: Location search, travel times, POI discovery
- **Weather Tool**: Current conditions, forecasts, weather alerts
- **Travel MCP Tool**: Comprehensive travel services (flights, accommodation, currency, budget)
- **Extensible Framework**: Easy to add new MCP tools

### ✅ REST API Endpoints
- Complete FastAPI application with all specified endpoints
- User profile management
- Trip planning workflow
- Dynamic replanning
- Real-time monitoring

### ✅ Key Capabilities
- **Day-by-day Planning**: User confirms each day before proceeding
- **Dynamic Replanning**: Handles real-time disruptions automatically
- **Quality Assurance**: Built-in critique and revision loops
- **Personalization**: Deep user profiling and preference matching
- **Real-time Monitoring**: Proactive disruption detection

## 📁 Project Structure

```
travel-plan-be/
├── src/
│   ├── agents/                 # Multi-agent system
│   │   ├── base_agent.py      # Base agent class
│   │   ├── orchestrator_agent.py
│   │   ├── profiler_agent.py
│   │   ├── itinerary_agent.py
│   │   ├── critique_agent.py
│   │   ├── monitor_agent.py
│   │   └── __init__.py
│   ├── api/                   # FastAPI application
│   │   └── main.py
│   ├── config/                # Configuration
│   │   └── settings.py
│   ├── database/              # Database layer
│   │   ├── firestore_client.py
│   │   ├── redis_client.py
│   │   └── __init__.py
│   ├── models/                # Data models
│   │   ├── user.py
│   │   ├── trip.py
│   │   └── __init__.py
│   ├── tools/                 # MCP tools
│   │   ├── base_mcp_tool.py
│   │   ├── google_maps_tool.py
│   │   ├── weather_tool.py
│   │   ├── travel_mcp_tool.py
│   │   └── __init__.py
│   └── utils/                 # Utilities
├── requirements.txt           # Python dependencies
├── run_server.py             # Server runner script
├── MCP_TOOLS_LIST.md         # Available MCP tools
└── README_PHASE2.md          # This file
```

## 🛠️ Setup and Installation

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
export FIRESTORE_PROJECT_ID=your-project-id
export GOOGLE_MAPS_API_KEY=your-maps-api-key
export GEMINI_API_KEY=your-gemini-api-key

# Travel MCP Tool APIs (optional)
export AMADEUS_API_KEY=your-amadeus-key
export AMADEUS_API_SECRET=your-amadeus-secret
export BOOKING_COM_API_KEY=your-booking-com-key
export EXCHANGE_RATES_API_KEY=your-exchange-rates-key

# Optional (with defaults)
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DEBUG=false
export LOG_LEVEL=INFO
```

### 3. Database Setup

**Firestore:**
- Create a Google Cloud project
- Enable Firestore API
- Download service account credentials (optional for local dev)

**Redis:**
- Install Redis locally or use cloud Redis
- Default connection: localhost:6379

### 4. Run the Server

```bash
# Development mode with auto-reload
python run_server.py --dev

# Production mode
python run_server.py

# Custom port
python run_server.py --port 8080
```

## 📡 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /agents` - List available agents

### User Profile
- `POST /profile` - Create/update user profile
- `GET /profile` - Get user profile

### Trip Planning
- `POST /trips` - Start trip planning
- `GET /trips/{trip_id}` - Get trip status
- `POST /trips/continue` - Continue planning process
- `GET /trips` - Get user trip history

### Itinerary Management
- `GET /trips/{trip_id}/itinerary/{day_index}` - Get day itinerary
- `POST /trips/{trip_id}/itinerary/{day_index}/confirm` - Confirm day
- `POST /trips/{trip_id}/itinerary/{day_index}/request-changes` - Request revisions

### Dynamic Replanning
- `POST /trips/{trip_id}/replan` - Handle disruptions

### Monitoring
- `POST /trips/{trip_id}/monitoring/start` - Start monitoring
- `GET /trips/{trip_id}/monitoring/status` - Get monitoring status

### Travel Services
- `POST /travel/flights/search` - Search flights
- `POST /travel/accommodation/search` - Search accommodation
- `POST /travel/currency/convert` - Convert currency
- `POST /travel/info` - Get travel information
- `POST /travel/budget/calculate` - Calculate trip budget

## 🔍 API Documentation

When the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing the System

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Create User Profile
```bash
curl -X POST http://localhost:8000/profile \
  -H "Content-Type: application/json" \
  -d '{
    "preferences": {
      "travel_style": ["cultural", "adventure"],
      "pace": "moderate",
      "interests": ["history", "food", "architecture"]
    },
    "budget": {
      "level": "mid-range",
      "currency": "USD",
      "daily_max": 200
    },
    "traveler_info": {
      "group_size": 2,
      "travels_with": ["couple"]
    }
  }'
```

### 3. Start Trip Planning
```bash
curl -X POST http://localhost:8000/trips \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Paris, France",
    "start_date": "2025-06-15",
    "end_date": "2025-06-20"
  }'
```

### 4. Search Flights
```bash
curl -X POST http://localhost:8000/travel/flights/search \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "JFK",
    "destination": "CDG",
    "departure_date": "2025-06-15",
    "return_date": "2025-06-20",
    "adults": 2,
    "cabin_class": "economy"
  }'
```

### 5. Search Accommodation
```bash
curl -X POST http://localhost:8000/travel/accommodation/search \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Paris, France",
    "check_in_date": "2025-06-15",
    "check_out_date": "2025-06-20",
    "guests": 2,
    "rooms": 1
  }'
```

### 6. Convert Currency
```bash
curl -X POST http://localhost:8000/travel/currency/convert \
  -H "Content-Type: application/json" \
  -d '{
    "from_currency": "USD",
    "to_currency": "EUR",
    "amount": 1000
  }'
```

## 🏗️ Architecture Highlights

### Multi-Agent Workflow
1. **Orchestrator** receives trip planning request
2. **Profiler** builds user profile (if needed)
3. **Itinerary** generates day-by-day plans
4. **Critique** reviews each plan for quality
5. **Monitor** watches for real-time disruptions

### Data Flow
```
API Request → Orchestrator → Specialized Agents → MCP Tools → Database → Response
```

### Memory Management
- **Session Memory**: Temporary conversation state
- **User Memory**: Persistent user preferences  
- **Application Memory**: Shared data and caching

## 🔧 MCP Tool System

### Available Tools
- **Google Maps**: Location search, travel times, POI discovery
- **Weather**: Current conditions, forecasts, alerts

### Adding New Tools
1. Create tool class inheriting from `BaseMCPTool`
2. Implement required methods
3. Register in tool registry
4. Add to agent tool lists

See `MCP_TOOLS_LIST.md` for detailed documentation.

## 📊 Monitoring & Observability

### Logging
- Structured logging with configurable levels
- File and console output
- Agent-specific log namespaces

### Health Checks
- Database connection monitoring
- Agent status tracking
- Performance metrics

### Error Handling
- Graceful error recovery
- Detailed error responses
- Automatic retries where appropriate

## 🚀 Production Considerations

### Deployment
- Use production WSGI server (Gunicorn + Uvicorn)
- Configure environment variables
- Set up proper logging
- Enable authentication

### Scaling
- Horizontal scaling with load balancer
- Redis clustering for session management
- Firestore automatic scaling

### Security
- Implement proper authentication
- Use HTTPS in production
- Secure API keys and credentials
- Rate limiting

## 🎯 Next Steps (Phase 3)

- Production deployment automation
- Advanced observability and monitoring
- Performance optimization
- Additional MCP tool integrations
- Enhanced frontend interface
- Mobile application development

## 📝 Development Notes

### Key Design Decisions
- **Agent-based architecture**: Modular, testable, maintainable
- **MCP integration**: Future-proof tool ecosystem
- **Unified database layer**: Performance with data consistency
- **Async/await**: Non-blocking operations throughout

### Performance Optimizations
- Redis caching for frequent operations
- Parallel tool calls where possible
- Database query optimization
- Memory-efficient agent communication

---

**AI Travel Planner Phase 2** - A complete agentic AI system for intelligent travel planning with real-time adaptability. 