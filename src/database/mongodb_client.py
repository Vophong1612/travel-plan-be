"""
MongoDB Client for AI Travel Planner

This module provides a MongoDB client as an on-premise alternative to Firestore.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
import json
from bson import ObjectId
from bson.json_util import dumps, loads
import pymongo
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

from src.config.settings import settings
from src.models.user import UserProfile
from src.models.trip import Trip, ItineraryDay


class MongoDBClient:
    """MongoDB client for persistent data storage as Firestore alternative."""
    
    def __init__(self):
        self.logger = logging.getLogger("mongodb_client")
        self.client = None
        self.db = None
        self._initialize_mongodb()
    
    def _initialize_mongodb(self):
        """Initialize MongoDB connection."""
        try:
            # Build connection string
            connection_string = self._build_connection_string()
            
            # Initialize async client
            self.client = AsyncIOMotorClient(connection_string)
            self.db = self.client[settings.mongodb_database]
            
            self.logger.info("MongoDB client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MongoDB: {str(e)}")
            raise
    
    def _build_connection_string(self) -> str:
        """Build MongoDB connection string from settings."""
        # Use the URI directly if provided
        if settings.mongodb_uri:
            return settings.mongodb_uri
        
        # Otherwise build from individual components
        if settings.mongodb_username and settings.mongodb_password:
            auth_part = f"{settings.mongodb_username}:{settings.mongodb_password}@"
        else:
            auth_part = ""
        
        connection_string = f"mongodb://{auth_part}{settings.mongodb_host}:{settings.mongodb_port}"
        
        if settings.mongodb_auth_database:
            connection_string += f"?authSource={settings.mongodb_auth_database}"
        
        return connection_string
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MongoDB connection health."""
        try:
            # Ping the database
            await self.client.admin.command('ping')
            
            # Get database stats
            stats = await self.db.command("dbstats")
            
            return {
                "mongodb": {
                    "status": "healthy",
                    "database": settings.mongodb_database,
                    "collections": len(await self.db.list_collection_names()),
                    "data_size": stats.get("dataSize", 0),
                    "index_size": stats.get("indexSize", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"MongoDB health check failed: {str(e)}")
            return {
                "mongodb": {
                    "status": "unhealthy",
                    "error": str(e)
                }
            }
    
    # User Profile Management
    
    async def save_user_profile(self, user_profile: UserProfile) -> bool:
        """Save user profile to MongoDB."""
        try:
            collection = self.db.user_profiles
            
            # Convert to dict and handle datetime serialization
            profile_data = self._serialize_document(user_profile.dict())
            profile_data["updated_at"] = datetime.utcnow()
            
            # Upsert (update or insert)
            result = await collection.replace_one(
                {"user_id": user_profile.user_id},
                profile_data,
                upsert=True
            )
            
            self.logger.info(f"Saved user profile for {user_profile.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from MongoDB."""
        try:
            collection = self.db.user_profiles
            
            profile_data = await collection.find_one({"user_id": user_id})
            
            if profile_data:
                # Remove MongoDB _id field and deserialize
                profile_data.pop("_id", None)
                profile_data = self._deserialize_document(profile_data)
                return UserProfile(**profile_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def delete_user_profile(self, user_id: str) -> bool:
        """Delete user profile from MongoDB."""
        try:
            collection = self.db.user_profiles
            
            result = await collection.delete_one({"user_id": user_id})
            
            if result.deleted_count > 0:
                self.logger.info(f"Deleted user profile for {user_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting user profile: {str(e)}")
            return False
    
    # Trip Management
    
    async def save_trip(self, trip: Trip) -> bool:
        """Save trip to MongoDB."""
        try:
            collection = self.db.trips
            
            # Convert to dict and handle serialization
            trip_data = self._serialize_document(trip.dict())
            trip_data["updated_at"] = datetime.utcnow()
            
            # Upsert
            result = await collection.replace_one(
                {"trip_id": trip.trip_id},
                trip_data,
                upsert=True
            )
            
            self.logger.info(f"Saved trip {trip.trip_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trip: {str(e)}")
            return False
    
    async def get_trip(self, trip_id: str) -> Optional[Trip]:
        """Get trip from MongoDB."""
        try:
            collection = self.db.trips
            
            trip_data = await collection.find_one({"trip_id": trip_id})
            
            if trip_data:
                trip_data.pop("_id", None)
                trip_data = self._deserialize_document(trip_data)
                return Trip(**trip_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting trip: {str(e)}")
            return None
    
    async def get_user_trips(self, user_id: str, limit: int = 20) -> List[Trip]:
        """Get trips for a user from MongoDB."""
        try:
            collection = self.db.trips
            
            cursor = collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            trips = []
            
            async for trip_data in cursor:
                trip_data.pop("_id", None)
                trip_data = self._deserialize_document(trip_data)
                trips.append(Trip(**trip_data))
            
            return trips
            
        except Exception as e:
            self.logger.error(f"Error getting user trips: {str(e)}")
            return []
    
    async def delete_trip(self, trip_id: str) -> bool:
        """Delete trip from MongoDB."""
        try:
            collection = self.db.trips
            
            result = await collection.delete_one({"trip_id": trip_id})
            
            if result.deleted_count > 0:
                self.logger.info(f"Deleted trip {trip_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting trip: {str(e)}")
            return False
    
    async def save_trip_details(self, trip_details: Dict[str, Any]) -> bool:
        """Save trip details to MongoDB."""
        try:
            collection = self.db.trips
            
            # Serialize and add timestamps
            trip_details = self._serialize_document(trip_details)
            trip_details["updated_at"] = datetime.utcnow()
            
            # Ensure trip_id exists
            trip_id = trip_details.get("trip_id")
            if not trip_id:
                self.logger.error("No trip_id provided in trip_details")
                return False
            
            # Upsert trip details
            result = await collection.replace_one(
                {"trip_id": trip_id},
                trip_details,
                upsert=True
            )
            
            self.logger.info(f"Saved trip details {trip_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trip details: {str(e)}")
            return False
    
    # Itinerary Management
    
    async def save_itinerary_day(self, trip_id: str, day_number: int, itinerary: ItineraryDay) -> bool:
        """Save daily itinerary to MongoDB."""
        try:
            collection = self.db.itineraries
            
            # Convert to dict and handle serialization
            itinerary_data = self._serialize_document(itinerary.dict())
            itinerary_data.update({
                "trip_id": trip_id,
                "day_number": day_number,
                "updated_at": datetime.utcnow()
            })
            
            # Upsert
            result = await collection.replace_one(
                {"trip_id": trip_id, "day_number": day_number},
                itinerary_data,
                upsert=True
            )
            
            self.logger.info(f"Saved itinerary for trip {trip_id}, day {day_number}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving itinerary: {str(e)}")
            return False
    
    async def get_itinerary_day(self, trip_id: str, day_number: int) -> Optional[ItineraryDay]:
        """Get daily itinerary from MongoDB."""
        try:
            collection = self.db.itineraries
            
            itinerary_data = await collection.find_one({
                "trip_id": trip_id,
                "day_number": day_number
            })
            
            if itinerary_data:
                itinerary_data.pop("_id", None)
                itinerary_data.pop("trip_id", None)
                itinerary_data.pop("day_number", None)
                itinerary_data = self._deserialize_document(itinerary_data)
                return ItineraryDay(**itinerary_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting itinerary: {str(e)}")
            return None
    
    async def get_trip_itineraries(self, trip_id: str) -> List[ItineraryDay]:
        """Get all itineraries for a trip from MongoDB."""
        try:
            collection = self.db.itineraries
            
            cursor = collection.find({"trip_id": trip_id}).sort("day_number", 1)
            itineraries = []
            
            async for itinerary_data in cursor:
                itinerary_data.pop("_id", None)
                itinerary_data.pop("trip_id", None)
                itinerary_data.pop("day_number", None)
                itinerary_data = self._deserialize_document(itinerary_data)
                itineraries.append(ItineraryDay(**itinerary_data))
            
            return itineraries
            
        except Exception as e:
            self.logger.error(f"Error getting trip itineraries: {str(e)}")
            return []
    
    # Generic Operations
    
    async def save_document(self, collection_name: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Save generic document to MongoDB."""
        try:
            collection = self.db[collection_name]
            
            # Serialize and add metadata
            document_data = self._serialize_document(data)
            document_data.update({
                "document_id": document_id,
                "updated_at": datetime.utcnow()
            })
            
            result = await collection.replace_one(
                {"document_id": document_id},
                document_data,
                upsert=True
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving document: {str(e)}")
            return False
    
    async def get_document(self, collection_name: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get generic document from MongoDB."""
        try:
            collection = self.db[collection_name]
            
            document_data = await collection.find_one({"document_id": document_id})
            
            if document_data:
                document_data.pop("_id", None)
                document_data.pop("document_id", None)
                return self._deserialize_document(document_data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting document: {str(e)}")
            return None
    
    async def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Delete document from MongoDB."""
        try:
            collection = self.db[collection_name]
            
            result = await collection.delete_one({"document_id": document_id})
            return result.deleted_count > 0
            
        except Exception as e:
            self.logger.error(f"Error deleting document: {str(e)}")
            return False
    
    async def query_documents(self, collection_name: str, query: Dict[str, Any], 
                            limit: int = 100, sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query documents from MongoDB."""
        try:
            collection = self.db[collection_name]
            
            cursor = collection.find(query)
            
            if sort_by:
                cursor = cursor.sort(sort_by, -1)
            
            cursor = cursor.limit(limit)
            
            documents = []
            async for doc in cursor:
                doc.pop("_id", None)
                documents.append(self._deserialize_document(doc))
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error querying documents: {str(e)}")
            return []
    
    # Utility Methods
    
    def _serialize_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize Python objects for MongoDB storage."""
        def convert_value(value):
            if isinstance(value, datetime):
                return value
            elif isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            elif isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            else:
                return value
        
        return convert_value(data)
    
    def _deserialize_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize MongoDB documents to Python objects."""
        def convert_value(value):
            if isinstance(value, dict):
                return {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [convert_value(item) for item in value]
            else:
                return value
        
        return convert_value(data)
    
    async def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")


# Global client instance
mongodb_client = MongoDBClient() 