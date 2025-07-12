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

from typing import Dict, Any, Optional


class AgentRegistry:
    """Registry for managing all agents in the system."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents."""
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


# Global agent registry instance
agent_registry = AgentRegistry()

__all__ = [
    'BaseAgent',
    'AgentMessage', 
    'AgentResponse',
    'ProfilerAgent',
    'ItineraryAgent',
    'CritiqueAgent',
    'MonitorAgent',
    'OrchestratorAgent',
    'AgentRegistry',
    'agent_registry'
] 