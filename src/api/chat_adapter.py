"""
Chat API Adapter for the new workflow

This adapter interfaces between the existing /chat endpoint and the new 4-phase workflow.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from src.agents import agent_registry, AgentMessage


class ChatAdapter:
    """Adapter to connect the /chat endpoint with the new workflow orchestrator."""
    
    def __init__(self):
        self.registry = agent_registry
    
    async def process_chat_request(self, user_message: str, user_id: str = "1") -> Dict[str, Any]:
        """
        Process a chat request using the new 4-phase workflow.
        
        Args:
            user_message: The user's travel planning query
            user_id: User identifier (defaults to "1")
            
        Returns:
            Dict containing the formatted response for the /chat endpoint
        """
        try:
            # Get the new orchestrator
            orchestrator = self.registry.get_agent("orchestrator")
            
            if not orchestrator:
                return self._create_error_response("Orchestrator agent not available")
            
            # Create message for orchestrator
            message = AgentMessage(
                agent_id="chat_adapter",
                message_type="process_user_query",
                content={
                    "user_id": user_id,
                    "user_query": user_message
                }
            )
            
            # Process through the workflow
            response = await orchestrator.process_message(message)
            
            if response.success:
                # The new orchestrator returns the properly formatted response
                return response.data
            else:
                return self._create_error_response(response.error)
                
        except Exception as e:
            return self._create_error_response(f"Chat processing failed: {str(e)}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create an error response in the expected format."""
        return {
            "success": False,
            "message": f"I apologize, but I encountered an error while planning your trip: {error_message}. Please try again with a different request.",
            "trip_id": None,
            "extracted_info": {
                "destination": None,
                "start_date": None,
                "end_date": None,
                "duration_days": None,
                "food_preferences": [],
                "activities": [],
                "travelers": 1,
                "budget_level": None,
                "accommodation_preferences": [],
                "transportation_preferences": [],
                "other_preferences": []
            },
            "trip_details": None,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_session_status(self, user_id: str) -> Dict[str, Any]:
        """Get the current session status for a user."""
        try:
            orchestrator = self.registry.get_agent("orchestrator")
            
            if not orchestrator:
                return {"error": "Orchestrator not available"}
            
            message = AgentMessage(
                agent_id="chat_adapter",
                message_type="get_session_status",
                content={"user_id": user_id}
            )
            
            response = await orchestrator.process_message(message)
            
            if response.success:
                return response.data
            else:
                return {"error": response.error}
                
        except Exception as e:
            return {"error": f"Failed to get session status: {str(e)}"}
    
    async def reset_session(self, user_id: str) -> Dict[str, Any]:
        """Reset the session for a user."""
        try:
            orchestrator = self.registry.get_agent("orchestrator")
            
            if not orchestrator:
                return {"error": "Orchestrator not available"}
            
            message = AgentMessage(
                agent_id="chat_adapter",
                message_type="reset_session",
                content={"user_id": user_id}
            )
            
            response = await orchestrator.process_message(message)
            
            if response.success:
                return response.data
            else:
                return {"error": response.error}
                
        except Exception as e:
            return {"error": f"Failed to reset session: {str(e)}"}


# Global chat adapter instance
chat_adapter = ChatAdapter() 