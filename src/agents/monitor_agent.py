import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.models.trip import Trip, DisruptionAlert, DisruptionType, Activity
from src.tools import MCPToolResponse


class MonitoringState(str, Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class MonitoringSession:
    """Monitoring session for a specific trip."""
    trip_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    current_activities: List[Activity]
    monitoring_interval: int = 300  # 5 minutes default
    last_check: Optional[datetime] = None
    active: bool = True


class MonitorAgent(BaseAgent):
    """Agent responsible for real-time monitoring of trip disruptions."""
    
    def __init__(self):
        super().__init__(
            agent_id="monitor",
            name="Trip Monitor",
            description="Real-time watchdog for trip disruptions and alerts",
            tools=["weather", "google_maps"]
        )
        
        # Active monitoring sessions
        self.monitoring_sessions: Dict[str, MonitoringSession] = {}
        self.monitoring_state = MonitoringState.IDLE
        
        # Monitoring parameters
        self.monitoring_config = {
            "weather_alert_threshold": {
                "precipitation": 20,  # mm
                "wind_speed": 50,     # km/h
                "temperature_low": -5,  # °C
                "temperature_high": 40  # °C
            },
            "traffic_delay_threshold": 30,  # minutes
            "flight_delay_threshold": 15,   # minutes
            "venue_closure_keywords": ["closed", "closure", "maintenance", "cancelled"],
            "monitoring_intervals": {
                "active_trip": 300,    # 5 minutes during active trip
                "upcoming_trip": 3600, # 1 hour for upcoming trips
                "completed_trip": 0    # No monitoring for completed trips
            }
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are a vigilant trip monitor. Your job is to:
        1. Continuously monitor active trips for potential disruptions
        2. Detect weather, traffic, venue, and flight-related issues
        3. Send timely alerts to the orchestrator for proactive handling
        4. Prioritize alerts based on severity and impact
        5. Maintain awareness of multiple concurrent trips
        
        Be proactive but not overly sensitive. Focus on actionable disruptions that require replanning.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the monitor agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "start_monitoring":
            return await self._start_monitoring(content)
        elif message_type == "stop_monitoring":
            return await self._stop_monitoring(content)
        elif message_type == "pause_monitoring":
            return await self._pause_monitoring(content)
        elif message_type == "resume_monitoring":
            return await self._resume_monitoring(content)
        elif message_type == "check_disruptions":
            return await self._check_disruptions(content)
        elif message_type == "get_monitoring_status":
            return await self._get_monitoring_status(content)
        elif message_type == "run_monitoring_cycle":
            return await self._run_monitoring_cycle(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _start_monitoring(self, content: Dict[str, Any]) -> AgentResponse:
        """Start monitoring a trip."""
        try:
            trip_id = content.get("trip_id")
            user_id = content.get("user_id")
            trip_data = content.get("trip_data")
            
            if not all([trip_id, user_id, trip_data]):
                return self._create_error_response("trip_id, user_id, and trip_data are required")
            
            # Parse trip data
            trip = Trip(**trip_data)
            
            # Create monitoring session
            session = MonitoringSession(
                trip_id=trip_id,
                user_id=user_id,
                start_time=datetime.utcnow(),
                end_time=datetime.combine(trip.end_date, datetime.min.time()),
                current_activities=self._get_current_activities(trip),
                monitoring_interval=self._get_monitoring_interval(trip)
            )
            
            # Store session
            self.monitoring_sessions[trip_id] = session
            
            # Update monitoring state
            if self.monitoring_state == MonitoringState.IDLE:
                self.monitoring_state = MonitoringState.MONITORING
            
            self.logger.info(f"Started monitoring trip {trip_id} for user {user_id}")
            
            return self._create_success_response({
                "monitoring_started": True,
                "trip_id": trip_id,
                "session_id": trip_id,
                "monitoring_interval": session.monitoring_interval,
                "current_activities": len(session.current_activities)
            })
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {str(e)}")
            return self._create_error_response(f"Failed to start monitoring: {str(e)}")
    
    async def _stop_monitoring(self, content: Dict[str, Any]) -> AgentResponse:
        """Stop monitoring a trip."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id:
                return self._create_error_response("trip_id is required")
            
            # Remove monitoring session
            if trip_id in self.monitoring_sessions:
                del self.monitoring_sessions[trip_id]
                self.logger.info(f"Stopped monitoring trip {trip_id}")
            
            # Update monitoring state
            if not self.monitoring_sessions:
                self.monitoring_state = MonitoringState.IDLE
            
            return self._create_success_response({
                "monitoring_stopped": True,
                "trip_id": trip_id
            })
            
        except Exception as e:
            self.logger.error(f"Error stopping monitoring: {str(e)}")
            return self._create_error_response(f"Failed to stop monitoring: {str(e)}")
    
    async def _pause_monitoring(self, content: Dict[str, Any]) -> AgentResponse:
        """Pause monitoring for a trip."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id:
                return self._create_error_response("trip_id is required")
            
            if trip_id in self.monitoring_sessions:
                self.monitoring_sessions[trip_id].active = False
                self.logger.info(f"Paused monitoring for trip {trip_id}")
            
            return self._create_success_response({
                "monitoring_paused": True,
                "trip_id": trip_id
            })
            
        except Exception as e:
            self.logger.error(f"Error pausing monitoring: {str(e)}")
            return self._create_error_response(f"Failed to pause monitoring: {str(e)}")
    
    async def _resume_monitoring(self, content: Dict[str, Any]) -> AgentResponse:
        """Resume monitoring for a trip."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id:
                return self._create_error_response("trip_id is required")
            
            if trip_id in self.monitoring_sessions:
                self.monitoring_sessions[trip_id].active = True
                self.logger.info(f"Resumed monitoring for trip {trip_id}")
            
            return self._create_success_response({
                "monitoring_resumed": True,
                "trip_id": trip_id
            })
            
        except Exception as e:
            self.logger.error(f"Error resuming monitoring: {str(e)}")
            return self._create_error_response(f"Failed to resume monitoring: {str(e)}")
    
    async def _check_disruptions(self, content: Dict[str, Any]) -> AgentResponse:
        """Check for disruptions for a specific trip."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id:
                return self._create_error_response("trip_id is required")
            
            if trip_id not in self.monitoring_sessions:
                return self._create_error_response(f"No monitoring session found for trip {trip_id}")
            
            session = self.monitoring_sessions[trip_id]
            disruptions = await self._detect_disruptions(session)
            
            return self._create_success_response({
                "trip_id": trip_id,
                "disruptions": disruptions,
                "check_time": datetime.utcnow().isoformat(),
                "disruption_count": len(disruptions)
            })
            
        except Exception as e:
            self.logger.error(f"Error checking disruptions: {str(e)}")
            return self._create_error_response(f"Failed to check disruptions: {str(e)}")
    
    async def _get_monitoring_status(self, content: Dict[str, Any]) -> AgentResponse:
        """Get current monitoring status."""
        try:
            active_sessions = {
                trip_id: {
                    "user_id": session.user_id,
                    "start_time": session.start_time.isoformat(),
                    "last_check": session.last_check.isoformat() if session.last_check else None,
                    "active": session.active,
                    "monitoring_interval": session.monitoring_interval,
                    "current_activities": len(session.current_activities)
                }
                for trip_id, session in self.monitoring_sessions.items()
            }
            
            return self._create_success_response({
                "monitoring_state": self.monitoring_state.value,
                "active_sessions": active_sessions,
                "total_sessions": len(self.monitoring_sessions)
            })
            
        except Exception as e:
            self.logger.error(f"Error getting monitoring status: {str(e)}")
            return self._create_error_response(f"Failed to get monitoring status: {str(e)}")
    
    async def _run_monitoring_cycle(self, content: Dict[str, Any]) -> AgentResponse:
        """Run a monitoring cycle for all active sessions."""
        try:
            all_disruptions = []
            
            for trip_id, session in self.monitoring_sessions.items():
                if not session.active:
                    continue
                
                # Check if it's time to monitor this session
                if session.last_check:
                    time_since_check = (datetime.utcnow() - session.last_check).total_seconds()
                    if time_since_check < session.monitoring_interval:
                        continue
                
                # Detect disruptions
                disruptions = await self._detect_disruptions(session)
                
                # Update last check time
                session.last_check = datetime.utcnow()
                
                # Add to results
                if disruptions:
                    all_disruptions.extend([{
                        "trip_id": trip_id,
                        "disruption": disruption
                    } for disruption in disruptions])
            
            return self._create_success_response({
                "monitoring_cycle_complete": True,
                "cycle_time": datetime.utcnow().isoformat(),
                "sessions_checked": len([s for s in self.monitoring_sessions.values() if s.active]),
                "disruptions_found": len(all_disruptions),
                "disruptions": all_disruptions
            })
            
        except Exception as e:
            self.logger.error(f"Error running monitoring cycle: {str(e)}")
            return self._create_error_response(f"Failed to run monitoring cycle: {str(e)}")
    
    async def _detect_disruptions(self, session: MonitoringSession) -> List[Dict[str, Any]]:
        """Detect disruptions for a monitoring session."""
        disruptions = []
        
        # Check weather disruptions
        weather_disruptions = await self._check_weather_disruptions(session)
        disruptions.extend(weather_disruptions)
        
        # Check traffic disruptions
        traffic_disruptions = await self._check_traffic_disruptions(session)
        disruptions.extend(traffic_disruptions)
        
        # Check venue disruptions (simplified)
        venue_disruptions = await self._check_venue_disruptions(session)
        disruptions.extend(venue_disruptions)
        
        # TODO: Add flight disruptions when flight tools are implemented
        
        return disruptions
    
    async def _check_weather_disruptions(self, session: MonitoringSession) -> List[Dict[str, Any]]:
        """Check for weather-related disruptions."""
        disruptions = []
        
        try:
            # Get current activities with locations
            current_activities = session.current_activities
            if not current_activities:
                return disruptions
            
            # Check weather for each activity location
            for activity in current_activities:
                if not activity.location or not activity.location.name:
                    continue
                
                # Get weather alerts
                weather_response = await self.use_tool(
                    "weather",
                    action="weather_alerts",
                    location=activity.location.name
                )
                
                if weather_response.success:
                    alerts = weather_response.data.get("alerts", [])
                    
                    for alert in alerts:
                        # Check if alert meets our thresholds
                        if self._is_significant_weather_alert(alert):
                            disruptions.append({
                                "type": DisruptionType.WEATHER.value,
                                "severity": alert.get("severity", "medium"),
                                "title": alert.get("title", "Weather Alert"),
                                "description": alert.get("description", "Weather conditions may affect travel"),
                                "affected_activity": activity.name,
                                "location": activity.location.name,
                                "detected_at": datetime.utcnow().isoformat(),
                                "source": "weather_monitor"
                            })
                
                # Also check current weather conditions
                current_weather_response = await self.use_tool(
                    "weather",
                    action="current_weather",
                    location=activity.location.name
                )
                
                if current_weather_response.success:
                    weather_data = current_weather_response.data.get("current_weather", {})
                    weather_disruption = self._analyze_weather_conditions(weather_data, activity)
                    
                    if weather_disruption:
                        disruptions.append(weather_disruption)
        
        except Exception as e:
            self.logger.error(f"Error checking weather disruptions: {str(e)}")
        
        return disruptions
    
    async def _check_traffic_disruptions(self, session: MonitoringSession) -> List[Dict[str, Any]]:
        """Check for traffic-related disruptions."""
        disruptions = []
        
        try:
            # Check travel times between consecutive activities
            activities = session.current_activities
            
            for i in range(len(activities) - 1):
                current = activities[i]
                next_activity = activities[i + 1]
                
                if not (current.location and next_activity.location):
                    continue
                
                # Get current travel time
                travel_response = await self.use_tool(
                    "google_maps",
                    action="calculate_travel_time",
                    origin=f"{current.location.latitude},{current.location.longitude}",
                    destination=f"{next_activity.location.latitude},{next_activity.location.longitude}",
                    travel_mode="driving"
                )
                
                if travel_response.success:
                    current_duration = travel_response.data.get("duration", {}).get("value_seconds", 0) / 60
                    expected_duration = next_activity.travel_time_from_previous or 30
                    
                    # Check if significantly longer than expected
                    if current_duration > expected_duration + self.monitoring_config["traffic_delay_threshold"]:
                        disruptions.append({
                            "type": DisruptionType.TRAFFIC.value,
                            "severity": "medium",
                            "title": "Traffic Delay",
                            "description": f"Travel time from {current.name} to {next_activity.name} is {current_duration:.0f} minutes (expected {expected_duration:.0f} minutes)",
                            "affected_activities": [current.name, next_activity.name],
                            "current_duration": current_duration,
                            "expected_duration": expected_duration,
                            "detected_at": datetime.utcnow().isoformat(),
                            "source": "traffic_monitor"
                        })
        
        except Exception as e:
            self.logger.error(f"Error checking traffic disruptions: {str(e)}")
        
        return disruptions
    
    async def _check_venue_disruptions(self, session: MonitoringSession) -> List[Dict[str, Any]]:
        """Check for venue-related disruptions."""
        disruptions = []
        
        try:
            # This is a simplified implementation
            # In a real system, you would integrate with venue APIs or news feeds
            
            for activity in session.current_activities:
                # Check if venue has operating hours and if it's currently open
                if activity.location and activity.location.place_id:
                    # Get updated place information
                    place_response = await self.use_tool(
                        "google_maps",
                        action="search_location",
                        query=activity.location.place_id
                    )
                    
                    if place_response.success:
                        locations = place_response.data.get("locations", [])
                        if locations:
                            location = locations[0]
                            opening_hours = location.get("opening_hours", {})
                            
                            # Check if venue is closed when it should be open
                            if opening_hours.get("open_now") is False:
                                # This is a simplification - in reality you'd check against the activity timing
                                disruptions.append({
                                    "type": DisruptionType.VENUE_CLOSURE.value,
                                    "severity": "high",
                                    "title": "Venue Closure",
                                    "description": f"{activity.name} appears to be closed",
                                    "affected_activity": activity.name,
                                    "location": activity.location.name,
                                    "detected_at": datetime.utcnow().isoformat(),
                                    "source": "venue_monitor"
                                })
        
        except Exception as e:
            self.logger.error(f"Error checking venue disruptions: {str(e)}")
        
        return disruptions
    
    def _get_current_activities(self, trip: Trip) -> List[Activity]:
        """Get current activities for the trip."""
        current_date = datetime.utcnow().date()
        current_activities = []
        
        for day in trip.itinerary:
            if day.date == current_date:
                current_activities.extend(day.activities)
        
        return current_activities
    
    def _get_monitoring_interval(self, trip: Trip) -> int:
        """Get monitoring interval based on trip status."""
        current_date = datetime.utcnow().date()
        
        if trip.start_date <= current_date <= trip.end_date:
            return self.monitoring_config["monitoring_intervals"]["active_trip"]
        elif trip.start_date > current_date:
            return self.monitoring_config["monitoring_intervals"]["upcoming_trip"]
        else:
            return self.monitoring_config["monitoring_intervals"]["completed_trip"]
    
    def _is_significant_weather_alert(self, alert: Dict[str, Any]) -> bool:
        """Check if weather alert is significant enough to report."""
        alert_type = alert.get("type", "").lower()
        severity = alert.get("severity", "").lower()
        
        # High severity alerts are always significant
        if severity == "high":
            return True
        
        # Check specific thresholds
        if alert_type == "precipitation":
            description = alert.get("description", "")
            # Extract precipitation amount if available
            # This is a simplified check
            return "heavy" in description.lower()
        
        return severity in ["medium", "high"]
    
    def _analyze_weather_conditions(self, weather_data: Dict[str, Any], activity: Activity) -> Optional[Dict[str, Any]]:
        """Analyze weather conditions for potential disruptions."""
        config = self.monitoring_config["weather_alert_threshold"]
        
        # Check precipitation
        precipitation = weather_data.get("precipitation", 0)
        if precipitation > config["precipitation"]:
            return {
                "type": DisruptionType.WEATHER.value,
                "severity": "medium",
                "title": "Heavy Precipitation",
                "description": f"Heavy precipitation ({precipitation}mm) may affect outdoor activities",
                "affected_activity": activity.name,
                "location": activity.location.name if activity.location else None,
                "detected_at": datetime.utcnow().isoformat(),
                "source": "weather_monitor"
            }
        
        # Check wind speed
        wind_speed = weather_data.get("wind_speed", 0)
        if wind_speed > config["wind_speed"]:
            return {
                "type": DisruptionType.WEATHER.value,
                "severity": "medium",
                "title": "Strong Wind",
                "description": f"Strong wind ({wind_speed} km/h) may affect outdoor activities",
                "affected_activity": activity.name,
                "location": activity.location.name if activity.location else None,
                "detected_at": datetime.utcnow().isoformat(),
                "source": "weather_monitor"
            }
        
        # Check temperature extremes
        temperature = weather_data.get("temperature", 20)
        if temperature < config["temperature_low"]:
            return {
                "type": DisruptionType.WEATHER.value,
                "severity": "medium",
                "title": "Extreme Cold",
                "description": f"Very cold temperature ({temperature}°C) may affect outdoor activities",
                "affected_activity": activity.name,
                "location": activity.location.name if activity.location else None,
                "detected_at": datetime.utcnow().isoformat(),
                "source": "weather_monitor"
            }
        
        if temperature > config["temperature_high"]:
            return {
                "type": DisruptionType.WEATHER.value,
                "severity": "medium",
                "title": "Extreme Heat",
                "description": f"Very hot temperature ({temperature}°C) may affect outdoor activities",
                "affected_activity": activity.name,
                "location": activity.location.name if activity.location else None,
                "detected_at": datetime.utcnow().isoformat(),
                "source": "weather_monitor"
            }
        
        return None 