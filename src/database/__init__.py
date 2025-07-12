"""
Database Layer for AI Travel Planner

This module provides unified access to persistent storage (MongoDB only).
"""

from .mongodb_client import MongoDBClient, mongodb_client
from src.config.settings import settings
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime


class DatabaseManager:
    """Unified database manager for the AI Travel Planner (MongoDB only)."""
    
    def __init__(self):
        self.logger = logging.getLogger("database_manager")
        self.persistent_db = mongodb_client
    
    # User Profile Management
    
    async def save_user_profile(self, user_profile) -> bool:
        """Save user profile to persistent storage."""
        try:
            persistent_success = await self.persistent_db.save_user_profile(user_profile)
            return persistent_success
        except Exception as e:
            self.logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str):
        """Get user profile from persistent storage."""
        try:
            profile = await self.persistent_db.get_user_profile(user_id)
            return profile
        except Exception as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile in persistent storage."""
        try:
            persistent_success = await self.persistent_db.update_user_profile(user_id, updates)
            return persistent_success
        except Exception as e:
            self.logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    # Trip Management
    
    async def save_trip(self, trip) -> bool:
        """Save trip to persistent storage."""
        try:
            persistent_success = await self.persistent_db.save_trip(trip)
            return persistent_success
        except Exception as e:
            self.logger.error(f"Error saving trip: {str(e)}")
            return False
    
    async def get_trip(self, trip_id: str):
        """Get trip from persistent storage."""
        try:
            return await self.persistent_db.get_trip(trip_id)
        except Exception as e:
            self.logger.error(f"Error getting trip: {str(e)}")
            return None
    
    async def get_user_trips(self, user_id: str, limit: Optional[int] = None) -> List:
        """Get user trips from persistent storage."""
        try:
            trips = await self.persistent_db.get_user_trips(user_id, limit)
            return trips
        except Exception as e:
            self.logger.error(f"Error getting user trips: {str(e)}")
            return []
    
    async def save_trip_details(self, trip_details: Dict[str, Any]) -> bool:
        """Save trip details to persistent storage."""
        try:
            persistent_success = await self.persistent_db.save_trip_details(trip_details)
            return persistent_success
        except Exception as e:
            self.logger.error(f"Error saving trip details: {str(e)}")
            return False
    
    # Health Check
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MongoDB health."""
        try:
            persistent_health = await self.persistent_db.health_check()
            health = {
                'overall': persistent_health.get('overall', False),
                'persistent_db': persistent_health.get('overall', False),
                'timestamp': datetime.utcnow().isoformat()
            }
            return health
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return {
                'overall': False,
                'persistent_db': False,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    # Connection Management
    
    async def close_connections(self):
        """Close MongoDB connections."""
        try:
            await self.persistent_db.close_connections()
            self.logger.info("Database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {str(e)}")

# Global database manager instance
db_manager = DatabaseManager() 