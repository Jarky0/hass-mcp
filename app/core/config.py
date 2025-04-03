import os
from typing import Optional, Dict

# Home Assistant configuration
HA_URL: str = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN: str = os.environ.get("HA_TOKEN", "")

# Log Level
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# FastAPI Settings
API_HOST: str = os.environ.get("API_HOST", "0.0.0.0")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))
API_DEBUG: bool = os.environ.get("API_DEBUG", "False").lower() == "true"

# MCP Settings
MCP_ENABLED: bool = os.environ.get("MCP_ENABLED", "True").lower() == "true"
MCP_PORT: int = int(os.environ.get("MCP_PORT", "8080"))

def get_ha_headers() -> Dict[str, str]:
    """Return the headers needed for Home Assistant API requests"""
    headers = {
        "Content-Type": "application/json",
    }
    
    # Only add Authorization header if token is provided
    if HA_TOKEN:
        headers["Authorization"] = f"Bearer {HA_TOKEN}"
    
    return headers 