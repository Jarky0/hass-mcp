# -*- coding: utf-8 -*-
import functools
import logging
import json
import httpx # Sicherstellen, dass httpx importiert ist, falls benötigt
from typing import List, Dict, Any, Optional, Callable, Awaitable, TypeVar, cast
import aiohttp
import os

# Logging einrichten
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler() # Loggt auf stderr, was in Claude Desktop Logs erscheint
    ]
)
logger = logging.getLogger(__name__)

# Importiere Home Assistant API-Funktionen
from app.hass import (
    get_hass_version, get_entity_state, call_service, get_entities,
    get_automations, restart_home_assistant,
    cleanup_client, filter_fields, summarize_domain, get_system_overview,
    get_hass_error_log, get_entity_history
)

# Import der neuen Funktionen aus simplified_extensions
from app.simplified_extensions import (
    configure_ha_component, delete_ha_component,
    set_entity_attributes
)

# Type variable for generic functions
T = TypeVar('T')

# Import the MCP instance from app.mcp.instance instead of app.mcp.server
from app.mcp.instance import initialize_mcp
# Stelle sicher, dass die MCP-Instanz initialisiert ist
mcp = initialize_mcp()
# Context direkt aus fastmcp importieren
from fastmcp import Context
from fastmcp.utilities.types import Image

# Asynchrone Handler-Dekorator (aus Ihrer Originaldatei)
def async_handler(command_type: str):
    """
    Simple decorator that logs the command

    Args:
        command_type: The type of command (for logging)
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            logger.info(f"Executing command: {command_type} - {func.__name__}") # Funktionsname zum Logging hinzugefügt
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                # Versuche, einen Fehler im erwarteten Rückgabetyp zurückzugeben
                # Holt die Rückgabe-Annotation der dekorierten Funktion
                return_annotation = func.__annotations__.get('return', None)

                # Prüfe, ob die Annotation ein generischer Alias wie List[Dict[str, Any]] ist
                origin_type = getattr(return_annotation, '__origin__', None)

                if origin_type is list or str(return_annotation) == 'list':
                     # Erwartet eine Liste, gib Fehler in einer Liste zurück
                     return [{"error": f"Internal server error in {func.__name__}: {str(e)}"}]
                elif origin_type is dict or str(return_annotation) == 'dict':
                     # Erwartet ein Dict, gib Fehler in einem Dict zurück
                     return {"error": f"Internal server error in {func.__name__}: {str(e)}"}
                else:
                     # Fallback für andere Typen (z.B. str) oder wenn Annotation fehlt
                     # Vorsicht: Dies könnte zu Typ-Fehlern führen, wenn der Aufrufer einen spezifischen Typ erwartet
                     return f"Error in {func.__name__}: {str(e)}"
        return cast(Callable[..., Awaitable[T]], wrapper)
    return decorator

# --- Standard Query & Control Tools ---
# Bereits mit dem @mcp.tool() Dekorator registriert

# Diese Funktion registriert alle Tool-Funktionen bei MCP, die in dieser Datei definiert sind
def register_all_tools():
    """
    Registriert alle Tools, die in dieser Datei definiert sind, bei der MCP-Instanz
    
    Diese Funktion wird nicht mehr benötigt, da wir jetzt den Dekorator @mcp.tool() 
    direkt bei den Funktionen verwenden.
    """
    logger.info("Tools wurden bereits über Dekoratoren registriert.")
    pass  # Die Registrierung passiert bereits über @mcp.tool() Dekoratoren

# Startet den MCP-Server und registriert alle Tools/Ressourcen
def start_mcp_server():
    """Startet den MCP-Server und registriert alle Tools/Ressourcen"""
    from app.mcp.server import start_server
    
    logger.info("Starte MCP-Server...")
    try:
        # Server mit SSE-Transport starten, damit er über HTTP erreichbar ist
        start_server(transport="sse")
        logger.info("MCP-Server erfolgreich gestartet.")
    except Exception as e:
        logger.error(f"Fehler beim Starten des MCP-Servers: {e}")
        raise

def cleanup():
    """Clean up resources when the server is shutting down"""
    logger.info("Cleaning up resources...")
    cleanup_client()

if __name__ == "__main__":
    # Stelle sicher, dass der Logger auf DEBUG-Level eingestellt ist
    logging.getLogger("app").setLevel(logging.DEBUG)
    
    try:
        # Starte den MCP-Server
        start_mcp_server()
        
        # Keep the main thread running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Server stopping...")
        cleanup()
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        cleanup()
        raise


