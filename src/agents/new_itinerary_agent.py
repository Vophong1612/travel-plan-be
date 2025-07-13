import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta, time

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import TravelContext


class NewItineraryAgent(BaseAgent):
    """Agent responsible for generating optimized daily itineraries from discovered POIs, activities, and restaurants."""
    
    def __init__(self):
        super().__init__(
            agent_id="new_itinerary",
            name="Itinerary Generation Agent",
            description="Organizes POIs, activities, and restaurants into optimized daily itineraries with travel times",
            tools=["google_maps"]
        )
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are an expert travel itinerary planner. Your goal is to create optimal daily itineraries that are:
        
        1. Logically sequenced with feasible travel times between activities
        2. Organized by geographical proximity to minimize travel
        3. Weather-appropriate and contextually aware
        4. Balanced with proper pacing and variety
        5. Include meals at appropriate times throughout the day
        
        Use Google Maps to calculate accurate travel times between activities.
        Consider opening hours, weather conditions, and user preferences.
        Ensure each day has a coherent theme and logical flow.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the itinerary generation agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "generate_proposed_itinerary":
            return await self._generate_proposed_itinerary(content)
        elif message_type == "generate_itinerary":
            # Handle legacy message type for backward compatibility
            return await self._handle_legacy_generate_itinerary(content)
        elif message_type == "revise_itinerary":
            # Handle legacy revise message type for backward compatibility
            return await self._handle_legacy_revise_itinerary(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _generate_proposed_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Generate the proposed itinerary from enriched travel context."""
        try:
            # Get travel context
            travel_context_data = content.get("travel_context")
            if not travel_context_data:
                return self._create_error_response("travel_context is required")
            
            # Recreate TravelContext object
            travel_context = TravelContext(**travel_context_data)
            
            # Validate required data
            if not travel_context.potential_pois:
                return self._create_error_response("potential_pois is required in travel_context")
            if not travel_context.potential_restaurants:
                return self._create_error_response("potential_restaurants is required in travel_context")
            
            # Generate daily itineraries
            proposed_itinerary = await self._create_multi_day_itinerary(travel_context)
            
            # Update travel context
            travel_context.proposed_itinerary = proposed_itinerary
            
            return self._create_success_response({
                "travel_context": travel_context.__dict__,
                "itinerary_summary": {
                    "total_days": len(proposed_itinerary),
                    "total_activities": sum(len(day.get("activities", [])) for day in proposed_itinerary),
                    "themes": [day.get("theme") for day in proposed_itinerary],
                    "total_estimated_cost": sum(day.get("total_cost", 0) for day in proposed_itinerary)
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error generating proposed itinerary: {str(e)}")
            return self._create_error_response(f"Failed to generate proposed itinerary: {str(e)}")
    
    async def _handle_legacy_generate_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Handle legacy generate_itinerary message type."""
        try:
            # Convert legacy request format to new format
            user_profile = content.get("user_profile")
            destination = content.get("destination")
            date_str = content.get("date")
            day_index = content.get("day_index", 1)
            preferences = content.get("preferences", {})
            
            if not all([user_profile, destination, date_str]):
                return self._create_error_response("user_profile, destination, and date are required")
            
            # Parse date
            if isinstance(date_str, str):
                target_date = datetime.fromisoformat(date_str).date()
            else:
                target_date = date_str
            
            # Set the current date context for the activities method
            self._current_legacy_date = target_date
            
            self.logger.info(f"Legacy generate_itinerary: Creating basic itinerary for {destination} on {target_date}")
            
            # Create a basic itinerary using Google Maps for activities
            activities = await self._discover_basic_activities(destination, user_profile, preferences)
            
            # Create a simple daily schedule
            daily_itinerary = {
                "day_index": day_index,
                "date": target_date.isoformat(),
                "theme": f"Exploring {destination}",
                "activities": activities,
                "total_cost": sum(activity.get("cost", 0) for activity in activities),
                "total_duration_minutes": sum(activity.get("duration_minutes", 0) for activity in activities),
                "weather_forecast": {},
                "special_considerations": ["Generated using legacy compatibility mode - limited functionality"]
            }
            
            # Clean up the date context
            if hasattr(self, '_current_legacy_date'):
                delattr(self, '_current_legacy_date')
            
            return self._create_success_response({
                "itinerary": daily_itinerary,
                "weather_info": {},
                "generation_context": {
                    "user_profile_summary": f"Legacy mode for {user_profile.get('name', 'user')}",
                    "constraints_applied": preferences,
                    "total_activities": len(activities),
                    "estimated_cost": daily_itinerary["total_cost"],
                    "legacy_mode": True
                }
            })
            
        except Exception as e:
            self.logger.error(f"Error handling legacy generate_itinerary: {str(e)}")
            return self._create_error_response(f"Failed to handle legacy request: {str(e)}")
    
    async def _handle_legacy_revise_itinerary(self, content: Dict[str, Any]) -> AgentResponse:
        """Handle legacy revise_itinerary message type."""
        try:
            # Extract required parameters
            user_profile = content.get("user_profile")
            destination = content.get("destination")
            date_str = content.get("date")
            day_index = content.get("day_index", 1)
            revision_feedback = content.get("revision_feedback", "")
            existing_itinerary = content.get("existing_itinerary")
            
            if not all([user_profile, destination, date_str]):
                return self._create_error_response("user_profile, destination, and date are required")
            
            # Parse date
            if isinstance(date_str, str):
                target_date = datetime.fromisoformat(date_str).date()
            else:
                target_date = date_str
            
            self.logger.info(f"Legacy revise_itinerary: Revising itinerary for {destination} on {target_date} with feedback: {revision_feedback}")
            
            # Set the current date context for the activities method
            self._current_legacy_date = target_date
            
            # If we have an existing itinerary, use it as a base
            if existing_itinerary:
                # Extract existing activities
                existing_activities = existing_itinerary.get("activities", [])
                
                # Create a modified version based on feedback
                activities = await self._modify_activities_based_on_feedback(
                    existing_activities, 
                    revision_feedback,
                    destination
                )
            else:
                # No existing itinerary, create a new one
                activities = await self._discover_basic_activities(destination, user_profile, {})
            
            # Create revised daily schedule
            revised_itinerary = {
                "day_index": day_index,
                "date": target_date.isoformat(),
                "theme": f"Exploring {destination} (Revised)",
                "activities": activities,
                "total_cost": sum(activity.get("cost", 0) for activity in activities),
                "total_duration_minutes": sum(activity.get("duration_minutes", 0) for activity in activities),
                "weather_forecast": {},
                "special_considerations": ["Revised based on feedback: " + revision_feedback]
            }
            
            # Clean up the date context
            if hasattr(self, '_current_legacy_date'):
                delattr(self, '_current_legacy_date')
            
            return self._create_success_response({
                "revised_itinerary": revised_itinerary,
                "revision_summary": {
                    "feedback_applied": True,
                    "original_activity_count": len(existing_itinerary.get("activities", [])) if existing_itinerary else 0,
                    "revised_activity_count": len(activities)
                },
                "changes_made": ["Applied user feedback to revise itinerary"]
            })
            
        except Exception as e:
            self.logger.error(f"Error handling legacy revise_itinerary: {str(e)}")
            return self._create_error_response(f"Failed to revise itinerary: {str(e)}")
            
    async def _modify_activities_based_on_feedback(self, existing_activities: List[Dict[str, Any]], 
                                                feedback: str, destination: str) -> List[Dict[str, Any]]:
        """Modify activities based on user feedback."""
        # Simple modification based on feedback keywords
        feedback_lower = feedback.lower()
        
        # If feedback mentions adding something
        if "add" in feedback_lower or "include" in feedback_lower or "want" in feedback_lower:
            # Try to find what to add
            try:
                # Very simple extraction - in real system would use NLP
                add_keywords = ["add", "include", "want", "more"]
                for keyword in add_keywords:
                    if keyword in feedback_lower:
                        activity_name = feedback_lower.split(keyword)[1].strip()
                        if activity_name:
                            # Add a new activity
                            target_date = getattr(self, '_current_legacy_date', date.today())
                            start_time = datetime.combine(target_date, time(14, 0))  # Default to 2 PM
                            end_time = datetime.combine(target_date, time(16, 0))  # 2 hours duration
                            
                            new_activity = {
                                "id": f"revised_activity_{int(datetime.utcnow().timestamp())}",
                                "name": activity_name.title(),
                                "type": "sightseeing",
                                "description": f"Added based on feedback: {activity_name}",
                                "location": {
                                    "name": activity_name.title(),
                                    "address": f"{destination}",
                                    "latitude": None,
                                    "longitude": None
                                },
                                "start_time": start_time.isoformat(),
                                "end_time": end_time.isoformat(),
                                "duration_minutes": 120,
                                "cost": 0,
                                "source": "user_feedback"
                            }
                            
                            # Add to existing activities
                            existing_activities.append(new_activity)
                            break
            except Exception as e:
                self.logger.warning(f"Error extracting activity to add: {str(e)}")
        
        # If feedback mentions removing something
        if "remove" in feedback_lower or "don't want" in feedback_lower or "skip" in feedback_lower:
            try:
                # Try to identify what to remove
                remove_keywords = ["remove", "don't want", "skip", "not interested"]
                for keyword in remove_keywords:
                    if keyword in feedback_lower:
                        activity_name = feedback_lower.split(keyword)[1].strip()
                        if activity_name:
                            # Remove matching activities
                            existing_activities = [
                                activity for activity in existing_activities 
                                if activity_name.lower() not in activity.get("name", "").lower()
                            ]
                            break
            except Exception as e:
                self.logger.warning(f"Error extracting activity to remove: {str(e)}")
        
        # Reschedule remaining activities
        if existing_activities:
            target_date = getattr(self, '_current_legacy_date', date.today())
            current_time = datetime.combine(target_date, time(9, 0))  # Start at 9 AM
            
            for activity in existing_activities:
                duration = activity.get("duration_minutes", 120)
                activity["start_time"] = current_time.isoformat()
                activity["end_time"] = (current_time + timedelta(minutes=duration)).isoformat()
                current_time += timedelta(minutes=duration + 60)  # Add 1 hour buffer
        
        return existing_activities
    
    async def _discover_basic_activities(self, destination: str, user_profile: Dict[str, Any], preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover basic activities for legacy mode."""
        activities = []
        
        try:
            # Use Google Maps to find popular tourist attractions
            places_response = await self.use_tool(
                "google_maps",
                action="find_nearby_places",
                query=destination,
                place_type="tourist_attraction",
                radius=5000,
                limit=5
            )
            
            if places_response.success:
                places = places_response.data.get("places", [])
                current_time = 9  # Start at 9 AM
                
                # Get the target date from the context (should be available from the calling method)
                target_date = getattr(self, '_current_legacy_date', date.today())
                
                for i, place in enumerate(places[:3]):  # Limit to 3 activities for legacy mode
                    start_datetime = datetime.combine(target_date, time(current_time, 0))
                    end_datetime = datetime.combine(target_date, time(current_time + 2, 0))
                    
                    activity = {
                        "id": f"legacy_activity_{i+1}",
                        "name": place.get("name", f"Activity {i+1}"),
                        "type": "sightseeing",
                        "description": f"Visit {place.get('name', 'attraction')}",
                        "location": {
                            "name": place.get("name", ""),
                            "address": place.get("formatted_address", ""),
                            "latitude": place.get("latitude"),
                            "longitude": place.get("longitude"),
                            "place_id": place.get("place_id")
                        },
                        "start_time": start_datetime.isoformat(),
                        "end_time": end_datetime.isoformat(),
                        "duration_minutes": 120,
                        "cost": 0,  # Default to free for basic mode
                        "rating": place.get("rating"),
                        "source": "google_maps_legacy"
                    }
                    activities.append(activity)
                    current_time += 3  # 2 hours activity + 1 hour travel/break
            
            # Add a basic dining option if no activities found
            if not activities:
                target_date = getattr(self, '_current_legacy_date', date.today())
                start_datetime = datetime.combine(target_date, time(10, 0))
                end_datetime = datetime.combine(target_date, time(12, 0))
                
                activities.append({
                    "id": "legacy_fallback",
                    "name": f"Explore {destination}",
                    "type": "sightseeing",
                    "description": f"General exploration of {destination}",
                    "location": {"name": destination},
                    "start_time": start_datetime.isoformat(),
                    "end_time": end_datetime.isoformat(),
                    "duration_minutes": 120,
                    "cost": 0,
                    "source": "legacy_fallback"
                })
                
        except Exception as e:
            self.logger.error(f"Error discovering basic activities: {str(e)}")
            # Return fallback activity
            target_date = getattr(self, '_current_legacy_date', date.today())
            start_datetime = datetime.combine(target_date, time(10, 0))
            end_datetime = datetime.combine(target_date, time(16, 0))
            
            activities = [{
                "id": "legacy_error_fallback",
                "name": f"Explore {destination}",
                "type": "sightseeing",
                "description": f"Basic exploration of {destination}",
                "location": {"name": destination},
                "start_time": start_datetime.isoformat(),
                "end_time": end_datetime.isoformat(),
                "duration_minutes": 360,
                "cost": 0,
                "source": "legacy_error_fallback"
            }]
        
        return activities
    
    async def _create_multi_day_itinerary(self, travel_context: TravelContext) -> List[Dict[str, Any]]:
        """Create multi-day itinerary from available POIs, activities, and restaurants."""
        itinerary = []
        
        try:
            duration = travel_context.duration or 3
            start_date = datetime.strptime(travel_context.start_date, "%Y-%m-%d").date()
            
            # Combine all available items
            all_items = (
                travel_context.potential_pois + 
                travel_context.potential_activities + 
                travel_context.potential_restaurants
            )
            
            # Group items by type for distribution
            pois = [item for item in all_items if item.get("type") in ["cultural", "sightseeing"]]
            activities = [item for item in all_items if item.get("type") in ["outdoor", "entertainment", "shopping"]]
            restaurants = [item for item in all_items if item.get("type") == "dining"]
            
            # Plan each day
            for day_index in range(duration):
                current_date = start_date + timedelta(days=day_index)
                
                # Get weather for this day
                daily_weather = self._get_daily_weather(travel_context.weather_data, current_date)
                
                # Create daily itinerary
                daily_itinerary = await self._create_daily_itinerary(
                    day_index + 1,
                    current_date,
                    pois,
                    activities,
                    restaurants,
                    travel_context,
                    daily_weather
                )
                
                itinerary.append(daily_itinerary)
                
                # Remove used items to avoid duplication
                used_items = daily_itinerary.get("activities", [])
                used_ids = {item.get("id") for item in used_items}
                
                pois = [item for item in pois if item.get("id") not in used_ids]
                activities = [item for item in activities if item.get("id") not in used_ids]
                restaurants = [item for item in restaurants if item.get("id") not in used_ids]
            
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error creating multi-day itinerary: {str(e)}")
            return []
    
    async def _create_daily_itinerary(self, day_index: int, date: date, pois: List[Dict[str, Any]], 
                                    activities: List[Dict[str, Any]], restaurants: List[Dict[str, Any]], 
                                    travel_context: TravelContext, weather: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single day's itinerary."""
        try:
            # Determine activities per day based on pace
            pace = getattr(travel_context, 'pace', 'moderate')
            if pace == "slow":
                max_non_dining = 3
            elif pace == "fast":
                max_non_dining = 6
            else:
                max_non_dining = 4
            
            # Select activities for the day
            daily_activities = []
            
            # Weather-based filtering
            if self._is_bad_weather(weather):
                # Prefer indoor activities
                indoor_pois = [poi for poi in pois if self._is_indoor_activity(poi)]
                indoor_activities = [act for act in activities if self._is_indoor_activity(act)]
                
                selected_pois = indoor_pois[:max_non_dining//2] if indoor_pois else pois[:max_non_dining//2]
                selected_activities = indoor_activities[:max_non_dining//2] if indoor_activities else activities[:max_non_dining//2]
            else:
                # Mix of indoor and outdoor
                selected_pois = pois[:max_non_dining//2]
                selected_activities = activities[:max_non_dining//2]
            
            # Combine selected items
            day_items = selected_pois + selected_activities
            
            # Add meals - aim for 3 meals per day
            meal_restaurants = self._select_daily_restaurants(restaurants, travel_context)
            
            # Create activity schedule
            scheduled_activities = await self._schedule_daily_activities(
                day_items + meal_restaurants,
                date,
                travel_context
            )
            
            # Calculate totals
            total_cost = sum(activity.get("cost", 0) or 0 for activity in scheduled_activities)
            total_duration = sum(activity.get("duration_minutes", 0) or 0 for activity in scheduled_activities)
            total_travel_time = sum(activity.get("travel_time_from_previous", 0) or 0 for activity in scheduled_activities)
            
            # Generate theme
            theme = self._generate_daily_theme(scheduled_activities, weather)
            
            return {
                "day_index": day_index,
                "date": date.isoformat(),
                "theme": theme,
                "status": "pending_confirmation",
                "activities": scheduled_activities,
                "total_cost": total_cost,
                "total_duration_minutes": total_duration,
                "travel_distance_km": None,  # Could be calculated from travel times
                "weather_forecast": weather,
                "special_considerations": self._generate_special_considerations(weather, scheduled_activities),
                "user_feedback": None,
                "revision_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "confirmed_at": None
            }
            
        except Exception as e:
            self.logger.error(f"Error creating daily itinerary: {str(e)}")
            return {
                "day_index": day_index,
                "date": date.isoformat(),
                "theme": "City Exploration",
                "status": "pending_confirmation",
                "activities": [],
                "total_cost": 0,
                "total_duration_minutes": 0,
                "travel_distance_km": None,
                "weather_forecast": weather or {},
                "special_considerations": None,
                "user_feedback": None,
                "revision_count": 0,
                "created_at": datetime.utcnow().isoformat(),
                "confirmed_at": None
            }
    
    async def _schedule_daily_activities(self, activities: List[Dict[str, Any]], date: date, 
                                       travel_context: TravelContext) -> List[Dict[str, Any]]:
        """Schedule activities throughout the day with proper timing."""
        if not activities:
            return []
        
        scheduled = []
        current_time = datetime.combine(date, datetime.min.time().replace(hour=9))  # Start at 9 AM
        
        try:
            # Sort activities by type to ensure good meal timing
            restaurants = [a for a in activities if a.get("type") == "dining"]
            non_restaurants = [a for a in activities if a.get("type") != "dining"]
            
            # Plan the day: morning activity, lunch, afternoon activities, dinner
            day_plan = []
            
            # Morning (9-12): 1-2 activities
            if non_restaurants:
                day_plan.extend(non_restaurants[:2])
            
            # Lunch (12-13): Add a lunch restaurant
            lunch_restaurants = [r for r in restaurants if self._is_lunch_suitable(r)]
            if lunch_restaurants:
                day_plan.append(lunch_restaurants[0])
                restaurants.remove(lunch_restaurants[0])
            
            # Afternoon (13-17): 1-2 more activities
            remaining_activities = [a for a in non_restaurants if a not in day_plan]
            if remaining_activities:
                day_plan.extend(remaining_activities[:2])
            
            # Dinner (17-19): Add a dinner restaurant
            dinner_restaurants = [r for r in restaurants if self._is_dinner_suitable(r)]
            if dinner_restaurants:
                day_plan.append(dinner_restaurants[0])
            elif restaurants:  # Fallback to any remaining restaurant
                day_plan.append(restaurants[0])
            
            # Schedule each activity with timing
            for i, activity in enumerate(day_plan):
                # Copy activity to avoid modifying original
                scheduled_activity = activity.copy()
                
                # Set timing
                duration = activity.get("duration_minutes", 90)
                scheduled_activity["start_time"] = current_time.isoformat()
                scheduled_activity["end_time"] = (current_time + timedelta(minutes=duration)).isoformat()
                
                # Calculate travel time from previous activity
                if i > 0:
                    travel_time = await self._calculate_travel_time(
                        scheduled[i-1]["location"],
                        activity["location"]
                    )
                    scheduled_activity["travel_time_from_previous"] = travel_time
                    scheduled_activity["travel_mode"] = "walking"
                else:
                    scheduled_activity["travel_time_from_previous"] = None
                    scheduled_activity["travel_mode"] = None
                
                scheduled.append(scheduled_activity)
                
                # Move to next time slot (activity + travel + buffer)
                travel_time = scheduled_activity.get("travel_time_from_previous", 0)
                current_time += timedelta(minutes=duration + travel_time + 30)  # 30 min buffer
            
            return scheduled
            
        except Exception as e:
            self.logger.error(f"Error scheduling activities: {str(e)}")
            # Return unscheduled activities as fallback
            for i, activity in enumerate(activities[:5]):  # Limit to 5 activities
                activity["start_time"] = (current_time + timedelta(hours=i*2)).isoformat()
                activity["end_time"] = (current_time + timedelta(hours=i*2, minutes=90)).isoformat()
                activity["travel_time_from_previous"] = 30 if i > 0 else None
                activity["travel_mode"] = "walking" if i > 0 else None
            
            return activities[:5]
    
    def _select_daily_restaurants(self, restaurants: List[Dict[str, Any]], travel_context: TravelContext) -> List[Dict[str, Any]]:
        """Select appropriate restaurants for the day."""
        if not restaurants:
            return []
        
        selected = []
        
        # Try to get variety in meal types
        breakfast_options = [r for r in restaurants if self._is_breakfast_suitable(r)]
        lunch_options = [r for r in restaurants if self._is_lunch_suitable(r)]
        dinner_options = [r for r in restaurants if self._is_dinner_suitable(r)]
        
        # Select one from each category if available
        if breakfast_options:
            selected.append(breakfast_options[0])
        
        if lunch_options:
            selected.append(lunch_options[0])
        
        if dinner_options:
            selected.append(dinner_options[0])
        
        # If we don't have enough variety, add general restaurants
        if len(selected) < 2:
            general_restaurants = [r for r in restaurants if r not in selected]
            selected.extend(general_restaurants[:3-len(selected)])
        
        return selected[:3]  # Max 3 meals per day
    
    async def _calculate_travel_time(self, origin_location: Dict[str, Any], destination_location: Dict[str, Any]) -> int:
        """Calculate travel time between two locations."""
        try:
            origin_lat = origin_location.get("latitude")
            origin_lng = origin_location.get("longitude")
            dest_lat = destination_location.get("latitude")
            dest_lng = destination_location.get("longitude")
            
            if not all([origin_lat, origin_lng, dest_lat, dest_lng]):
                return 30  # Default 30 minutes if coordinates missing
            
            # Use Google Maps to calculate travel time
            travel_response = await self.use_tool(
                "google_maps",
                action="calculate_travel_time",
                origin=f"{origin_lat},{origin_lng}",
                destination=f"{dest_lat},{dest_lng}",
                travel_mode="walking"
            )
            
            if travel_response.success:
                duration = travel_response.data.get("duration", {})
                return duration.get("value_seconds", 1800) // 60  # Convert to minutes
            else:
                self.logger.warning(f"Travel time calculation failed: {travel_response.error}")
                return 30  # Default 30 minutes
                
        except Exception as e:
            self.logger.error(f"Error calculating travel time: {str(e)}")
            return 30  # Default 30 minutes
    
    def _get_daily_weather(self, weather_data: Dict[str, Any], date: date) -> Dict[str, Any]:
        """Get weather forecast for a specific date."""
        if not weather_data or weather_data.get("error"):
            return {}
        
        forecast_days = weather_data.get("forecast", [])
        if not forecast_days:
            return {}
        
        # Find forecast for the specific date
        date_str = date.isoformat()
        for day_forecast in forecast_days:
            if day_forecast.get("date") == date_str:
                return day_forecast
        
        # If exact date not found, return first forecast day
        return forecast_days[0] if forecast_days else {}
    
    def _is_bad_weather(self, weather: Dict[str, Any]) -> bool:
        """Check if weather is bad for outdoor activities."""
        if not weather:
            return False
        
        weather_info = weather.get("weather", [])
        if weather_info:
            main_condition = weather_info[0].get("main", "").lower()
            if "rain" in main_condition or "storm" in main_condition or "snow" in main_condition:
                return True
        
        # Check precipitation probability
        pop = weather.get("pop", 0)
        if pop > 0.5:  # More than 50% chance of precipitation
            return True
        
        return False
    
    def _is_indoor_activity(self, activity: Dict[str, Any]) -> bool:
        """Check if an activity is typically indoor."""
        activity_type = activity.get("type", "").lower()
        name = activity.get("name", "").lower()
        
        indoor_types = ["cultural", "shopping", "dining"]
        indoor_keywords = ["museum", "gallery", "mall", "restaurant", "cafe", "theater", "cinema"]
        
        if activity_type in indoor_types:
            return True
        
        if any(keyword in name for keyword in indoor_keywords):
            return True
        
        return False
    
    def _is_breakfast_suitable(self, restaurant: Dict[str, Any]) -> bool:
        """Check if restaurant is suitable for breakfast."""
        name = restaurant.get("name", "").lower()
        cuisine = restaurant.get("cuisine_type", "").lower()
        
        breakfast_keywords = ["cafe", "bakery", "breakfast", "coffee", "brunch"]
        return any(keyword in name or keyword in cuisine for keyword in breakfast_keywords)
    
    def _is_lunch_suitable(self, restaurant: Dict[str, Any]) -> bool:
        """Check if restaurant is suitable for lunch."""
        # Most restaurants are suitable for lunch, exclude breakfast-only places
        if self._is_breakfast_suitable(restaurant):
            name = restaurant.get("name", "").lower()
            return "cafe" in name  # Cafes can do lunch, pure bakeries usually don't
        return True
    
    def _is_dinner_suitable(self, restaurant: Dict[str, Any]) -> bool:
        """Check if restaurant is suitable for dinner."""
        cuisine = restaurant.get("cuisine_type", "").lower()
        price_level = restaurant.get("price_level", 2)
        
        # Exclude pure breakfast places
        if cuisine in ["bakery"] and price_level <= 1:
            return False
        
        # Most other restaurants work for dinner
        return True
    
    def _generate_daily_theme(self, activities: List[Dict[str, Any]], weather: Dict[str, Any]) -> str:
        """Generate a theme for the day based on activities."""
        if not activities:
            return "City Exploration"
        
        activity_types = [activity.get("type", "") for activity in activities]
        
        # Count activity types
        type_counts = {}
        for activity_type in activity_types:
            type_counts[activity_type] = type_counts.get(activity_type, 0) + 1
        
        # Determine theme based on dominant activity type
        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else ""
        
        theme_mapping = {
            "cultural": "Cultural Immersion",
            "sightseeing": "City Highlights",
            "outdoor": "Nature & Adventure",
            "entertainment": "Entertainment & Fun",
            "shopping": "Shopping & Local Markets",
            "dining": "Culinary Discovery"
        }
        
        theme = theme_mapping.get(dominant_type, "City Exploration")
        
        # Modify theme based on weather
        if self._is_bad_weather(weather):
            if "outdoor" in theme.lower() or "nature" in theme.lower():
                theme = "Indoor Exploration"
        
        return theme
    
    def _generate_special_considerations(self, weather: Dict[str, Any], activities: List[Dict[str, Any]]) -> Optional[str]:
        """Generate special considerations for the day."""
        considerations = []
        
        # Weather considerations
        if self._is_bad_weather(weather):
            considerations.append("Weather may affect outdoor activities - indoor alternatives recommended")
        
        # Activity-specific considerations
        outdoor_count = sum(1 for activity in activities if activity.get("type") == "outdoor")
        if outdoor_count > 2:
            considerations.append("Day includes multiple outdoor activities - consider weather and energy levels")
        
        dining_count = sum(1 for activity in activities if activity.get("type") == "dining")
        if dining_count < 2:
            considerations.append("Limited dining options planned - consider additional meal stops")
        
        # High-cost day warning
        total_cost = sum(activity.get("cost", 0) or 0 for activity in activities)
        if total_cost > 100:
            considerations.append(f"High-cost day (${total_cost:.0f}) - consider budget implications")
        
        return "; ".join(considerations) if considerations else None 