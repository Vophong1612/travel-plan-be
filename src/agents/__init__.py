"""
AI Travel Planner Agents

This module contains all the agents for the multi-agent travel planning system.
"""

from .base_agent import BaseAgent, AgentMessage, AgentResponse
from .profiler_agent import ProfilerAgent
from .itinerary_agent import ItineraryAgent
from .critique_agent import CritiqueAgent
from .monitor_agent import MonitorAgent
from .orchestrator_agent import OrchestratorAgent

# New workflow agents
from .user_intent_agent import UserIntentAgent, TravelContext
from .location_weather_agent import LocationWeatherAgent
from .poi_activity_agent import POIActivityAgent
from .food_recommendation_agent import FoodRecommendationAgent
from .new_itinerary_agent import NewItineraryAgent
from .budget_estimation_agent import BudgetEstimationAgent
from .output_formatting_agent import OutputFormattingAgent
from .new_orchestrator_agent import NewOrchestratorAgent

from typing import Dict, Any, Optional


class AgentRegistry:
    """Registry for managing all agents in the system."""
    
    def __init__(self, use_new_workflow: bool = True):
        self.agents: Dict[str, BaseAgent] = {}
        self.use_new_workflow = use_new_workflow
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents."""
        if self.use_new_workflow:
            # New 4-phase workflow agents
            self.agents = {
                "orchestrator": NewOrchestratorAgent(),
                "user_intent": UserIntentAgent(),
                "location_weather": LocationWeatherAgent(),
                "poi_activity": POIActivityAgent(),
                "food_recommendation": FoodRecommendationAgent(),
                "itinerary": NewItineraryAgent(),
                "budget_estimation": BudgetEstimationAgent(),
                "output_formatting": OutputFormattingAgent(),
                "critique": CritiqueAgent(),  # Add critique agent for backward compatibility
                "monitor": MonitorAgent()  # Keep monitor for future use
            }
        else:
            # Original workflow agents
            self.agents = {
                "orchestrator": OrchestratorAgent(),
                "profiler": ProfilerAgent(),
                "itinerary": ItineraryAgent(),
                "critique": CritiqueAgent(),
                "monitor": MonitorAgent()
            }
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> Dict[str, str]:
        """List all available agents."""
        return {
            agent_id: agent.description 
            for agent_id, agent in self.agents.items()
        }
    
    async def send_message(self, agent_id: str, message: AgentMessage) -> AgentResponse:
        """Send a message to a specific agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return AgentResponse(
                success=False,
                error=f"Agent '{agent_id}' not found",
                agent_id="registry"
            )
        
        return await agent.process_message(message)
    
    def get_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all agents."""
        return {
            agent_id: agent.get_performance_metrics()
            for agent_id, agent in self.agents.items()
        }
    
    def switch_workflow(self, use_new_workflow: bool):
        """Switch between old and new workflow."""
        if self.use_new_workflow != use_new_workflow:
            self.use_new_workflow = use_new_workflow
            self._initialize_agents()


# Global agent registry instance - using new workflow by default
agent_registry = AgentRegistry(use_new_workflow=True)

__all__ = [
    'BaseAgent',
    'AgentMessage', 
    'AgentResponse',
    # Original agents
    'ProfilerAgent',
    'ItineraryAgent',
    'CritiqueAgent',
    'MonitorAgent',
    'OrchestratorAgent',
    # New workflow agents
    'UserIntentAgent',
    'LocationWeatherAgent',
    'POIActivityAgent',
    'FoodRecommendationAgent',
    'NewItineraryAgent',
    'BudgetEstimationAgent',
    'OutputFormattingAgent',
    'NewOrchestratorAgent',
    'TravelContext',
    # Registry
    'AgentRegistry',
    'agent_registry'
] 