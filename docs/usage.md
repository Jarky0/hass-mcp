# Hass-MCP User Guide

This guide describes how to use the Hass-MCP integration with large language models (LLMs) and AI assistants to control your Home Assistant environment.

## Overview

The Hass-MCP integration allows language models and AI assistants to interact with your Home Assistant instance. You can use natural language to:

- Query the status of devices
- Control devices (turn on/off, adjust brightness, etc.)
- Analyze historical data
- Execute and manage automations

## Getting Started

After completing the [installation](setup.md):

1. Make sure your MCP server is running
2. In your preferred AI assistant or LLM chat (e.g., Claude, GPT, Gemini, or others), reference the MCP integration

## Integration with AI Assistants

### Claude

Claude can communicate with the Hass-MCP server through the FastMCP integration. Here's an example configuration:

1. Ensure your Hass-MCP server is running and accessible
2. In your chat with Claude, inform the assistant that it can access the MCP server

#### MCP Server Configuration for Claude

To connect Claude with the Hass-MCP server, you can use the following JSON configuration in your Custom Instructions:

```json
{
  "mcpServers": {
    "hass-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "HA_URL",
        "-e",
        "HA_TOKEN",
        "--network",
        "host",
        "hass-mcp"
      ],
      "env": {
        "HA_URL": "https://your-homeassistant-instance.example.com",
        "HA_TOKEN": "your_long_lived_access_token"
      }
    }
  }
}
```

**Configuration explanation:**
- `mcpServers`: Contains all configured MCP servers
- `hass-mcp`: Name of the MCP server
- `command`: The main command (here "docker" for Docker-based installation)
- `args`: The arguments for the Docker command
- `env`: The environment variables with the access data for Home Assistant
  - `HA_URL`: URL of your Home Assistant instance
  - `HA_TOKEN`: Your Long-Lived Access Token for Home Assistant

You can add this JSON configuration to your Custom Instructions for Claude so it knows how to access your Home Assistant server.

Alternatively, you can directly tell Claude in the chat to use the MCP tools:

```
Please use the MCP tools for Home Assistant to complete the following task: 
[Insert your request here]
```

### Cursor

Cursor can interact with the Hass-MCP server to control smart home devices while you're programming. Here's an example configuration:

1. Ensure your Hass-MCP server is running and accessible
2. Configure Cursor with the appropriate rules

#### MCP Server Configuration for Cursor

To connect Cursor with the Hass-MCP server, you need to create or edit the `mcp.json` configuration file under `~/.cursor/mcp.json`. Here's an example:

```json
{
  "mcpServers": {
    "hass-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "HA_URL",
        "-e",
        "HA_TOKEN",
        "--network",
        "host",
        "hass-mcp"
      ],
      "env": {
        "HA_URL": "https://your-homeassistant-instance.example.com",
        "HA_TOKEN": "your_long_lived_access_token"
      }
    }
  }
}
```

**Configuration explanation:**
- `mcpServers`: Contains all configured MCP servers
- `hass-mcp`: Name of the MCP server (can be freely chosen)
- `command`: The main command (here "docker" for Docker-based installation)
- `args`: The arguments for the Docker command
  - Docker parameters (`run`, `-i`, `--rm`)
  - Environment variable flags (`-e HA_URL`, `-e HA_TOKEN`)
  - Network settings (`--network host`)
  - Docker image (`hass-mcp`)
- `env`: Object with the actual environment variables
  - `HA_URL`: URL of your Home Assistant instance
  - `HA_TOKEN`: Your Long-Lived Access Token for Home Assistant

#### Workflow in Cursor

1. While programming, you can send a command to your AI assistant at any time
2. Example: "Please turn on the office light while I'm working on this code"
3. The assistant uses the MCP tools to communicate with Home Assistant and execute the action

## Example Queries for AI Assistants

Here are some general example queries you can ask any LLM or AI assistant that is connected to the Hass-MCP integration:

### Status Queries

- "Which lights are currently turned on?"
- "Is the front door locked?"
- "What's the current temperature in the kitchen?"
- "Show me all sensors with their current values"
- "Are any windows open?"

### Device Control

- "Turn on the living room light"
- "Set the ceiling lamp brightness to 50%"
- "Turn off the heater in the bedroom"
- "Set the living room thermostat to 22 degrees"
- "Close all blinds upstairs"

### Scenes and Automations

- "Activate the 'Movie Night' scene"
- "Run the 'Turn Everything Off' automation"
- "Show me all available scenes"
- "Which automations are active?"
- "When was the 'Dawn' automation last triggered?"

### Information and Analysis

- "How has the living room temperature changed over the last 24 hours?"
- "Which devices are currently consuming the most electricity?"
- "Are there any unusual activities in my smart home?"
- "Create an overview of all devices by room"
- "Show me the humidity trend in the bathroom"

## Usage Tips

- Be as specific as possible when naming devices
- Ask for a system overview to get an overview of all available devices
- For complex queries, you can ask the AI model to break down the request into multiple steps
- If you're uncertain about the exact name of a device, you can ask the AI model to search for similar devices

## Troubleshooting

If your AI assistant can't access your Home Assistant devices:

1. Make sure the MCP server is running
2. Check if your Home Assistant token is valid
3. Check the network connection between the MCP server and Home Assistant
4. Check the server logs for error messages (`LOG_LEVEL=DEBUG` for more detailed logs)

---

*This documentation is continuously expanded and updated.* 