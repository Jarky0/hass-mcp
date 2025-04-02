"""
Erweiterungsmodul für Home Assistant Interaktionen.
Bietet allgemeine, flexible Funktionen zur Steuerung und Konfiguration von Home Assistant.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

# Import existing functions from app.hass
from app.hass import call_service, get_entity_state, get_client, get_ha_headers
from app.config import HA_URL

async def configure_ha_component(
    component_type: str,
    object_id: str,
    config_data: Dict[str, Any],
    update: bool = False
) -> Dict[str, Any]:
    """
    Flexible Funktion zum Erstellen oder Aktualisieren von HA-Komponenten
    
    Diese Funktion kann verschiedene Typen von HA-Komponenten konfigurieren,
    einschließlich Automatisierungen, Skripte, Szenen, Dashboards etc.
    
    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der Komponente
        config_data: Konfigurationsdaten für die Komponente
        update: True für Update, False für Neuanlage
        
    Returns:
        Antwort von Home Assistant
    """
    client = await get_client()
    headers = get_ha_headers()
    
    logger.info(f"{'Aktualisiere' if update else 'Erstelle'} {component_type}: {object_id}")
    
    # Konstruiere den API-Pfad
    method = "post" if update else "post"  # API verwendet POST für beides
    api_path = f"/api/config/{component_type}/config/{object_id}"
    
    try:
        # API-Aufruf
        if update:
            # Bei Update erst die aktuelle Konfiguration abrufen
            response = await client.get(f"{HA_URL}{api_path}", headers=headers)
            response.raise_for_status()
            current_config = response.json()
            
            # Konfiguration aktualisieren (ohne Überschreiben nicht bereitgestellter Werte)
            merged_config = {**current_config, **config_data}
            response = await client.post(f"{HA_URL}{api_path}", headers=headers, json=merged_config)
        else:
            # Bei Neuanlage direkt erstellen
            response = await client.post(f"{HA_URL}{api_path}", headers=headers, json=config_data)
        
        response.raise_for_status()
        
        # Abhängig vom Komponententyp nachladen
        if component_type in ["automation", "script", "scene"]:
            await call_service(component_type, "reload", {})
        
        if hasattr(response, 'json'):
            try:
                return response.json()
            except:
                return {"result": "success"}
        return {"result": "success"}
    except Exception as e:
        return {"error": str(e)}

async def delete_ha_component(
    component_type: str,
    object_id: str
) -> Dict[str, Any]:
    """
    Flexible Funktion zum Löschen von HA-Komponenten
    
    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der Komponente
        
    Returns:
        Antwort von Home Assistant
    """
    client = await get_client()
    headers = get_ha_headers()
    
    logger.info(f"Lösche {component_type}: {object_id}")
    
    # Konstruiere den API-Pfad
    api_path = f"/api/config/{component_type}/config/{object_id}"
    
    try:
        # API-Aufruf
        response = await client.delete(f"{HA_URL}{api_path}", headers=headers)
        response.raise_for_status()
        
        # Abhängig vom Komponententyp nachladen
        if component_type in ["automation", "script", "scene"]:
            await call_service(component_type, "reload", {})
        
        return {"result": "success", "message": f"{component_type} {object_id} gelöscht"}
    except Exception as e:
        return {"error": str(e)}

async def set_entity_attributes(
    entity_id: str,
    attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attribute für eine HA-Entität setzen
    
    Diese Funktion erkennt den Domaintyp und ruft den entsprechenden Service auf.
    
    Args:
        entity_id: ID der Entität
        attributes: Zu setzende Attribute
        
    Returns:
        Antwort von Home Assistant
    """
    # Domain aus der entity_id extrahieren
    domain = entity_id.split(".")[0]
    
    # Servicedaten vorbereiten
    data = {
        "entity_id": entity_id,
        **attributes
    }
    
    # Passenden Service basierend auf der Domain und den Attributen auswählen
    service = "turn_on"  # Standardservice
    
    # Domainspezifische Services bestimmen
    if domain == "light":
        service = "turn_on"
    elif domain == "switch":
        service = "turn_on"
    elif domain == "climate":
        if "temperature" in attributes:
            service = "set_temperature"
        elif "hvac_mode" in attributes:
            service = "set_hvac_mode"
    elif domain == "cover":
        if "position" in attributes:
            service = "set_cover_position"
        else:
            service = "open_cover"
    elif domain == "media_player":
        if "media_content_id" in attributes:
            service = "play_media"
        elif "volume_level" in attributes:
            service = "volume_set"
        else:
            service = "turn_on"
    
    # Service aufrufen
    return await call_service(domain, service, data)

# Dashboard-Funktionen

async def get_dashboard_config(dashboard_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Konfiguration eines Dashboards abrufen
    
    Args:
        dashboard_id: ID des Dashboards, None für das Standarddashboard
        
    Returns:
        Dashboard-Konfiguration
    """
    client = await get_client()
    
    # URL je nach Standarddashboard oder spezifischem Dashboard konstruieren
    url = f"{HA_URL}/api/lovelace/{'dashboards/' + dashboard_id if dashboard_id else 'config'}"
    
    response = await client.get(
        url,
        headers=get_ha_headers()
    )
    response.raise_for_status()
    
    return response.json()

async def update_dashboard_config(
    config: Dict[str, Any],
    dashboard_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dashboard-Konfiguration aktualisieren
    
    Args:
        config: Neue Dashboard-Konfiguration
        dashboard_id: ID des Dashboards, None für das Standarddashboard
        
    Returns:
        Antwort von Home Assistant
    """
    client = await get_client()
    
    # URL je nach Standarddashboard oder spezifischem Dashboard konstruieren
    url = f"{HA_URL}/api/lovelace/{'dashboards/' + dashboard_id + '/config' if dashboard_id else 'config'}"
    
    response = await client.post(
        url,
        headers=get_ha_headers(),
        json=config
    )
    response.raise_for_status()
    
    return {"result": "success", "message": f"Dashboard {dashboard_id or 'default'} aktualisiert"}

async def manage_dashboard(
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
    Flexible Funktion zur Verwaltung von Dashboards
    
    Args:
        action: Aktion (create, update, delete, get)
        dashboard_id: ID des Dashboards (optional für get/create)
        config: Konfiguration (für update)
        title: Titel des Dashboards (für create)
        icon: Icon des Dashboards (für create)
        show_in_sidebar: Ob das Dashboard in der Seitenleiste angezeigt werden soll (für create)
        views: Dashboard-Ansichten (für create)
        resources: Benutzerdefinierte Ressourcen (für create/update)
        
    Returns:
        Antwort von Home Assistant
    """
    client = await get_client()
    headers = get_ha_headers()
    
    if action == "get":
        return await get_dashboard_config(dashboard_id)
    
    elif action == "create":
        # Dashboard-Daten vorbereiten
        dashboard_data = {
            "title": title,
            "show_in_sidebar": show_in_sidebar,
            "require_admin": False
        }
        
        if icon:
            dashboard_data["icon"] = icon
        
        # Dashboard erstellen
        create_url = f"{HA_URL}/api/lovelace/dashboards"
        response = await client.post(
            create_url,
            headers=headers,
            json=dashboard_data
        )
        response.raise_for_status()
        created_dashboard = response.json()
        
        # Views und Ressourcen hinzufügen, wenn angegeben
        if views or resources:
            config_data = {}
            if title:
                config_data["title"] = title
            if views:
                config_data["views"] = views
            if resources:
                config_data["resources"] = resources
                
            config_url = f"{HA_URL}/api/lovelace/dashboards/{created_dashboard['url_path']}/config"
            await client.post(
                config_url,
                headers=headers,
                json=config_data
            )
        
        return created_dashboard
    
    elif action == "update":
        if config:
            return await update_dashboard_config(config, dashboard_id)
        else:
            # Bestehende Konfiguration holen und aktualisieren
            current_config = await get_dashboard_config(dashboard_id)
            
            # Ressourcen aktualisieren wenn angegeben
            if resources:
                if "resources" not in current_config:
                    current_config["resources"] = []
                
                # Neue Ressourcen hinzufügen (ohne Duplikate)
                existing_urls = [r.get("url") for r in current_config["resources"]]
                for resource in resources:
                    if resource.get("url") not in existing_urls:
                        current_config["resources"].append(resource)
            
            return await update_dashboard_config(current_config, dashboard_id)
    
    elif action == "delete":
        if not dashboard_id:
            return {"error": "Für das Löschen wird eine dashboard_id benötigt"}
        
        delete_url = f"{HA_URL}/api/lovelace/dashboards/{dashboard_id}"
        response = await client.delete(
            delete_url,
            headers=headers
        )
        response.raise_for_status()
        
        return {"result": "success", "message": f"Dashboard {dashboard_id} gelöscht"}
    
    else:
        return {"error": f"Unbekannte Aktion: {action}"}