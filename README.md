# Hass-MCP

A Model Context Protocol (MCP) server for Home Assistant integration with Claude and other LLMs.

## Overview

Hass-MCP enables AI assistants like Claude to interact directly with your Home Assistant instance, allowing them to:

- Query the state of devices and sensors
- Control lights, switches, and other entities
- Get summaries of your smart home
- Troubleshoot automations and entities
- Search for specific entities
- Create guided conversations for common tasks
- Modify Home Assistant configurations directly (automations, scripts, scenes, dashboards)

## Screenshots

<img width="700" alt="Screenshot 2025-03-16 at 15 48 01" src="https://github.com/user-attachments/assets/5f9773b4-6aef-4139-a978-8ec2cc8c0aea" />
<img width="400" alt="Screenshot 2025-03-16 at 15 50 59" src="https://github.com/user-attachments/assets/17e1854a-9399-4e6d-92cf-cf223a93466e" />
<img width="400" alt="Screenshot 2025-03-16 at 15 49 26" src="https://github.com/user-attachments/assets/4565f3cd-7e75-4472-985c-7841e1ad6ba8" />

## Features

- **Entity Management**: Get states, control devices, and search for entities
- **Domain Summaries**: Get high-level information about entity types
- **Automation Support**: List and control automations
- **Guided Conversations**: Use prompts for common tasks like creating automations
- **Smart Search**: Find entities by name, type, or state
- **Token Efficiency**: Lean JSON responses to minimize token usage
- **Direct Configuration**: Create and modify automations, scripts, scenes, and dashboards

## Installation

### Prerequisites

- Home Assistant instance with Long-Lived Access Token
- One of the following:
  - Docker (recommended)
  - Python 3.13+ and [uv](https://github.com/astral-sh/uv)

## Setting Up With Claude Desktop

### Docker Installation (Recommended)

1. Build the Docker image:

   ```bash
   # Clone the repository
   git clone https://github.com/Jarky0/hass-mcp.git
   cd hass-mcp

   # Build the Docker image
   docker build -t hass-mcp:latest .
   
   # Optional: Tag with your own namespace
   # docker tag hass-mcp:latest your-username/hass-mcp:latest
   
   # Optional: Push to your Docker registry
   # docker push your-username/hass-mcp:latest
   ```

2. Add the MCP server to Claude Desktop:

   a. Open Claude Desktop and go to Settings
   b. Navigate to Developer > Edit Config
   c. Add the following configuration to your `claude_desktop_config.json` file:

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
           "hass-mcp"
         ],
         "env": {
           "HA_URL": "http://homeassistant.local:8123",
           "HA_TOKEN": "YOUR_LONG_LIVED_TOKEN"
         }
       }
     }
   }
   ```

   d. Replace `YOUR_LONG_LIVED_TOKEN` with your actual Home Assistant long-lived access token
   e. Update the `HA_URL`:

   - If running Home Assistant on the same machine: use `http://host.docker.internal:8123` (Docker Desktop on Mac/Windows)
   - If running Home Assistant on another machine: use the actual IP or hostname

   f. Save the file and restart Claude Desktop

3. The "Hass-MCP" tool should now appear in your Claude Desktop tools menu

> **Note**: If you're running Home Assistant in Docker on the same machine, you may need to add `--network host` to the Docker args for the container to access Home Assistant. Alternatively, use the IP address of your machine instead of `host.docker.internal`.

## Other MCP Clients

### Cursor

1. Go to Cursor Settings > MCP > Add New MCP Server
2. Fill in the form:
   - Name: `Hass-MCP`
   - Type: `command`
   - Command:
     ```
     docker run -i --rm -e HA_URL=http://homeassistant.local:8123 -e HA_TOKEN=YOUR_LONG_LIVED_TOKEN hass-mcp
     ```
   - Replace `YOUR_LONG_LIVED_TOKEN` with your actual Home Assistant token
   - Update the HA_URL to match your Home Assistant instance address
3. Click "Add" to save

### Claude Code (CLI)

To use with Claude Code CLI, you can add the MCP server directly using the `mcp add` command:

**Using Docker (recommended):**

```bash
claude mcp add hass-mcp -e HA_URL=http://homeassistant.local:8123 -e HA_TOKEN=YOUR_LONG_LIVED_TOKEN -- docker run -i --rm -e HA_URL -e HA_TOKEN hass-mcp
```

Replace `YOUR_LONG_LIVED_TOKEN` with your actual Home Assistant token and update the HA_URL to match your Home Assistant instance address.

## Usage Examples

Here are some examples of prompts you can use with Claude once Hass-MCP is set up:

- "What's the current state of my living room lights?"
- "Turn off all the lights in the kitchen"
- "List all my sensors that contain temperature data"
- "Give me a summary of my climate entities"
- "Create an automation that turns on the lights at sunset"
- "Help me troubleshoot why my bedroom motion sensor automation isn't working"
- "Search for entities related to my living room"
- "Create a dashboard to monitor my home"

## Available Tools

Hass-MCP provides several tools for interacting with Home Assistant:

### Standard Query & Control Tools

- `get_version`: Get the Home Assistant version
- `get_entity`: Get the state of a specific entity with optional field filtering
- `entity_action`: Perform actions on entities (turn on, off, toggle)
- `list_entities`: Get a list of entities with optional domain filtering and search
- `search_entities_tool`: Search for entities matching a query
- `domain_summary_tool`: Get a summary of a domain's entities
- `list_automations`: Get a list of all automations
- `call_service_tool`: Call any Home Assistant service
- `restart_ha`: Restart Home Assistant
- `reload_ha`: Reload specific Home Assistant components without a full restart
- `get_history`: Get the state history of an entity
- `get_error_log`: Get the Home Assistant error log

### REST API Tools

- `api_root`: Get information about the API (API root endpoint)
- `get_config`: Get Home Assistant configuration information
- `get_events`: Get available events in Home Assistant
- `get_services`: Get available services in Home Assistant
- `get_history_period`: Get history for entities during a specific period
- `get_logbook`: Get logbook entries
- `get_states`: Get all entity states
- `set_state`: Set the state of an entity
- `fire_event`: Fire an event
- `render_template`: Render a template
- `check_config`: Check Home Assistant configuration
- `handle_intent`: Handle an intent request

### Configuration Tools

- `configure_component`: Universal function for creating or updating any Home Assistant component (automations, scripts, scenes)
- `delete_component`: Delete any Home Assistant component
- `set_attributes`: Flexible entity control with automatic service detection

## Prompts for Guided Conversations

Hass-MCP includes several prompts for guided conversations:

- `create_automation_prompt`: Guide for creating Home Assistant automations
- `debug_automation`: Troubleshooting help for automations that aren't working
- `troubleshoot_entity`: Diagnose issues with entities
- `routine_optimizer`: Analyze usage patterns and suggest optimized routines based on actual behavior
- `automation_health_check`: Review all automations, find conflicts, redundancies, or improvement opportunities
- `entity_naming_consistency`: Audit entity names and suggest standardization improvements

## Configuration Examples

Here are examples of how to use the configuration tools:

```python
# Create an automation
configure_component(
    component_type="automation",
    object_id="lights_at_sunset",
    config_data={
        "alias": "Turn on lights at sunset",
        "description": "Automatically turn on living room lights at sunset",
        "trigger": [
            {"platform": "sun", "event": "sunset", "offset": "+00:30:00"}
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.living_room"}
            }
        ],
        "mode": "single"
    }
)

# Set attributes for a light
set_attributes(
    entity_id="light.living_room",
    attributes={"brightness": 255, "rgb_color": [255, 0, 0], "transition": 2}
)
```

## Available Resources

Hass-MCP provides the following resource endpoints:

- `hass://entities/{entity_id}`: Get the state of a specific entity
- `hass://entities/{entity_id}/detailed`: Get detailed information about an entity with all attributes
- `hass://entities`: List all Home Assistant entities grouped by domain
- `hass://entities/domain/{domain}`: Get a list of entities for a specific domain
- `hass://search/{query}/{limit}`: Search for entities matching a query with custom result limit

## Development

### Running Tests

```bash
uv run pytest tests/
```

## License

[MIT License](LICENSE)