import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from src.agents.base_agent import BaseAgent, AgentMessage, AgentResponse
from src.agents.user_intent_agent import UserIntentAgent
from src.agents.location_weather_agent import LocationWeatherAgent
from src.agents.poi_activity_agent import POIActivityAgent
from src.agents.food_recommendation_agent import FoodRecommendationAgent
from src.agents.new_itinerary_agent import NewItineraryAgent
from src.agents.budget_estimation_agent import BudgetEstimationAgent
from src.agents.output_formatting_agent import OutputFormattingAgent


class WorkflowPhase(str, Enum):
    PHASE_1_INFORMATION_GATHERING = "phase_1_information_gathering"
    PHASE_2_PLAN_GENERATION = "phase_2_plan_generation"
    PHASE_3_BUDGET_ESTIMATION = "phase_3_budget_estimation"
    PHASE_4_OUTPUT_FORMATTING = "phase_4_output_formatting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class WorkflowSession:
    """Workflow session tracking."""
    session_id: str
    user_id: str
    current_phase: WorkflowPhase
    travel_context: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
    error_message: Optional[str] = None


class NewOrchestratorAgent(BaseAgent):
    """Master orchestrator following the 4-phase workflow design."""
    
    def __init__(self):
        super().__init__(
            agent_id="new_orchestrator",
            name="Travel Planning Orchestrator",
            description="Orchestrates the 4-phase travel planning workflow",
            tools=[]  # Orchestrator coordinates agents, doesn't use tools directly
        )
        
        # Initialize all workflow agents
        self.user_intent_agent = UserIntentAgent()
        self.location_weather_agent = LocationWeatherAgent()
        self.poi_activity_agent = POIActivityAgent()
        self.food_recommendation_agent = FoodRecommendationAgent()
        self.itinerary_agent = NewItineraryAgent()
        self.budget_estimation_agent = BudgetEstimationAgent()
        self.output_formatting_agent = OutputFormattingAgent()
        
        # Active workflow sessions
        self.workflow_sessions: Dict[str, WorkflowSession] = {}
    
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        return """
        You are the master orchestrator for a multi-agent AI travel planning system.
        
        Your workflow follows 4 phases:
        1. Phase 1: Information Gathering
           - User Intent Agent: Extract destination, duration, preferences
           - Location & Weather Agent: Validate location and get weather
           - POI & Activity Agent: Discover POIs and activities
           - Food Recommendation Agent: Find restaurants
        
        2. Phase 2: Plan Generation
           - Itinerary Generation Agent: Create optimized daily itineraries
        
        3. Phase 3: Budget Estimation
           - Budget Estimation Agent: Calculate costs and budget breakdown
        
        4. Phase 4: Output Formatting
           - Output Formatting Agent: Create final JSON response
        
        Coordinate agents sequentially, ensuring each phase completes before starting the next.
        Handle errors gracefully and provide clear feedback to users.
        """
    
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the orchestrator agent's functionality."""
        message_type = message.message_type
        content = message.content
        
        if message_type == "process_user_query":
            return await self._process_user_query(content)
        elif message_type == "get_session_status":
            return await self._get_session_status(content)
        elif message_type == "reset_session":
            return await self._reset_session(content)
        else:
            return self._create_error_response(f"Unknown message type: {message_type}")
    
    async def _process_user_query(self, content: Dict[str, Any]) -> AgentResponse:
        """Process a user query through the 4-phase workflow."""
        try:
            user_id = content.get("user_id", "default_user")
            user_query = content.get("user_query", "")
            
            if not user_query:
                return self._create_error_response("user_query is required")
            
            # Create or get workflow session
            session_id = f"session_{user_id}_{int(datetime.utcnow().timestamp())}"
            session = WorkflowSession(
                session_id=session_id,
                user_id=user_id,
                current_phase=WorkflowPhase.PHASE_1_INFORMATION_GATHERING
            )
            self.workflow_sessions[session_id] = session
            
            # Execute the complete workflow
            result = await self._execute_complete_workflow(session, user_query)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing user query: {str(e)}")
            return self._create_error_response(f"Failed to process user query: {str(e)}")
    
    async def _execute_complete_workflow(self, session: WorkflowSession, user_query: str) -> AgentResponse:
        """Execute the complete 4-phase workflow."""
        try:
            # Phase 1: Information Gathering
            self.logger.info(f"Starting Phase 1: Information Gathering for session {session.session_id}")
            phase1_result = await self._execute_phase_1(session, user_query)
            
            if not phase1_result:
                session.current_phase = WorkflowPhase.ERROR
                session.error_message = "Phase 1 failed"
                return self._create_error_response("Information gathering phase failed")
            
            # Phase 2: Plan Generation
            self.logger.info(f"Starting Phase 2: Plan Generation for session {session.session_id}")
            session.current_phase = WorkflowPhase.PHASE_2_PLAN_GENERATION
            phase2_result = await self._execute_phase_2(session)
            
            if not phase2_result:
                session.current_phase = WorkflowPhase.ERROR
                session.error_message = "Phase 2 failed"
                return self._create_error_response("Plan generation phase failed")
            
            # Phase 3: Budget Estimation
            self.logger.info(f"Starting Phase 3: Budget Estimation for session {session.session_id}")
            session.current_phase = WorkflowPhase.PHASE_3_BUDGET_ESTIMATION
            phase3_result = await self._execute_phase_3(session)
            
            if not phase3_result:
                session.current_phase = WorkflowPhase.ERROR
                session.error_message = "Phase 3 failed"
                return self._create_error_response("Budget estimation phase failed")
            
            # Phase 4: Output Formatting
            self.logger.info(f"Starting Phase 4: Output Formatting for session {session.session_id}")
            session.current_phase = WorkflowPhase.PHASE_4_OUTPUT_FORMATTING
            final_output = await self._execute_phase_4(session)
            
            if not final_output:
                session.current_phase = WorkflowPhase.ERROR
                session.error_message = "Phase 4 failed"
                return self._create_error_response("Output formatting phase failed")
            
            # Mark as completed
            session.current_phase = WorkflowPhase.COMPLETED
            session.updated_at = datetime.utcnow()
            
            self.logger.info(f"Workflow completed successfully for session {session.session_id}")
            
            # Return the final formatted output
            return self._create_success_response(final_output.data["final_response"])
            
        except Exception as e:
            session.current_phase = WorkflowPhase.ERROR
            session.error_message = str(e)
            self.logger.error(f"Error in workflow execution: {str(e)}")
            return self._create_error_response(f"Workflow execution failed: {str(e)}")
    
    async def _execute_phase_1(self, session: WorkflowSession, user_query: str) -> bool:
        """Execute Phase 1: Information Gathering."""
        try:
            # Step 1: User Intent Agent - Extract user intent
            intent_message = AgentMessage(
                agent_id="orchestrator",
                message_type="extract_user_intent",
                content={"user_query": user_query}
            )
            
            intent_response = await self.user_intent_agent.process_message(intent_message)
            if not intent_response.success:
                self.logger.error(f"User Intent Agent failed: {intent_response.error}")
                return False
            
            travel_context = intent_response.data["travel_context"]
            session.travel_context = travel_context
            
            # Step 2: Location & Weather Agent - Validate location and get weather
            location_message = AgentMessage(
                agent_id="orchestrator",
                message_type="validate_and_enrich",
                content={"travel_context": travel_context}
            )
            
            location_response = await self.location_weather_agent.process_message(location_message)
            if not location_response.success:
                self.logger.error(f"Location & Weather Agent failed: {location_response.error}")
                return False
            
            travel_context = location_response.data["travel_context"]
            session.travel_context = travel_context
            
            # Step 3: POI & Activity Agent - Discover POIs and activities
            poi_message = AgentMessage(
                agent_id="orchestrator",
                message_type="discover_pois_activities",
                content={"travel_context": travel_context}
            )
            
            poi_response = await self.poi_activity_agent.process_message(poi_message)
            if not poi_response.success:
                self.logger.error(f"POI & Activity Agent failed: {poi_response.error}")
                return False
            
            travel_context = poi_response.data["travel_context"]
            session.travel_context = travel_context
            
            # Step 4: Food Recommendation Agent - Discover restaurants
            food_message = AgentMessage(
                agent_id="orchestrator",
                message_type="discover_restaurants",
                content={"travel_context": travel_context}
            )
            
            food_response = await self.food_recommendation_agent.process_message(food_message)
            if not food_response.success:
                self.logger.error(f"Food Recommendation Agent failed: {food_response.error}")
                return False
            
            travel_context = food_response.data["travel_context"]
            session.travel_context = travel_context
            session.updated_at = datetime.utcnow()
            
            self.logger.info("Phase 1: Information Gathering completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Phase 1: {str(e)}")
            return False
    
    async def _execute_phase_2(self, session: WorkflowSession) -> bool:
        """Execute Phase 2: Plan Generation."""
        try:
            # Itinerary Generation Agent - Create proposed itinerary
            itinerary_message = AgentMessage(
                agent_id="orchestrator",
                message_type="generate_proposed_itinerary",
                content={"travel_context": session.travel_context}
            )
            
            itinerary_response = await self.itinerary_agent.process_message(itinerary_message)
            if not itinerary_response.success:
                self.logger.error(f"Itinerary Agent failed: {itinerary_response.error}")
                return False
            
            session.travel_context = itinerary_response.data["travel_context"]
            session.updated_at = datetime.utcnow()
            
            self.logger.info("Phase 2: Plan Generation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Phase 2: {str(e)}")
            return False
    
    async def _execute_phase_3(self, session: WorkflowSession) -> bool:
        """Execute Phase 3: Budget Estimation."""
        try:
            # Budget Estimation Agent - Calculate budget
            budget_message = AgentMessage(
                agent_id="orchestrator",
                message_type="calculate_budget",
                content={"travel_context": session.travel_context}
            )
            
            budget_response = await self.budget_estimation_agent.process_message(budget_message)
            if not budget_response.success:
                self.logger.error(f"Budget Estimation Agent failed: {budget_response.error}")
                return False
            
            session.travel_context = budget_response.data["travel_context"]
            session.updated_at = datetime.utcnow()
            
            self.logger.info("Phase 3: Budget Estimation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in Phase 3: {str(e)}")
            return False
    
    async def _execute_phase_4(self, session: WorkflowSession) -> Optional[AgentResponse]:
        """Execute Phase 4: Output Formatting."""
        try:
            # Output Formatting Agent - Create final response
            output_message = AgentMessage(
                agent_id="orchestrator",
                message_type="format_final_output",
                content={"travel_context": session.travel_context}
            )
            
            output_response = await self.output_formatting_agent.process_message(output_message)
            if not output_response.success:
                self.logger.error(f"Output Formatting Agent failed: {output_response.error}")
                return None
            
            session.updated_at = datetime.utcnow()
            
            self.logger.info("Phase 4: Output Formatting completed successfully")
            return output_response
            
        except Exception as e:
            self.logger.error(f"Error in Phase 4: {str(e)}")
            return None
    
    async def _get_session_status(self, content: Dict[str, Any]) -> AgentResponse:
        """Get the status of a workflow session."""
        try:
            user_id = content.get("user_id")
            session_id = content.get("session_id")
            
            if session_id and session_id in self.workflow_sessions:
                session = self.workflow_sessions[session_id]
            else:
                # Find most recent session for user
                user_sessions = [s for s in self.workflow_sessions.values() if s.user_id == user_id]
                if not user_sessions:
                    return self._create_success_response({
                        "status": "no_active_session",
                        "message": "No active workflow session found"
                    })
                session = max(user_sessions, key=lambda s: s.updated_at)
            
            return self._create_success_response({
                "session_id": session.session_id,
                "current_phase": session.current_phase.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "error_message": session.error_message,
                "has_travel_context": session.travel_context is not None
            })
            
        except Exception as e:
            self.logger.error(f"Error getting session status: {str(e)}")
            return self._create_error_response(f"Failed to get session status: {str(e)}")
    
    async def _reset_session(self, content: Dict[str, Any]) -> AgentResponse:
        """Reset workflow sessions for a user."""
        try:
            user_id = content.get("user_id")
            
            # Remove all sessions for the user
            sessions_to_remove = [sid for sid, session in self.workflow_sessions.items() if session.user_id == user_id]
            
            for session_id in sessions_to_remove:
                del self.workflow_sessions[session_id]
            
            return self._create_success_response({
                "message": "Workflow sessions reset successfully",
                "sessions_removed": len(sessions_to_remove)
            })
            
        except Exception as e:
            self.logger.error(f"Error resetting session: {str(e)}")
            return self._create_error_response(f"Failed to reset session: {str(e)}")
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        phase_counts = {}
        for session in self.workflow_sessions.values():
            phase = session.current_phase.value
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        return {
            "total_sessions": len(self.workflow_sessions),
            "phase_distribution": phase_counts,
            "active_sessions": len([s for s in self.workflow_sessions.values() if s.current_phase != WorkflowPhase.COMPLETED]),
            "completed_sessions": len([s for s in self.workflow_sessions.values() if s.current_phase == WorkflowPhase.COMPLETED]),
            "error_sessions": len([s for s in self.workflow_sessions.values() if s.current_phase == WorkflowPhase.ERROR])
        } 