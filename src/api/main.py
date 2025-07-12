import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from src.config.settings import settings
from src.database import db_manager
from src.agents import agent_registry
from src.agents.base_agent import AgentMessage

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_main")


# Hardcoded user ID
USER_ID = "1"


# Pydantic models for Chat API
class ChatRequest(BaseModel):
    """Chat request from user."""
    message: str


class ChatResponse(BaseModel):
    """Response from chat API."""
    success: bool
    message: str
    trip_id: Optional[str] = None
    extracted_info: Optional[Dict[str, Any]] = None
    trip_details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


# Application lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    logger.info("Starting AI Travel Planner API")
    
    # Startup
    try:
        # Test database connections
        health = await db_manager.health_check()
        if not health['overall']:
            logger.warning(f"Database health check failed: {health}")
            logger.warning("Server will start anyway and attempt to reconnect to database")
        else:
            logger.info("Database connections established")
        yield
        
    except Exception as e:
        logger.warning(f"Database connection issue during startup: {str(e)}")
        logger.warning("Server will start anyway and attempt to reconnect to database")
        yield
    
    # Shutdown
    logger.info("Shutting down AI Travel Planner API")
    await db_manager.close_connections()


# Create FastAPI application
app = FastAPI(
    title="AI Travel Planner API",
    description="Backend API for AI Travel Planner - An Agentic Travel Companion",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Chat API Endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_planner(chat_request: ChatRequest):
    """
    Main chat endpoint for trip planning.
    
    Logic:
    1. Call Main AI to classify and extract information (places, foods, datetime, etc.)
    2. Call appropriate AI agents based on extracted information
    3. Get trip details from agents
    4. Store trip details in database
    5. Return response
    """
    try:
        logger.info(f"Chat request from user {USER_ID}: {chat_request.message[:100]}...")
        
        # Step 1: Call Main AI to classify and extract information
        extracted_info = await _extract_trip_information(chat_request.message)
        
        if not extracted_info:
            return ChatResponse(
                success=False,
                message="I couldn't understand your trip request. Please provide more details about where you want to go and when.",
                error="No trip information extracted"
            )
        
        # Step 2: Call appropriate AI agents based on extracted information
        trip_details = await _coordinate_ai_agents(extracted_info)
        
        if not trip_details:
            return ChatResponse(
                success=False,
                message="I encountered an error while planning your trip. Please try again.",
                error="Failed to generate trip details"
            )
        
        # Step 3: Store trip details in database
        trip_id = await _store_trip_details(trip_details)
        
        # Step 4: Return response
        return ChatResponse(
            success=True,
            message=_generate_response_message(trip_details),
            trip_id=trip_id,
            extracted_info=extracted_info,
            trip_details=trip_details
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return ChatResponse(
            success=False,
            message="I'm sorry, something went wrong. Please try again.",
            error=str(e)
        )


# Helper functions

async def _extract_trip_information(message: str) -> Optional[Dict[str, Any]]:
    """
    Call Main AI to classify and extract trip information from user message.
    
    Extracts:
    - Places/destinations
    - Dates and duration
    - Food preferences
    - Activities/interests
    - Budget information
    - Number of travelers
    """
    try:
        # Create AI message for information extraction
        ai_message = AgentMessage(
            agent_id="api",
            message_type="extract_trip_info",
            content={
                "user_id": USER_ID,
                "user_message": message
            }
        )
        
        # Send to orchestrator agent for AI processing
        response = await agent_registry.send_message("orchestrator", ai_message)
        
        if response.success and response.data:
            return response.data.get("extracted_info")
        else:
            # Fallback: simple keyword-based extraction
            return _simple_extraction_fallback(message)
            
    except Exception as e:
        logger.error(f"Error extracting trip information: {str(e)}")
        return _simple_extraction_fallback(message)


def _simple_extraction_fallback(message: str) -> Optional[Dict[str, Any]]:
    """Simple keyword-based extraction as fallback."""
    message_lower = message.lower()
    
    # Extract destinations
    destinations = ["paris", "tokyo", "new york", "london", "rome", "barcelona", "amsterdam", "berlin", "prague", "vienna"]
    found_destination = None
    for dest in destinations:
        if dest in message_lower:
            found_destination = dest.title()
            break
    
    if not found_destination:
        return None
    
    # Extract duration
    duration_days = 5  # Default
    if "week" in message_lower or "7 days" in message_lower:
        duration_days = 7
    elif "month" in message_lower or "30 days" in message_lower:
        duration_days = 30
    elif "3 days" in message_lower:
        duration_days = 3
    elif "10 days" in message_lower:
        duration_days = 10
    
    # Extract food preferences
    food_preferences = []
    food_keywords = ["pizza", "sushi", "pasta", "steak", "seafood", "vegetarian", "vegan", "street food"]
    for food in food_keywords:
        if food in message_lower:
            food_preferences.append(food)
    
    # Extract activities
    activities = []
    activity_keywords = ["museum", "shopping", "hiking", "beach", "culture", "history", "nightlife", "relax"]
    for activity in activity_keywords:
        if activity in message_lower:
            activities.append(activity)
    
    # Calculate dates (30 days from now)
    from datetime import datetime, timedelta
    start_date = datetime.now().date() + timedelta(days=30)
    end_date = start_date + timedelta(days=duration_days - 1)
    
    return {
        "destination": found_destination,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "duration_days": duration_days,
        "food_preferences": food_preferences,
        "activities": activities,
        "travelers": 1,  # Default
        "budget_level": "medium"  # Default
    }


async def _coordinate_ai_agents(extracted_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Coordinate AI agents to generate trip details.
    
    Agents used:
    - Profiler Agent: Create user profile if needed
    - Itinerary Agent: Generate detailed itinerary
    - Critique Agent: Review and improve itinerary
    """
    try:
        # Step 1: Check if user profile exists, create if needed
        user_profile = await _ensure_user_profile(extracted_info)
        
        # Step 2: Generate itinerary
        itinerary = await _generate_itinerary(extracted_info, user_profile)
        
        if not itinerary:
            return None
        
        # Step 3: Critique and improve itinerary
        improved_itinerary = await _critique_itinerary(itinerary, user_profile)
        
        # Step 4: Compile trip details
        trip_details = {
            "user_id": USER_ID,
            "destination": extracted_info["destination"],
            "start_date": extracted_info["start_date"],
            "end_date": extracted_info["end_date"],
            "duration_days": extracted_info["duration_days"],
            "user_profile": user_profile,
            "itinerary": improved_itinerary,
            "extracted_preferences": extracted_info,
            "status": "planned",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return trip_details
        
    except Exception as e:
        logger.error(f"Error coordinating AI agents: {str(e)}")
        return None


async def _ensure_user_profile(extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure user profile exists, create if needed."""
    try:
        # Check if profile exists in memory
        existing_profile = agent_registry.get_agent("orchestrator").get_memory(f"user_profile_{USER_ID}", scope="user")
        
        if existing_profile:
            return existing_profile
        
        # Create new profile based on extracted info
        profile = {
            "user_id": USER_ID,
            "preferences": {
                "destinations": [extracted_info["destination"]],
                "food_preferences": extracted_info.get("food_preferences", []),
                "activities": extracted_info.get("activities", []),
                "budget_level": extracted_info.get("budget_level", "medium"),
                "travel_style": "flexible"
            },
            "traveler_info": {
                "group_size": extracted_info.get("travelers", 1),
                "travels_with": ["solo"] if extracted_info.get("travelers", 1) == 1 else ["group"]
            }
        }
        
        # Store profile in memory
        agent_registry.get_agent("orchestrator").set_memory(f"user_profile_{USER_ID}", profile, scope="user")
        
        return profile
        
    except Exception as e:
        logger.error(f"Error ensuring user profile: {str(e)}")
        return {"user_id": USER_ID, "preferences": {}, "traveler_info": {"group_size": 1}}


async def _generate_itinerary(extracted_info: Dict[str, Any], user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate itinerary using Itinerary Agent."""
    try:
        # Create message for itinerary generation
        itinerary_message = AgentMessage(
            agent_id="api",
            message_type="generate_itinerary",
            content={
                "user_profile": user_profile,
                "destination": extracted_info["destination"],
                "start_date": extracted_info["start_date"],
                "end_date": extracted_info["end_date"],
                "duration_days": extracted_info["duration_days"],
                "preferences": extracted_info
            }
        )
        
        # Send to itinerary agent
        response = await agent_registry.send_message("itinerary", itinerary_message)
        
        if response.success:
            return response.data.get("itinerary")
        else:
            logger.error(f"Itinerary generation failed: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating itinerary: {str(e)}")
        return None


async def _critique_itinerary(itinerary: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Critique and improve itinerary using Critique Agent."""
    try:
        # Create message for critique
        critique_message = AgentMessage(
            agent_id="api",
            message_type="critique_itinerary",
            content={
                "itinerary": itinerary,
                "user_profile": user_profile
            }
        )
        
        # Send to critique agent
        response = await agent_registry.send_message("critique", critique_message)
        
        if response.success:
            critique_result = response.data.get("critique_result", {})
            
            # If critique suggests improvements, revise itinerary
            if not critique_result.get("approved", False):
                revised_itinerary = await _revise_itinerary(itinerary, critique_result)
                return revised_itinerary if revised_itinerary else itinerary
            
            return itinerary
        else:
            logger.error(f"Critique failed: {response.error}")
            return itinerary
            
    except Exception as e:
        logger.error(f"Error critiquing itinerary: {str(e)}")
        return itinerary


async def _revise_itinerary(itinerary: Dict[str, Any], critique_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Revise itinerary based on critique feedback."""
    try:
        # Create revision message
        revision_message = AgentMessage(
            agent_id="api",
            message_type="revise_itinerary",
            content={
                "itinerary": itinerary,
                "critique_feedback": critique_result.get("feedback", ""),
                "issues": critique_result.get("issues", [])
            }
        )
        
        # Send to itinerary agent for revision
        response = await agent_registry.send_message("itinerary", revision_message)
        
        if response.success:
            return response.data.get("revised_itinerary")
        else:
            logger.error(f"Itinerary revision failed: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"Error revising itinerary: {str(e)}")
        return None


async def _store_trip_details(trip_details: Dict[str, Any]) -> str:
    """Store trip details in database."""
    try:
        # Generate trip ID
        trip_id = f"trip_{USER_ID}_{int(datetime.utcnow().timestamp())}"
        trip_details["trip_id"] = trip_id
        
        # Store in database
        success = await db_manager.save_trip_details(trip_details)
        
        if success:
            logger.info(f"Trip details stored successfully: {trip_id}")
            return trip_id
        else:
            logger.error("Failed to store trip details in database")
            return trip_id  # Return ID even if storage failed
            
    except Exception as e:
        logger.error(f"Error storing trip details: {str(e)}")
        # Return a generated ID even if storage fails
        return f"trip_{USER_ID}_{int(datetime.utcnow().timestamp())}"


def _generate_response_message(trip_details: Dict[str, Any]) -> str:
    """Generate user-friendly response message."""
    destination = trip_details.get("destination", "your destination")
    duration = trip_details.get("duration_days", 0)
    
    base_message = f"Great! I've planned your {duration}-day trip to {destination}. "
    
    itinerary = trip_details.get("itinerary", {})
    if itinerary:
        base_message += "Here's what I've arranged for you:\n\n"
        
        # Add highlights from itinerary
        days = itinerary.get("days", [])
        if days:
            base_message += f"Day 1: {days[0].get('theme', 'Exploring the city')}\n"
            if len(days) > 1:
                base_message += f"Day 2: {days[1].get('theme', 'Cultural experiences')}\n"
            if len(days) > 2:
                base_message += "... and more exciting activities!\n"
        
        base_message += "\nYour trip is ready! Would you like me to make any adjustments?"
    else:
        base_message += "I'm working on the detailed itinerary. Would you like me to continue?"
    
    return base_message


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    ) 