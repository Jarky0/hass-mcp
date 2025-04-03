from typing import Dict, List, Any, Optional, TypedDict
import logging
import json
import asyncio
from datetime import datetime, timedelta

from app.api.client import HomeAssistantAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Globale API-Client-Instanz
_api_client: Optional[HomeAssistantAPI] = None

async def get_api_client() -> HomeAssistantAPI:
    """Liefert eine gemeinsam genutzte API-Client-Instanz"""
    global _api_client
    if _api_client is None:
        _api_client = HomeAssistantAPI()
        await _api_client.setup()
    return _api_client

async def cleanup_api_client() -> None:
    """Schließt die API-Client-Verbindung"""
    global _api_client
    if _api_client:
        await _api_client.close()
        _api_client = None

# MCP-Tool-Funktionen

async def get_version(random_string: str = "") -> str:
    """
    Ruft die Home Assistant Version ab
    
    Returns:
        Eine Zeichenkette mit der Home Assistant Version (z.B. "2025.3.0")
    """
    client = await get_api_client()
    config = await client.get_config()
    
    if isinstance(config, dict) and "error" in config:
        return f"Fehler beim Abrufen der Version: {config['error']}"
    
    return config.get("version", "Unbekannt")

async def get_entity(entity_id: str, fields: Optional[List[str]] = None, detailed: bool = False) -> Dict[str, Any]:
    """
    Ruft den Status einer Home Assistant Entität ab, optional mit Felderfilterung
    
    Args:
        entity_id: Die abzufragende Entitäts-ID (z.B. 'light.living_room')
        fields: Optionale Liste der einzuschließenden Felder (z.B. ['state', 'attr.brightness'])
        detailed: Wenn True, gibt alle Entitätsfelder ohne Filterung zurück
        
    Returns:
        Entitätsinformationen als Dictionary
    """
    client = await get_api_client()
    result = await client.get_state(entity_id)
    
    # Prüfe auf Fehler
    if isinstance(result, dict) and "error" in result:
        return result
    
    # Wenn detailed True ist, gib alle Informationen zurück
    if detailed:
        return result
    
    # Wenn fields angegeben ist, filtere die Ergebnisse
    if fields and not detailed:
        filtered_result = {"entity_id": entity_id}
        
        # Verarbeite Standardfelder
        for field in fields:
            if field == "state" and "state" in result:
                filtered_result["state"] = result["state"]
            elif field == "entity_id":
                continue  # Bereits hinzugefügt
            elif field.startswith("attr.") and "attributes" in result:
                # Extrahiere Attributnamen
                attr_name = field[5:]  # Entferne "attr." Präfix
                if attr_name in result["attributes"]:
                    if "attributes" not in filtered_result:
                        filtered_result["attributes"] = {}
                    filtered_result["attributes"][attr_name] = result["attributes"][attr_name]
            elif field in result:
                filtered_result[field] = result[field]
        
        return filtered_result
    
    # Standardrückgabe, wenn keine spezifischen Felder angefordert wurden
    return result

async def entity_action(entity_id: str, action: str, params: str) -> Dict[str, Any]:
    """
    Führt eine Aktion auf einer Home Assistant Entität aus (on, off, toggle)
    
    Args:
        entity_id: Die zu steuernde Entitäts-ID (z.B. 'light.living_room')
        action: Die auszuführende Aktion ('on', 'off', 'toggle')
        params: Zusätzliche Parameter für den Service-Aufruf als JSON-String
        
    Returns:
        Die Antwort von Home Assistant
    """
    client = await get_api_client()
    
    # Extrahiere Domain aus entity_id
    if "." not in entity_id:
        return {"error": f"Ungültige entity_id: {entity_id}. Format sollte 'domain.entity' sein."}
    
    domain = entity_id.split(".", 1)[0]
    
    # Mapping von Aktionen zu Service-Namen
    service_map = {
        "on": "turn_on",
        "off": "turn_off",
        "toggle": "toggle"
    }
    
    if action not in service_map:
        return {"error": f"Nicht unterstützte Aktion: {action}. Erlaubte Aktionen: on, off, toggle"}
    
    service = service_map[action]
    
    # Parse zusätzliche Parameter
    try:
        parameters = json.loads(params)
    except json.JSONDecodeError:
        return {"error": f"Ungültiger JSON-String für Parameter: {params}"}
    
    # Füge entity_id zu Parametern hinzu
    parameters["entity_id"] = entity_id
    
    # Rufe den Service auf
    return await client.call_service(domain, service, parameters)

async def list_entities(
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
    client = await get_api_client()
    
    # Hole alle Zustände
    states = await client.get_states()
    
    # Prüfe auf Fehler
    if isinstance(states, dict) and "error" in states:
        return [states]
    
    # Filtere nach Domain, wenn angegeben
    if domain:
        states = [state for state in states if state["entity_id"].startswith(f"{domain}.")]
    
    # Filtere nach Suchbegriff, wenn angegeben
    if search_query:
        query = search_query.lower()
        filtered_states = []
        
        for state in states:
            entity_id = state["entity_id"].lower()
            friendly_name = state.get("attributes", {}).get("friendly_name", "").lower()
            
            if query in entity_id or query in friendly_name:
                filtered_states.append(state)
        
        states = filtered_states
    
    # Begrenze die Anzahl der Ergebnisse
    states = states[:limit]
    
    # Wenn detailed True ist, gib alle Informationen zurück
    if detailed:
        return states
    
    # Wenn fields angegeben sind, filtere die Ergebnisse
    if fields and not detailed:
        filtered_states = []
        
        for state in states:
            filtered_state = {"entity_id": state["entity_id"]}
            
            # Verarbeite Standardfelder
            for field in fields:
                if field == "state" and "state" in state:
                    filtered_state["state"] = state["state"]
                elif field == "entity_id":
                    continue  # Bereits hinzugefügt
                elif field.startswith("attr.") and "attributes" in state:
                    # Extrahiere Attributnamen
                    attr_name = field[5:]  # Entferne "attr." Präfix
                    if attr_name in state["attributes"]:
                        if "attributes" not in filtered_state:
                            filtered_state["attributes"] = {}
                        filtered_state["attributes"][attr_name] = state["attributes"][attr_name]
                elif field in state:
                    filtered_state[field] = state[field]
            
            filtered_states.append(filtered_state)
        
        return filtered_states
    
    # Füge für jede Entität zumindest den Zustand hinzu
    lean_states = []
    for state in states:
        lean_state = {
            "entity_id": state["entity_id"],
            "state": state["state"]
        }
        
        # Füge friendly_name hinzu, falls vorhanden
        if "attributes" in state and "friendly_name" in state["attributes"]:
            if "attributes" not in lean_state:
                lean_state["attributes"] = {}
            lean_state["attributes"]["friendly_name"] = state["attributes"]["friendly_name"]
        
        lean_states.append(lean_state)
    
    return lean_states

async def search_entities_tool(query: str, limit: int = 20) -> Dict[str, Any]:
    """
    Sucht nach Entitäten, die einer Abfrage entsprechen
    
    Args:
        query: Die Suchabfrage, die mit Entitäts-IDs, Namen und Attributen abgeglichen werden soll
        limit: Maximale Anzahl zurückzugebender Ergebnisse
        
    Returns:
        Ein Wörterbuch mit Suchergebnissen und Metadaten
    """
    # Verwende list_entities mit der Suchabfrage
    entities = await list_entities(search_query=query, limit=limit, detailed=True)
    
    # Prüfe auf Fehler
    if entities and isinstance(entities[0], dict) and "error" in entities[0]:
        return {"error": entities[0]["error"], "count": 0, "results": [], "domains": {}}
    
    # Zähle Domains
    domain_counts = {}
    for entity in entities:
        domain = entity["entity_id"].split(".", 1)[0]
        if domain in domain_counts:
            domain_counts[domain] += 1
        else:
            domain_counts[domain] = 1
    
    # Erstelle eine vereinfachte Ergebnisliste mit wichtigen Informationen
    results = []
    for entity in entities:
        entity_id = entity["entity_id"]
        domain = entity_id.split(".", 1)[0]
        friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
        
        result = {
            "entity_id": entity_id,
            "domain": domain,
            "name": friendly_name,
            "state": entity["state"]
        }
        
        # Füge ein wichtiges Attribut hinzu, falls vorhanden
        attributes = entity.get("attributes", {})
        if domain == "light" and "brightness" in attributes:
            result["brightness"] = attributes["brightness"]
        elif domain == "sensor" and "unit_of_measurement" in attributes:
            result["unit"] = attributes["unit_of_measurement"]
        elif domain == "climate" and "temperature" in attributes:
            result["temperature"] = attributes["temperature"]
        
        results.append(result)
    
    return {
        "count": len(entities),
        "results": results,
        "domains": domain_counts
    }

async def domain_summary_tool(domain: str, example_limit: int = 3) -> Dict[str, Any]:
    """
    Liefert eine Zusammenfassung der Entitäten in einer bestimmten Domain
    
    Args:
        domain: Die zu analysierende Domain (z.B. 'light', 'switch', 'sensor')
        example_limit: Maximale Anzahl der Beispiele für jeden Zustand
        
    Returns:
        Ein Wörterbuch mit Statistiken und Beispielen
    """
    # Hole alle Entitäten der Domain
    entities = await list_entities(domain=domain, detailed=True)
    
    # Prüfe auf Fehler
    if entities and isinstance(entities[0], dict) and "error" in entities[0]:
        return {"error": entities[0]["error"]}
    
    # Sammle Zustandsverteilung
    state_distribution = {}
    state_examples = {}
    all_attributes = {}
    
    for entity in entities:
        state = entity["state"]
        entity_id = entity["entity_id"]
        
        # Zähle Zustände
        if state in state_distribution:
            state_distribution[state] += 1
        else:
            state_distribution[state] = 1
        
        # Sammle Beispiele für jeden Zustand
        if state not in state_examples:
            state_examples[state] = []
        
        if len(state_examples[state]) < example_limit:
            friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
            state_examples[state].append(f"{entity_id} ({friendly_name})")
        
        # Sammle Attribute für häufigkeitsanalyse
        for attr_name in entity.get("attributes", {}):
            if attr_name in all_attributes:
                all_attributes[attr_name] += 1
            else:
                all_attributes[attr_name] = 1
    
    # Sortiere Attribute nach Häufigkeit
    common_attributes = sorted(all_attributes.items(), key=lambda x: x[1], reverse=True)
    common_attributes = [attr[0] for attr in common_attributes[:10]]  # Top 10 Attribute
    
    return {
        "total_count": len(entities),
        "state_distribution": state_distribution,
        "examples": state_examples,
        "common_attributes": common_attributes
    }

async def system_overview(random_string: str = "") -> Dict[str, Any]:
    """
    Liefert einen umfassenden Überblick über das gesamte Home Assistant System
    
    Returns:
        Ein Wörterbuch mit Systeminformationen
    """
    client = await get_api_client()
    
    # Hole alle Zustände
    states = await client.get_states()
    
    # Prüfe auf Fehler
    if isinstance(states, dict) and "error" in states:
        return {"error": states["error"]}
    
    # Sammle Informationen nach Domains
    domains = {}
    area_distribution = {}
    
    for state in states:
        entity_id = state["entity_id"]
        domain = entity_id.split(".", 1)[0]
        current_state = state["state"]
        attributes = state.get("attributes", {})
        
        # Domain-Statistiken
        if domain not in domains:
            domains[domain] = {
                "count": 0,
                "states": {},
                "examples": {},
                "attributes": {}
            }
        
        domains[domain]["count"] += 1
        
        # Zustandsverteilung
        if current_state in domains[domain]["states"]:
            domains[domain]["states"][current_state] += 1
        else:
            domains[domain]["states"][current_state] = 1
        
        # Sammle Beispiele (maximal 3 pro Domain)
        if len(domains[domain].get("examples", {})) < 3:
            friendly_name = attributes.get("friendly_name", entity_id)
            domains[domain]["examples"][entity_id] = friendly_name
        
        # Sammle häufige Attribute
        for attr_name in attributes:
            if attr_name in domains[domain]["attributes"]:
                domains[domain]["attributes"][attr_name] += 1
            else:
                domains[domain]["attributes"][attr_name] = 1
        
        # Sammle Bereichsinformationen
        area = attributes.get("area", "Unbekannt")
        if area in area_distribution:
            area_distribution[area] += 1
        else:
            area_distribution[area] = 1
    
    # Vereinfache die Domain-Attribute auf die häufigsten
    for domain in domains:
        attr_items = sorted(domains[domain]["attributes"].items(), key=lambda x: x[1], reverse=True)
        domains[domain]["common_attributes"] = [attr[0] for attr in attr_items[:5]]  # Top 5
        del domains[domain]["attributes"]  # Entferne das vollständige Wörterbuch
    
    return {
        "total_entities": len(states),
        "domains": domains,
        "area_distribution": area_distribution,
        "ha_version": await get_version()
    }

async def list_automations(random_string: str = "") -> List[Dict[str, Any]]:
    """
    Ruft eine Liste aller Automatisierungen von Home Assistant ab
    
    Returns:
        Eine Liste von Automatisierungs-Wörterbüchern
    """
    # Verwende list_entities, um Automatisierungsentitäten zu finden
    automations = await list_entities(domain="automation", detailed=True)
    
    # Prüfe auf Fehler
    if automations and isinstance(automations[0], dict) and "error" in automations[0]:
        return automations
    
    # Extrahiere relevante Informationen
    result = []
    for automation in automations:
        entity_id = automation["entity_id"]
        automation_id = entity_id.split(".", 1)[1]  # Entferne "automation." Präfix
        
        info = {
            "id": automation_id,
            "entity_id": entity_id,
            "state": automation["state"],
            "alias": automation.get("attributes", {}).get("friendly_name", entity_id)
        }
        
        # Füge Beschreibung hinzu, falls vorhanden
        description = automation.get("attributes", {}).get("description")
        if description:
            info["description"] = description
        
        result.append(info)
    
    return result

async def restart_ha(random_string: str = "") -> Dict[str, Any]:
    """
    Startet Home Assistant neu
    
    ⚠️ WARNUNG: Unterbricht vorübergehend alle Home Assistant Operationen
    
    Returns:
        Ergebnis des Neustarts
    """
    client = await get_api_client()
    return await client.restart()

async def call_service_tool(domain: str, service: str, data: Optional[str] = None) -> Dict[str, Any]:
    """
    Ruft einen beliebigen Home Assistant Service auf (Low-Level API-Zugriff)
    
    Args:
        domain: Die Domain des Services (z.B. 'light', 'switch', 'automation')
        service: Der aufzurufende Service (z.B. 'turn_on', 'turn_off', 'toggle')
        data: Optionale Daten für den Service als JSON-String
        
    Returns:
        Die Antwort von Home Assistant
    """
    client = await get_api_client()
    
    # Parse Daten
    service_data = {}
    if data:
        try:
            service_data = json.loads(data)
        except json.JSONDecodeError:
            return {"error": f"Ungültiger JSON-String für Daten: {data}"}
    
    return await client.call_service(domain, service, service_data)

async def get_history(entity_id: str, hours: int = 24) -> Dict[str, Any]:
    """
    Ruft den Verlauf der Zustandsänderungen einer Entität ab
    
    Args:
        entity_id: Die Entitäts-ID, für die der Verlauf abgerufen werden soll
        hours: Anzahl der abzurufenden Verlaufsstunden
        
    Returns:
        Ein Wörterbuch mit:
        - entity_id: Die angeforderte Entitäts-ID
        - states: Liste der Zustandseinträge mit Zeitstempel und Wert
        - count: Anzahl der Zustandsänderungen
        - statistics: Zusammenfassende Statistiken, wenn die Entität numerische Zustände hat
    """
    client = await get_api_client()
    
    # Berechne Zeitstempel für den Anfang der Abfrage
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    start_iso = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Rufe Verlaufsdaten ab
    history = await client.get_history(start_iso, entity_id)
    
    # Prüfe auf Fehler
    if isinstance(history, dict) and "error" in history:
        return {"error": history["error"]}
    
    # Verlauf kann eine Liste von Listen sein, wobei jede innere Liste zu einer Entität gehört
    entity_history = []
    for group in history:
        if group and isinstance(group, list) and group[0]["entity_id"] == entity_id:
            entity_history = group
            break
    
    # Erstelle Antwort
    states = []
    numeric_states = []
    
    for state_entry in entity_history:
        # Prüfe, ob der Zustand numerisch ist
        try:
            numeric_value = float(state_entry["state"])
            is_numeric = True
        except (ValueError, TypeError):
            is_numeric = False
        
        # Formatiere den Zeitstempel für bessere Lesbarkeit
        timestamp = state_entry.get("last_changed", state_entry.get("last_updated", ""))
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%d.%m.%Y %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = timestamp
        else:
            formatted_time = "Unbekannt"
        
        # Sammle Zustandseinträge
        states.append({
            "timestamp": formatted_time,
            "state": state_entry["state"]
        })
        
        # Sammle numerische Werte für Statistiken
        if is_numeric:
            numeric_states.append(numeric_value)
    
    result = {
        "entity_id": entity_id,
        "states": states,
        "count": len(states)
    }
    
    # Füge Statistiken für numerische Zustände hinzu
    if numeric_states:
        result["statistics"] = {
            "min": min(numeric_states),
            "max": max(numeric_states),
            "average": sum(numeric_states) / len(numeric_states),
            "current": numeric_states[-1] if numeric_states else None,
            "is_numeric": True
        }
    
    return result

async def get_error_log(random_string: str = "") -> Dict[str, Any]:
    """
    Ruft das Home Assistant Fehlerprotokoll zur Fehlerbehebung ab
    
    Returns:
        Ein Wörterbuch mit:
        - log_text: Der vollständige Fehlerprotokolltext
        - error_count: Anzahl der gefundenen ERROR-Einträge
        - warning_count: Anzahl der gefundenen WARNING-Einträge
        - integration_mentions: Zuordnung von Integrationsnamen zu Erwähnungszahlen
    """
    client = await get_api_client()
    
    # Home Assistant hat keinen direkten API-Endpunkt für das Fehlerprotokoll
    # Dies ist eine Beispielimplementierung
    
    return {
        "error": "Diese Funktion ist noch nicht implementiert. In einer vollständigen Implementierung würde sie das Home Assistant Fehlerprotokoll abrufen."
    }
