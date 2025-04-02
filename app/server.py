# -*- coding: utf-8 -*-
import functools
import logging
import json
import httpx # Sicherstellen, dass httpx importiert ist, falls benötigt
from typing import List, Dict, Any, Optional, Callable, Awaitable, TypeVar, cast

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
    set_entity_attributes, manage_dashboard,
    list_all_dashboards # NEUEN Import hinzufügen
)


# Type variable for generic functions
T = TypeVar('T')

# Create an MCP server using FastMCP
from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.stdio import stdio_server
import mcp.types as types

# MCP Server Instanz erstellen
# Der Name sollte mit dem in der Claude Desktop Konfiguration übereinstimmen
mcp = FastMCP("Hass-MCP", version="0.4.0", capabilities={ # Version erhöht
    "resources": {},
    "tools": {},
    "prompts": {}
})

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
# (get_version, get_entity, entity_action, list_entities, search_entities_tool,
#  domain_summary_tool, system_overview, list_automations, restart_ha, call_service,
#  get_history, get_error_log bleiben unverändert)
# ... (Code der bestehenden Tools hier einfügen) ...

@mcp.tool()
@async_handler("get_version")
async def get_version() -> str:
    """
    Get the Home Assistant version

    Returns:
        A string with the Home Assistant version (e.g., "2025.3.0")
    """
    logger.info("Getting Home Assistant version")
    return await get_hass_version()

@mcp.tool()
@async_handler("get_entity")
async def get_entity(entity_id: str, fields: Optional[List[str]] = None, detailed: bool = False) -> dict:
    """
    Get the state of a Home Assistant entity with optional field filtering

    Args:
        entity_id: The entity ID to get (e.g. 'light.living_room')
        fields: Optional list of fields to include (e.g. ['state', 'attr.brightness'])
        detailed: If True, returns all entity fields without filtering

    Examples:
        entity_id="light.living_room" - basic state check
        entity_id="light.living_room", fields=["state", "attr.brightness"] - specific fields
        entity_id="light.living_room", detailed=True - all details
    """
    logger.info(f"Getting entity state: {entity_id}, Detailed: {detailed}, Fields: {fields}")
    # lean=True ist der Standard, es sei denn, 'detailed' ist True oder 'fields' werden angegeben.
    lean_mode = not detailed and not fields
    return await get_entity_state(entity_id, fields=fields, lean=lean_mode) # use_cache entfernt

@mcp.tool()
@async_handler("entity_action")
async def entity_action(entity_id: str, action: str, **params) -> dict:
    """
    Perform an action on a Home Assistant entity (on, off, toggle)

    Args:
        entity_id: The entity ID to control (e.g. 'light.living_room')
        action: The action to perform ('on', 'off', 'toggle')
        **params: Additional parameters for the service call

    Returns:
        The response from Home Assistant

    Examples:
        entity_id="light.living_room", action="on", brightness=255
        entity_id="switch.garden_lights", action="off"
        entity_id="climate.living_room", action="on", temperature=22.5

    Domain-Specific Parameters:
        - Lights: brightness (0-255), color_temp, rgb_color, transition, effect
        - Covers: position (0-100), tilt_position
        - Climate: temperature, target_temp_high, target_temp_low, hvac_mode
        - Media players: source, volume_level (0-1)
    """
    if action not in ["on", "off", "toggle"]:
        logger.error(f"Invalid action requested: {action}")
        return {"error": f"Invalid action: {action}. Valid actions are 'on', 'off', 'toggle'"}

    # Map action to service name
    # Korrigiert: 'turn_on'/'turn_off' statt nur 'on'/'off'
    service = f"turn_{action}" if action in ["on", "off"] else action # toggle bleibt toggle

    # Extract the domain from the entity_id
    domain = entity_id.split(".")[0]

    # Prepare service data
    data = {"entity_id": entity_id, **params}

    logger.info(f"Performing action '{service}' on entity: {entity_id} with params: {params}")
    return await call_service(domain, service, data)


@mcp.tool()
@async_handler("list_entities")
async def list_entities(
    domain: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
    fields: Optional[List[str]] = None,
    detailed: bool = False # Behält 'detailed' bei, um lean zu steuern
) -> List[Dict[str, Any]]:
    """
    Get a list of Home Assistant entities with optional filtering

    Args:
        domain: Optional domain to filter by (e.g., 'light', 'switch', 'sensor')
        search_query: Optional search term to filter entities by name, id, or attributes
                      (Note: Does not support wildcards. To get all entities, leave this empty)
        limit: Maximum number of entities to return (default: 100)
        fields: Optional list of specific fields to include in each entity
        detailed: If True, returns all entity fields without filtering (lean=False)

    Returns:
        A list of entity dictionaries with lean formatting by default

    Examples:
        domain="light" - get all lights
        search_query="kitchen", limit=20 - search entities
        domain="sensor", detailed=True - full sensor details

    Best Practices:
        - Use lean format (default) for most operations
        - Prefer domain filtering over no filtering
        - For domain overviews, use domain_summary_tool instead of list_entities
        - Only request detailed=True when necessary for full attribute inspection
        - To get all entity types/domains, use list_entities without a domain filter,
          then extract domains from entity_ids
    """
    log_message = "Getting entities"
    if domain:
        log_message += f" for domain: {domain}"
    if search_query:
        log_message += f" matching: '{search_query}'"
    if limit != 100:
        log_message += f" (limit: {limit})"
    if detailed:
        log_message += " (detailed format)"
    elif fields:
        log_message += f" (custom fields: {fields})"
    else:
        log_message += " (lean format)"

    logger.info(log_message)

    # Handle special case where search_query is a wildcard/asterisk - just ignore it
    if search_query == "*":
        search_query = None
        logger.info("Converting '*' search query to None (retrieving all entities)")

    # Use the updated get_entities function with field filtering
    # lean wird durch 'detailed' gesteuert
    return await get_entities(
        domain=domain,
        search_query=search_query,
        limit=limit,
        fields=fields,
        lean=not detailed  # Use lean format unless detailed is requested
    )

@mcp.tool()
@async_handler("search_entities_tool")
async def search_entities_tool(query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Search for entities matching a query string

    Args:
        query: The search query to match against entity IDs, names, and attributes.
               (Note: Does not support wildcards. To get all entities, leave this blank or use list_entities tool)
        limit: Maximum number of results to return (default: 20)

    Returns:
        A dictionary containing search results and metadata:
        - count: Total number of matching entities found
        - results: List of matching entities with essential information
        - domains: Map of domains with counts (e.g. {"light": 3, "sensor": 2})

    Examples:
        query="temperature" - find temperature entities
        query="living room", limit=10 - find living room entities
        query="", limit=500 - list all entity types (up to limit)

    """
    logger.info(f"Searching for entities matching: '{query}' with limit: {limit}")

    # Special case - treat "*" as empty query to just return entities without filtering
    if query == "*":
        query = ""
        logger.info("Converting '*' to empty query (retrieving all entities up to limit)")

    # Handle empty query as a special case to just return entities up to the limit
    if not query or not query.strip():
        logger.info(f"Empty query - retrieving up to {limit} entities without filtering")
        entities = await get_entities(limit=limit, lean=True)
        search_term_used = "all entities (no filtering)"
    else:
        # Normal search with non-empty query
        entities = await get_entities(search_query=query, limit=limit, lean=True)
        search_term_used = query


    # Check if there was an error
    if isinstance(entities, dict) and "error" in entities:
        return {"query": search_term_used, "error": entities["error"], "count": 0, "results": [], "domains": {}}
    if isinstance(entities, list) and len(entities) > 0 and isinstance(entities[0], dict) and "error" in entities[0]:
         return {"query": search_term_used, "error": entities[0]["error"], "count": 0, "results": [], "domains": {}}

    # Prepare the results
    domains_count = {}
    simplified_entities = []

    for entity in entities:
        domain = entity["entity_id"].split(".")[0]

        # Count domains
        if domain not in domains_count:
            domains_count[domain] = 0
        domains_count[domain] += 1

        # Create simplified entity representation
        simplified_entity = {
            "entity_id": entity["entity_id"],
            "state": entity.get("state", "unknown"), # Sicherstellen, dass state existiert
            "domain": domain,
            "friendly_name": entity.get("attributes", {}).get("friendly_name", entity["entity_id"])
        }

        # Add key attributes based on domain
        attributes = entity.get("attributes", {})

        # Include domain-specific important attributes
        if domain == "light" and "brightness" in attributes:
            simplified_entity["brightness"] = attributes["brightness"]
        elif domain == "sensor" and "unit_of_measurement" in attributes:
            simplified_entity["unit"] = attributes["unit_of_measurement"]
        elif domain == "climate" and "temperature" in attributes:
            simplified_entity["temperature"] = attributes["temperature"]
        elif domain == "media_player" and "media_title" in attributes:
            simplified_entity["media_title"] = attributes["media_title"]

        simplified_entities.append(simplified_entity)

    # Return structured response
    return {
        "count": len(simplified_entities),
        "results": simplified_entities,
        "domains": domains_count,
        "query": search_term_used # Verwende den tatsächlichen Suchbegriff
    }


@mcp.tool()
@async_handler("domain_summary")
async def domain_summary_tool(domain: str, example_limit: int = 3) -> Dict[str, Any]:
    """
    Get a summary of entities in a specific domain

    Args:
        domain: The domain to summarize (e.g., 'light', 'switch', 'sensor')
        example_limit: Maximum number of examples to include for each state

    Returns:
        A dictionary containing:
        - total_count: Number of entities in the domain
        - state_distribution: Count of entities in each state
        - examples: Sample entities for each state
        - common_attributes: Most frequently occurring attributes

    Examples:
        domain="light" - get light summary
        domain="climate", example_limit=5 - climate summary with more examples
    Best Practices:
        - Use this before retrieving all entities in a domain to understand what's available
    """
    logger.info(f"Getting domain summary for: {domain}")
    return await summarize_domain(domain, example_limit)

@mcp.tool()
@async_handler("system_overview")
async def system_overview() -> Dict[str, Any]:
    """
    Get a comprehensive overview of the entire Home Assistant system

    Returns:
        A dictionary containing:
        - total_entities: Total count of all entities
        - domains: Dictionary of domains with their entity counts and state distributions
        - domain_samples: Representative sample entities for each domain (2-3 per domain)
        - domain_attributes: Common attributes for each domain
        - area_distribution: Entities grouped by area (if available)

    Examples:
        Returns domain counts, sample entities, and common attributes
    Best Practices:
        - Use this as the first call when exploring an unfamiliar Home Assistant instance
        - Perfect for building context about the structure of the smart home
        - After getting an overview, use domain_summary_tool to dig deeper into specific domains
    """
    logger.info("Generating complete system overview")
    return await get_system_overview()


@mcp.tool()
@async_handler("list_automations")
async def list_automations() -> List[Dict[str, Any]]:
    """
    Get a list of all automations from Home Assistant

    This function retrieves all automations configured in Home Assistant,
    including their IDs, entity IDs, state, and display names.

    Returns:
        A list of automation dictionaries, each containing id, entity_id,
        state, and alias (friendly name) fields. Returns an empty list on error.

    Examples:
        Returns all automation objects with state and friendly names

    """
    logger.info("Getting all automations")
    try:
        # Get automations will now return data from states API, which is more reliable
        automations = await get_automations()

        # Handle error responses that might still occur
        if isinstance(automations, dict) and "error" in automations:
            logger.warning(f"Error getting automations: {automations['error']}")
            return []

        # Handle case where response is a list with error
        if isinstance(automations, list) and len(automations) > 0 and isinstance(automations[0], dict) and "error" in automations[0]:
            logger.warning(f"Error getting automations: {automations[0]['error']}")
            return []

        # Ensure return type is List[Dict]
        if isinstance(automations, list):
             # Check if elements are dicts (basic check)
             if all(isinstance(item, dict) for item in automations):
                 return automations
             else:
                 logger.warning("list_automations received a list with non-dict elements.")
                 return [] # Return empty list if format is unexpected
        else:
             logger.warning(f"Unexpected return type from get_automations: {type(automations)}")
             return [] # Return empty list for unexpected types

    except Exception as e:
        logger.error(f"Exception in list_automations: {str(e)}", exc_info=True)
        return [] # Return empty list on exception

@mcp.tool()
@async_handler("restart_ha")
async def restart_ha() -> Dict[str, Any]:
    """
    Restart Home Assistant

    ⚠️ WARNING: Temporarily disrupts all Home Assistant operations

    Returns:
        Result of restart operation
    """
    logger.info("Restarting Home Assistant")
    return await restart_home_assistant()

@mcp.tool()
@async_handler("call_service")
async def call_service_tool(domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Call any Home Assistant service (low-level API access)

    Args:
        domain: The domain of the service (e.g., 'light', 'switch', 'automation')
        service: The service to call (e.g., 'turn_on', 'turn_off', 'toggle')
        data: Optional data to pass to the service (e.g., {'entity_id': 'light.living_room'})

    Returns:
        The response from Home Assistant (usually empty for successful calls)

    Examples:
        domain='light', service='turn_on', data={'entity_id': 'light.x', 'brightness': 255}
        domain='automation', service='reload'
        domain='fan', service='set_percentage', data={'entity_id': 'fan.x', 'percentage': 50}

    """
    logger.info(f"Calling Home Assistant service: {domain}.{service} with data: {data}")
    return await call_service(domain, service, data or {})


@mcp.tool()
@async_handler("get_history")
async def get_history(entity_id: str, hours: int = 24) -> Dict[str, Any]:
    """
    Get the history of an entity's state changes

    Args:
        entity_id: The entity ID to get history for
        hours: Number of hours of history to retrieve (default: 24)

    Returns:
        A dictionary containing:
        - entity_id: The requested entity ID
        - states: List of state records with timestamp and value
        - count: Number of state changes
        - statistics: Summary statistics if the entity has numeric states
        - trend: For energy/power sensors, shows if values are increasing or decreasing

    Examples:
        entity_id="light.living_room" - get 24h history
        entity_id="sensor.temperature", hours=168 - get 7 day history
    Best Practices:
        - For large history data, consider limiting hours to reduce token usage
        - For power/energy sensors, requesting at least 24 hours provides daily averages
        - Use this data to identify patterns or troubleshoot automations
    """
    logger.info(f"Getting history for entity: {entity_id}, hours: {hours}")
    
    # Use our new implementation with minimal=True to reduce token usage
    return await get_entity_history(entity_id, hours=hours, minimal=True)

@mcp.tool()
@async_handler("get_error_log")
async def get_error_log() -> Dict[str, Any]:
    """
    Get the Home Assistant error log for troubleshooting

    Returns:
        A dictionary containing:
        - log_text: The full error log text
        - error_count: Number of ERROR entries found
        - warning_count: Number of WARNING entries found
        - integration_mentions: Map of integration names to mention counts
        - error: Error message if retrieval failed

    Examples:
        Returns errors, warnings count and integration mentions
    Best Practices:
        - Use this tool when troubleshooting specific Home Assistant errors
        - Look for patterns in repeated errors
        - Pay attention to timestamps to correlate errors with events
        - Focus on integrations with many mentions in the log
    """
    logger.info("Getting Home Assistant error log")
    return await get_hass_error_log()

# --- Configuration Tools (aus simplified_extensions) ---

@mcp.tool()
@async_handler("configure_component")
async def configure_component_tool(
    component_type: str,
    object_id: str,
    config_data: Dict[str, Any],
    update: bool = False
) -> Dict[str, Any]:
    """
    Home Assistant Komponente erstellen oder aktualisieren.

    Eine flexible Funktion, die verwendet werden kann, um verschiedene Arten von
    Home Assistant Komponenten zu konfigurieren wie Automatisierungen, Skripte,
    Szenen und mehr.

    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der zu konfigurierenden Komponente
        config_data: Konfigurationsdaten für die Komponente
        update: True für Update, False für Neuanlage

    Returns:
        Antwort von Home Assistant

    Beispiel - Neue Automatisierung:
    ```json
    {
        "component_type": "automation",
        "object_id": "lights_at_sunset_new",
        "config_data": {
            "alias": "Lichter bei Sonnenuntergang einschalten (Neu)",
            "description": "Schaltet die Lichter automatisch bei Sonnenuntergang ein",
            "trigger": [
                {"platform": "sun", "event": "sunset", "offset": "+00:30:00"}
            ],
            "action": [
                {"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}
            ],
            "mode": "single"
        }
    }
    ```
    """
    logger.info(f"Tool configure_component aufgerufen: Typ={component_type}, ID={object_id}, Update={update}")
    # Ruft die importierte Funktion aus simplified_extensions auf
    return await configure_ha_component(component_type, object_id, config_data, update)

@mcp.tool()
@async_handler("delete_component")
async def delete_component_tool(
    component_type: str,
    object_id: str
) -> Dict[str, Any]:
    """
    Home Assistant Komponente löschen.

    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der zu löschenden Komponente

    Returns:
        Antwort von Home Assistant

    Beispiel:
    ```json
    {
        "component_type": "automation",
        "object_id": "lights_at_sunset_new"
    }
    ```
    """
    logger.info(f"Tool delete_component aufgerufen: Typ={component_type}, ID={object_id}")
    # Ruft die importierte Funktion aus simplified_extensions auf
    return await delete_ha_component(component_type, object_id)

@mcp.tool()
@async_handler("set_attributes")
async def set_attributes_tool(
    entity_id: str,
    attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attribute für eine Home Assistant Entität setzen.

    Diese Funktion erkennt automatisch den richtigen Service basierend
    auf dem Entity-Typ und den zu setzenden Attributen.

    Args:
        entity_id: ID der Entität
        attributes: Zu setzende Attribute

    Returns:
        Antwort von Home Assistant

    Beispiele:
        Für Lampen:
        ```json
        {
            "entity_id": "light.living_room",
            "attributes": {"brightness": 150, "rgb_color": [0, 255, 0], "transition": 1}
        }
        ```
        Für Klimageräte:
        ```json
        {
            "entity_id": "climate.living_room",
            "attributes": {"temperature": 21.0, "hvac_mode": "cool"}
        }
        ```
    """
    logger.info(f"Tool set_attributes aufgerufen für {entity_id}: {attributes}")
    # Ruft die importierte Funktion aus simplified_extensions auf
    return await set_entity_attributes(entity_id, attributes)

# --- NEUES TOOL ---
@mcp.tool()
@async_handler("list_dashboards_tool")
async def list_dashboards_tool() -> List[Dict[str, Any]]:
    """
    Listet alle verfügbaren Lovelace-Dashboards in Home Assistant auf.

    Gibt eine Liste von Dictionaries zurück, jedes enthält Informationen
    über ein Dashboard (z.B. id, url_path, title, icon, mode).
    Der 'mode' kann 'storage' (UI-verwaltet) oder 'yaml' sein.

    Returns:
        Eine Liste von Dashboard-Informations-Dictionaries oder eine Liste
        mit einem Fehler-Dictionary bei Problemen.
        Beispiel Rückgabe:
        [
          {"id": "lovelace-generated", "url_path": null, "title": "Übersicht", "icon": "mdi:view-dashboard", "show_in_sidebar": true, "require_admin": false, "mode": "storage"},
          {"id": "mein-yaml-dashboard", "url_path": "mein-yaml-dashboard", "title": "YAML Dashboard", "icon": "mdi:file-document", "show_in_sidebar": true, "require_admin": false, "mode": "yaml"}
        ]
    """
    logger.info("Tool list_dashboards_tool aufgerufen")
    # Ruft die neu importierte Funktion aus simplified_extensions auf
    return await list_all_dashboards()
# --- ENDE NEUES TOOL ---


@mcp.tool()
@async_handler("manage_dashboard")
async def manage_dashboard_tool(
    action: str,
    dashboard_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
    icon: Optional[str] = None,
    show_in_sidebar: bool = True,
    views: Optional[List[Dict[str, Any]]] = None,
    resources: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Dashboards in Home Assistant verwalten (erstellen, aktualisieren, löschen, abrufen).

    Nutzt die Home Assistant Lovelace API. Funktioniert am besten mit Dashboards im 'storage' Modus.
    Operationen auf YAML-Dashboards können fehlschlagen oder unerwartetes Verhalten zeigen.

    Args:
        action: Aktion (create, update, delete, get)
        dashboard_id: ID (url_path) des Dashboards (optional für get/create, erforderlich für update/delete).
                      Für das Standard-Dashboard bei 'get' weglassen oder `None` übergeben.
        config: Komplette Konfiguration als Dictionary (für update).
        title: Titel des Dashboards (für create).
        icon: Icon des Dashboards (für create).
        show_in_sidebar: Ob das Dashboard in der Seitenleiste angezeigt werden soll (für create).
        views: Dashboard-Ansichten (Liste von Dictionaries) (für create/update).
        resources: Benutzerdefinierte Ressourcen/HACS-Module (Liste von Dictionaries) (für create/update).

    Returns:
        Antwort von Home Assistant oder ein Fehler-Dictionary.

    Beispiele:
        Dashboard erstellen:
        ```json
        {
            "action": "create",
            "title": "Mein Test Dashboard",
            "icon": "mdi:test-tube",
            "views": [
                {
                    "title": "Test View", "path": "test",
                    "cards": [{"type": "entities", "entities": ["light.living_room"]}]
                }
            ],
            "resources": [{"type": "module", "url": "/hacsfiles/button-card/button-card.js"}]
        }
        ```
        Dashboard abrufen (Standard):
        ```json
        {"action": "get"}
        ```
        Dashboard abrufen (Spezifisch):
        ```json
        {"action": "get", "dashboard_id": "mein_test_dashboard"}
        ```
        Dashboard löschen:
        ```json
        {"action": "delete", "dashboard_id": "mein_test_dashboard"}
        ```
        Dashboard aktualisieren (mit config):
         ```json
        {
            "action": "update",
            "dashboard_id": "mein_test_dashboard",
            "config": { "title": "Neuer Titel", "views": [...] }
        }
        ```
         Dashboard aktualisieren (mit Parametern):
         ```json
        {
            "action": "update",
            "dashboard_id": "mein_test_dashboard",
            "title": "Anderer Titel",
            "views": [...]
        }
        ```
    """
    logger.info(f"Tool manage_dashboard aufgerufen: Aktion={action}, ID={dashboard_id or 'default'}")
    # Ruft die importierte Funktion aus simplified_extensions auf
    return await manage_dashboard(
        action, dashboard_id, config, title, icon,
        show_in_sidebar, views, resources
    )


# --- Resource Endpoints ---
# (Unverändert)
# ... (Code der bestehenden Ressourcen hier einfügen) ...
@mcp.resource("hass://entities/{entity_id}")
@async_handler("get_entity_resource")
async def get_entity_resource(entity_id: str) -> str:
    """
    Get the state of a Home Assistant entity as a resource

    This endpoint provides a standard view with common entity information.
    For comprehensive attribute details, use the /detailed endpoint.

    Args:
        entity_id: The entity ID to get information for
    """
    logger.info(f"Getting entity resource: {entity_id}")

    # Get the entity state (using lean format for token efficiency)
    state = await get_entity_state(entity_id, lean=True) # use_cache entfernt

    # Check if there was an error
    if isinstance(state, dict) and "error" in state:
        return f"# Entity: {entity_id}\n\nError retrieving entity: {state['error']}"

    # Format the entity as markdown
    result = f"# Entity: {entity_id}\n\n"

    # Get friendly name if available
    friendly_name = state.get("attributes", {}).get("friendly_name")
    if friendly_name and friendly_name != entity_id:
        result += f"**Name**: {friendly_name}\n\n"

    # Add state
    result += f"**State**: {state.get('state')}\n\n"

    # Add domain info
    domain = entity_id.split(".")[0]
    result += f"**Domain**: {domain}\n\n"

    # Add key attributes based on domain type
    attributes = state.get("attributes", {})

    # Add a curated list of important attributes
    important_attrs = []

    # Common attributes across many domains
    common_attrs = ["device_class", "unit_of_measurement", "friendly_name"]

    # Domain-specific important attributes
    if domain == "light":
        important_attrs = ["brightness", "color_temp", "rgb_color", "supported_features", "supported_color_modes"]
    elif domain == "sensor":
        important_attrs = ["unit_of_measurement", "device_class", "state_class"]
    elif domain == "climate":
        important_attrs = ["hvac_mode", "hvac_action", "temperature", "current_temperature", "target_temp_*"]
    elif domain == "media_player":
        important_attrs = ["media_title", "media_artist", "source", "volume_level", "media_content_type"]
    elif domain == "switch" or domain == "binary_sensor":
        important_attrs = ["device_class", "is_on"] # is_on ist kein Standardattribut, eher der state

    # Combine with common attributes
    important_attrs.extend(common_attrs)

    # Deduplicate the list while preserving order
    important_attrs = list(dict.fromkeys(important_attrs))

    # Create and add the important attributes section
    result += "## Key Attributes\n\n"

    # Display only the important attributes that exist
    displayed_attrs = 0
    for attr_name in important_attrs:
        # Handle wildcard attributes (e.g., target_temp_*)
        if attr_name.endswith("*"):
            prefix = attr_name[:-1]
            matching_attrs = [name for name in attributes if name.startswith(prefix)]
            for name in matching_attrs:
                result += f"- **{name}**: {attributes[name]}\n"
                displayed_attrs += 1
        # Regular attribute match
        elif attr_name in attributes:
            attr_value = attributes[attr_name]
            # Truncate long values
            if isinstance(attr_value, (list, dict)) and len(str(attr_value)) > 100:
                result += f"- **{attr_name}**: *[Complex data, see detailed view]*\n"
            else:
                result += f"- **{attr_name}**: {attr_value}\n"
            displayed_attrs += 1

    # If no important attributes were found, show a message
    if displayed_attrs == 0:
        result += "No key attributes found for this entity type.\n"

    # Add attribute count and link to detailed view
    total_attr_count = len(attributes)
    # Korrigiert: Link zur detaillierten Ansicht nur anzeigen, wenn es mehr Attribute gibt
    if total_attr_count > displayed_attrs:
        hidden_count = total_attr_count - displayed_attrs
        result += f"\n**Note**: Showing {displayed_attrs} of {total_attr_count} total attributes. "
        # Korrigiert: Verwende den korrekten Pfad für Ressourcen
        result += f"{hidden_count} additional attributes are available in the [detailed view](resource:hass://entities/{entity_id}/detailed).\n"
    result += "\n" # Zusätzlicher Zeilenumbruch für Lesbarkeit

    # Add last updated time if available
    if "last_updated" in state:
        result += f"**Last Updated**: {state['last_updated']}\n"

    return result

@mcp.resource("hass://entities/{entity_id}/detailed")
@async_handler("get_entity_resource_detailed")
async def get_entity_resource_detailed(entity_id: str) -> str:
    """
    Get detailed information about a Home Assistant entity as a resource

    Use this detailed view selectively when you need to:
    - Understand all available attributes of an entity
    - Debug entity behavior or capabilities
    - See comprehensive state information

    For routine operations where you only need basic state information,
    prefer the standard entity endpoint or specify fields in the get_entity tool.

    Args:
        entity_id: The entity ID to get information for
    """
    logger.info(f"Getting detailed entity resource: {entity_id}")

    # Get all fields, no filtering (detailed view explicitly requests all data)
    state = await get_entity_state(entity_id, lean=False) # use_cache entfernt

    # Check if there was an error
    if isinstance(state, dict) and "error" in state:
        return f"# Entity: {entity_id}\n\nError retrieving entity: {state['error']}"

    # Format the entity as markdown
    result = f"# Entity: {entity_id} (Detailed View)\n\n"

    # Get friendly name if available
    friendly_name = state.get("attributes", {}).get("friendly_name")
    if friendly_name and friendly_name != entity_id:
        result += f"**Name**: {friendly_name}\n\n"

    # Add state
    result += f"**State**: {state.get('state')}\n\n"

    # Add domain and entity type information
    domain = entity_id.split(".")[0]
    result += f"**Domain**: {domain}\n\n"

    # Add usage guidance
    result += "## Usage Note\n"
    result += "This is the detailed view showing all entity attributes. For token-efficient interactions, "
    # Korrigiert: Verwende den korrekten Pfad für Ressourcen
    result += f"consider using the [standard entity endpoint](resource:hass://entities/{entity_id}) or the get_entity tool with field filtering.\n\n"

    # Add all attributes with full details
    attributes = state.get("attributes", {})
    if attributes:
        result += "## Attributes\n\n"

        # Sort attributes for better organization
        sorted_attrs = sorted(attributes.items())

        # Format each attribute with complete information
        for attr_name, attr_value in sorted_attrs:
            # Format the attribute value
            if isinstance(attr_value, (list, dict)):
                # Use json.dumps for complex types for better readability
                try:
                    attr_str = json.dumps(attr_value, indent=2)
                    result += f"- **{attr_name}**:\n```json\n{attr_str}\n```\n"
                except TypeError:
                    # Fallback if json serialization fails
                     result += f"- **{attr_name}**: *[Cannot serialize value]*\n"
            else:
                result += f"- **{attr_name}**: {attr_value}\n"
        result += "\n" # Add space after attributes list

    # Add context data section
    result += "## Context Data\n\n"

    # Add last updated time if available
    if "last_updated" in state:
        result += f"**Last Updated**: {state['last_updated']}\n"

    # Add last changed time if available
    if "last_changed" in state:
        result += f"**Last Changed**: {state['last_changed']}\n"

    # Add entity ID and context information if available
    if "context" in state and state["context"]: # Check if context is not None
        context = state["context"]
        result += f"**Context ID**: {context.get('id', 'N/A')}\n"
        if context.get("parent_id"): # Check if parent_id exists and is not None
            result += f"**Parent Context**: {context['parent_id']}\n"
        if context.get("user_id"): # Check if user_id exists and is not None
            result += f"**User ID**: {context['user_id']}\n"
    else:
        result += "*No context information available.*\n"


    # Add related entities suggestions
    related_domains = []
    if domain == "light":
        related_domains = ["switch", "scene", "automation"]
    elif domain == "sensor":
        related_domains = ["binary_sensor", "input_number", "utility_meter"]
    elif domain == "climate":
        related_domains = ["sensor", "switch", "fan"]
    elif domain == "media_player":
        related_domains = ["remote", "switch", "sensor"]

    if related_domains:
        result += "\n## Related Entity Types\n\n"
        result += "You may want to check entities in these related domains:\n"
        for related in related_domains:
             # Korrigiert: Verwende den korrekten Pfad für Ressourcen
            result += f"- [{related}](resource:hass://entities/domain/{related})\n"

    return result

@mcp.resource("hass://entities")
@async_handler("get_all_entities_resource")
async def get_all_entities_resource() -> str:
    """
    Get a list of all Home Assistant entities as a resource

    This endpoint returns a complete list of all entities in Home Assistant,
    organized by domain. For token efficiency with large installations,
    consider using domain-specific endpoints or the domain summary instead.

    Returns:
        A markdown formatted string listing all entities grouped by domain

    Examples:
        ```
        # Get all entities
        entities_md = mcp.get_resource("hass://entities")
        ```

    Best Practices:
        - WARNING: This endpoint can return large amounts of data with many entities
        - Prefer domain-filtered endpoints: hass://entities/domain/{domain}
        - For overview information, use domain summaries instead of full entity lists
        - Consider starting with a search if looking for specific entities
    """
    logger.info("Getting all entities as a resource")
    entities = await get_entities(lean=True) # lean=True für Performance

    # Check if there was an error
    if isinstance(entities, dict) and "error" in entities:
        return f"Error retrieving entities: {entities['error']}"
    if isinstance(entities, list) and len(entities) > 0 and isinstance(entities[0], dict) and "error" in entities[0]:
        return f"Error retrieving entities: {entities[0]['error']}"

    # Format the entities as a string
    result = "# Home Assistant Entities\n\n"
    result += f"Total entities: {len(entities)}\n\n"
    result += "⚠️ **Note**: For better performance and token efficiency, consider using:\n"
    # Korrigiert: Verwende den korrekten Pfad für Ressourcen
    result += "- Domain filtering: `[hass://entities/domain/{domain}](resource:hass://entities/domain/{domain})`\n"
    # Summary endpoint existiert nicht standardmäßig, Tool verwenden
    # result += "- Domain summaries: `hass://entities/domain/{domain}/summary`\n"
    result += "- Domain summaries: Use the `domain_summary` tool.\n"
    # Korrigiert: Verwende den korrekten Pfad für Ressourcen
    result += "- Entity search: `[hass://search/{query}/{limit}](resource:hass://search/{query}/{limit})`\n\n"


    # Group entities by domain for better organization
    domains = {}
    for entity in entities:
        # Sicherstellen, dass entity ein dict ist und entity_id hat
        if isinstance(entity, dict) and "entity_id" in entity:
            domain = entity["entity_id"].split(".")[0]
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(entity)
        else:
            logger.warning(f"Skipping invalid entity data: {entity}")


    # Build the string with entities grouped by domain
    for domain in sorted(domains.keys()):
        domain_count = len(domains[domain])
        # Korrigiert: Verwende den korrekten Pfad für Ressourcen
        result += f"## [{domain.capitalize()} ({domain_count})](resource:hass://entities/domain/{domain})\n\n"
        for entity in sorted(domains[domain], key=lambda e: e["entity_id"]):
            # Get a friendly name if available
            friendly_name = entity.get("attributes", {}).get("friendly_name", "")
            # Korrigiert: Verwende den korrekten Pfad für Ressourcen
            result += f"- **[{entity['entity_id']}](resource:hass://entities/{entity['entity_id']})**: {entity.get('state', 'unknown')}"
            if friendly_name and friendly_name != entity["entity_id"]:
                result += f" ({friendly_name})"
            result += "\n"
        result += "\n"

    return result


@mcp.resource("hass://entities/domain/{domain}")
@async_handler("list_states_by_domain_resource")
async def list_states_by_domain_resource(domain: str) -> str:
    """
    Get a list of entities for a specific domain as a resource

    This endpoint provides all entities of a specific type (domain). It's much more
    token-efficient than retrieving all entities when you only need entities of a
    specific type.

    Args:
        domain: The domain to filter by (e.g., 'light', 'switch', 'sensor')

    Returns:
        A markdown formatted string with all entities in the specified domain

    Examples:
        ```
        # Get all lights
        lights_md = mcp.get_resource("hass://entities/domain/light")

        # Get all climate devices
        climate_md = mcp.get_resource("hass://entities/domain/climate")

        # Get all sensors
        sensors_md = mcp.get_resource("hass://entities/domain/sensor")
        ```

    Best Practices:
        - Use this endpoint when you need detailed information about all entities of a specific type
        - For a more concise overview, use the domain_summary tool
        - For sensors and other high-count domains, consider using a search to further filter results
    """
    logger.info(f"Getting entities for domain: {domain}")

    # Get all entities for the specified domain (using lean format for token efficiency)
    entities = await get_entities(domain=domain, lean=True)

    # Check if there was an error
    if isinstance(entities, dict) and "error" in entities:
        return f"Error retrieving entities: {entities['error']}"
    if isinstance(entities, list) and len(entities) > 0 and isinstance(entities[0], dict) and "error" in entities[0]:
        return f"Error retrieving entities: {entities[0]['error']}"


    # Format the entities as a string
    result = f"# {domain.capitalize()} Entities\n\n"

    total_entities = len(entities)
    result += f"Total entities in this domain: {total_entities}\n\n"

    if not entities:
         result += "No entities found in this domain.\n"
         return result

    # List the entities
    for entity in sorted(entities, key=lambda e: e["entity_id"]):
         # Sicherstellen, dass entity ein dict ist und entity_id hat
        if isinstance(entity, dict) and "entity_id" in entity:
            # Get a friendly name if available
            friendly_name = entity.get("attributes", {}).get("friendly_name", entity["entity_id"])
            # Korrigiert: Verwende den korrekten Pfad für Ressourcen
            result += f"- **[{entity['entity_id']}](resource:hass://entities/{entity['entity_id']})**: {entity.get('state', 'unknown')}"
            if friendly_name != entity["entity_id"]:
                result += f" ({friendly_name})"
            result += "\n"
        else:
            logger.warning(f"Skipping invalid entity data in domain {domain}: {entity}")


    # Add link to summary tool usage
    result += f"\n## Related Information\n\n"
    result += f"- Use the `domain_summary` tool for a concise overview of the '{domain}' domain.\n"
    # Korrigiert: Verwende den korrekten Pfad für Ressourcen
    result += f"- [View all entities](resource:hass://entities)\n"


    return result

@mcp.resource("hass://search/{query}/{limit}")
@async_handler("search_entities_resource_with_limit")
async def search_entities_resource_with_limit(query: str, limit: str) -> str:
    """
    Search for entities matching a query string with a specified result limit

    This endpoint extends the basic search functionality by allowing you to specify
    a custom limit on the number of results returned. It's useful for both broader
    searches (larger limit) and more focused searches (smaller limit).

    Args:
        query: The search query to match against entity IDs, names, and attributes
        limit: Maximum number of entities to return (as a string, will be converted to int)

    Returns:
        A markdown formatted string with search results and a JSON summary

    Examples:
        ```
        # Search with a larger limit (up to 50 results)
        results_md = mcp.get_resource("hass://search/sensor/50")

        # Search with a smaller limit for focused results
        results_md = mcp.get_resource("hass://search/kitchen/5")
        ```

    Best Practices:
        - Use smaller limits (5-10) for focused searches where you need just a few matches
        - Use larger limits (30-50) for broader searches when you need more comprehensive results
        - Balance larger limits against token usage - more results means more tokens
        - Consider domain-specific searches for better precision: "light kitchen" instead of just "kitchen"
    """
    try:
        limit_int = int(limit)
        if limit_int <= 0:
            limit_int = 20 # Default bei ungültigem Limit
    except ValueError:
        limit_int = 20 # Default bei ungültigem Limit

    logger.info(f"Searching for entities matching: '{query}' with custom limit: {limit_int}")

    if not query or not query.strip():
        return "# Entity Search\n\nError: No search query provided"

    # Verwende das search_entities_tool, um die Logik nicht zu duplizieren
    search_result_dict = await search_entities_tool(query=query, limit=limit_int)

    # Check if there was an error from the tool
    if "error" in search_result_dict:
        return f"# Entity Search\n\nError retrieving entities: {search_result_dict['error']}"

    entities = search_result_dict.get("results", [])
    query_used = search_result_dict.get("query", query) # Nehme den Query aus dem Ergebnis, falls modifiziert

    # Format the search results
    result = f"# Entity Search Results for '{query_used}' (Limit: {limit_int})\n\n"

    if not entities:
        result += "No entities found matching your search query.\n"
        return result

    result += f"Found {len(entities)} matching entities:\n\n"

    # Group entities by domain for better organization
    domains = {}
    for entity in entities:
        domain = entity.get("domain", entity.get("entity_id", "unknown.unknown").split(".")[0]) # Nehme Domain aus Ergebnis oder parse
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(entity)

    # Build the string with entities grouped by domain
    for domain in sorted(domains.keys()):
         # Korrigiert: Verwende den korrekten Pfad für Ressourcen
        result += f"## [{domain.capitalize()}](resource:hass://entities/domain/{domain})\n\n"
        for entity in sorted(domains[domain], key=lambda e: e.get("entity_id", "")):
            # Get a friendly name if available
            friendly_name = entity.get("friendly_name", entity.get("entity_id", ""))
            # Korrigiert: Verwende den korrekten Pfad für Ressourcen
            result += f"- **[{entity.get('entity_id', 'N/A')}](resource:hass://entities/{entity.get('entity_id', '')})**: {entity.get('state', 'unknown')}"
            if friendly_name != entity.get("entity_id", ""):
                result += f" ({friendly_name})"
            result += "\n"
        result += "\n"

    # Add a more structured summary section for easy LLM processing
    result += "## Summary in JSON format\n\n"
    result += "```json\n"

    # Use the simplified entities directly from the search_result_dict
    result += json.dumps(entities, indent=2)
    result += "\n```\n"

    return result

# --- Guided Conversation Prompts ---
# (Unverändert)
# ... (Code der bestehenden Prompts hier einfügen) ...
@mcp.prompt()
def create_automation(trigger_type: str, entity_id: str = None):
    """
    Guide a user through creating a Home Assistant automation

    This prompt provides a step-by-step guided conversation for creating
    a new automation in Home Assistant based on the specified trigger type.

    Args:
        trigger_type: The type of trigger for the automation (state, time, etc.)
        entity_id: Optional entity to use as the trigger source

    Returns:
        A list of messages for the interactive conversation
    """
    # Define the initial system message
    system_message = """You are an automation creation assistant for Home Assistant.
You'll guide the user through creating an automation with the following steps:
1. Define the trigger conditions based on their specified trigger type
2. Specify the actions to perform
3. Add any conditions (optional)
4. Review and confirm the automation using the `configure_component` tool.""" # Tool-Referenz hinzugefügt

    # Define the first user message based on parameters
    trigger_description = {
        "state": "an entity changing state",
        "time": "a specific time of day",
        "numeric_state": "a numeric value crossing a threshold",
        "zone": "entering or leaving a zone",
        "sun": "sun events (sunrise/sunset)",
        "template": "a template condition becoming true"
    }

    description = trigger_description.get(trigger_type, trigger_type)

    if entity_id:
        user_message = f"I want to create an automation triggered by {description} for {entity_id}."
    else:
        user_message = f"I want to create an automation triggered by {description}."

    # Return the conversation starter messages
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def debug_automation(automation_id: str):
    """
    Help a user troubleshoot an automation that isn't working

    This prompt guides the user through the process of diagnosing and fixing
    issues with an existing Home Assistant automation.

    Args:
        automation_id: The entity ID of the automation to troubleshoot (e.g., 'automation.mein_licht_an')

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant automation troubleshooting expert.
You'll help the user diagnose problems with their automation by checking:
1. Identify the automation using `list_automations` or `get_entity`.
2. Review the automation's configuration using `configure_component` (read-only if possible, or just describe based on knowledge).
3. Check the `last_triggered` attribute using `get_entity`.
4. Analyze triggers, conditions, and actions for logical errors.
5. Verify the state of related entities using `get_entity`.
6. Check the Home Assistant error log using `get_error_log`.
7. Suggest corrections and potentially use `configure_component` to apply fixes.""" # Tool-Referenzen hinzugefügt

    user_message = f"My automation {automation_id} isn't working properly. Can you help me troubleshoot it?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def troubleshoot_entity(entity_id: str):
    """
    Guide a user through troubleshooting issues with an entity

    This prompt helps diagnose and resolve problems with a specific
    Home Assistant entity that isn't functioning correctly.

    Args:
        entity_id: The entity ID having issues

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant entity troubleshooting expert.
You'll help the user diagnose problems with their entity by checking:
1. Current entity status and attributes using `get_entity` (use `detailed=True`).
2. Ask about expected vs. actual behavior.
3. Review related automations/scripts (using `list_automations`, etc.).
4. Check the Home Assistant error log using `get_error_log`.
5. Suggest potential causes (connectivity, integration issues, configuration).
6. Recommend solutions (restart integration, check device, update configuration).""" # Tool-Referenzen hinzugefügt

    user_message = f"My entity {entity_id} isn't working properly. Can you help me troubleshoot it?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def routine_optimizer():
    """
    Analyze usage patterns and suggest optimized routines based on actual behavior

    This prompt helps users analyze their Home Assistant usage patterns and create
    more efficient routines, automations, and schedules based on real usage data.

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant optimization expert specializing in routine analysis.
You'll help the user analyze their usage patterns and create optimized routines by:
1. Reviewing entity state histories using `get_history` (if available and useful) or analyzing patterns from current states/logs.
2. Analyzing when lights (`light`), climate controls (`climate`), etc., are used (using `get_entity`, `list_entities`).
3. Finding correlations between different device usages.
4. Suggesting new automations based on detected routines (using `configure_component`).
5. Optimizing existing automations (using `configure_component`).
6. Creating schedules (potentially via automations).
7. Identifying energy-saving opportunities based on usage patterns.""" # Tool-Referenzen hinzugefügt

    user_message = "I'd like to optimize my home automations based on my actual usage patterns. Can you help analyze how I use my smart home and suggest better routines?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def automation_health_check():
    """
    Review all automations, find conflicts, redundancies, or improvement opportunities

    This prompt helps users perform a comprehensive review of their Home Assistant
    automations to identify issues, optimize performance, and improve reliability.

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant automation expert specializing in system optimization.
You'll help the user perform a comprehensive audit of their automations by:
1. Reviewing all automations using `list_automations`.
2. Analyzing configurations for potential conflicts, redundancies, or inefficiencies.
3. Checking for missing conditions or inefficient triggers.
4. Suggesting template optimizations.
5. Identifying potential race conditions.
6. Recommending structural improvements and best practices.
7. Suggesting updates using `configure_component`.""" # Tool-Referenzen hinzugefügt

    user_message = "I'd like to do a health check on all my Home Assistant automations. Can you help me review them for conflicts, redundancies, and potential improvements?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def entity_naming_consistency():
    """
    Audit entity names and suggest standardization improvements

    This prompt helps users analyze their entity naming conventions and create
    a more consistent, organized naming system across their Home Assistant instance.

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant organization expert specializing in entity naming conventions.
You'll help the user audit and improve their entity naming by:
1. Analyzing current entity IDs and friendly names using `list_entities`.
2. Identifying patterns and inconsistencies.
3. Suggesting standardized naming schemes (e.g., `domain.location_device_function`).
4. Creating clear guidelines for future naming.
5. Proposing specific name changes (manual process, HA doesn't easily allow ID changes via API).
6. Explaining benefits of consistent naming.""" # Tool-Referenzen hinzugefügt

    user_message = "I'd like to make my Home Assistant entity names more consistent and organized. Can you help me audit my current naming conventions and suggest improvements?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def dashboard_layout_generator():
    """
    Create optimized dashboards based on user preferences and usage patterns

    This prompt helps users design effective, user-friendly dashboards
    for their Home Assistant instance based on their specific needs.

    Returns:
        A list of messages for the interactive conversation
    """
    system_message = """You are a Home Assistant UI design expert specializing in dashboard creation.
You'll help the user create optimized dashboards by:
1. Analyzing entity usage patterns (using history, logs, or user input).
2. Identifying logical groupings (by room, function).
3. Suggesting layouts and views using appropriate card types.
4. Designing specialized views (mobile, tablet).
5. Recommending custom cards (HACS).
6. Creating the dashboard structure using `manage_dashboard`.""" # Tool-Referenzen hinzugefügt

    user_message = "I'd like to redesign my Home Assistant dashboards to be more functional and user-friendly. Can you help me create optimized layouts based on how I actually use my system?"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]


# --- Main Execution Logic ---
# HINWEIS: Die Verwendung von asyncio.run() hier ist korrekt für das direkte
# Ausführen des Skripts, aber wenn es als Modul importiert wird (z.B. durch
# `python -m app`), wird __main__.py ausgeführt, welches mcp.run() aufruft.
# stdio_server(mcp) wird normalerweise innerhalb von mcp.run() gehandhabt.
# Wir behalten diesen Block für den Fall bei, dass server.py direkt ausgeführt wird,
# aber die primäre Ausführung sollte über __main__.py erfolgen.
import asyncio # Importiere asyncio hier

async def main():
    """Runs the MCP server using stdio."""
    logger.info("Starting Hass-MCP server with stdio...")
    # Setup cleanup hook for the HTTP client
    # Note: stdio_server might not have explicit shutdown hooks,
    # cleanup might depend on process termination signals.
    try:
        # Normalerweise würde mcp.run() hier verwendet, was stdio_server intern aufruft.
        # Wenn mcp von FastMCP kommt, hat es vielleicht keine run() Methode.
        # Wir verwenden stdio_server direkt, wenn mcp.run() nicht existiert.
        if hasattr(mcp, 'run'):
             mcp.run() # Geht davon aus, dass run() stdio handhabt und blockiert
        else:
             await stdio_server(mcp) # Direkter Aufruf, falls mcp.run nicht existiert
    finally:
        logger.info("Closing HTTP client...")
        await cleanup_client() # Ensure client is closed on exit
        logger.info("Hass-MCP server stopped.")

if __name__ == "__main__":
    # Überprüfe, ob eine Event-Loop bereits läuft (wichtig für einige Umgebungen)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.warning("Asyncio loop already running. Cannot start new one for main().")
        # Hier könnte man alternativ eine Task erstellen: loop.create_task(main())
        # Aber das Standardverhalten für __main__ ist oft, eine neue Loop zu starten.
    else:
        asyncio.run(main())


