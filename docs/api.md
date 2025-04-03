# Hass-MCP API Documentation

This documentation describes the API components used by the Hass-MCP integration.

## Home Assistant API Client

The Home Assistant API Client (`app/api/client.py`) provides an abstracted interface to the Home Assistant REST API.

### Main Functions

- **Status queries** for Home Assistant entities
- **Control commands** for devices and services
- **Historical data** retrieval for entities
- **Configuration management** for Home Assistant

## MCP Tools

The MCP Tools (`app/mcp/tools.py`) provide an interface for Large Language Models (LLMs) and AI assistants to interact with Home Assistant.

### Available Tools

- **Entity Management**: Query and control Home Assistant entities
- **System Management**: Configuration and control of the Home Assistant instance
- **Automation Tools**: Interaction with Home Assistant automations

## Resources

The MCP Resources (`app/mcp/resources.py`) provide structured data for LLMs and AI assistants.

---

*This documentation is continuously expanded and updated.* 