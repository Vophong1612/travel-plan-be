import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.profiler_agent import ProfilerAgent
from src.agents.itinerary_agent import ItineraryAgent
from src.agents.critique_agent import CritiqueAgent
from src.agents.monitor_agent import MonitorAgent
from src.models.trip import Trip, TripStatus, ItineraryDay, ItineraryDayStatus, DisruptionAlert
from src.models.user import UserProfile


class PlanningState(str, Enum):
    IDLE = "idle"
    PROFILING = "profiling"
    PLANNING = "planning"
    REVIEWING = "reviewing"
    CONFIRMING = "confirming"
    MONITORING = "monitoring"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class PlanningSession:
    """Planning session for a trip."""
    trip_id: str
    user_id: str
    state: PlanningState
    current_day: int
    total_days: int
    user_profile: Optional[UserProfile] = None
    trip_data: Optional[Trip] = None
    context: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


class OrchestratorAgent(BaseAgent):
    """Master orchestrator agent that manages the entire trip planning workflow."""
    
    def __init__(self):
        super().__init__(
            agent_id="orchestrator",
            name="Trip Planning Orchestrator",
            description="Manages end-to-end trip planning and coordination between all agents",
            tools=["travel_mcp_tool"]  # Orchestrator uses travel tool for budget calculation and flight search
        )
        
        # Initialize sub-agents
        self.profiler = ProfilerAgent()
        self.itinerary = ItineraryAgent()
        self.critique = CritiqueAgent()
        self.monitor = MonitorAgent()
        
        # Active planning sessions
        self.planning_sessions: Dict[str, PlanningSession] = {}
        
        # Workflow configuration
        self.workflow_config = {
            "max_revision_cycles": 3,
            "auto_approve_threshold": 85,
            "max_planning_time_minutes": 30,
            "enable_auto_monitoring": True,
            "confirmation_timeout_minutes": 60
        }
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are the master orchestrator for an AI travel planning service. Your role is to:
        1. Guide users from initial request to trip completion
        2. Coordinate all specialized agents (Profiler, Itinerary, Critique, Monitor)
        3. Manage the complete planning workflow
        4. Handle dynamic replanning during trips
        5. Ensure high-quality, personalized travel experiences
        
        Your workflow:
        - Start with user profiling if needed
        - Enter planning loop for each day: generate -> critique -> revise -> confirm
        - Monitor trips during execution
        - Handle disruptions with dynamic replanning
        
        Always maintain user control and confirm major decisions.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the orchestrator agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "start_trip_planning":
            return await self._start_trip_planning(content)
        elif message_type == "continue_planning":
            return await self._continue_planning(content)
        elif message_type == "confirm_day":
            return await self._confirm_day(content)
        elif message_type == "request_revision":
            return await self._request_revision(content)
        elif message_type == "start_trip_monitoring":
            return await self._start_trip_monitoring(content)
        elif message_type == "handle_disruption":
            return await self._handle_disruption(content)
        elif message_type == "get_planning_status":
            return await self._get_planning_status(content)
        elif message_type == "cancel_planning":
            return await self._cancel_planning(content)
        # Chat-related message types
        elif message_type == "get_session_status":
            return await self._get_session_status(content)
        elif message_type == "reset_session":
            return await self._reset_session(content)
        elif message_type == "get_chat_history":
            return await self._get_chat_history(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _start_trip_planning(self, content: Dict[str, Any]) -> AgentResponse:
        """Start the trip planning process."""
        try:
            # Extract trip parameters
            user_id = content.get("user_id")
            user_message = content.get("user_message", "")
            
            # Parse trip information from user message
            trip_info = await self._parse_trip_from_message(user_message)
            
            if not trip_info:
                return self._create_success_response({
                    "message": "I'd be happy to help you plan a trip! Please tell me where you'd like to go and when. For example: 'I want to visit Paris from October 10th to October 15th' or 'Plan a 5-day trip to Tokyo in December'.",
                    "planning_state": "waiting_for_details"
                })
            
            destination = trip_info.get("destination")
            start_date = trip_info.get("start_date")
            end_date = trip_info.get("end_date")
            duration_days = trip_info.get("duration_days", 1)
            
            # Generate trip ID
            trip_id = f"trip_{user_id}_{int(datetime.utcnow().timestamp())}"
            
            # Create planning session
            session = PlanningSession(
                trip_id=trip_id,
                user_id=user_id,
                state=PlanningState.PROFILING,
                current_day=0,
                total_days=duration_days,
                context={
                    "destination": destination,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "duration_days": duration_days
                }
            )
            
            # Store session
            self.planning_sessions[trip_id] = session
            
            # Check if user profile exists
            existing_profile = self.get_memory(f"user_profile_{user_id}", scope="user")
            
            if existing_profile:
                # Use existing profile
                session.user_profile = UserProfile(**existing_profile)
                session.state = PlanningState.PLANNING
                
                # Start planning
                return await self._start_daily_planning(session)
            else:
                # Start profiling
                return await self._start_profiling(session)
            
        except Exception as e:
            self.logger.error(f"Error starting trip planning: {str(e)}")
            return self._create_error_response(f"Failed to start trip planning: {str(e)}")
    
    async def _start_profiling(self, session: PlanningSession) -> AgentResponse:
        """Start user profiling process."""
        try:
            # Start profiling with the Profiler agent
            profiler_message = AgentMessage(
                agent_id="orchestrator",
                message_type="start_onboarding",
                content={"user_id": session.user_id}
            )
            
            profiler_response = await self.profiler.process_message(profiler_message)
            
            if profiler_response.success:
                return self._create_success_response({
                    "trip_id": session.trip_id,
                    "state": "profiling",
                    "profiling_started": True,
                    "question": profiler_response.data.get("question"),
                    "progress": profiler_response.data.get("progress")
                })
            else:
                return self._create_error_response(f"Profiling failed: {profiler_response.error}")
                
        except Exception as e:
            self.logger.error(f"Error starting profiling: {str(e)}")
            return self._create_error_response(f"Failed to start profiling: {str(e)}")
    
    async def _continue_planning(self, content: Dict[str, Any]) -> AgentResponse:
        """Continue the planning process."""
        try:
            user_id = content.get("user_id")
            user_message = content.get("user_message", "")
            trip_id = content.get("trip_id")
            
            # If no trip_id, try to find active session for user
            if not trip_id:
                for session in self.planning_sessions.values():
                    if session.user_id == user_id:
                        trip_id = session.trip_id
                        break
            
            if not trip_id or trip_id not in self.planning_sessions:
                # No active session, try to start new planning
                return await self._start_trip_planning(content)
            
            session = self.planning_sessions[trip_id]
            
            if session.state == PlanningState.PROFILING:
                return await self._continue_profiling(session, content)
            elif session.state == PlanningState.PLANNING:
                return await self._continue_daily_planning(session, content)
            elif session.state == PlanningState.CONFIRMING:
                return await self._handle_confirmation(session, content)
            else:
                return self._create_success_response({
                    "message": f"I'm currently in {session.state.value} state. How can I help you?",
                    "trip_id": trip_id,
                    "planning_state": session.state.value
                })
                
        except Exception as e:
            self.logger.error(f"Error continuing planning: {str(e)}")
            return self._create_error_response(f"Failed to continue planning: {str(e)}")
    
    async def _continue_profiling(self, session: PlanningSession, content: Dict[str, Any]) -> AgentResponse:
        """Continue the profiling process."""
        try:
            user_response = content.get("user_response")
            if not user_response:
                return self._create_error_response("user_response is required")
            
            # Process response with Profiler agent
            profiler_message = AgentMessage(
                agent_id="orchestrator",
                message_type="process_response",
                content={"response": user_response}
            )
            
            profiler_response = await self.profiler.process_message(profiler_message)
            
            if profiler_response.success:
                if profiler_response.data.get("onboarding_complete"):
                    # Profiling complete, confirm with user
                    return self._create_success_response({
                        "trip_id": session.trip_id,
                        "profiling_complete": True,
                        "profile": profiler_response.data.get("profile"),
                        "summary": profiler_response.data.get("summary"),
                        "confirmation_needed": True
                    })
                else:
                    # Continue profiling
                    return self._create_success_response({
                        "trip_id": session.trip_id,
                        "state": "profiling",
                        "next_question": profiler_response.data.get("next_question"),
                        "progress": profiler_response.data.get("progress")
                    })
            else:
                return self._create_error_response(f"Profiling failed: {profiler_response.error}")
                
        except Exception as e:
            self.logger.error(f"Error continuing profiling: {str(e)}")
            return self._create_error_response(f"Failed to continue profiling: {str(e)}")
    
    async def _start_daily_planning(self, session: PlanningSession) -> AgentResponse:
        """Start daily planning process."""
        try:
            session.state = PlanningState.PLANNING
            session.current_day = 1
            session.updated_at = datetime.utcnow()
            
            # Start planning Day 1
            return await self._plan_day(session, 1)
            
        except Exception as e:
            self.logger.error(f"Error starting daily planning: {str(e)}")
            return self._create_error_response(f"Failed to start daily planning: {str(e)}")
    
    async def _plan_day(self, session: PlanningSession, day_number: int) -> AgentResponse:
        """Plan a specific day."""
        try:
            # Calculate date for this day
            start_date = datetime.fromisoformat(session.context["start_date"]).date()
            day_date = start_date + timedelta(days=day_number - 1)
            
            # Generate itinerary with Itinerary agent
            itinerary_message = AgentMessage(
                agent_id="orchestrator",
                message_type="generate_itinerary",
                content={
                    "user_profile": session.user_profile.dict(),
                    "destination": session.context["destination"],
                    "date": day_date.isoformat(),
                    "day_index": day_number
                }
            )
            
            itinerary_response = await self.itinerary.process_message(itinerary_message)
            
            if not itinerary_response.success:
                return self._create_error_response(f"Itinerary generation failed: {itinerary_response.error}")
            
            # Critique the itinerary
            critique_message = AgentMessage(
                agent_id="orchestrator",
                message_type="critique_itinerary",
                content={
                    "itinerary": itinerary_response.data["itinerary"],
                    "user_profile": session.user_profile.dict()
                }
            )
            
            critique_response = await self.critique.process_message(critique_message)
            
            if not critique_response.success:
                return self._create_error_response(f"Critique failed: {critique_response.error}")
            
            critique_result = critique_response.data["critique_result"]
            
            # Check if approved
            if critique_result["approved"]:
                # Present to user for confirmation
                session.state = PlanningState.CONFIRMING
                session.updated_at = datetime.utcnow()
                
                return self._create_success_response({
                    "trip_id": session.trip_id,
                    "day_number": day_number,
                    "state": "confirming",
                    "itinerary": itinerary_response.data["itinerary"],
                    "critique_score": critique_result["score"],
                    "day_progress": {
                        "current": day_number,
                        "total": session.total_days
                    }
                })
            else:
                # Needs revision
                return await self._revise_itinerary(session, day_number, itinerary_response.data, critique_result)
                
        except Exception as e:
            self.logger.error(f"Error planning day {day_number}: {str(e)}")
            return self._create_error_response(f"Failed to plan day {day_number}: {str(e)}")
    
    async def _revise_itinerary(self, session: PlanningSession, day_number: int, itinerary_data: Dict[str, Any], critique_result: Dict[str, Any]) -> AgentResponse:
        """Revise an itinerary based on critique."""
        try:
            # Check revision cycle limit
            revision_count = session.context.get("revision_count", 0)
            if revision_count >= self.workflow_config["max_revision_cycles"]:
                # Too many revisions, present current version
                return self._create_success_response({
                    "trip_id": session.trip_id,
                    "day_number": day_number,
                    "state": "confirming",
                    "itinerary": itinerary_data["itinerary"],
                    "critique_score": critique_result["score"],
                    "warning": "Maximum revisions reached, presenting current version",
                    "issues": critique_result["issues"]
                })
            
            # Generate revision feedback
            revision_feedback = self._generate_revision_feedback(critique_result)
            
            # Revise with Itinerary agent
            revision_message = AgentMessage(
                agent_id="orchestrator",
                message_type="revise_itinerary",
                content={
                    "user_profile": session.user_profile.dict(),
                    "destination": session.context["destination"],
                    "date": datetime.fromisoformat(session.context["start_date"]).date() + timedelta(days=day_number - 1),
                    "day_index": day_number,
                    "existing_itinerary": itinerary_data["itinerary"],
                    "revision_feedback": revision_feedback
                }
            )
            
            revision_response = await self.itinerary.process_message(revision_message)
            
            if revision_response.success:
                # Update revision count
                session.context["revision_count"] = revision_count + 1
                
                # Re-critique the revised itinerary
                return await self._plan_day(session, day_number)
            else:
                return self._create_error_response(f"Revision failed: {revision_response.error}")
                
        except Exception as e:
            self.logger.error(f"Error revising itinerary: {str(e)}")
            return self._create_error_response(f"Failed to revise itinerary: {str(e)}")
    
    async def _confirm_day(self, content: Dict[str, Any]) -> AgentResponse:
        """Confirm a day's itinerary."""
        try:
            trip_id = content.get("trip_id")
            day_number = content.get("day_number")
            confirmed = content.get("confirmed", False)
            
            if not trip_id or trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            session = self.planning_sessions[trip_id]
            
            if not confirmed:
                return self._create_error_response("Day not confirmed")
            
            # Mark day as confirmed
            session.current_day = day_number
            session.updated_at = datetime.utcnow()
            
            # Check if all days are planned
            if day_number >= session.total_days:
                # Trip planning complete
                session.state = PlanningState.COMPLETED
                
                # Start monitoring if enabled
                if self.workflow_config["enable_auto_monitoring"]:
                    await self._start_trip_monitoring({"trip_id": trip_id})
                
                return self._create_success_response({
                    "trip_id": trip_id,
                    "planning_complete": True,
                    "state": "completed",
                    "total_days": session.total_days,
                    "monitoring_started": self.workflow_config["enable_auto_monitoring"]
                })
            else:
                # Plan next day
                next_day = day_number + 1
                return await self._plan_day(session, next_day)
                
        except Exception as e:
            self.logger.error(f"Error confirming day: {str(e)}")
            return self._create_error_response(f"Failed to confirm day: {str(e)}")
    
    async def _request_revision(self, content: Dict[str, Any]) -> AgentResponse:
        """Request revision of a day's itinerary."""
        try:
            trip_id = content.get("trip_id")
            day_number = content.get("day_number")
            feedback = content.get("feedback")
            
            if not all([trip_id, day_number, feedback]):
                return self._create_error_response("trip_id, day_number, and feedback are required")
            
            if trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            session = self.planning_sessions[trip_id]
            
            # Store user feedback
            session.context["user_feedback"] = feedback
            session.updated_at = datetime.utcnow()
            
            # Calculate date for this day
            start_date = datetime.fromisoformat(session.context["start_date"]).date()
            day_date = start_date + timedelta(days=day_number - 1)
            
            # Revise with user feedback
            revision_message = AgentMessage(
                agent_id="orchestrator",
                message_type="revise_itinerary",
                content={
                    "user_profile": session.user_profile.dict(),
                    "destination": session.context["destination"],
                    "date": day_date.isoformat(),
                    "day_index": day_number,
                    "revision_feedback": feedback
                }
            )
            
            revision_response = await self.itinerary.process_message(revision_message)
            
            if revision_response.success:
                # Re-critique the revised itinerary
                return await self._plan_day(session, day_number)
            else:
                return self._create_error_response(f"Revision failed: {revision_response.error}")
                
        except Exception as e:
            self.logger.error(f"Error requesting revision: {str(e)}")
            return self._create_error_response(f"Failed to request revision: {str(e)}")
    
    async def _start_trip_monitoring(self, content: Dict[str, Any]) -> AgentResponse:
        """Start monitoring a trip."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id or trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            session = self.planning_sessions[trip_id]
            
            # Get trip data
            trip_data = session.trip_data
            if not trip_data:
                # Create trip data from session
                trip_data = Trip(
                    trip_id=trip_id,
                    user_id=session.user_id,
                    destination=session.context["destination"],
                    start_date=datetime.fromisoformat(session.context["start_date"]).date(),
                    end_date=datetime.fromisoformat(session.context["end_date"]).date(),
                    duration_days=session.context["duration_days"],
                    status=TripStatus.CONFIRMED
                )
            
            # Start monitoring
            monitor_message = AgentMessage(
                agent_id="orchestrator",
                message_type="start_monitoring",
                content={
                    "trip_id": trip_id,
                    "user_id": session.user_id,
                    "trip_data": trip_data.dict()
                }
            )
            
            monitor_response = await self.monitor.process_message(monitor_message)
            
            if monitor_response.success:
                session.state = PlanningState.MONITORING
                session.updated_at = datetime.utcnow()
                
                return self._create_success_response({
                    "trip_id": trip_id,
                    "monitoring_started": True,
                    "state": "monitoring",
                    "monitoring_interval": monitor_response.data.get("monitoring_interval")
                })
            else:
                return self._create_error_response(f"Monitoring failed: {monitor_response.error}")
                
        except Exception as e:
            self.logger.error(f"Error starting trip monitoring: {str(e)}")
            return self._create_error_response(f"Failed to start trip monitoring: {str(e)}")
    
    async def _handle_disruption(self, content: Dict[str, Any]) -> AgentResponse:
        """Handle a trip disruption."""
        try:
            trip_id = content.get("trip_id")
            disruption_data = content.get("disruption")
            
            if not all([trip_id, disruption_data]):
                return self._create_error_response("trip_id and disruption are required")
            
            if trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            session = self.planning_sessions[trip_id]
            session.state = PlanningState.REPLANNING
            session.updated_at = datetime.utcnow()
            
            # Analyze disruption impact
            disruption_impact = await self._analyze_disruption_impact(session, disruption_data)
            
            # Generate replanning options
            replanning_options = await self._generate_replanning_options(session, disruption_data, disruption_impact)
            
            return self._create_success_response({
                "trip_id": trip_id,
                "disruption_handled": True,
                "state": "replanning",
                "disruption_impact": disruption_impact,
                "replanning_options": replanning_options
            })
            
        except Exception as e:
            self.logger.error(f"Error handling disruption: {str(e)}")
            return self._create_error_response(f"Failed to handle disruption: {str(e)}")
    
    async def _get_planning_status(self, content: Dict[str, Any]) -> AgentResponse:
        """Get current planning status."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id or trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            session = self.planning_sessions[trip_id]
            
            return self._create_success_response({
                "trip_id": trip_id,
                "state": session.state.value,
                "current_day": session.current_day,
                "total_days": session.total_days,
                "progress": session.current_day / session.total_days * 100,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "context": session.context
            })
            
        except Exception as e:
            self.logger.error(f"Error getting planning status: {str(e)}")
            return self._create_error_response(f"Failed to get planning status: {str(e)}")
    
    async def _cancel_planning(self, content: Dict[str, Any]) -> AgentResponse:
        """Cancel trip planning."""
        try:
            trip_id = content.get("trip_id")
            if not trip_id or trip_id not in self.planning_sessions:
                return self._create_error_response("Invalid trip_id")
            
            # Remove session
            del self.planning_sessions[trip_id]
            
            return self._create_success_response({
                "trip_id": trip_id,
                "planning_cancelled": True
            })
            
        except Exception as e:
            self.logger.error(f"Error cancelling planning: {str(e)}")
            return self._create_error_response(f"Failed to cancel planning: {str(e)}")
    
    def _generate_revision_feedback(self, critique_result: Dict[str, Any]) -> str:
        """Generate feedback for revision based on critique."""
        issues = critique_result.get("issues", [])
        
        feedback_parts = []
        for issue in issues:
            if issue.get("severity") == "high":
                feedback_parts.append(f"Critical: {issue.get('description', 'Unknown issue')}")
            elif issue.get("severity") == "medium":
                feedback_parts.append(f"Issue: {issue.get('description', 'Unknown issue')}")
        
        return "; ".join(feedback_parts) if feedback_parts else "Please improve the itinerary quality"
    
    async def _analyze_disruption_impact(self, session: PlanningSession, disruption_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the impact of a disruption."""
        # Simplified disruption impact analysis
        return {
            "severity": disruption_data.get("severity", "medium"),
            "affected_activities": disruption_data.get("affected_activities", []),
            "requires_replanning": True,
            "impact_score": 0.7  # Simplified scoring
        }
    
    async def _generate_replanning_options(self, session: PlanningSession, disruption_data: Dict[str, Any], impact: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate replanning options for a disruption."""
        # Simplified replanning options
        return [
            {
                "option": "reschedule_activities",
                "description": "Reschedule affected activities to later times",
                "estimated_impact": "low"
            },
            {
                "option": "replace_activities",
                "description": "Replace affected activities with alternatives",
                "estimated_impact": "medium"
            },
            {
                "option": "cancel_activities",
                "description": "Cancel affected activities and extend others",
                "estimated_impact": "high"
            }
        ]
    
    # Chat-related handlers
    
    async def _get_session_status(self, content: Dict[str, Any]) -> AgentResponse:
        """Get current session status for chat."""
        try:
            user_id = content.get("user_id")
            if not user_id:
                return self._create_error_response("user_id is required")
            
            # Find active session for user
            active_session = None
            for session in self.planning_sessions.values():
                if session.user_id == user_id:
                    active_session = session
                    break
            
            if not active_session:
                return self._create_success_response({
                    "status": "no_active_session",
                    "message": "No active planning session found"
                })
            
            return self._create_success_response({
                "status": "active",
                "trip_id": active_session.trip_id,
                "state": active_session.state.value,
                "current_day": active_session.current_day,
                "total_days": active_session.total_days,
                "progress": active_session.current_day / active_session.total_days * 100 if active_session.total_days > 0 else 0,
                "created_at": active_session.created_at.isoformat(),
                "updated_at": active_session.updated_at.isoformat(),
                "destination": active_session.context.get("destination") if active_session.context else None
            })
            
        except Exception as e:
            self.logger.error(f"Error getting session status: {str(e)}")
            return self._create_error_response(f"Failed to get session status: {str(e)}")
    
    async def _reset_session(self, content: Dict[str, Any]) -> AgentResponse:
        """Reset the current session for the user."""
        try:
            user_id = content.get("user_id")
            if not user_id:
                return self._create_error_response("user_id is required")
            
            # Find and remove active session for user
            sessions_to_remove = []
            for trip_id, session in self.planning_sessions.items():
                if session.user_id == user_id:
                    sessions_to_remove.append(trip_id)
            
            for trip_id in sessions_to_remove:
                del self.planning_sessions[trip_id]
            
            return self._create_success_response({
                "message": "Session reset successfully",
                "sessions_removed": len(sessions_to_remove)
            })
            
        except Exception as e:
            self.logger.error(f"Error resetting session: {str(e)}")
            return self._create_error_response(f"Failed to reset session: {str(e)}")
    
    async def _get_chat_history(self, content: Dict[str, Any]) -> AgentResponse:
        """Get chat history for the user."""
        try:
            user_id = content.get("user_id")
            if not user_id:
                return self._create_error_response("user_id is required")
            
            # Get conversation history from orchestrator agent
            history = self.get_conversation_history()
            
            # Filter for user-specific messages (simplified)
            user_history = [
                {
                    "timestamp": msg.timestamp.isoformat(),
                    "message_type": msg.message_type,
                    "content": msg.content
                }
                for msg in history[-50:]  # Last 50 messages
            ]
            
            return self._create_success_response({
                "history": user_history,
                "count": len(user_history)
            })
            
        except Exception as e:
            self.logger.error(f"Error getting chat history: {str(e)}")
            return self._create_error_response(f"Failed to get chat history: {str(e)}")
    
    # Helper methods for chat functionality
    
    async def _parse_trip_from_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Parse trip information from user message."""
        try:
            # Simple keyword-based parsing (in production, use AI for better parsing)
            message_lower = message.lower()
            
            # Common destination keywords
            destinations = ["paris", "tokyo", "new york", "london", "rome", "barcelona", "amsterdam", "berlin", "prague", "vienna"]
            found_destination = None
            for dest in destinations:
                if dest in message_lower:
                    found_destination = dest.title()
                    break
            
            if not found_destination:
                return None
            
            # Simple date parsing (very basic)
            import re
            from datetime import datetime, timedelta
            
            # Look for date patterns
            date_patterns = [
                r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})",  # MM/DD/YYYY or DD/MM/YYYY
                r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",  # YYYY/MM/DD
            ]
            
            start_date = None
            end_date = None
            
            # For demo purposes, use current date + 30 days as default
            current_date = datetime.now().date()
            start_date = current_date + timedelta(days=30)
            end_date = start_date + timedelta(days=4)  # 5-day trip
            
            # Look for duration keywords
            if "week" in message_lower or "7 days" in message_lower:
                end_date = start_date + timedelta(days=6)
            elif "month" in message_lower or "30 days" in message_lower:
                end_date = start_date + timedelta(days=29)
            
            return {
                "destination": found_destination,
                "start_date": start_date,
                "end_date": end_date,
                "duration_days": (end_date - start_date).days + 1
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing trip from message: {str(e)}")
            return None
    
    async def _handle_confirmation(self, session: PlanningSession, content: Dict[str, Any]) -> AgentResponse:
        """Handle user confirmation in CONFIRMING state."""
        try:
            user_message = content.get("user_message", "").lower()
            
            # Check if user is confirming
            confirm_keywords = ["yes", "okay", "sure", "confirm", "approve", "good", "perfect", "looks good"]
            if any(keyword in user_message for keyword in confirm_keywords):
                # Confirm the current day
                return await self._confirm_day({
                    "trip_id": session.trip_id,
                    "day_number": session.current_day,
                    "confirmed": True
                })
            else:
                # User might be requesting changes
                return await self._request_revision({
                    "trip_id": session.trip_id,
                    "day_number": session.current_day,
                    "feedback": user_message
                })
                
        except Exception as e:
            self.logger.error(f"Error handling confirmation: {str(e)}")
            return self._create_error_response(f"Failed to handle confirmation: {str(e)}")
    
    async def _continue_daily_planning(self, session: PlanningSession, content: Dict[str, Any]) -> AgentResponse:
        """Continue daily planning process."""
        try:
            # For now, just return current status
            return self._create_success_response({
                "message": f"I'm currently planning day {session.current_day} of {session.total_days} for your trip to {session.context.get('destination')}. What would you like me to do?",
                "trip_id": session.trip_id,
                "planning_state": session.state.value,
                "current_day": session.current_day,
                "total_days": session.total_days
            })
            
        except Exception as e:
            self.logger.error(f"Error continuing daily planning: {str(e)}")
            return self._create_error_response(f"Failed to continue daily planning: {str(e)}") 