import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel

from src.tools import tool_registry, MCPToolResponse
from src.config.settings import settings
from src.utils import gemini_client


class AgentMessage(BaseModel):
    """Standard message format for inter-agent communication."""
    agent_id: str
    message_type: str
    content: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()
    correlation_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentResponse(BaseModel):
    """Standard response format for agent operations."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    agent_id: str
    timestamp: datetime = datetime.utcnow()
    execution_time_ms: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, 
                 agent_id: str, 
                 name: str, 
                 description: str, 
                 tools: Optional[List[str]] = None,
                 **kwargs):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.available_tools = tools or []
        self.config = kwargs
        
        # Set up logging
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Tool access
        self.tools = tool_registry
        
        # Agent state
        self.state = {}
        self.memory = {}
        self.conversation_history = []
        
        # Performance tracking
        self.execution_count = 0
        self.total_execution_time = 0
        self.error_count = 0
        
        self.logger.info(f"Initialized agent {self.agent_id} ({self.name})")
    
    @abstractmethod
    async def execute(self, message: AgentMessage) -> AgentResponse:
        """Execute the agent's main functionality."""
        pass
    
    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the agent's prompt template."""
        pass
    
    async def process_message(self, message: AgentMessage) -> AgentResponse:
        """Process an incoming message with error handling and performance tracking."""
        start_time = datetime.utcnow()
        
        try:
            self.logger.debug(f"Processing message type: {message.message_type}")
            
            # Add to conversation history
            self.conversation_history.append(message)
            
            # Execute the agent's main logic
            response = await self.execute(message)
            
            # Update performance metrics
            end_time = datetime.utcnow()
            execution_time = int((end_time - start_time).total_seconds() * 1000)
            
            response.execution_time_ms = execution_time
            self.execution_count += 1
            self.total_execution_time += execution_time
            
            # Add to conversation history
            self.conversation_history.append(AgentMessage(
                agent_id=self.agent_id,
                message_type="response",
                content=response.dict(),
                correlation_id=message.correlation_id
            ))
            
            self.logger.debug(f"Processed message in {execution_time}ms")
            return response
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error processing message: {str(e)}")
            
            return AgentResponse(
                success=False,
                error=str(e),
                agent_id=self.agent_id,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
    
    async def use_tool(self, tool_name: str, **kwargs) -> MCPToolResponse:
        """Use an MCP tool with validation."""
        if tool_name not in self.available_tools:
            raise ValueError(f"Tool '{tool_name}' not available to agent {self.agent_id}")
        
        self.logger.debug(f"Using tool: {tool_name}")
        
        try:
            response = await self.tools.execute_tool(tool_name, **kwargs)
            self.logger.debug(f"Tool {tool_name} response: {response.success}")
            return response
        except Exception as e:
            self.logger.error(f"Tool {tool_name} failed: {str(e)}")
            raise
    
    def update_state(self, key: str, value: Any):
        """Update agent state."""
        self.state[key] = value
        self.logger.debug(f"Updated state: {key}")
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get value from agent state."""
        return self.state.get(key, default)
    
    def set_memory(self, key: str, value: Any, scope: str = "session"):
        """Set memory with scope (session, user, app)."""
        if scope not in self.memory:
            self.memory[scope] = {}
        
        self.memory[scope][key] = value
        self.logger.debug(f"Set memory [{scope}]: {key}")
    
    def get_memory(self, key: str, scope: str = "session", default: Any = None) -> Any:
        """Get memory value with scope."""
        if scope not in self.memory:
            return default
        
        return self.memory[scope].get(key, default)
    
    def clear_memory(self, scope: Optional[str] = None):
        """Clear memory for a specific scope or all scopes."""
        if scope:
            if scope in self.memory:
                del self.memory[scope]
                self.logger.debug(f"Cleared memory scope: {scope}")
        else:
            self.memory.clear()
            self.logger.debug("Cleared all memory")
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[AgentMessage]:
        """Get conversation history with optional limit."""
        if limit:
            return self.conversation_history[-limit:]
        return self.conversation_history
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.logger.debug("Cleared conversation history")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics."""
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 else 0
        )
        
        return {
            "agent_id": self.agent_id,
            "execution_count": self.execution_count,
            "total_execution_time_ms": self.total_execution_time,
            "average_execution_time_ms": avg_execution_time,
            "error_count": self.error_count,
            "error_rate": self.error_count / self.execution_count if self.execution_count > 0 else 0,
            "memory_usage": len(self.memory),
            "conversation_history_length": len(self.conversation_history)
        }
    
    # AI Generation Methods
    
    async def generate_ai_response(self, 
                                  prompt: str, 
                                  context: Optional[Dict[str, Any]] = None) -> str:
        """Generate an AI response using the agent's prompt template."""
        try:
            system_prompt = self.get_prompt_template()
            
            # Add agent context
            agent_context = {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "available_tools": self.available_tools,
                "current_state": self.state,
                **(context or {})
            }
            
            response = await gemini_client.generate_response(
                prompt=prompt,
                system_prompt=system_prompt,
                context=agent_context
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating AI response: {str(e)}")
            raise
    
    async def generate_ai_json_response(self, 
                                      prompt: str, 
                                      context: Optional[Dict[str, Any]] = None,
                                      schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a structured JSON response using AI."""
        try:
            system_prompt = self.get_prompt_template()
            
            # Add agent context
            agent_context = {
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "available_tools": self.available_tools,
                "current_state": self.state,
                **(context or {})
            }
            
            response = await gemini_client.generate_json_response(
                prompt=prompt,
                system_prompt=system_prompt,
                context=agent_context,
                schema=schema
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating AI JSON response: {str(e)}")
            raise
    
    async def chat_with_ai(self, 
                          messages: List[Dict[str, str]]) -> str:
        """Have a multi-turn conversation with AI."""
        try:
            system_prompt = self.get_prompt_template()
            
            response = await gemini_client.chat_completion(
                messages=messages,
                system_prompt=system_prompt
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error in AI chat: {str(e)}")
            raise
    
    def _create_success_response(self, data: Dict[str, Any]) -> AgentResponse:
        """Create a successful response."""
        return AgentResponse(
            success=True,
            data=data,
            agent_id=self.agent_id
        )
    
    def _create_error_response(self, error: str) -> AgentResponse:
        """Create an error response."""
        return AgentResponse(
            success=False,
            error=error,
            agent_id=self.agent_id
        )
    
    def __str__(self) -> str:
        return f"Agent({self.agent_id}: {self.name})"
    
    def __repr__(self) -> str:
        return f"<Agent {self.agent_id} ({self.name})>" 