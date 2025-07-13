import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta, date

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from src.config.settings import settings
from src.database import db_manager
from src.agents import agent_registry
from src.agents.base_agent import AgentMessage
from src.utils.gemini_client import gemini_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_main")


# Hardcoded user ID
USER_ID = "1"


# In-memory store for user context (for demo purposes)
# In a real application, this should be in a database or a proper session manager.
global_user_context = ""


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


# Health Check Endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify server and database status.
    """
    try:
        # Check database health
        db_health = await db_manager.health_check()
        
        return {
            "status": "healthy" if db_health['overall'] else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": db_health,
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "version": "1.0.0"
        }


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "AI Travel Planner API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


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
    logger.info(f"CHAT API: Processing request for user {USER_ID} - '{chat_request.message[:50]}...'")
    global global_user_context
    
    try:
        if global_user_context != "":
            # call LLM to combine the new message with the user context and update the user context
            logger.info("Combining new message with existing user context.")
            prompt = f"Please combine the user's new message with the existing conversation context. The goal is to create a consolidated, updated context that reflects the latest information and nuances from the new message, while maintaining the key details from the prior context.  It should be a summary of the whole conversation state. Only return the updated user context itself, with no extra commentary or labels.\n\nNew Message: '{chat_request.message}'\n\nExisting Context: '{global_user_context}'"
            
            try:
                updated_context = await gemini_client.generate_response(prompt)
                global_user_context = updated_context
                logger.info(f"Updated user context: {global_user_context}")
            except Exception as e:
                logger.error(f"Failed to update user context with Gemini: {e}")
        else:
            # If no context, the new message becomes the initial context
             global_user_context = chat_request.message
        
        # Step 1: Call Main AI to classify and extract information
        extracted_info = await _extract_trip_information(global_user_context)
        
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
        response_message = _generate_response_message(trip_details)
        global_user_context = "User question: \n" + global_user_context + "\n\n" + "User context: \n" + response_message
        return ChatResponse(
            success=True,
            message=response_message,
            trip_id=trip_id,
            extracted_info=extracted_info,
            trip_details=trip_details
        )
        
    except Exception as e:
        logger.error(f"CHAT API ERROR: {str(e)}")
        return ChatResponse(
            success=False,
            message="I'm sorry, something went wrong. Please try again.",
            error=str(e)
        )


# Helper functions

def _parse_date_safely(date_value: Union[str, date, datetime]) -> date:
    """
    Safely parse a date value that could be a string, date object, or datetime object.
    Returns a date object.
    """
    if isinstance(date_value, str):
        return datetime.fromisoformat(date_value).date()
    elif isinstance(date_value, datetime):
        return date_value.date()
    elif isinstance(date_value, date):
        return date_value
    else:
        # Fallback: assume it's a string representation
        return datetime.fromisoformat(str(date_value)).date()


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
    logger.info(f"EXTRACT INFO: Processing message '{message[:30]}...'")
    
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
        logger.error(f"EXTRACT INFO ERROR: {str(e)}")
        return _simple_extraction_fallback(message)


def _simple_extraction_fallback(message: str) -> Optional[Dict[str, Any]]:
    """Simple keyword-based extraction as fallback."""
    logger.info(f"FALLBACK EXTRACT: Processing message '{message[:30]}...'")
    
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
    - Itinerary Agent: Generate detailed itinerary for each day
    - Critique Agent: Review and improve itinerary
    """
    logger.info(f"COORDINATE AGENTS: Processing destination '{extracted_info.get('destination', 'unknown')}'")
    
    try:
        # Step 1: Check if user profile exists, create if needed
        user_profile = await _ensure_user_profile(extracted_info)
        
        # Step 2: Generate itinerary for each day
        duration_days = extracted_info["duration_days"]
        daily_itineraries = []
        
        for day_number in range(1, duration_days + 1):
            logger.info(f"COORDINATE AGENTS: Generating itinerary for day {day_number}/{duration_days}")
            
            # Generate itinerary for this specific day
            day_itinerary = await _generate_daily_itinerary(extracted_info, user_profile, day_number)
            
            if not day_itinerary:
                logger.error(f"COORDINATE AGENTS ERROR: Failed to generate itinerary for day {day_number}")
                return None
            
            # Step 3: Critique and improve this day's itinerary
            improved_day_itinerary = await _critique_itinerary(day_itinerary, user_profile)
            daily_itineraries.append(improved_day_itinerary)
        
        # Step 4: Compile trip details
        trip_details = {
            "user_id": USER_ID,
            "destination": extracted_info["destination"],
            "start_date": extracted_info["start_date"],
            "end_date": extracted_info["end_date"],
            "duration_days": extracted_info["duration_days"],
            "user_profile": user_profile,
            "itinerary": daily_itineraries,  # Now a list of daily itineraries
            "extracted_preferences": extracted_info,
            "status": "planned",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return trip_details
        
    except Exception as e:
        logger.error(f"COORDINATE AGENTS ERROR: {str(e)}")
        return None


async def _ensure_user_profile(extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure user profile exists, create if needed."""
    logger.info(f"ENSURE PROFILE: Checking profile for user {USER_ID}")
    
    try:
        # Check if profile exists in memory
        existing_profile = agent_registry.get_agent("orchestrator").get_memory(f"user_profile_{USER_ID}", scope="user")
        
        if existing_profile:
            return existing_profile
        
        # Create new profile based on extracted info
        profile = {
            "user_id": USER_ID, 
            "preferences": {
                "travel_style": ["cultural"],  # Should be a list of TravelStyle enums
                "pace": "moderate",
                "interests": extracted_info.get("activities", []),
                "dietary_restrictions": None,
                "accommodation_preferences": None,
                "transport_preferences": None,
                "activity_preferences": None
            }, 
            "traveler_info": {
                "group_size": int(extracted_info.get("travelers") or 1),
                "travels_with": ["solo"] if int(extracted_info.get("travelers") or 1) == 1 else ["friends"],
                "ages": None,
                "accessibility_needs": None
            },
            "budget": {
                "level": "mid-range",  # Default budget level
                "currency": "USD",
                "daily_max": None,
                "total_max": None
            }
        }
        
        # Store profile in memory
        agent_registry.get_agent("orchestrator").set_memory(f"user_profile_{USER_ID}", profile, scope="user")
        
        return profile
        
    except Exception as e:
        logger.error(f"ENSURE PROFILE ERROR: {str(e)}")
        return {
            "user_id": USER_ID, 
            "preferences": {
                "travel_style": ["cultural"],
                "pace": "moderate",
                "interests": [],
                "dietary_restrictions": None,
                "accommodation_preferences": None,
                "transport_preferences": None,
                "activity_preferences": None
            }, 
            "traveler_info": {
                "group_size": 1,
                "travels_with": ["solo"],
                "ages": None,
                "accessibility_needs": None
            },
            "budget": {
                "level": "mid-range",
                "currency": "USD",
                "daily_max": None,
                "total_max": None
            }
        }


async def _generate_daily_itinerary(extracted_info: Dict[str, Any], user_profile: Dict[str, Any], day_number: int) -> Optional[Dict[str, Any]]:
    """Generate itinerary for a specific day using Itinerary Agent."""
    logger.info(f"GENERATE DAILY ITINERARY: Creating itinerary for day {day_number} in {extracted_info.get('destination', 'unknown')}")
    
    try:
        # Calculate the specific date for this day
        start_date = _parse_date_safely(extracted_info["start_date"])
        day_date = start_date + timedelta(days=day_number - 1)
        
        # Create message for itinerary generation
        itinerary_message = AgentMessage(
            agent_id="api",
            message_type="generate_itinerary",
            content={
                "user_profile": user_profile,
                "destination": extracted_info["destination"],
                "date": day_date.isoformat(),
                "day_index": day_number,
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
            logger.error(f"GENERATE DAILY ITINERARY ERROR: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"GENERATE DAILY ITINERARY ERROR: {str(e)}")
        return None


async def _generate_itinerary(extracted_info: Dict[str, Any], user_profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate itinerary using Itinerary Agent."""
    logger.info(f"GENERATE ITINERARY: Creating itinerary for {extracted_info.get('destination', 'unknown')}")
    
    try:
        # Create message for itinerary generation
        itinerary_message = AgentMessage(
            agent_id="api",
            message_type="generate_itinerary",
            content={
                "user_profile": user_profile,
                "destination": extracted_info["destination"],
                "date": extracted_info["start_date"],  # Pass start_date as date for the itinerary agent
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
            logger.error(f"GENERATE ITINERARY ERROR: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"GENERATE ITINERARY ERROR: {str(e)}")
        return None


async def _critique_itinerary(itinerary: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Critique and improve itinerary using Critique Agent."""
    logger.info("CRITIQUE ITINERARY: Reviewing itinerary for improvements")
    
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
            logger.error(f"CRITIQUE ITINERARY ERROR: {response.error}")
            return itinerary
            
    except Exception as e:
        logger.error(f"CRITIQUE ITINERARY ERROR: {str(e)}")
        return itinerary


async def _revise_itinerary(itinerary: Dict[str, Any], critique_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Revise itinerary based on critique feedback."""
    logger.info("REVISE ITINERARY: Revising itinerary based on critique feedback")
    
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
            logger.error(f"REVISE ITINERARY ERROR: {response.error}")
            return None
            
    except Exception as e:
        logger.error(f"REVISE ITINERARY ERROR: {str(e)}")
        return None


async def _store_trip_details(trip_details: Dict[str, Any]) -> str:
    """Store trip details in database."""
    logger.info(f"STORE TRIP: Storing trip details for destination '{trip_details.get('destination', 'unknown')}'")
    
    try:
        # Generate trip ID
        trip_id = f"trip_{USER_ID}_{int(datetime.utcnow().timestamp())}"
        trip_details["trip_id"] = trip_id
        
        # Store in database
        success = await db_manager.save_trip_details(trip_details)
        
        if success:
            return trip_id
        else:
            logger.error("STORE TRIP ERROR: Failed to store trip details in database")
            return trip_id  # Return ID even if storage failed
            
    except Exception as e:
        logger.error(f"STORE TRIP ERROR: {str(e)}")
        # Return a generated ID even if storage fails
        return f"trip_{USER_ID}_{int(datetime.utcnow().timestamp())}"


def _generate_response_message(trip_details: Dict[str, Any]) -> str:
    """Generate user-friendly response message with comprehensive trip details table."""
    logger.info(f"GENERATE RESPONSE: Creating response for destination '{trip_details.get('destination', 'unknown')}'")
    
    destination = trip_details.get("destination", "your destination")
    duration = trip_details.get("duration_days", 0)
    
    # Create comprehensive trip details table wrapped in scrollable div
    message = f'<div style="overflow-x: auto;">\n\nGreat! I\'ve planned your {duration}-day trip to {destination}. Here\'s your complete travel plan:\n\n'
    
    # Trip Overview Table
    message += "## 🌍 Trip Overview\n\n"
    message += "| **Field** | **Details** |\n"
    message += "|-----------|-------------|\n"
    message += f"| **Destination** | {destination} |\n"
    message += f"| **Duration** | {duration} days |\n"
    message += f"| **Start Date** | {trip_details.get('start_date', 'Not specified')} |\n"
    message += f"| **End Date** | {trip_details.get('end_date', 'Not specified')} |\n"
    message += f"| **Status** | {trip_details.get('status', 'Planned').title()} |\n"
    message += f"| **Created** | {trip_details.get('created_at', 'Now')} |\n\n"
    
    # Itinerary Details Table
    itinerary = trip_details.get("itinerary", []) # Itinerary is now a list of daily itineraries
    if itinerary:
        message += "## 📅 Daily Itinerary\n\n"
        
        for day_num, day_itinerary in enumerate(itinerary, 1):
            message += f"### Day {day_num}: {day_itinerary.get('theme', 'Exploring')}\n\n"
            message += "| **Time** | **Activity** | **Location** | **Cost** |\n"
            message += "|----------|-------------|-------------|----------|\n"
            
            activities = day_itinerary.get("activities", [])
            if activities:
                for activity in activities:
                    start_time = activity.get("start_time", "TBD")
                    if start_time and start_time != "TBD":
                        try:
                            # Handle both datetime objects and strings
                            if isinstance(start_time, str):
                                time_str = start_time.split("T")[1][:5] if "T" in start_time else start_time
                            else:
                                time_str = start_time.strftime("%H:%M") if hasattr(start_time, 'strftime') else str(start_time)
                        except:
                            time_str = "TBD"
                    else:
                        time_str = "TBD"
                    
                    name = activity.get("name", "Activity")
                    activity_type = activity.get("type", "Unknown")  # Keep in background
                    location = activity.get("location", {}).get("name", "Location TBD")
                    duration = f"{activity.get('duration_minutes', 0)} min" if activity.get('duration_minutes') else "TBD"  # Keep in background
                    
                    # Safely handle cost calculation
                    try:
                        activity_cost = float(activity.get('cost', 0) or 0)
                        cost = f"${activity_cost:.2f}" if activity_cost > 0 else "Free"
                    except (ValueError, TypeError):
                        cost = "Free"
                    
                    message += f"| {time_str} | {name} | {location} | {cost} |\n"
        
        message += "\n"
    
    # Budget Summary
    message += "## 💰 Budget Summary\n\n"
    message += "| **Category** | **Amount** |\n"
    message += "|-------------|------------|\n"
    
    # Calculate total cost from all daily itineraries
    total_cost = 0.0
    try:
        if isinstance(itinerary, list):
            for day_itinerary in itinerary:
                day_cost = float(day_itinerary.get("total_cost", 0) or 0)
                total_cost += day_cost
        else:
            total_cost = float(itinerary.get("total_cost", 0) or 0)
    except (ValueError, TypeError):
        total_cost = 0.0
    
    try:
        estimated_cost = float(trip_details.get("estimated_total_cost", 0) or 0)
    except (ValueError, TypeError):
        estimated_cost = 0.0
    
    try:
        duration_num = int(duration) if duration else 1
    except (ValueError, TypeError):
        duration_num = 1
    
    budget_currency = trip_details.get("budget_currency", "USD")
    max_cost = max(total_cost, estimated_cost)
    daily_average = max_cost / duration_num if duration_num > 0 else 0
    
    message += f"| **Estimated Total** | {budget_currency} {max_cost:.2f} |\n"
    message += f"| **Daily Average** | {budget_currency} {daily_average:.2f} |\n"
    
    # User preferences summary
    user_profile = trip_details.get("user_profile", {})
    if user_profile:
        message += "\n## 👤 Your Travel Preferences\n\n"
        message += "| **Preference** | **Details** |\n"
        message += "|---------------|-------------|\n"
        
        preferences = user_profile.get("preferences", {})
        traveler_info = user_profile.get("traveler_info", {})
        budget_info = user_profile.get("budget", {})
        
        if preferences.get("travel_style"):
            message += f"| **Travel Style** | {', '.join(preferences['travel_style'])} |\n"
        if preferences.get("pace"):
            message += f"| **Pace** | {preferences['pace'].title()} |\n"
        if preferences.get("interests"):
            message += f"| **Interests** | {', '.join(preferences['interests'])} |\n"
        if traveler_info.get("group_size"):
            message += f"| **Group Size** | {traveler_info['group_size']} |\n"
        if budget_info.get("level"):
            message += f"| **Budget Level** | {budget_info['level'].title()} |\n"
    
    # Weather Information
    weather_info = trip_details.get("weather_info")
    if weather_info:
        message += "\n## 🌤️ Weather Information\n\n"
        message += "| **Day** | **Condition** | **Temperature** | **Recommendations** |\n"
        message += "|--------|---------------|----------------|--------------------|\n"
        
        # Handle different weather data formats
        if isinstance(weather_info, dict):
            temp = weather_info.get("temperature", "Unknown")
            condition = weather_info.get("condition", "Unknown")
            message += f"| All Days | {condition} | {temp} | Check local forecast |\n"
    
    # Additional Information
    extracted_info = trip_details.get("extracted_preferences", {})
    if extracted_info:
        message += "\n## 📝 Additional Notes\n\n"
        message += "| **Category** | **Details** |\n"
        message += "|-------------|-------------|\n"
        
        if extracted_info.get("dietary_restrictions"):
            message += f"| **Dietary Needs** | {extracted_info['dietary_restrictions']} |\n"
        if extracted_info.get("accessibility_needs"):
            message += f"| **Accessibility** | {extracted_info['accessibility_needs']} |\n"
        if extracted_info.get("special_requests"):
            message += f"| **Special Requests** | {extracted_info['special_requests']} |\n"
    
    message += "\n---\n"
    message += "🎯 **Your trip is ready!** Would you like me to make any adjustments to your itinerary, budget, or preferences?"
    message += "\n\n</div>"
    
    return message


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    ) 