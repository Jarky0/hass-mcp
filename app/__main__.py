#!/usr/bin/env python
"""
Einstiegspunkt für die Ausführung der Home Assistant MCP-Anwendung
"""

import logging
from app.server import start_mcp_server, cleanup

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Starting Home Assistant MCP Server")
    
    try:
        # MCP-Server starten
        start_mcp_server()
        
        # Hauptthread am Laufen halten
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server stopping due to keyboard interrupt...")
        cleanup()
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        cleanup()
        raise