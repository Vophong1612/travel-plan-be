# AI Travel Planner - Backend

A complete agentic AI travel planning system that creates personalized, dynamic travel itineraries using **Google Gemini API**, and a modern backend architecture.

## 🚀 Overview

AI Travel Planner is not just another trip generator - it's an **autonomous AI system** that plans, monitors, and adapts your travel experience in real-time. Built with a multi-agent architecture, it provides:

- **Conversational Trip Planning**: Natural language interaction for planning
- **Day-by-Day Itinerary Generation**: Detailed daily plans.
- **Real-time Monitoring**: Proactive disruption detection and replanning (future capability)
- **Personalized Recommendations**: Deep user profiling for tailored experiences
- **Dynamic Adaptation**: Automatic replanning when things go wrong (future capability)

## ✨ Key Features

### 🤖 **Multi-Agent Intelligence**
- **Orchestrator Agent**: Master coordinator managing the entire workflow
- **Profiler Agent**: Conducts conversational user onboarding and profiling
- **Itinerary Agent**: Generates detailed daily itineraries using real-time data
- **Critique Agent**: Quality assurance and itinerary validation
- **Monitor Agent**: Real-time trip monitoring for disruptions (future capability)

### 🧠 **AI-Powered Planning**
- **Google Gemini 1.5 Pro**: Advanced reasoning and planning capabilities
- **Contextual Memory**: Learns and remembers user preferences via the database.
- **Quality Assurance**: Built-in critique and revision loops
- **Natural Language**: Conversational interaction throughout

### 🛠️ **Tool Integration**
- **Google Maps**: Location search, travel times, route optimization
- **Weather Services**: Current conditions and forecasts.
- **TripAdvisor**: Rich content for locations, including reviews and photos.

### 🗄️ **Robust Data Layer**
- **MongoDB**: A flexible, scalable NoSQL database for storing user profiles, trip data, and agent memory.

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
│         ┌───────────────────┐           │
│         │     MongoDB       │           │
│         │ (Persistent Data) │           │
│         └───────────────────┘           │
└─────────────────────────────────────────┘
```

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.8+
- Docker and Docker Compose

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

# Database (MongoDB)
# Option 1: Full URI (takes precedence)
MONGODB_URI=mongodb://admin:password123@localhost:27017/travel_planner?authSource=admin

# Option 2: Individual components (if URI is not set)
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password123
MONGODB_DATABASE=travel_planner
MONGODB_AUTH_DATABASE=admin
```

**Optional (Recommended):**
```bash
# Weather Services (OpenWeatherMap One Call API 3.0)
OPENWEATHER_API_KEY=your-openweather-api-key

# TripAdvisor Content API
TRIPADVISOR_API_KEY=your-tripadvisor-api-key
```

### 4. Database Setup with Docker

This project uses MongoDB as its database. The easiest way to get started is with Docker Compose.

```bash
# Start MongoDB and Mongo Express UI
docker-compose up -d
```

This command will:
- Start a MongoDB container named `travel-planner-mongodb` on port `27017`.
- Start a Mongo Express container named `travel-planner-mongo-ui` on port `8081`.
- Create a persistent volume to store your database data.
- Connect both containers to a shared network.

You can access the Mongo Express web UI at `http://localhost:8081` to view and manage your database.

### 5. Integration Tests

Before running the main application, you can verify that your external API connections are configured correctly. Test files are located in the `tool_tests/` directory.

```bash
# Test Gemini API integration
python tool_tests/test_gemini_integration.py

# Test Google Maps Platform integration
python tool_tests/test_google_maps_integration.py

# Test OpenWeatherMap integration
python tool_tests/test_openweather_integration.py

# Test TripAdvisor Content API integration
python tool_tests/test_tripadvisor_integration.py
```

### 6. Run the Server

```bash
# Development mode
python run_server.py --dev

# Production mode
python run_server.py

# Custom port
python run_server.py --port 8080
```

## 🧪 Testing

### API Testing
```bash
# Server health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## 📚 API Documentation

The primary interaction with the service is through the `/chat` endpoint.

### Core Endpoints

**Health & Status:**
- `GET /health` - System health check.
- `GET /` - Basic API information.

**Trip Planning:**
- `POST /chat` - Main endpoint for all conversational trip planning. Send user messages here to create and manage travel plans.

### Interactive API Documentation
Visit `http://localhost:8000/docs` when the server is running for full interactive API documentation and to try out the endpoints.

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

## 🚀 Development

### Project Structure
```
travel-plan-be/
├── src/
│   ├── agents/                 # Multi-agent system
│   │   ├── base_agent.py
│   │   ├── orchestrator_agent.py
│   │   ├── profiler_agent.py
│   │   ├── itinerary_agent.py
│   │   ├── critique_agent.py
│   │   └── monitor_agent.py
│   ├── api/                    # FastAPI application
│   │   └── main.py
│   ├── config/                 # Configuration
│   │   └── settings.py
│   ├── database/               # Database layer
│   │   └── mongodb_client.py
│   ├── models/                 # Data models (Pydantic)
│   │   ├── user.py
│   │   └── trip.py
│   ├── tools/                  # Tools for agents
│   │   ├── base_mcp_tool.py
│   │   ├── google_maps_tool.py
│   │   ├── weather_tool.py
│   │   └── tripadvisor_tool.py
│   └── utils/                  # Utilities
│       └── gemini_client.py
├── tool_tests/                 # Integration tests for tools
├── requirements.txt            # Dependencies
├── run_server.py               # Server runner
├── docker-compose.yml          # Docker setup for MongoDB
└── .env.template               # Environment template
```

### Adding New Agents
1. Create new agent class inheriting from `BaseAgent`
2. Implement `execute()` and `get_prompt_template()` methods
3. Register in `agent_registry`
4. Add to orchestrator workflow

### Adding New Tools
1. Create tool class inheriting from `BaseMCPTool`
2. Implement `execute()` and `get_schema()` methods
3. Register in `tool_registry`
4. Add to agent tool lists

## 🌍 Production Deployment

### Environment Setup
```bash
# Production environment variables
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Strong security settings
MONGODB_URI=your-production-mongodb-uri
```

### Docker Deployment (Optional)
A `Dockerfile` can be created for containerizing the main application.
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
# Use uv for faster installation
RUN pip install uv && uv pip install -r requirements.txt --no-cache-dir

COPY src/ src/
COPY run_server.py .

EXPOSE 8000
CMD ["python", "run_server.py"]
```

### Scaling Considerations
- Use a production WSGI server (Gunicorn + Uvicorn).
- Use a managed MongoDB service (like MongoDB Atlas) for scalability and reliability.
- Use a load balancer for multiple application instances.
- Set up robust monitoring and alerting.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

---

**Built with ❤️ using Google Gemini API, FastAPI, and MongoDB.**
