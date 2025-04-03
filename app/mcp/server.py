"""
Home Assistant MCP Server

Stellt einen MCP-Server bereit, der Home Assistant über Claude steuern kann.
"""
import logging
import asyncio
from typing import Dict, Any, Optional

# Importiere die MCP-Instanz aus der instance.py
from app.mcp.instance import mcp, initialize_mcp
# Context direkt aus fastmcp importieren
from fastmcp import Context
# Importiere nur die verfügbaren Tool-Funktionen
from app.mcp.tools import (
    get_version,
    get_entity,
    entity_action,
    list_entities,
    search_entities_tool,
    domain_summary_tool,
    system_overview,
    list_automations,
    restart_ha,
    call_service_tool,
    get_history,
    get_error_log,
    cleanup_api_client  # Diese Funktion wird für die stop-Methode benötigt
)
from app.mcp.prompts import get_all_prompts, get_prompt

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HassMCPServer:
    """Home Assistant MCP Server"""
    
    def __init__(self):
        """Initialisiert den MCP-Server"""
        # Stelle sicher, dass die MCP-Instanz initialisiert ist
        self.mcp = initialize_mcp()
        self._setup_tools()
        self._setup_resources()
        self._setup_prompts()
        self._api_client = None
        logger.info("Hass-MCP-Server initialisiert")
    
    def _setup_tools(self):
        """Registriert alle verfügbaren MCP-Tools"""
        # Basiswerkzeuge - FastMCP Dekorator-Syntax verwenden
        self.mcp.tool(name="get_version")(get_version)
        self.mcp.tool(name="get_entity")(get_entity)
        self.mcp.tool(name="entity_action")(entity_action)
        self.mcp.tool(name="list_entities")(list_entities)
        
        # Erweiterte Abfragewerkzeuge
        self.mcp.tool(name="search_entities_tool")(search_entities_tool)
        self.mcp.tool(name="domain_summary_tool")(domain_summary_tool)
        self.mcp.tool(name="system_overview")(system_overview)
        
        # Administrative Werkzeuge
        self.mcp.tool(name="list_automations")(list_automations)
        self.mcp.tool(name="restart_ha")(restart_ha)
        self.mcp.tool(name="get_error_log")(get_error_log)
        self.mcp.tool(name="get_history")(get_history)
        self.mcp.tool(name="call_service_tool")(call_service_tool)
        
        # Folgende Tools sind noch nicht implementiert
        # self.mcp.tool(name="configure_component_tool")(configure_component_tool)
        # self.mcp.tool(name="delete_component_tool")(delete_component_tool)
        # self.mcp.tool(name="set_attributes_tool")(set_attributes_tool)
        # self.mcp.tool(name="api_root")(api_root)
        # self.mcp.tool(name="get_config")(get_config)
        # self.mcp.tool(name="get_events")(get_events)
        # self.mcp.tool(name="get_services")(get_services)
        # self.mcp.tool(name="get_history_period")(get_history_period)
        # self.mcp.tool(name="get_logbook")(get_logbook)
        # self.mcp.tool(name="get_states")(get_states)
        # self.mcp.tool(name="set_state")(set_state)
        # self.mcp.tool(name="fire_event")(fire_event)
        # self.mcp.tool(name="render_template")(render_template)
        # self.mcp.tool(name="check_config")(check_config)
        # self.mcp.tool(name="handle_intent")(handle_intent)
        # self.mcp.tool(name="reload_ha")(reload_ha)
        # self.mcp.tool(name="light_control")(light_control)
        
        logger.info("MCP-Tools registriert")
    
    def _setup_resources(self):
        """Registriert alle MCP-Ressourcen"""
        # Die Ressourcen werden in der app/server.py bereits definiert
        # In Zukunft könnten wir spezifische Ressourcen hier hinzufügen
        pass
    
    def _setup_prompts(self):
        """Registriert alle MCP-Prompts (Gesprächsvorlagen)"""
        prompts = get_all_prompts()
        
        # Registriere jede Prompt-Vorlage mit FastMCP Syntax
        for name, prompt_data in prompts.items():
            @self.mcp.prompt(name=name)
            async def prompt_handler(context: Context) -> Dict[str, str]:
                return {
                    "system": prompt_data["system"],
                    "prompt": prompt_data["prompt"]
                }
            
            # Setze die Beschreibung der Prompt
            prompt_handler.__doc__ = prompt_data["description"]
            
            logger.info(f"Prompt '{name}' registriert: {prompt_data['description']}")
    
    def start(self, host: str = "localhost", port: int = 8000, transport: str = "stdio"):
        """Startet den MCP-Server (synchron)"""
        logger.info(f"Starte Hass-MCP Server auf {host}:{port} mit Transport {transport}")
        try:
            # FastMCP.run() ist synchron und blockiert, bis der Server beendet wird
            self.mcp.run(transport=transport)
            logger.info("Hass-MCP Server gestartet")
        except Exception as e:
            logger.error(f"Fehler beim Starten des Servers: {e}")
            raise
    
    async def start_async(self, host: str = "localhost", port: int = 8000, transport: str = "stdio"):
        """Startet den MCP-Server in einem separaten Thread (asynchron)"""
        # Diese Methode kann verwendet werden, um den Server asynchron zu starten
        import threading
        
        logger.info(f"Starte Hass-MCP Server asynchron auf {host}:{port} mit Transport {transport}")
        
        def _run_server():
            try:
                self.mcp.run(transport=transport)
            except Exception as e:
                logger.error(f"Fehler im Server-Thread: {e}")
                
        # Starte den Server in einem separaten Thread
        server_thread = threading.Thread(target=_run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Kurz warten, um sicherzustellen, dass der Server gestartet wird
        await asyncio.sleep(0.5)
        logger.info("Hass-MCP Server asynchron gestartet")
    
    async def stop(self):
        """Bereinigt Ressourcen nach Serverbeendigung
        
        Hinweis: FastMCP hat keine explizite stop()-Methode. Der Server wird beendet,
        wenn der Prozess beendet wird oder die run()-Methode zurückkehrt.
        Diese Methode führt nur Client-Bereinigungen durch.
        """
        logger.info("Bereinige API-Client-Ressourcen...")
        try:
            # Bereinigt API-Client-Ressourcen
            await cleanup_api_client()
            logger.info("API-Client-Ressourcen bereinigt")
        except Exception as e:
            logger.error(f"Fehler bei der Bereinigung: {e}")
            raise

# Server-Instanz erstellen
server = HassMCPServer()

def start_server(host: str = "localhost", port: int = 8000, transport: str = "stdio"):
    """Hilfsfunktion zum synchronen Starten des Servers"""
    server.start(host, port, transport)

async def start_server_async(host: str = "localhost", port: int = 8000, transport: str = "stdio"):
    """Hilfsfunktion zum asynchronen Starten des Servers"""
    await server.start_async(host, port, transport)

async def stop_server():
    """Hilfsfunktion zum Bereinigen der Ressourcen"""
    await server.stop()

# Hauptfunktion zum Ausführen des Servers
def main():
    """Hauptfunktion zum Starten des Servers"""
    try:
        start_server()
    except KeyboardInterrupt:
        logger.info("Server-Unterbrechung erkannt")
    finally:
        # Da FastMCP.run() blockiert, erreichen wir diesen Code erst nach Beendigung
        asyncio.run(stop_server())

if __name__ == "__main__":
    main()
