from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TravelStyle(str, Enum):
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    RELAXATION = "relaxation"
    BUSINESS = "business"
    LUXURY = "luxury"
    BUDGET = "budget"


class TravelPace(str, Enum):
    SLOW = "slow"
    MODERATE = "moderate"
    FAST = "fast"


class BudgetLevel(str, Enum):
    BUDGET = "budget"
    MID_RANGE = "mid-range"
    LUXURY = "luxury"


class TravelerType(str, Enum):
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    FRIENDS = "friends"
    BUSINESS = "business"


class Budget(BaseModel):
    """User's budget preferences."""
    level: BudgetLevel
    currency: str = Field(default="USD")
    daily_max: Optional[float] = Field(None, description="Maximum daily budget")
    total_max: Optional[float] = Field(None, description="Maximum total trip budget")


class TravelerInfo(BaseModel):
    """Information about the traveler(s)."""
    group_size: int = Field(default=1, ge=1, le=20)
    travels_with: List[TravelerType] = Field(default=[TravelerType.SOLO])
    ages: Optional[List[int]] = Field(None, description="Ages of travelers")
    accessibility_needs: Optional[List[str]] = Field(None, description="Any accessibility requirements")


class UserPreferences(BaseModel):
    """User's travel preferences."""
    travel_style: List[TravelStyle] = Field(default=[])
    pace: TravelPace = Field(default=TravelPace.MODERATE)
    interests: List[str] = Field(default=[], description="User's interests and hobbies")
    dietary_restrictions: Optional[List[str]] = Field(None, description="Dietary restrictions")
    accommodation_preferences: Optional[List[str]] = Field(None, description="Preferred accommodation types")
    transport_preferences: Optional[List[str]] = Field(None, description="Preferred transport methods")
    activity_preferences: Optional[Dict[str, Any]] = Field(None, description="Activity preferences")


class UserProfile(BaseModel):
    """Complete user profile for travel planning."""
    user_id: str = Field(..., description="Unique user identifier")
    preferences: UserPreferences
    traveler_info: TravelerInfo
    budget: Budget
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Learning and personalization
    past_trips: Optional[List[str]] = Field(None, description="List of past trip IDs")
    feedback_history: Optional[Dict[str, Any]] = Field(None, description="User feedback for learning")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserOnboardingRequest(BaseModel):
    """Request model for user onboarding."""
    user_id: str
    responses: Dict[str, Any] = Field(..., description="User responses to onboarding questions")
    
    
class UserProfileUpdateRequest(BaseModel):
    """Request model for updating user profile."""
    preferences: Optional[UserPreferences] = None
    traveler_info: Optional[TravelerInfo] = None
    budget: Optional[Budget] = None 