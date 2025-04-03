"""
MCP-Paket für Home Assistant MCP Server
"""

# Expose the MCP instance and initialization function
from app.mcp.instance import mcp, initialize_mcp

# Define what is available when importing from app.mcp
__all__ = ['mcp', 'initialize_mcp']
