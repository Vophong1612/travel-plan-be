from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class TripStatus(str, Enum):
    PLANNING_STARTED = "planning_started"
    PLANNING_IN_PROGRESS = "planning_in_progress"
    PLANNING_COMPLETED = "planning_completed"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ItineraryDayStatus(str, Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NEEDS_REVISION = "needs_revision"


class ActivityType(str, Enum):
    SIGHTSEEING = "sightseeing"
    DINING = "dining"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    OUTDOOR = "outdoor"
    CULTURAL = "cultural"
    RELAXATION = "relaxation"
    BUSINESS = "business"


class DisruptionType(str, Enum):
    FLIGHT_DELAY = "flight_delay"
    WEATHER = "weather"
    VENUE_CLOSURE = "venue_closure"
    TRAFFIC = "traffic"
    ACCOMMODATION_ISSUE = "accommodation_issue"
    HEALTH_EMERGENCY = "health_emergency"
    OTHER = "other"


class Location(BaseModel):
    """Geographic location information."""
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    place_id: Optional[str] = None  # Google Places ID
    country: Optional[str] = None
    city: Optional[str] = None


class Activity(BaseModel):
    """Individual activity within an itinerary."""
    id: str = Field(..., description="Unique activity identifier")
    name: str = Field(..., description="Activity name")
    type: ActivityType
    description: Optional[str] = None
    
    # Location and timing
    location: Location
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    
    # Booking and pricing
    cost: Optional[float] = None
    currency: str = Field(default="USD")
    booking_url: Optional[str] = None
    booking_reference: Optional[str] = None
    
    # Additional details
    rating: Optional[float] = Field(None, ge=0, le=5)
    review_count: Optional[int] = None
    opening_hours: Optional[Dict[str, str]] = None
    contact_info: Optional[Dict[str, str]] = None
    
    # Travel information
    travel_time_from_previous: Optional[int] = Field(None, description="Travel time in minutes from previous activity")
    travel_mode: Optional[str] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = Field(None, description="Source of the activity recommendation")


class ItineraryDay(BaseModel):
    """A single day's itinerary."""
    day_index: int = Field(..., ge=1, description="Day number in the trip")
    date: date
    theme: Optional[str] = Field(None, description="Theme or focus of the day")
    status: ItineraryDayStatus = Field(default=ItineraryDayStatus.PENDING_CONFIRMATION)
    
    # Activities
    activities: List[Activity] = Field(default=[])
    
    # Daily summary
    total_cost: Optional[float] = None
    total_duration_minutes: Optional[int] = None
    travel_distance_km: Optional[float] = None
    
    # Weather and conditions
    weather_forecast: Optional[Dict[str, Any]] = None
    special_considerations: Optional[List[str]] = None
    
    # Feedback and revisions
    user_feedback: Optional[str] = None
    revision_count: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class Trip(BaseModel):
    """Complete trip information."""
    trip_id: str = Field(..., description="Unique trip identifier")
    user_id: str = Field(..., description="User who owns this trip")
    
    # Basic trip information
    destination: str = Field(..., description="Primary destination")
    start_date: date
    end_date: date
    duration_days: int = Field(..., ge=1)
    
    # Trip details
    title: Optional[str] = None
    description: Optional[str] = None
    status: TripStatus = Field(default=TripStatus.PLANNING_STARTED)
    
    # Itinerary
    itinerary: List[ItineraryDay] = Field(default=[])
    
    # Budget tracking
    estimated_total_cost: Optional[float] = None
    actual_total_cost: Optional[float] = None
    budget_currency: str = Field(default="USD")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = None
    
    # Planning metadata
    planning_preferences: Optional[Dict[str, Any]] = None
    agent_notes: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }


class TripCreateRequest(BaseModel):
    """Request model for creating a new trip."""
    destination: str
    start_date: date
    end_date: date
    title: Optional[str] = None
    description: Optional[str] = None
    planning_preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class DayConfirmationRequest(BaseModel):
    """Request model for confirming a day's itinerary."""
    trip_id: str
    day_index: int
    feedback: Optional[str] = None


class DayRevisionRequest(BaseModel):
    """Request model for requesting changes to a day's itinerary."""
    trip_id: str
    day_index: int
    feedback: str = Field(..., description="Specific feedback for revision")


class DisruptionAlert(BaseModel):
    """Model for disruption alerts during trips."""
    alert_id: str
    trip_id: str
    disruption_type: DisruptionType
    affected_day: int
    affected_activities: List[str] = Field(default=[])
    
    # Disruption details
    title: str
    description: str
    severity: str = Field(default="medium")  # low, medium, high, critical
    
    # Timing
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    expected_duration: Optional[int] = Field(None, description="Expected duration in minutes")
    
    # Source and details
    source: str = Field(..., description="Source of the disruption alert")
    details: Optional[Dict[str, Any]] = None
    
    # Resolution
    suggested_actions: Optional[List[str]] = None
    auto_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None


class ReplanningRequest(BaseModel):
    """Request model for dynamic replanning."""
    trip_id: str
    disruption_type: DisruptionType
    details: str = Field(..., description="Description of the disruption")
    affected_day: Optional[int] = None
    user_initiated: bool = Field(default=True, description="Whether user initiated the replanning")
    
    # Additional context
    current_location: Optional[Location] = None
    constraints: Optional[Dict[str, Any]] = None 