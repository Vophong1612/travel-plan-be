import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.config.settings import settings
from src.database import db_manager
from src.agents import agent_registry
from src.agents.base_agent import AgentMessage
from src.models.user import UserProfile
from src.models.trip import Trip, TripStatus
from src.tools import tool_registry

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_main")


# Pydantic models for API requests/responses
class TripCreateRequest(BaseModel):
    destination: str
    start_date: str
    end_date: str
    

class UserResponseRequest(BaseModel):
    trip_id: str
    user_response: str
    

class ProfileConfirmationRequest(BaseModel):
    trip_id: str
    confirmed: bool
    modifications: Optional[Dict[str, Any]] = None
    

class DayConfirmationRequest(BaseModel):
    trip_id: str
    day_number: int
    confirmed: bool
    

class RevisionRequest(BaseModel):
    trip_id: str
    day_number: int
    feedback: str
    

class DisruptionRequest(BaseModel):
    trip_id: str
    disruption_type: str
    details: str
    

class FlightSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    children: int = 0
    cabin_class: str = "economy"
    currency: str = "USD"
    

class AccommodationSearchRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str
    guests: int = 1
    rooms: int = 1
    currency: str = "USD"
    

class CurrencyConversionRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    

class TravelInfoRequest(BaseModel):
    destination: str
    request_type: str  # "city_info", "airport_info", "weather_forecast"
    additional_params: Optional[Dict[str, Any]] = None
    

class BudgetCalculationRequest(BaseModel):
    destination: str
    days: int
    travelers: int = 1
    budget_level: str = "medium"  # low, medium, high
    

class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
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
            logger.error(f"Database health check failed: {health}")
            raise RuntimeError("Database connections failed")
        
        logger.info("Database connections established")
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
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


# Dependency for user authentication (simplified)
async def get_current_user(user_id: str = "demo_user") -> str:
    """Get current user ID. Simplified for demo purposes."""
    return user_id


# Error handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            success=False,
            error=f"Validation error: {str(exc)}"
        ).dict()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            error=exc.detail
        ).dict()
    )


# Health Check Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db_health = await db_manager.health_check()
        agent_status = agent_registry.list_agents()
        
        return APIResponse(
            success=True,
            data={
                "status": "healthy",
                "database": db_health,
                "agents": len(agent_status),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.get("/agents")
async def list_agents():
    """List all available agents."""
    try:
        agents = agent_registry.list_agents()
        metrics = agent_registry.get_agent_metrics()
        
        return APIResponse(
            success=True,
            data={
                "agents": agents,
                "metrics": metrics
            }
        )
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list agents"
        )


# User Profile Endpoints

@app.post("/profile")
async def create_or_update_profile(
    profile_data: Dict[str, Any],
    user_id: str = Depends(get_current_user)
):
    """Create or update user profile."""
    try:
        # Add user_id to profile data
        profile_data["user_id"] = user_id
        
        # Create UserProfile object
        user_profile = UserProfile(**profile_data)
        
        # Save to database
        success = await db_manager.save_user_profile(user_profile)
        
        if success:
            return APIResponse(
                success=True,
                data={"profile": user_profile.dict()}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save profile"
            )
            
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid profile data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile"
        )


@app.get("/profile")
async def get_user_profile(user_id: str = Depends(get_current_user)):
    """Get user profile."""
    try:
        profile = await db_manager.get_user_profile(user_id)
        
        if profile:
            return APIResponse(
                success=True,
                data={"profile": profile.dict()}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


# Trip Planning Endpoints

@app.post("/trips")
async def start_trip_planning(
    trip_request: TripCreateRequest,
    user_id: str = Depends(get_current_user)
):
    """Initiate a new trip planning session."""
    try:
        # Send message to orchestrator agent
        message = AgentMessage(
            agent_id="api",
            message_type="start_trip_planning",
            content={
                "user_id": user_id,
                "destination": trip_request.destination,
                "start_date": trip_request.start_date,
                "end_date": trip_request.end_date
            }
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        logger.error(f"Error starting trip planning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start trip planning"
        )


@app.get("/trips/{trip_id}")
async def get_trip(
    trip_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get trip details and status."""
    try:
        # Get trip from database
        trip = await db_manager.get_trip(trip_id)
        
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found"
            )
        
        # Check if user owns this trip
        if trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get planning status from orchestrator
        message = AgentMessage(
            agent_id="api",
            message_type="get_planning_status",
            content={"trip_id": trip_id}
        )
        
        status_response = await agent_registry.send_message("orchestrator", message)
        
        return APIResponse(
            success=True,
            data={
                "trip": trip.dict(),
                "planning_status": status_response.data if status_response.success else None
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trip: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trip"
        )


@app.post("/trips/continue")
async def continue_planning(
    user_response: UserResponseRequest,
    user_id: str = Depends(get_current_user)
):
    """Continue the planning process with user response."""
    try:
        # Send message to orchestrator agent
        message = AgentMessage(
            agent_id="api",
            message_type="continue_planning",
            content={
                "trip_id": user_response.trip_id,
                "user_response": user_response.user_response
            }
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except Exception as e:
        logger.error(f"Error continuing planning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to continue planning"
        )


# Itinerary Management Endpoints

@app.get("/trips/{trip_id}/itinerary/{day_index}")
async def get_itinerary_day(
    trip_id: str,
    day_index: int,
    user_id: str = Depends(get_current_user)
):
    """Get detailed itinerary for a specific day."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get itinerary day
        itinerary_day = await db_manager.firestore.get_itinerary_day(trip_id, day_index)
        
        if itinerary_day:
            return APIResponse(
                success=True,
                data={"itinerary": itinerary_day.dict()}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Itinerary day not found"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting itinerary day: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get itinerary day"
        )


@app.post("/trips/{trip_id}/itinerary/{day_index}/confirm")
async def confirm_day(
    trip_id: str,
    day_index: int,
    confirmation: DayConfirmationRequest,
    user_id: str = Depends(get_current_user)
):
    """Confirm the proposed plan for a specific day."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Send confirmation to orchestrator
        message = AgentMessage(
            agent_id="api",
            message_type="confirm_day",
            content={
                "trip_id": trip_id,
                "day_number": day_index,
                "confirmed": confirmation.confirmed
            }
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming day: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm day"
        )


@app.post("/trips/{trip_id}/itinerary/{day_index}/request-changes")
async def request_changes(
    trip_id: str,
    day_index: int,
    revision: RevisionRequest,
    user_id: str = Depends(get_current_user)
):
    """Request modifications to a proposed day's plan."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Send revision request to orchestrator
        message = AgentMessage(
            agent_id="api",
            message_type="request_revision",
            content={
                "trip_id": trip_id,
                "day_number": day_index,
                "feedback": revision.feedback
            }
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting changes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request changes"
        )


# Dynamic Replanning Endpoints

@app.post("/trips/{trip_id}/replan")
async def handle_disruption(
    trip_id: str,
    disruption: DisruptionRequest,
    user_id: str = Depends(get_current_user)
):
    """Handle trip disruption and initiate dynamic replanning."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Send disruption to orchestrator
        message = AgentMessage(
            agent_id="api",
            message_type="handle_disruption",
            content={
                "trip_id": trip_id,
                "disruption": {
                    "type": disruption.disruption_type,
                    "details": disruption.details,
                    "detected_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling disruption: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle disruption"
        )


# Monitoring Endpoints

@app.post("/trips/{trip_id}/monitoring/start")
async def start_monitoring(
    trip_id: str,
    user_id: str = Depends(get_current_user)
):
    """Start monitoring a trip for disruptions."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Start monitoring
        message = AgentMessage(
            agent_id="api",
            message_type="start_trip_monitoring",
            content={"trip_id": trip_id}
        )
        
        response = await agent_registry.send_message("orchestrator", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.error
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting monitoring: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start monitoring"
        )


@app.get("/trips/{trip_id}/monitoring/status")
async def get_monitoring_status(
    trip_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get monitoring status for a trip."""
    try:
        # Verify trip ownership
        trip = await db_manager.get_trip(trip_id)
        if not trip or trip.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Get monitoring status from monitor agent
        message = AgentMessage(
            agent_id="api",
            message_type="get_monitoring_status",
            content={"trip_id": trip_id}
        )
        
        response = await agent_registry.send_message("monitor", message)
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=True,
                data={"monitoring": False, "message": "No active monitoring"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monitoring status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get monitoring status"
        )


# User Trip History

@app.get("/trips")
async def get_user_trips(
    limit: Optional[int] = 10,
    user_id: str = Depends(get_current_user)
):
    """Get user's trip history."""
    try:
        trips = await db_manager.get_user_trips(user_id, limit)
        
        return APIResponse(
            success=True,
            data={
                "trips": [trip.dict() for trip in trips],
                "count": len(trips)
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting user trips: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trips"
        )


# Travel MCP Tool Endpoints

@app.post("/travel/flights/search")
async def search_flights(
    flight_request: FlightSearchRequest,
    user_id: str = Depends(get_current_user)
):
    """Search for flights using the Travel MCP Tool."""
    try:
        # Execute flight search using the travel MCP tool
        response = await tool_registry.execute_tool(
            "travel_mcp_tool",
            action="search_flights",
            origin=flight_request.origin,
            destination=flight_request.destination,
            departure_date=flight_request.departure_date,
            return_date=flight_request.return_date,
            adults=flight_request.adults,
            children=flight_request.children,
            cabin_class=flight_request.cabin_class,
            currency=flight_request.currency
        )
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=False,
                error=response.error
            )
    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search flights"
        )


@app.post("/travel/accommodation/search")
async def search_accommodation(
    accommodation_request: AccommodationSearchRequest,
    user_id: str = Depends(get_current_user)
):
    """Search for accommodation using the Travel MCP Tool."""
    try:
        # Execute accommodation search using the travel MCP tool
        response = await tool_registry.execute_tool(
            "travel_mcp_tool",
            action="search_accommodation",
            location=accommodation_request.location,
            check_in_date=accommodation_request.check_in_date,
            check_out_date=accommodation_request.check_out_date,
            guests=accommodation_request.guests,
            rooms=accommodation_request.rooms,
            currency=accommodation_request.currency
        )
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=False,
                error=response.error
            )
    except Exception as e:
        logger.error(f"Error searching accommodation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search accommodation"
        )


@app.post("/travel/currency/convert")
async def convert_currency(
    currency_request: CurrencyConversionRequest,
    user_id: str = Depends(get_current_user)
):
    """Convert currency using the Travel MCP Tool."""
    try:
        # Execute currency conversion using the travel MCP tool
        response = await tool_registry.execute_tool(
            "travel_mcp_tool",
            action="convert_currency",
            from_currency=currency_request.from_currency,
            to_currency=currency_request.to_currency,
            amount=currency_request.amount
        )
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=False,
                error=response.error
            )
    except Exception as e:
        logger.error(f"Error converting currency: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert currency"
        )


@app.post("/travel/info")
async def get_travel_info(
    travel_info_request: TravelInfoRequest,
    user_id: str = Depends(get_current_user)
):
    """Get travel information using the Travel MCP Tool."""
    try:
        # Map request type to action
        action_mapping = {
            "city_info": "get_city_info",
            "airport_info": "get_airport_info",
            "weather_forecast": "get_weather_forecast"
        }
        
        action = action_mapping.get(travel_info_request.request_type)
        if not action:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request type"
            )
        
        # Prepare parameters
        params = {"destination": travel_info_request.destination}
        if travel_info_request.additional_params:
            params.update(travel_info_request.additional_params)
        
        # Handle different parameter names for different actions
        if action == "get_city_info":
            params["city_name"] = params.pop("destination")
        elif action == "get_airport_info":
            params["airport_code"] = params.pop("destination")
        elif action == "get_weather_forecast":
            params["location"] = params.pop("destination")
        
        # Execute travel info request using the travel MCP tool
        response = await tool_registry.execute_tool(
            "travel_mcp_tool",
            action=action,
            **params
        )
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=False,
                error=response.error
            )
    except Exception as e:
        logger.error(f"Error getting travel info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get travel information"
        )


@app.post("/travel/budget/calculate")
async def calculate_trip_budget(
    budget_request: BudgetCalculationRequest,
    user_id: str = Depends(get_current_user)
):
    """Calculate trip budget using the Travel MCP Tool."""
    try:
        # Execute budget calculation using the travel MCP tool
        response = await tool_registry.execute_tool(
            "travel_mcp_tool",
            action="calculate_trip_budget",
            destination=budget_request.destination,
            days=budget_request.days,
            travelers=budget_request.travelers,
            budget_level=budget_request.budget_level
        )
        
        if response.success:
            return APIResponse(
                success=True,
                data=response.data
            )
        else:
            return APIResponse(
                success=False,
                error=response.error
            )
    except Exception as e:
        logger.error(f"Error calculating trip budget: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate trip budget"
        )


# Background tasks for monitoring
async def run_monitoring_cycle():
    """Background task to run monitoring cycles."""
    try:
        message = AgentMessage(
            agent_id="background",
            message_type="run_monitoring_cycle",
            content={}
        )
        
        await agent_registry.send_message("monitor", message)
        
    except Exception as e:
        logger.error(f"Error in monitoring cycle: {str(e)}")


@app.post("/admin/monitoring/run-cycle")
async def trigger_monitoring_cycle(background_tasks: BackgroundTasks):
    """Manually trigger a monitoring cycle (admin endpoint)."""
    try:
        background_tasks.add_task(run_monitoring_cycle)
        
        return APIResponse(
            success=True,
            data={"message": "Monitoring cycle triggered"}
        )
        
    except Exception as e:
        logger.error(f"Error triggering monitoring cycle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger monitoring cycle"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    ) 