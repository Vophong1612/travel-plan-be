# AI Travel Planner - Backend

A complete agentic AI travel planning system that creates personalized, dynamic travel itineraries using **Google Gemini API**, **MCP tools**, and modern backend architecture.

## 🚀 Overview

AI Travel Planner is not just another trip generator - it's an **autonomous AI system** that plans, monitors, and adapts your travel experience in real-time. Built with a multi-agent architecture, it provides:

- **Conversational Trip Planning**: Natural language interaction for planning
- **Day-by-Day Confirmation**: User stays in control with step-by-step approval
- **Real-time Monitoring**: Proactive disruption detection and replanning
- **Personalized Recommendations**: Deep user profiling for tailored experiences
- **Dynamic Adaptation**: Automatic replanning when things go wrong

## ✨ Key Features

### 🤖 **Multi-Agent Intelligence**
- **Orchestrator Agent**: Master coordinator managing the entire workflow
- **Profiler Agent**: Conducts conversational user onboarding and profiling
- **Itinerary Agent**: Generates detailed daily itineraries using real-time data
- **Critique Agent**: Quality assurance and itinerary validation
- **Monitor Agent**: Real-time trip monitoring for disruptions

### 🧠 **AI-Powered Planning**
- **Google Gemini 1.5 Pro**: Advanced reasoning and planning capabilities
- **Contextual Memory**: Learns and remembers user preferences
- **Quality Assurance**: Built-in critique and revision loops
- **Natural Language**: Conversational interaction throughout

### 🛠️ **MCP Tool Integration**
- **Google Maps**: Location search, travel times, route optimization
- **Weather Services**: Current conditions, forecasts, alerts
- **Travel APIs**: Flights, accommodation, currency conversion
- **Extensible Architecture**: Easy to add new tools and services

### 🗄️ **Robust Data Layer**
- **Firestore**: Persistent storage for user profiles and trip data
- **Redis**: Session management, caching, and agent memory
- **Multi-scope Memory**: Session, user, and application-level persistence

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│              Frontend Layer             │
│         (Web/Mobile Clients)            │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│              API Gateway                │
│           (FastAPI Backend)             │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│           Multi-Agent System            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │Profiler │ │Itinerary│ │Critique │   │
│  │ Agent   │ │ Agent   │ │ Agent   │   │
│  └─────────┘ └─────────┘ └─────────┘   │
│         ┌─────────────────┐             │
│         │  Orchestrator   │             │
│         │     Agent       │             │
│         └─────────────────┘             │
│                  │                      │
│  ┌─────────┐    │    ┌─────────────┐   │
│  │Monitor  │────┴────│   Gemini    │   │
│  │ Agent   │         │     API     │   │
│  └─────────┘         └─────────────┘   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│              Data Layer                 │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  Firestore  │    │    Redis    │    │
│  │(Persistent) │    │ (Sessions)  │    │
│  └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────┘
```

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.8+
- Redis server
- Google Cloud account (for Firestore)
- API keys for external services

### 1. Clone & Install Dependencies

```bash
git clone <repository-url>
cd travel-plan-be

# Install dependencies (using uv recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
# Copy the environment template
cp .env.template .env

# Edit .env with your configuration
nano .env
```

### 3. Required Environment Variables

**Essential (Must Have):**
```bash
# AI Model
GEMINI_API_KEY=your-gemini-api-key

# Location Services (Google Maps Platform)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Database
FIRESTORE_PROJECT_ID=your-google-cloud-project-id
```

**Optional (Recommended):**
```bash
# Weather Services (OpenWeatherMap One Call API 3.0)
OPENWEATHER_API_KEY=your-openweather-api-key

# TripAdvisor Content API
TRIPADVISOR_API_KEY=your-tripadvisor-api-key

# External APIs for enhanced functionality
AMADEUS_API_KEY=your-amadeus-api-key
AMADEUS_API_SECRET=your-amadeus-api-secret

# Redis (if not using localhost)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### 4. Google Maps Platform Setup

**Enable Required APIs:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project
3. Enable the following APIs:
   - **Required**: Maps JavaScript API, Places API, Geocoding API, Directions API, Distance Matrix API, Elevation API, Time Zone API, Static Maps API, Street View API
   - **Optional**: Address Validation API, Air Quality API, Pollen API, Solar API
4. Create an API key with appropriate restrictions
5. Set `GOOGLE_MAPS_API_KEY` in your `.env`

### 5. TripAdvisor Content API Setup

**Get TripAdvisor API Access:**
1. Visit [TripAdvisor Developer Portal](https://developer-tripadvisor.com/)
2. Sign up for a developer account
3. Create a new application
4. Get your API key from the dashboard
5. Set `TRIPADVISOR_API_KEY` in your `.env`

**Features Available:**
- 7.5+ million locations worldwide
- 1+ billion reviews and opinions
- Up to 5 photos per location
- Up to 5 reviews per location
- 29 language support
- Pay-as-you-go model (first 5000 calls free per month)

### 6. Database Setup

**Firestore:**
1. Create a Google Cloud project (can be the same as Maps Platform)
2. Enable Firestore API
3. Download service account credentials (optional for local dev)
4. Set `FIRESTORE_PROJECT_ID` in your `.env`

**Redis:**
```bash
# Install Redis (Ubuntu/Debian)
sudo apt install redis-server

# Start Redis
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping
```

### 6. Test the Setup

```bash
# Test Gemini API integration
python test_gemini_integration.py

# Test Google Maps Platform integration
python test_google_maps_integration.py

# Test OpenWeatherMap integration
python test_openweather_integration.py

# Test TripAdvisor Content API integration
python test_tripadvisor_integration.py

# Should show:
# ✅ All integration tests passed!
# 🎯 Your AI Travel Planner is ready to use comprehensive APIs!
```

### 7. Run the Server

```bash
# Development mode
python run_server.py --dev

# Production mode
python run_server.py

# Custom port
python run_server.py --port 8080
```

## 🧪 Testing

### Integration Tests
```bash
# Test Gemini API integration
python test_gemini_integration.py

# Test OpenWeatherMap integration
python test_openweather_integration.py

# Test Google Maps Platform integration
python test_google_maps_integration.py

# Test TripAdvisor Content API integration
python test_tripadvisor_integration.py

# Test MCP tools integration
python test_travel_mcp_integration.py
```

### API Testing
```bash
# Server health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 📚 API Documentation

### Core Endpoints

**Health & Status:**
- `GET /health` - System health check
- `GET /status` - Detailed system status

**User Management:**
- `POST /users/profile` - Create/update user profile
- `GET /users/profile` - Get user profile
- `POST /users/onboarding` - Start user onboarding

**Trip Planning:**
- `POST /trips/create` - Start new trip planning
- `POST /trips/{trip_id}/continue` - Continue planning process
- `POST /trips/{trip_id}/confirm-day` - Confirm daily itinerary
- `POST /trips/{trip_id}/revise` - Request itinerary revision

**Trip Monitoring:**
- `POST /trips/{trip_id}/start-monitoring` - Start real-time monitoring
- `GET /trips/{trip_id}/status` - Get trip status
- `POST /trips/{trip_id}/handle-disruption` - Handle disruptions

### Interactive API Documentation
Visit `http://localhost:8000/docs` when the server is running for full interactive API documentation.

## 🔧 Configuration

### AI Model Settings
```bash
GEMINI_MODEL=gemini-1.5-pro      # Model version
GEMINI_TEMPERATURE=0.1           # Creativity (0.0-1.0)
GEMINI_MAX_TOKENS=4096          # Response length
```

### Agent Configuration
```bash
MAX_AGENT_ITERATIONS=10          # Max planning iterations
AGENT_TIMEOUT_SECONDS=120        # Agent timeout
MAX_TRIP_DAYS=30                # Maximum trip duration
MAX_ACTIVITIES_PER_DAY=8        # Activities per day limit
```

### Security Settings
```bash
SECRET_KEY=your-super-secret-key         # JWT secret
ACCESS_TOKEN_EXPIRE_MINUTES=30          # Token expiration
```

## 🚀 Development

### Project Structure
```
travel-plan-be/
├── src/
│   ├── agents/                 # Multi-agent system
│   │   ├── base_agent.py      # Base agent class
│   │   ├── orchestrator_agent.py
│   │   ├── profiler_agent.py
│   │   ├── itinerary_agent.py
│   │   ├── critique_agent.py
│   │   └── monitor_agent.py
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
│   │   └── travel_mcp_tool.py
│   └── utils/                 # Utilities
│       ├── gemini_client.py
│       └── __init__.py
├── requirements.txt           # Dependencies
├── run_server.py             # Server runner
├── test_gemini_integration.py # Integration tests
└── .env.template             # Environment template
```

### Adding New Agents
1. Create new agent class inheriting from `BaseAgent`
2. Implement `execute()` and `get_prompt_template()` methods
3. Register in `AgentRegistry`
4. Add to orchestrator workflow

### Adding New MCP Tools
1. Create tool class inheriting from `BaseMCPTool`
2. Implement `execute()` and `get_schema()` methods
3. Register in `tool_registry`
4. Add to agent tool lists

## 🔍 Monitoring & Observability

### Logging
- Structured logging with configurable levels
- Agent-specific log namespaces
- File and console output

### Performance Metrics
- Agent execution times and success rates
- Tool usage statistics
- Memory and state tracking

### Health Checks
- Database connection monitoring
- Agent status tracking
- External API availability

## 🌍 Production Deployment

### Environment Setup
```bash
# Production environment variables
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Strong security settings
SECRET_KEY=generate-strong-random-key
REDIS_PASSWORD=secure-redis-password
```

### Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ src/
COPY run_server.py .

EXPOSE 8000
CMD ["python", "run_server.py"]
```

### Scaling Considerations
- Use production WSGI server (Gunicorn + Uvicorn)
- Redis clustering for session management
- Load balancer for multiple instances
- Monitoring and alerting setup

## 📊 Performance & Costs

### Gemini API Usage
- **Model**: Gemini 1.5 Pro
- **Cost**: Pay-per-token pricing
- **Optimization**: Smart caching and context management

### Expected Performance
- **Response Time**: < 2s for simple requests
- **Planning Time**: 30-60s for full day planning
- **Concurrent Users**: 100+ with proper scaling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

### Common Issues

**Gemini API Errors:**
- Check your API key is valid
- Verify you have sufficient quota
- Review rate limiting

**Database Connection Issues:**
- Verify Firestore project ID
- Check Redis server is running
- Review network connectivity

**Tool Integration Problems:**
- Validate API keys for external services
- Check MCP tool configurations
- Review tool permissions

### Getting Help
- Check the [troubleshooting guide](docs/troubleshooting.md)
- Review API documentation at `/docs`
- Run integration tests to verify setup

---

**Built with ❤️ using Google Gemini API, FastAPI, and the Model Context Protocol (MCP)**
