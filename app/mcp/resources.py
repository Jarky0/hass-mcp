from typing import Dict, List, Any, Optional, Callable, Awaitable, Union
import logging
import json
import asyncio
import inspect
from fastapi import APIRouter, HTTPException, Depends

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
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API-Router für MCP-Endpunkte
router = APIRouter(prefix="/mcp")

# Hilfsfunktion zum Konvertieren von async zu sync für die FastMCP-Integration
def async_to_sync(func: Callable[..., Awaitable[Any]]) -> Callable[..., Any]:
    """Konvertiert eine async-Funktion in eine synchrone Funktion für FastMCP"""
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

# MCP-Ressourcen-Funktionen

@router.get("/version")
async def mcp_get_version(random_string: str = "") -> str:
    """
    Ruft die Home Assistant Version ab
    
    Returns:
        Eine Zeichenkette mit der Home Assistant Version (z.B. "2025.3.0")
    """
    return await get_version(random_string)

@router.get("/entity/{entity_id}")
async def mcp_get_entity(
    entity_id: str,
    fields: Optional[List[str]] = None,
    detailed: bool = False
) -> Dict[str, Any]:
    """
    Ruft den Status einer Home Assistant Entität ab, optional mit Felderfilterung
    
    Args:
        entity_id: Die abzufragende Entitäts-ID (z.B. 'light.living_room')
        fields: Optionale Liste der einzuschließenden Felder (z.B. ['state', 'attr.brightness'])
        detailed: Wenn True, gibt alle Entitätsfelder ohne Filterung zurück
        
    Returns:
        Entitätsinformationen als Dictionary
    """
    return await get_entity(entity_id, fields, detailed)

@router.post("/entity_action")
async def mcp_entity_action(
    entity_id: str,
    action: str,
    params: str = "{}"
) -> Dict[str, Any]:
    """
    Führt eine Aktion auf einer Home Assistant Entität aus (on, off, toggle)
    
    Args:
        entity_id: Die zu steuernde Entitäts-ID (z.B. 'light.living_room')
        action: Die auszuführende Aktion ('on', 'off', 'toggle')
        params: Zusätzliche Parameter für den Service-Aufruf als JSON-String
        
    Returns:
        Die Antwort von Home Assistant
    """
    # Stellen Sie sicher, dass params ein String ist
    if params is None:
        params = "{}"
    elif not isinstance(params, str):
        try:
            import json
            params = json.dumps(params)
        except:
            params = "{}"
    
    return await entity_action(entity_id, action, params)

@router.get("/entities")
async def mcp_list_entities(
    domain: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    fields: Optional[List[str]] = None,
    detailed: bool = False
) -> List[Dict[str, Any]]:
    """
    Ruft eine Liste von Home Assistant Entitäten mit optionaler Filterung ab
    
    Args:
        domain: Optionaler Domain-Filter (z.B. 'light', 'switch', 'sensor')
        search_query: Optionaler Suchbegriff zum Filtern von Entitäten nach Name oder ID
        limit: Maximale Anzahl zurückzugebender Entitäten
        fields: Optionale Liste spezifischer Felder, die für jede Entität eingeschlossen werden sollen
        detailed: Wenn True, gibt alle Entitätsfelder ohne Filterung zurück
        
    Returns:
        Eine Liste von Entitäts-Wörterbüchern
    """
    return await list_entities(domain, search_query, limit, fields, detailed)

@router.get("/search_entities")
async def mcp_search_entities(
    query: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Sucht nach Entitäten, die einer Abfrage entsprechen
    
    Args:
        query: Die Suchabfrage, die mit Entitäts-IDs, Namen und Attributen abgeglichen werden soll
        limit: Maximale Anzahl zurückzugebender Ergebnisse
        
    Returns:
        Ein Wörterbuch mit Suchergebnissen und Metadaten
    """
    return await search_entities_tool(query, limit)

@router.get("/domain_summary/{domain}")
async def mcp_domain_summary(
    domain: str,
    example_limit: int = 3
) -> Dict[str, Any]:
    """
    Liefert eine Zusammenfassung der Entitäten in einer bestimmten Domain
    
    Args:
        domain: Die zu analysierende Domain (z.B. 'light', 'switch', 'sensor')
        example_limit: Maximale Anzahl der Beispiele für jeden Zustand
        
    Returns:
        Ein Wörterbuch mit Statistiken und Beispielen
    """
    return await domain_summary_tool(domain, example_limit)

@router.get("/system_overview")
async def mcp_system_overview(random_string: str = "") -> Dict[str, Any]:
    """
    Liefert einen umfassenden Überblick über das gesamte Home Assistant System
    
    Returns:
        Ein Wörterbuch mit Systeminformationen
    """
    return await system_overview(random_string)

@router.get("/automations")
async def mcp_list_automations(random_string: str = "") -> List[Dict[str, Any]]:
    """
    Ruft eine Liste aller Automatisierungen von Home Assistant ab
    
    Returns:
        Eine Liste von Automatisierungs-Wörterbüchern
    """
    return await list_automations(random_string)

@router.post("/restart_ha")
async def mcp_restart_ha(random_string: str = "") -> Dict[str, Any]:
    """
    Startet Home Assistant neu
    
    ⚠️ WARNUNG: Unterbricht vorübergehend alle Home Assistant Operationen
    
    Returns:
        Ergebnis des Neustarts
    """
    return await restart_ha(random_string)

@router.post("/call_service")
async def mcp_call_service(
    domain: str,
    service: str,
    data: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ruft einen beliebigen Home Assistant Service auf (Low-Level API-Zugriff)
    
    Args:
        domain: Die Domain des Services (z.B. 'light', 'switch', 'automation')
        service: Der aufzurufende Service (z.B. 'turn_on', 'turn_off', 'toggle')
        data: Optionale Daten für den Service als JSON-String
        
    Returns:
        Die Antwort von Home Assistant
    """
    return await call_service_tool(domain, service, data)

@router.get("/history/{entity_id}")
async def mcp_get_history(
    entity_id: str,
    hours: int = 24
) -> Dict[str, Any]:
    """
    Ruft den Verlauf der Zustandsänderungen einer Entität ab
    
    Args:
        entity_id: Die Entitäts-ID, für die der Verlauf abgerufen werden soll
        hours: Anzahl der abzurufenden Verlaufsstunden
        
    Returns:
        Ein Wörterbuch mit Verlaufsdaten und Statistiken
    """
    return await get_history(entity_id, hours)

@router.get("/error_log")
async def mcp_get_error_log(random_string: str = "") -> Dict[str, Any]:
    """
    Ruft das Home Assistant Fehlerprotokoll zur Fehlerbehebung ab
    
    Returns:
        Ein Wörterbuch mit Fehlerprotokollanalyse
    """
    return await get_error_log(random_string)


# MCP-Tool-Registry-Funktion
def register_mcp_tools() -> Dict[str, Callable]:
    """
    Registriert alle MCP-Tools für die FastMCP-Integration
    
    Returns:
        Ein Dictionary mit Tool-Namen und synchronisierten Funktionen
    """
    tools = {
        "Hass_MCP_get_version": async_to_sync(get_version),
        "Hass_MCP_get_entity": async_to_sync(get_entity),
        "Hass_MCP_entity_action": async_to_sync(entity_action),
        "Hass_MCP_list_entities": async_to_sync(list_entities),
        "Hass_MCP_search_entities_tool": async_to_sync(search_entities_tool),
        "Hass_MCP_domain_summary_tool": async_to_sync(domain_summary_tool),
        "Hass_MCP_system_overview": async_to_sync(system_overview),
        "Hass_MCP_list_automations": async_to_sync(list_automations),
        "Hass_MCP_restart_ha": async_to_sync(restart_ha),
        "Hass_MCP_call_service_tool": async_to_sync(call_service_tool),
        "Hass_MCP_get_history": async_to_sync(get_history),
        "Hass_MCP_get_error_log": async_to_sync(get_error_log),
    }
    
    return tools
