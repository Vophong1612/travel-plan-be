"""
Database Layer for AI Travel Planner

This module provides unified access to persistent storage (Firestore or MongoDB) and Redis (session/cache storage).
"""

from .firestore_client import FirestoreClient, firestore_client
from .mongodb_client import MongoDBClient, mongodb_client
from .redis_client import RedisClient, redis_client
from src.config.settings import settings
from typing import Dict, Any, List, Optional
import logging


class DatabaseManager:
    """Unified database manager for the AI Travel Planner."""
    
    def __init__(self):
        self.logger = logging.getLogger("database_manager")
        
        # Choose database based on configuration
        if settings.use_mongodb:
            self.logger.info("Using MongoDB as persistent storage")
            self.persistent_db = mongodb_client
        else:
            self.logger.info("Using Firestore as persistent storage")
            self.persistent_db = firestore_client
        
        # Redis for sessions and caching
        self.redis = redis_client
    
    # User Profile Management
    
    async def save_user_profile(self, user_profile) -> bool:
        """Save user profile to persistent storage and Redis cache."""
        try:
            # Save to persistent storage (Firestore or MongoDB)
            persistent_success = await self.persistent_db.save_user_profile(user_profile)
            
            # Cache in Redis for quick access
            if persistent_success:
                redis_key = f"user_profile:{user_profile.user_id}"
                await self.redis.set(redis_key, user_profile.dict(), expire=3600)  # 1 hour cache
            
            return persistent_success
            
        except Exception as e:
            self.logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str):
        """Get user profile, checking Redis cache first, then persistent storage."""
        try:
            # Try Redis cache first
            redis_key = f"user_profile:{user_id}"
            cached_profile = await self.redis.get(redis_key)
            
            if cached_profile:
                from src.models.user import UserProfile
                return UserProfile(**cached_profile)
            
            # If not in cache, get from persistent storage
            profile = await self.persistent_db.get_user_profile(user_id)
            
            # Cache the result
            if profile:
                await self.redis.set(redis_key, profile.dict(), expire=3600)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile in persistent storage and invalidate Redis cache."""
        try:
            # Update in persistent storage
            persistent_success = await self.persistent_db.update_user_profile(user_id, updates)
            
            # Invalidate Redis cache
            if persistent_success:
                redis_key = f"user_profile:{user_id}"
                await self.redis.delete(redis_key)
            
            return persistent_success
            
        except Exception as e:
            self.logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    # Trip Management
    
    async def save_trip(self, trip) -> bool:
        """Save trip to persistent storage and cache key info in Redis."""
        try:
            # Save to persistent storage
            persistent_success = await self.persistent_db.save_trip(trip)
            
            # Cache trip summary in Redis
            if persistent_success:
                trip_summary = {
                    'trip_id': trip.trip_id,
                    'user_id': trip.user_id,
                    'destination': trip.destination,
                    'start_date': trip.start_date.isoformat(),
                    'end_date': trip.end_date.isoformat(),
                    'status': trip.status.value
                }
                
                redis_key = f"trip_summary:{trip.trip_id}"
                await self.redis.set(redis_key, trip_summary, expire=7200)  # 2 hour cache
            
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
        """Get user trips with Redis caching."""
        try:
            # Check cache first
            cache_key = f"user_trips:{user_id}"
            cached_trips = await self.redis.get(cache_key)
            
            if cached_trips and not limit:  # Only use cache for unlimited queries
                return cached_trips
            
            # Get from persistent storage
            trips = await self.persistent_db.get_user_trips(user_id, limit)
            
            # Cache the result (without limit)
            if trips and not limit:
                trip_data = [trip.dict() for trip in trips]
                await self.redis.set(cache_key, trip_data, expire=1800)  # 30 minute cache
            
            return trips
            
        except Exception as e:
            self.logger.error(f"Error getting user trips: {str(e)}")
            return []
    
    # Session Management
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any], expire_minutes: int = 60) -> str:
        """Create user session in Redis."""
        return await self.redis.create_session(user_id, session_data, expire_minutes)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        return await self.redis.get_session(session_id)
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data in Redis."""
        return await self.redis.update_session(session_id, updates)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        return await self.redis.delete_session(session_id)
    
    # Agent Memory Management
    
    async def set_agent_memory(self, agent_id: str, scope: str, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set agent memory in Redis."""
        return await self.redis.set_agent_memory(agent_id, scope, key, value, expire)
    
    async def get_agent_memory(self, agent_id: str, scope: str, key: str) -> Optional[Any]:
        """Get agent memory from Redis."""
        return await self.redis.get_agent_memory(agent_id, scope, key)
    
    async def delete_agent_memory(self, agent_id: str, scope: Optional[str] = None, key: Optional[str] = None) -> int:
        """Delete agent memory from Redis."""
        return await self.redis.delete_agent_memory(agent_id, scope, key)
    
    async def get_agent_memory_scope(self, agent_id: str, scope: str) -> Dict[str, Any]:
        """Get all memory for an agent scope from Redis."""
        return await self.redis.get_agent_memory_scope(agent_id, scope)
    
    # Caching Operations
    
    async def cache_tool_response(self, tool_name: str, params_hash: str, response: Any, expire_minutes: int = 60) -> bool:
        """Cache tool response in Redis."""
        return await self.redis.cache_tool_response(tool_name, params_hash, response, expire_minutes)
    
    async def get_cached_tool_response(self, tool_name: str, params_hash: str) -> Optional[Any]:
        """Get cached tool response from Redis."""
        return await self.redis.get_cached_tool_response(tool_name, params_hash)
    
    async def cache_location_data(self, location_query: str, data: Any, expire_hours: int = 24) -> bool:
        """Cache location data in Redis."""
        return await self.redis.cache_location_data(location_query, data, expire_hours)
    
    async def get_cached_location_data(self, location_query: str) -> Optional[Any]:
        """Get cached location data from Redis."""
        return await self.redis.get_cached_location_data(location_query)
    
    # Health Checks
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of both database connections."""
        try:
            persistent_health = await self.persistent_db.health_check()
            redis_health = await self.redis.health_check()
            
            db_type = "mongodb" if settings.use_mongodb else "firestore"
            
            return {
                db_type: persistent_health,
                'redis': redis_health,
                'overall': persistent_health and redis_health
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            db_type = "mongodb" if settings.use_mongodb else "firestore"
            return {
                db_type: False,
                'redis': False,
                'overall': False
            }
    
    # Cleanup Operations
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (Redis handles this automatically, but we can track)."""
        try:
            # This is mostly handled by Redis TTL, but we can add custom logic here
            # For now, just return 0 as Redis handles expiration automatically
            return 0
        except Exception as e:
            self.logger.error(f"Error cleaning up sessions: {str(e)}")
            return 0
    
    async def flush_cache(self, pattern: Optional[str] = None) -> int:
        """Flush cache entries from Redis."""
        return await self.redis.flush_cache(pattern)
    
    async def close_connections(self):
        """Close all database connections."""
        try:
            await self.redis.close()
            
            # Close persistent database connection
            if hasattr(self.persistent_db, 'close_connection'):
                await self.persistent_db.close_connection()
            
            self.logger.info("Database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing database connections: {str(e)}")


# Global database manager instance
db_manager = DatabaseManager()

__all__ = [
    'FirestoreClient',
    'MongoDBClient',
    'RedisClient', 
    'DatabaseManager',
    'firestore_client',
    'mongodb_client',
    'redis_client',
    'db_manager'
] 