"""
MCP Tools for AI Travel Planner

This module contains all the MCP (Model Context Protocol) tools for external service integrations.
"""

from .base_mcp_tool import BaseMCPTool, MCPToolResponse, MCPToolError, tool_registry
from .google_maps_tool import GoogleMapsTool
from .weather_tool import WeatherTool
from .travel_mcp_tool import TravelMCPTool

# Register all tools
def register_all_tools():
    """Register all available MCP tools."""
    tool_registry.register(GoogleMapsTool())
    tool_registry.register(WeatherTool())
    tool_registry.register(TravelMCPTool())

# Auto-register tools when module is imported
register_all_tools()

__all__ = [
    'BaseMCPTool',
    'MCPToolResponse', 
    'MCPToolError',
    'tool_registry',
    'GoogleMapsTool',
    'WeatherTool',
    'TravelMCPTool',
    'register_all_tools'
] 