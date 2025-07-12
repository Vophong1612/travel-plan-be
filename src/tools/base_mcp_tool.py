import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel
import httpx
import asyncio
from datetime import datetime


class MCPToolError(Exception):
    """Custom exception for MCP tool errors."""
    pass


class MCPToolResponse(BaseModel):
    """Standard response format for MCP tools."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.utcnow()
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseMCPTool(ABC):
    """Base class for all MCP tools."""
    
    def __init__(self, name: str, description: str, **kwargs):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"mcp_tool.{name}")
        self.config = kwargs
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @abstractmethod
    async def execute(self, **kwargs) -> MCPToolResponse:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's parameter schema."""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate parameters against the tool's schema."""
        # Basic validation - can be extended by subclasses
        return True
    
    async def _make_request(self, 
                          method: str, 
                          url: str, 
                          headers: Optional[Dict[str, str]] = None,
                          params: Optional[Dict[str, Any]] = None,
                          json: Optional[Dict[str, Any]] = None,
                          **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling."""
        try:
            self.logger.debug(f"Making {method} request to {url}")
            
            response = await self.client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                **kwargs
            )
            
            response.raise_for_status()
            
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            else:
                return {"content": response.text}
                
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise MCPToolError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            self.logger.error(f"Request error: {str(e)}")
            raise MCPToolError(f"Request failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise MCPToolError(f"Unexpected error: {str(e)}")
    
    def _handle_success(self, data: Dict[str, Any]) -> MCPToolResponse:
        """Create successful response."""
        return MCPToolResponse(success=True, data=data)
    
    def _handle_error(self, error: str) -> MCPToolResponse:
        """Create error response."""
        self.logger.error(f"Tool {self.name} error: {error}")
        return MCPToolResponse(success=False, error=error)


class MCPToolRegistry:
    """Registry for managing MCP tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseMCPTool] = {}
        self.logger = logging.getLogger("mcp_tool_registry")
    
    def register(self, tool: BaseMCPTool):
        """Register a new tool."""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered MCP tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseMCPTool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self.tools.keys())
    
    def get_all_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get schemas for all tools."""
        return {name: tool.get_schema() for name, tool in self.tools.items()}
    
    async def execute_tool(self, name: str, **kwargs) -> MCPToolResponse:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return MCPToolResponse(success=False, error=f"Tool '{name}' not found")
        
        try:
            if not tool.validate_parameters(kwargs):
                return MCPToolResponse(success=False, error="Invalid parameters")
            
            return await tool.execute(**kwargs)
        except Exception as e:
            return MCPToolResponse(success=False, error=str(e))


# Global tool registry instance
tool_registry = MCPToolRegistry() 