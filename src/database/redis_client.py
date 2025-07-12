import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.asyncio import Redis

from src.config.settings import settings


class RedisClient:
    """Redis client for session management, caching, and agent memory."""
    
    def __init__(self):
        self.logger = logging.getLogger("redis_client")
        self.redis: Optional[Redis] = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            connection_params = {
                'host': settings.redis_host,
                'port': settings.redis_port,
                'db': settings.redis_db,
                'decode_responses': True,
                'encoding': 'utf-8'
            }
            
            if settings.redis_password:
                connection_params['password'] = settings.redis_password
            
            self.redis = redis.Redis(**connection_params)
            self.logger.info("Redis client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis: {str(e)}")
            raise
    
    # Generic Key-Value Operations
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        try:
            # Serialize value to JSON if it's not a string
            if not isinstance(value, str):
                value = json.dumps(value, default=self._json_serializer)
            
            result = await self.redis.set(key, value, ex=expire)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Error setting key {key}: {str(e)}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key."""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            self.logger.error(f"Error getting key {key}: {str(e)}")
            return None
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return await self.redis.delete(*keys)
        except Exception as e:
            self.logger.error(f"Error deleting keys {keys}: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            self.logger.error(f"Error checking key existence {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for a key."""
        try:
            return bool(await self.redis.expire(key, seconds))
        except Exception as e:
            self.logger.error(f"Error setting expiration for key {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            self.logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return -1
    
    # Session Management
    
    async def create_session(self, user_id: str, session_data: Dict[str, Any], expire_minutes: int = 60) -> str:
        """Create a new session."""
        try:
            session_id = f"session:{user_id}:{int(datetime.utcnow().timestamp())}"
            
            session_info = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat(),
                'data': session_data
            }
            
            success = await self.set(session_id, session_info, expire=expire_minutes * 60)
            
            if success:
                # Also store a mapping from user to current session
                await self.set(f"user_session:{user_id}", session_id, expire=expire_minutes * 60)
                self.logger.info(f"Created session {session_id} for user {user_id}")
                return session_id
            else:
                raise Exception("Failed to store session")
                
        except Exception as e:
            self.logger.error(f"Error creating session for user {user_id}: {str(e)}")
            return ""
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        try:
            session_data = await self.get(session_id)
            if session_data:
                # Update last activity
                session_data['last_activity'] = datetime.utcnow().isoformat()
                await self.set(session_id, session_data)
                
            return session_data
            
        except Exception as e:
            self.logger.error(f"Error getting session {session_id}: {str(e)}")
            return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data."""
        try:
            session_data = await self.get(session_id)
            if not session_data:
                return False
            
            # Update the data field
            session_data['data'].update(updates)
            session_data['last_activity'] = datetime.utcnow().isoformat()
            
            return await self.set(session_id, session_data)
            
        except Exception as e:
            self.logger.error(f"Error updating session {session_id}: {str(e)}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            # Get session to find user_id
            session_data = await self.get(session_id)
            if session_data:
                user_id = session_data.get('user_id')
                if user_id:
                    await self.delete(f"user_session:{user_id}")
            
            result = await self.delete(session_id)
            return result > 0
            
        except Exception as e:
            self.logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    async def get_user_session(self, user_id: str) -> Optional[str]:
        """Get current session ID for a user."""
        try:
            return await self.get(f"user_session:{user_id}")
        except Exception as e:
            self.logger.error(f"Error getting user session for {user_id}: {str(e)}")
            return None
    
    # Agent Memory Management
    
    async def set_agent_memory(self, agent_id: str, scope: str, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set agent memory with scope."""
        try:
            memory_key = f"agent_memory:{agent_id}:{scope}:{key}"
            return await self.set(memory_key, value, expire=expire)
        except Exception as e:
            self.logger.error(f"Error setting agent memory: {str(e)}")
            return False
    
    async def get_agent_memory(self, agent_id: str, scope: str, key: str) -> Optional[Any]:
        """Get agent memory with scope."""
        try:
            memory_key = f"agent_memory:{agent_id}:{scope}:{key}"
            return await self.get(memory_key)
        except Exception as e:
            self.logger.error(f"Error getting agent memory: {str(e)}")
            return None
    
    async def delete_agent_memory(self, agent_id: str, scope: Optional[str] = None, key: Optional[str] = None) -> int:
        """Delete agent memory. Can delete all memory, scope, or specific key."""
        try:
            if scope is None:
                # Delete all memory for agent
                pattern = f"agent_memory:{agent_id}:*"
            elif key is None:
                # Delete all memory for agent and scope
                pattern = f"agent_memory:{agent_id}:{scope}:*"
            else:
                # Delete specific key
                memory_key = f"agent_memory:{agent_id}:{scope}:{key}"
                return await self.delete(memory_key)
            
            # For pattern deletion, we need to scan for keys
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                return await self.delete(*keys)
            return 0
            
        except Exception as e:
            self.logger.error(f"Error deleting agent memory: {str(e)}")
            return 0
    
    async def get_agent_memory_scope(self, agent_id: str, scope: str) -> Dict[str, Any]:
        """Get all memory for an agent scope."""
        try:
            pattern = f"agent_memory:{agent_id}:{scope}:*"
            memory = {}
            
            async for key in self.redis.scan_iter(match=pattern):
                # Extract the memory key from the full key
                memory_key = key.split(':', 3)[-1]  # Get the part after the last ':'
                value = await self.get(key)
                memory[memory_key] = value
            
            return memory
            
        except Exception as e:
            self.logger.error(f"Error getting agent memory scope: {str(e)}")
            return {}
    
    # Caching Operations
    
    async def cache_tool_response(self, tool_name: str, params_hash: str, response: Any, expire_minutes: int = 60) -> bool:
        """Cache tool response."""
        try:
            cache_key = f"tool_cache:{tool_name}:{params_hash}"
            cache_data = {
                'response': response,
                'cached_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(minutes=expire_minutes)).isoformat()
            }
            
            return await self.set(cache_key, cache_data, expire=expire_minutes * 60)
            
        except Exception as e:
            self.logger.error(f"Error caching tool response: {str(e)}")
            return False
    
    async def get_cached_tool_response(self, tool_name: str, params_hash: str) -> Optional[Any]:
        """Get cached tool response."""
        try:
            cache_key = f"tool_cache:{tool_name}:{params_hash}"
            cache_data = await self.get(cache_key)
            
            if cache_data:
                return cache_data.get('response')
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cached tool response: {str(e)}")
            return None
    
    async def cache_location_data(self, location_query: str, data: Any, expire_hours: int = 24) -> bool:
        """Cache location data."""
        try:
            cache_key = f"location_cache:{location_query.lower().replace(' ', '_')}"
            return await self.set(cache_key, data, expire=expire_hours * 3600)
        except Exception as e:
            self.logger.error(f"Error caching location data: {str(e)}")
            return False
    
    async def get_cached_location_data(self, location_query: str) -> Optional[Any]:
        """Get cached location data."""
        try:
            cache_key = f"location_cache:{location_query.lower().replace(' ', '_')}"
            return await self.get(cache_key)
        except Exception as e:
            self.logger.error(f"Error getting cached location data: {str(e)}")
            return None
    
    # List Operations
    
    async def list_push(self, key: str, value: Any, expire: Optional[int] = None) -> int:
        """Push value to a list."""
        try:
            # Serialize value if needed
            if not isinstance(value, str):
                value = json.dumps(value, default=self._json_serializer)
            
            result = await self.redis.lpush(key, value)
            
            if expire:
                await self.redis.expire(key, expire)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error pushing to list {key}: {str(e)}")
            return 0
    
    async def list_pop(self, key: str) -> Optional[Any]:
        """Pop value from a list."""
        try:
            value = await self.redis.rpop(key)
            if value is None:
                return None
            
            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            self.logger.error(f"Error popping from list {key}: {str(e)}")
            return None
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list."""
        try:
            values = await self.redis.lrange(key, start, end)
            result = []
            
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting list range {key}: {str(e)}")
            return []
    
    async def list_length(self, key: str) -> int:
        """Get length of a list."""
        try:
            return await self.redis.llen(key)
        except Exception as e:
            self.logger.error(f"Error getting list length {key}: {str(e)}")
            return 0
    
    # Hash Operations
    
    async def hash_set(self, key: str, field: str, value: Any) -> bool:
        """Set field in a hash."""
        try:
            if not isinstance(value, str):
                value = json.dumps(value, default=self._json_serializer)
            
            result = await self.redis.hset(key, field, value)
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Error setting hash field {key}:{field}: {str(e)}")
            return False
    
    async def hash_get(self, key: str, field: str) -> Optional[Any]:
        """Get field from a hash."""
        try:
            value = await self.redis.hget(key, field)
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except Exception as e:
            self.logger.error(f"Error getting hash field {key}:{field}: {str(e)}")
            return None
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """Get all fields from a hash."""
        try:
            data = await self.redis.hgetall(key)
            result = {}
            
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting all hash fields {key}: {str(e)}")
            return {}
    
    async def hash_delete(self, key: str, *fields: str) -> int:
        """Delete fields from a hash."""
        try:
            return await self.redis.hdel(key, *fields)
        except Exception as e:
            self.logger.error(f"Error deleting hash fields {key}: {str(e)}")
            return 0
    
    # Utility Methods
    
    def _json_serializer(self, obj):
        """JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    async def get_info(self) -> Dict[str, str]:
        """Get Redis server information."""
        try:
            return await self.redis.info()
        except Exception as e:
            self.logger.error(f"Error getting Redis info: {str(e)}")
            return {}
    
    async def flush_cache(self, pattern: Optional[str] = None) -> int:
        """Flush cache entries matching pattern."""
        try:
            if pattern:
                keys = []
                async for key in self.redis.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    return await self.delete(*keys)
                return 0
            else:
                # Flush all cache keys (be careful with this!)
                return await self.redis.flushdb()
                
        except Exception as e:
            self.logger.error(f"Error flushing cache: {str(e)}")
            return 0
    
    async def close(self):
        """Close Redis connection."""
        try:
            if self.redis:
                await self.redis.close()
                self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {str(e)}")


# Global Redis client instance
redis_client = RedisClient() 