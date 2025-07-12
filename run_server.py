#!/usr/bin/env python3
"""
AI Travel Planner - Phase 2 Server Runner

This script starts the AI Travel Planner backend server with all agents and database connections.
Phase 2 includes:
- Complete multi-agent system (Orchestrator, Profiler, Itinerary, Critique, Monitor)
- Database integration (Firestore or MongoDB)
- REST API endpoints
- MCP tool integrations

Usage:
    python run_server.py [--dev] [--port PORT]
"""

import asyncio
import argparse
import logging
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from src.config.settings import settings


def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('travel_planner.log')
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


def check_environment():
    """Check that required environment variables are set."""
    # Always required
    required_vars = [
        "GOOGLE_MAPS_API_KEY",
        "GEMINI_API_KEY"
    ]
    
    # Database-specific requirements
    use_mongodb = os.getenv("USE_MONGODB", "false").lower() == "true"
    
    if use_mongodb:
        # MongoDB is configured via defaults, only check if custom values make sense
        mongodb_host = os.getenv("MONGODB_HOST", "localhost")
        mongodb_port = os.getenv("MONGODB_PORT", "27017")
        print(f"Using MongoDB: {mongodb_host}:{mongodb_port}")
    else:
        # Firestore requires project ID
        required_vars.append("FIRESTORE_PROJECT_ID")
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set the following environment variables:")
        for var in missing:
            print(f"  export {var}=your_value_here")
        print(f"\nDatabase: {'MongoDB (on-premise)' if use_mongodb else 'Firestore (Google Cloud)'}")
        print("\nFor development, you can create a .env file with these values.")
        return False
    
    return True


def print_startup_info():
    """Print startup information."""
    print("🚀 AI Travel Planner - Phase 2 Backend")
    print("=====================================")
    print(f"Environment: {'Development' if settings.debug else 'Production'}")
    print(f"Host: {settings.host}")
    print(f"Port: {settings.port}")
    print(f"Log Level: {settings.log_level}")
    
    # Database info
    if settings.use_mongodb:
        print(f"Database: MongoDB ({settings.mongodb_host}:{settings.mongodb_port})")
    else:
        print(f"Database: Firestore ({settings.firestore_project_id})")
    
    print(f"AI Model: {settings.gemini_model}")
    print("\n🔧 Phase 2 Features:")
    print("✅ Multi-Agent System (Orchestrator, Profiler, Itinerary, Critique, Monitor)")
    print("✅ Database Integration (Firestore or MongoDB)")
    print("✅ MCP Tool Integration (Google Maps, Weather)")
    print("✅ REST API Endpoints")
    print("✅ Dynamic Replanning Engine")
    print("✅ Real-time Trip Monitoring")
    print("✅ Direct Gemini API Integration")
    print("\n📡 API Documentation will be available at:")
    print(f"   http://{settings.host}:{settings.port}/docs")
    print(f"   http://{settings.host}:{settings.port}/redoc")
    print("\n🔍 Health Check:")
    print(f"   http://{settings.host}:{settings.port}/health")
    print("\n" + "="*50)


async def test_connections():
    """Test database connections."""
    try:
        from src.database import db_manager
        
        print("🔍 Testing database connections...")
        health = await db_manager.health_check()
        
        if health['persistent_db']:
            db_type = "MongoDB" if settings.use_mongodb else "Firestore"
            print(f"✅ {db_type} connection: OK")
        else:
            db_type = "MongoDB" if settings.use_mongodb else "Firestore"
            print(f"❌ {db_type} connection: FAILED")
        
        if health['overall']:
            print("✅ All database connections successful")
            return True
        else:
            print("❌ Database connection issues detected")
            return False
            
    except Exception as e:
        print(f"❌ Database connection test failed: {str(e)}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="AI Travel Planner Backend Server")
    parser.add_argument("--dev", action="store_true", help="Run in development mode with auto-reload")
    parser.add_argument("--port", type=int, default=settings.port, help="Port to run server on")
    parser.add_argument("--host", default=settings.host, help="Host to bind server to")
    parser.add_argument("--log-level", default=settings.log_level, 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(debug=args.dev)
    logger = logging.getLogger("server_runner")
    
    # Print startup info
    print_startup_info()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test connections
    if not asyncio.run(test_connections()):
        print("\n⚠️  Database connections failed. Starting server anyway...")
        print("   The server will attempt to reconnect automatically.")
    
    # Update settings if command line args provided
    if args.port != settings.port:
        settings.port = args.port
    if args.host != settings.host:
        settings.host = args.host
    if args.log_level != settings.log_level:
        settings.log_level = args.log_level
    
    # Configure uvicorn
    uvicorn_config = {
        "app": "src.api.main:app",
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level.lower(),
        "reload": args.dev,
        "reload_dirs": ["src"] if args.dev else None,
        "access_log": True,
    }
    
    print(f"\n🌟 Starting server on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        uvicorn.run(**uvicorn_config)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed to start: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 