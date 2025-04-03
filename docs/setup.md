# Hass-MCP Setup Guide

This guide describes the installation and setup of the Hass-MCP integration for Home Assistant.

## Prerequisites

- Python 3.9 or higher
- Access to a running Home Assistant instance
- Home Assistant Long-Lived Access Token
- Docker (optional, for container-based installation)

## Installation

### Option 1: Local Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jarky0/hass-mcp.git
   cd hass-mcp
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your Home Assistant credentials
   ```

### Option 2: Docker Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jarky0/hass-mcp.git
   cd hass-mcp
   ```

2. Build the Docker container:
   ```bash
   docker build -t hass-mcp .
   ```

3. Run the container:
   ```bash
   docker run -i --rm -e HA_URL=http://your-homeassistant-url:8123 -e HA_TOKEN=your_access_token --network=host hass-mcp:latest
   ```

## Configuration

### Creating a Home Assistant Access Token

1. In Home Assistant, navigate to your user profile (click on your name in the bottom left corner)
2. Scroll down to "Long-Lived Access Tokens"
3. Click "Create Token", enter a name, and copy the generated token

### Environment Variables

The following environment variables must be configured in the .env file or as Docker environment variables:

#### Required Variables
- `HA_URL`: URL of your Home Assistant instance (e.g., `http://homeassistant.local:8123`)
- `HA_TOKEN`: Your Long-Lived Access Token

#### Optional Variables
- `MCP_ENABLED`: Enable/disable the MCP server (Default: `True`)
- `MCP_PORT`: Port for the MCP server (Default: `3000`) 
- `LOG_LEVEL`: Logging level (Default: `INFO`)

## Getting Started

### Starting the MCP Server

After successful installation, you can start the MCP server:

```bash
# For local installation
python -m app

# Or using Docker (as described above)
```

## Assistant Configuration

After your MCP server is running, you can connect it to various AI assistants:

- **Claude**: Configure Claude via Custom Instructions to communicate with your Home Assistant
- **Cursor**: Use the MCP server configuration in `~/.cursor/mcp.json` for Cursor integration

In the [User Guide](usage.md#integration-with-ai-assistants) you'll find:
- Detailed instructions for configuring each assistant
- Concrete examples for the `mcp.json` configuration in Cursor

---

*For more information on usage, see the [User Guide](usage.md).* 