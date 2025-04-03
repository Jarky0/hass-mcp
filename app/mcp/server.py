"""
Home Assistant MCP Server

Stellt einen MCP-Server bereit, der Home Assistant über Claude steuern kann.
"""
import logging
import asyncio
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP, Context
from app.mcp.tools import (
    get_version, get_entity, entity_action, list_entities,
    search_entities_tool, domain_summary_tool, system_overview,
    list_automations, restart_ha, get_error_log, get_history
)
from app.mcp.prompts import get_all_prompts, get_prompt

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HassMCPServer:
    """Home Assistant MCP Server"""
    
    def __init__(self):
        """Initialisiert den MCP-Server"""
        self.mcp = FastMCP(
            "Hass-MCP", 
            version="0.1.0", 
            capabilities={
                "resources": {},
                "tools": {},
                "prompts": {}
            }
        )
        self._setup_tools()
        self._setup_resources()
        self._setup_prompts()
        self._api_client = None
        logger.info("Hass-MCP-Server initialisiert")
    
    def _setup_tools(self):
        """Registriert alle verfügbaren MCP-Tools"""
        # Basiswerkzeuge
        self.mcp.register_tool("get_version", get_version)
        self.mcp.register_tool("get_entity", get_entity)
        self.mcp.register_tool("entity_action", entity_action)
        self.mcp.register_tool("list_entities", list_entities)
        
        # Erweiterte Abfragewerkzeuge
        self.mcp.register_tool("search_entities_tool", search_entities_tool)
        self.mcp.register_tool("domain_summary_tool", domain_summary_tool)
        self.mcp.register_tool("system_overview", system_overview)
        
        # Administrative Werkzeuge
        self.mcp.register_tool("list_automations", list_automations)
        self.mcp.register_tool("restart_ha", restart_ha)
        self.mcp.register_tool("get_error_log", get_error_log)
        self.mcp.register_tool("get_history", get_history)
        
        logger.info("MCP-Tools registriert")
    
    def _setup_resources(self):
        """Registriert alle MCP-Ressourcen"""
        # Die Ressourcen werden in der app/server.py bereits definiert
        # In Zukunft könnten wir spezifische Ressourcen hier hinzufügen
        pass
    
    def _setup_prompts(self):
        """Registriert alle MCP-Prompts (Gesprächsvorlagen)"""
        prompts = get_all_prompts()
        
        # Registriere jede Prompt-Vorlage
        for name, prompt_data in prompts.items():
            @self.mcp.prompt()
            def prompt_handler(context: Context) -> Dict[str, str]:
                return {
                    "system": prompt_data["system"],
                    "prompt": prompt_data["prompt"]
                }
            
            # Setze den Namen und die Beschreibung der Prompt
            prompt_handler.__name__ = name
            prompt_handler.__doc__ = prompt_data["description"]
            
            logger.info(f"Prompt '{name}' registriert: {prompt_data['description']}")
    
    async def start(self, host: str = "localhost", port: int = 8000):
        """Startet den MCP-Server"""
        logger.info(f"Starte Hass-MCP Server auf {host}:{port}")
        try:
            await self.mcp.start(host=host, port=port)
            logger.info("Hass-MCP Server gestartet")
        except Exception as e:
            logger.error(f"Fehler beim Starten des Servers: {e}")
            raise
    
    async def stop(self):
        """Stoppt den MCP-Server"""
        logger.info("Stoppe Hass-MCP Server...")
        try:
            await self.mcp.stop()
            # Bereinigt API-Client-Ressourcen
            from app.mcp.tools import cleanup_api_client
            await cleanup_api_client()
            logger.info("Hass-MCP Server gestoppt")
        except Exception as e:
            logger.error(f"Fehler beim Stoppen des Servers: {e}")
            raise

# Server-Instanz erstellen
server = HassMCPServer()

async def start_server(host: str = "localhost", port: int = 8000):
    """Hilfsfunktion zum Starten des Servers"""
    await server.start(host, port)

async def stop_server():
    """Hilfsfunktion zum Stoppen des Servers"""
    await server.stop()

# Hauptfunktion zum Ausführen des Servers
async def main():
    """Hauptfunktion zum Starten des Servers"""
    try:
        await start_server()
        # Halte den Server am Laufen
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server-Unterbrechung erkannt")
    finally:
        await stop_server()

if __name__ == "__main__":
    asyncio.run(main())
