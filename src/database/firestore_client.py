import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore

from src.config.settings import settings
from src.models.user import UserProfile
from src.models.trip import Trip, ItineraryDay


class FirestoreClient:
    """Firestore database client for persistent data storage."""
    
    def __init__(self):
        self.logger = logging.getLogger("firestore_client")
        self.db = None
        self._initialize_firestore()
    
    def _initialize_firestore(self):
        """Initialize Firestore connection."""
        try:
            # Initialize Firebase Admin SDK if not already done
            if not firebase_admin._apps:
                if settings.firestore_credentials_path:
                    cred = credentials.Certificate(settings.firestore_credentials_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': settings.firestore_project_id,
                    })
                else:
                    # Use default credentials (for Cloud Run)
                    firebase_admin.initialize_app()
            
            self.db = admin_firestore.client()
            self.logger.info("Firestore client initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Firestore: {str(e)}")
            raise
    
    # User Profile Operations
    
    async def save_user_profile(self, user_profile: UserProfile) -> bool:
        """Save user profile to Firestore."""
        try:
            # Convert to dict and handle datetime serialization
            profile_data = user_profile.dict()
            profile_data = self._serialize_datetime_fields(profile_data)
            
            # Save to users collection
            doc_ref = self.db.collection('users').document(user_profile.user_id)
            doc_ref.set(profile_data, merge=True)
            
            self.logger.info(f"Saved user profile for user {user_profile.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user profile: {str(e)}")
            return False
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from Firestore."""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                profile_data = doc.to_dict()
                profile_data = self._deserialize_datetime_fields(profile_data)
                return UserProfile(**profile_data)
            else:
                self.logger.info(f"No profile found for user {user_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile in Firestore."""
        try:
            # Serialize datetime fields
            updates = self._serialize_datetime_fields(updates)
            updates['updated_at'] = datetime.utcnow()
            
            doc_ref = self.db.collection('users').document(user_id)
            doc_ref.update(updates)
            
            self.logger.info(f"Updated user profile for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    async def delete_user_profile(self, user_id: str) -> bool:
        """Delete user profile from Firestore."""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc_ref.delete()
            
            self.logger.info(f"Deleted user profile for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting user profile: {str(e)}")
            return False
    
    # Trip Operations
    
    async def save_trip(self, trip: Trip) -> bool:
        """Save trip to Firestore."""
        try:
            # Convert to dict and handle datetime serialization
            trip_data = trip.dict()
            trip_data = self._serialize_datetime_fields(trip_data)
            
            # Save to trips collection
            doc_ref = self.db.collection('trips').document(trip.trip_id)
            doc_ref.set(trip_data, merge=True)
            
            # Also save to user's trips subcollection for easier querying
            user_trip_ref = self.db.collection('users').document(trip.user_id).collection('trips').document(trip.trip_id)
            user_trip_data = {
                'trip_id': trip.trip_id,
                'destination': trip.destination,
                'start_date': trip.start_date,
                'end_date': trip.end_date,
                'status': trip.status.value,
                'created_at': trip.created_at,
                'updated_at': trip.updated_at
            }
            user_trip_data = self._serialize_datetime_fields(user_trip_data)
            user_trip_ref.set(user_trip_data, merge=True)
            
            self.logger.info(f"Saved trip {trip.trip_id} for user {trip.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving trip: {str(e)}")
            return False
    
    async def get_trip(self, trip_id: str) -> Optional[Trip]:
        """Get trip from Firestore."""
        try:
            doc_ref = self.db.collection('trips').document(trip_id)
            doc = doc_ref.get()
            
            if doc.exists:
                trip_data = doc.to_dict()
                trip_data = self._deserialize_datetime_fields(trip_data)
                return Trip(**trip_data)
            else:
                self.logger.info(f"No trip found with ID {trip_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting trip: {str(e)}")
            return None
    
    async def get_user_trips(self, user_id: str, limit: Optional[int] = None) -> List[Trip]:
        """Get all trips for a user."""
        try:
            query = self.db.collection('trips').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            trips = []
            
            for doc in docs:
                trip_data = doc.to_dict()
                trip_data = self._deserialize_datetime_fields(trip_data)
                trips.append(Trip(**trip_data))
            
            self.logger.info(f"Retrieved {len(trips)} trips for user {user_id}")
            return trips
            
        except Exception as e:
            self.logger.error(f"Error getting user trips: {str(e)}")
            return []
    
    async def update_trip(self, trip_id: str, updates: Dict[str, Any]) -> bool:
        """Update trip in Firestore."""
        try:
            # Serialize datetime fields
            updates = self._serialize_datetime_fields(updates)
            updates['updated_at'] = datetime.utcnow()
            
            doc_ref = self.db.collection('trips').document(trip_id)
            doc_ref.update(updates)
            
            self.logger.info(f"Updated trip {trip_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating trip: {str(e)}")
            return False
    
    async def delete_trip(self, trip_id: str) -> bool:
        """Delete trip from Firestore."""
        try:
            # Get trip first to get user_id
            trip = await self.get_trip(trip_id)
            if not trip:
                return False
            
            # Delete from main trips collection
            doc_ref = self.db.collection('trips').document(trip_id)
            doc_ref.delete()
            
            # Delete from user's trips subcollection
            user_trip_ref = self.db.collection('users').document(trip.user_id).collection('trips').document(trip_id)
            user_trip_ref.delete()
            
            self.logger.info(f"Deleted trip {trip_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting trip: {str(e)}")
            return False
    
    # Itinerary Operations
    
    async def save_itinerary_day(self, trip_id: str, itinerary_day: ItineraryDay) -> bool:
        """Save itinerary day to Firestore."""
        try:
            # Convert to dict and handle datetime serialization
            day_data = itinerary_day.dict()
            day_data = self._serialize_datetime_fields(day_data)
            
            # Save to trip's itinerary subcollection
            doc_ref = self.db.collection('trips').document(trip_id).collection('itinerary').document(f"day_{itinerary_day.day_index}")
            doc_ref.set(day_data, merge=True)
            
            self.logger.info(f"Saved itinerary day {itinerary_day.day_index} for trip {trip_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving itinerary day: {str(e)}")
            return False
    
    async def get_itinerary_day(self, trip_id: str, day_index: int) -> Optional[ItineraryDay]:
        """Get itinerary day from Firestore."""
        try:
            doc_ref = self.db.collection('trips').document(trip_id).collection('itinerary').document(f"day_{day_index}")
            doc = doc_ref.get()
            
            if doc.exists:
                day_data = doc.to_dict()
                day_data = self._deserialize_datetime_fields(day_data)
                return ItineraryDay(**day_data)
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting itinerary day: {str(e)}")
            return None
    
    async def get_trip_itinerary(self, trip_id: str) -> List[ItineraryDay]:
        """Get complete itinerary for a trip."""
        try:
            docs = self.db.collection('trips').document(trip_id).collection('itinerary').order_by('day_index').stream()
            
            itinerary = []
            for doc in docs:
                day_data = doc.to_dict()
                day_data = self._deserialize_datetime_fields(day_data)
                itinerary.append(ItineraryDay(**day_data))
            
            self.logger.info(f"Retrieved itinerary with {len(itinerary)} days for trip {trip_id}")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error getting trip itinerary: {str(e)}")
            return []
    
    # Search and Query Operations
    
    async def search_trips_by_destination(self, destination: str, limit: int = 10) -> List[Trip]:
        """Search trips by destination."""
        try:
            query = self.db.collection('trips').where('destination', '==', destination).limit(limit)
            docs = query.stream()
            
            trips = []
            for doc in docs:
                trip_data = doc.to_dict()
                trip_data = self._deserialize_datetime_fields(trip_data)
                trips.append(Trip(**trip_data))
            
            return trips
            
        except Exception as e:
            self.logger.error(f"Error searching trips by destination: {str(e)}")
            return []
    
    async def get_active_trips(self, limit: int = 50) -> List[Trip]:
        """Get currently active trips."""
        try:
            today = date.today()
            
            # Query for trips that are in progress
            query = (self.db.collection('trips')
                    .where('start_date', '<=', today)
                    .where('end_date', '>=', today)
                    .limit(limit))
            
            docs = query.stream()
            
            trips = []
            for doc in docs:
                trip_data = doc.to_dict()
                trip_data = self._deserialize_datetime_fields(trip_data)
                trips.append(Trip(**trip_data))
            
            return trips
            
        except Exception as e:
            self.logger.error(f"Error getting active trips: {str(e)}")
            return []
    
    # Utility Methods
    
    def _serialize_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert datetime objects to ISO strings for Firestore storage."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, date):
                    result[key] = value.isoformat()
                elif isinstance(value, dict):
                    result[key] = self._serialize_datetime_fields(value)
                elif isinstance(value, list):
                    result[key] = [self._serialize_datetime_fields(item) if isinstance(item, dict) else item for item in value]
                else:
                    result[key] = value
            return result
        return data
    
    def _deserialize_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ISO strings back to datetime objects."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str) and self._is_iso_datetime(value):
                    try:
                        if 'T' in value or ' ' in value:
                            result[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        else:
                            result[key] = datetime.fromisoformat(value).date()
                    except ValueError:
                        result[key] = value
                elif isinstance(value, dict):
                    result[key] = self._deserialize_datetime_fields(value)
                elif isinstance(value, list):
                    result[key] = [self._deserialize_datetime_fields(item) if isinstance(item, dict) else item for item in value]
                else:
                    result[key] = value
            return result
        return data
    
    def _is_iso_datetime(self, value: str) -> bool:
        """Check if string is an ISO datetime format."""
        if not isinstance(value, str):
            return False
        
        # Check for ISO date format (YYYY-MM-DD)
        if len(value) == 10 and value.count('-') == 2:
            return True
        
        # Check for ISO datetime format
        if 'T' in value or (' ' in value and ':' in value):
            return True
        
        return False
    
    async def health_check(self) -> bool:
        """Check Firestore connection health."""
        try:
            # Simple query to test connection
            self.db.collection('health_check').limit(1).get()
            return True
        except Exception as e:
            self.logger.error(f"Firestore health check failed: {str(e)}")
            return False


# Global Firestore client instance
firestore_client = FirestoreClient() 