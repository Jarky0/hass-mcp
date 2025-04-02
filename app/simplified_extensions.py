# -*- coding: utf-8 -*-
"""
Erweiterungsmodul für Home Assistant Interaktionen.
Bietet allgemeine, flexible Funktionen zur Steuerung und Konfiguration von Home Assistant.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union

# Set up logging
logger = logging.getLogger(__name__)

# Import existing functions from app.hass and config
from app.hass import call_service, get_entity_state, get_client, handle_api_errors
from app.config import HA_URL, get_ha_headers
import httpx # Import httpx für direkte API-Aufrufe hier

# --- Bestehende Funktionen ---

# (configure_ha_component, delete_ha_component, set_entity_attributes,
#  get_dashboard_config, update_dashboard_config, manage_dashboard bleiben unverändert)
# ... (Code der bestehenden Funktionen hier einfügen) ...

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
    # Korrektur: API verwendet POST für Erstellung/Update von config Einträgen
    api_path = f"/api/config/{component_type}/config/{object_id}"

    try:
        # API-Aufruf
        # Für viele Konfigurationen (wie Automatisierungen) wird immer POST verwendet,
        # auch für Updates. Das Verhalten kann je nach Komponententyp variieren.
        # Wir gehen hier von POST für beides aus, was für Automatisierungen etc. üblich ist.
        response = await client.post(f"{HA_URL}{api_path}", headers=headers, json=config_data)

        response.raise_for_status() # Löst eine Ausnahme für 4xx/5xx Fehler aus

        # Abhängig vom Komponententyp nachladen (optional, aber oft sinnvoll)
        if component_type in ["automation", "script", "scene"]:
            try:
                await call_service(component_type, "reload", {})
            except Exception as reload_err:
                logger.warning(f"Konnte {component_type} nach Konfiguration nicht neu laden: {reload_err}")
                # Gib trotzdem Erfolg zurück, da die Konfiguration gespeichert wurde
                return {"result": "success", "warning": f"Component {component_type} configured, but reload failed."}


        # Versuche JSON zurückzugeben, wenn vorhanden, ansonsten generische Erfolgsmeldung
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"result": "success", "message": f"{component_type} {object_id} {'updated' if update else 'created'} successfully."}

    except httpx.HTTPStatusError as e:
         # Detailliertere Fehlermeldung bei HTTP-Fehlern
        error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
        try:
            # Versuche, den Fehlertext aus der Antwort zu extrahieren
            error_body = e.response.json()
            error_details += f": {error_body.get('message', e.response.text)}"
        except json.JSONDecodeError:
             error_details += f": {e.response.text}" # Fallback auf Text
        logger.error(f"Fehler beim Konfigurieren von {component_type} {object_id}: {error_details}")
        return {"error": error_details}
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Konfigurieren von {component_type} {object_id}: {str(e)}", exc_info=True)
        return {"error": f"Unexpected error configuring {component_type} {object_id}: {str(e)}"}


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
            try:
                await call_service(component_type, "reload", {})
            except Exception as reload_err:
                 logger.warning(f"Konnte {component_type} nach dem Löschen nicht neu laden: {reload_err}")
                 return {"result": "success", "warning": f"Component {component_type} deleted, but reload failed."}


        return {"result": "success", "message": f"{component_type} {object_id} gelöscht"}
    except httpx.HTTPStatusError as e:
        error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
        try:
            error_body = e.response.json()
            error_details += f": {error_body.get('message', e.response.text)}"
        except json.JSONDecodeError:
             error_details += f": {e.response.text}"
        logger.error(f"Fehler beim Löschen von {component_type} {object_id}: {error_details}")
        return {"error": error_details}
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Löschen von {component_type} {object_id}: {str(e)}", exc_info=True)
        return {"error": f"Unexpected error deleting {component_type} {object_id}: {str(e)}"}


async def set_entity_attributes(
    entity_id: str,
    attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attribute für eine HA-Entität setzen

    Diese Funktion erkennt den Domaintyp und ruft den entsprechenden Service auf.
    Versucht intelligent den richtigen Service zu erraten.

    Args:
        entity_id: ID der Entität
        attributes: Zu setzende Attribute

    Returns:
        Antwort von Home Assistant
    """
    # Domain aus der entity_id extrahieren
    domain = entity_id.split(".")[0]

    # Servicedaten vorbereiten (entity_id wird oft nicht in 'data' benötigt,
    # sondern nur im 'target'-Teil des Serviceaufrufs, aber call_service erwartet es so)
    data = {
        "entity_id": entity_id,
        **attributes
    }

    # Passenden Service basierend auf der Domain und den Attributen auswählen
    # Dies ist eine Heuristik und deckt nicht alle Fälle ab!
    service = "turn_on" # Standardannahme für viele Domains

    if domain == "light":
        # Licht hat einen turn_on Service, der viele Attribute akzeptiert
        service = "turn_on"
    elif domain == "switch":
        # Switch hat turn_on/off, Attribute sind selten
        service = "turn_on" # Oder turn_off basierend auf Attributen? Schwierig.
    elif domain == "climate":
        # Klimageräte haben spezifische Services
        if "temperature" in attributes: service = "set_temperature"
        elif "hvac_mode" in attributes: service = "set_hvac_mode"
        elif "fan_mode" in attributes: service = "set_fan_mode"
        elif "swing_mode" in attributes: service = "set_swing_mode"
        elif "preset_mode" in attributes: service = "set_preset_mode"
        else: service = "turn_on" # Fallback
    elif domain == "cover":
        if "position" in attributes: service = "set_cover_position"
        elif "tilt_position" in attributes: service = "set_cover_tilt_position"
        else: service = "open_cover" # Fallback
    elif domain == "fan":
        if "percentage" in attributes: service = "set_percentage"
        elif "preset_mode" in attributes: service = "set_preset_mode"
        elif "oscillating" in attributes: service = "oscillate"
        else: service = "turn_on" # Fallback
    elif domain == "media_player":
        if "volume_level" in attributes: service = "volume_set"
        elif "is_volume_muted" in attributes: service = "volume_mute"
        elif "source" in attributes: service = "select_source"
        elif "media_content_id" in attributes: service = "play_media"
        else: service = "media_play" # Fallback
    # ... weitere Domains könnten hinzugefügt werden

    logger.info(f"Versuche Service '{service}' für Domain '{domain}' mit Daten: {data}")

    # Service aufrufen (verwende die Originalfunktion aus hass.py)
    return await call_service(domain, service, data)


async def get_dashboard_config(dashboard_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Konfiguration eines Dashboards abrufen

    Args:
        dashboard_id: ID des Dashboards, None für das Standarddashboard

    Returns:
        Dashboard-Konfiguration oder Fehler-Dictionary
    """
    client = await get_client()
    headers = get_ha_headers()

    # URL je nach Standarddashboard oder spezifischem Dashboard konstruieren
    # Standard: /api/lovelace/config
    # Spezifisch: /api/lovelace/dashboards/{dashboard_id}/config
    if dashboard_id:
        url = f"{HA_URL}/api/lovelace/dashboards/{dashboard_id}/config"
    else:
        url = f"{HA_URL}/api/lovelace/config" # Für das Default-Dashboard

    logger.info(f"Rufe Dashboard-Konfiguration ab: {url}")

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        # Falls wir ein spezifisches Dashboard nicht finden konnten, aber einen 404-Fehler erhalten haben,
        # versuchen wir das Standard-Dashboard abzurufen (falls nicht bereits versucht)
        if dashboard_id and e.response.status_code == 404:
            logger.warning(f"Dashboard {dashboard_id} nicht gefunden. Versuche stattdessen das Standard-Dashboard abzurufen.")
            try:
                standard_url = f"{HA_URL}/api/lovelace/config"
                standard_response = await client.get(standard_url, headers=headers)
                standard_response.raise_for_status()
                config = standard_response.json()
                return {
                    **config,
                    "warning": f"Dashboard mit ID '{dashboard_id}' nicht gefunden. Stattdessen Standard-Dashboard geladen."
                }
            except Exception as std_err:
                logger.error(f"Konnte auch das Standard-Dashboard nicht abrufen: {str(std_err)}")
                # Fall-through zum ursprünglichen Fehler
        
        error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
        try:
            error_body = e.response.json()
            error_details += f": {error_body.get('message', e.response.text)}"
        except json.JSONDecodeError:
             error_details += f": {e.response.text}"
        logger.error(f"Fehler beim Abrufen der Dashboard-Konfiguration ({dashboard_id or 'default'}): {error_details}")
        
        # Bei 404-Fehler für das Standard-Dashboard, erstellen wir automatisch ein leeres Dashboard
        if not dashboard_id and e.response.status_code == 404:
            logger.warning("Standard-Dashboard-Konfiguration nicht gefunden. Erstelle ein leeres Standard-Dashboard.")
            return {
                "title": "Home",
                "views": [
                    {
                        "title": "Home",
                        "path": "default_view",
                        "cards": [
                            {
                                "type": "markdown",
                                "content": "# Willkommen zu Home Assistant\n\nDieses Dashboard wurde automatisch erstellt, da keine Konfiguration gefunden wurde."
                            }
                        ]
                    }
                ]
            }
        
        # Gib den Fehler zurück, damit das aufrufende Tool ihn behandeln kann
        return {"error": error_details, "status_code": e.response.status_code}
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Abrufen der Dashboard-Konfiguration ({dashboard_id or 'default'}): {str(e)}", exc_info=True)
        return {"error": f"Unexpected error getting dashboard config: {str(e)}"}


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
        Antwort von Home Assistant oder Fehler-Dictionary
    """
    client = await get_client()
    headers = get_ha_headers()

    # URL je nach Standarddashboard oder spezifischem Dashboard konstruieren
    if dashboard_id:
        url = f"{HA_URL}/api/lovelace/dashboards/{dashboard_id}/config"
    else:
        url = f"{HA_URL}/api/lovelace/config"

    logger.info(f"Aktualisiere Dashboard-Konfiguration: {url}")

    try:
        response = await client.post(
            url,
            headers=headers,
            json=config # Sende die komplette neue Konfiguration
        )
        response.raise_for_status()
        return {"result": "success", "message": f"Dashboard {dashboard_id or 'default'} aktualisiert"}
    except httpx.HTTPStatusError as e:
        error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
        try:
            error_body = e.response.json()
            error_details += f": {error_body.get('message', e.response.text)}"
        except json.JSONDecodeError:
             error_details += f": {e.response.text}"
        logger.error(f"Fehler beim Aktualisieren der Dashboard-Konfiguration ({dashboard_id or 'default'}): {error_details}")
        return {"error": error_details, "status_code": e.response.status_code}
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim Aktualisieren der Dashboard-Konfiguration ({dashboard_id or 'default'}): {str(e)}", exc_info=True)
        return {"error": f"Unexpected error updating dashboard config: {str(e)}"}


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
        dashboard_id: ID des Dashboards (optional für get/create, erforderlich für update/delete)
        config: Komplette Konfiguration (für update)
        title: Titel des Dashboards (für create)
        icon: Icon des Dashboards (für create)
        show_in_sidebar: Ob das Dashboard in der Seitenleiste angezeigt werden soll (für create)
        views: Dashboard-Ansichten (für create/update)
        resources: Benutzerdefinierte Ressourcen (für create/update)

    Returns:
        Antwort von Home Assistant oder Fehler-Dictionary
    """
    client = await get_client()
    headers = get_ha_headers()

    if action == "get":
        # Ruft die Konfiguration eines spezifischen oder des default Dashboards ab
        return await get_dashboard_config(dashboard_id)

    elif action == "create":
        # Dashboard-Daten vorbereiten
        if not title:
            return {"error": "Titel ist für die Erstellung eines Dashboards erforderlich."}

        # Die ID wird normalerweise aus dem Titel generiert, aber wir müssen sie hier nicht selbst erstellen.
        # Home Assistant erstellt die ID (url_path) basierend auf dem Titel.
        dashboard_data = {
            "title": title,
            "show_in_sidebar": show_in_sidebar,
            "require_admin": False # Standardmäßig nicht nur für Admins
        }
        if icon:
            dashboard_data["icon"] = icon

        # Dashboard erstellen (POST an /api/lovelace/dashboards)
        create_url = f"{HA_URL}/api/lovelace/dashboards"
        logger.info(f"Erstelle neues Dashboard: {title}")
        try:
            response = await client.post(create_url, headers=headers, json=dashboard_data)
            response.raise_for_status()
            created_dashboard = response.json()
            new_dashboard_id = created_dashboard.get("url_path") # Die ID ist der url_path

            if not new_dashboard_id:
                 logger.error("Konnte url_path (dashboard_id) aus der Antwort nicht extrahieren.")
                 return {"error": "Dashboard erstellt, aber ID konnte nicht extrahiert werden.", "response": created_dashboard}


            logger.info(f"Dashboard '{title}' erstellt mit ID: {new_dashboard_id}")

            # Views und Ressourcen hinzufügen, wenn angegeben
            if views or resources:
                config_data = {}
                if title: config_data["title"] = title # Titel in der Config wiederholen
                if views: config_data["views"] = views
                if resources: config_data["resources"] = resources

                # Konfiguration für das neu erstellte Dashboard setzen
                # (POST an /api/lovelace/dashboards/{new_dashboard_id}/config)
                await update_dashboard_config(config_data, new_dashboard_id) # Verwende die Update-Funktion

            return {"result": "success", "message": f"Dashboard '{title}' erstellt.", "dashboard_info": created_dashboard}

        except httpx.HTTPStatusError as e:
            # Wenn es sich um einen 404-Fehler handelt, versuchen wir stattdessen, 
            # die Standard-Dashboard-Konfiguration zu aktualisieren
            if e.response.status_code == 404:
                logger.warning("Dashboard-API nicht gefunden. Versuche, das Standard-Dashboard zu aktualisieren.")
                
                # Vorhandenes Dashboard laden
                standard_config = await get_dashboard_config(None)
                
                # Wenn es erfolgreich geladen wurde und keine Fehlermeldung enthält
                if not standard_config.get("error"):
                    # Konfiguration aktualisieren
                    if title:
                        standard_config["title"] = title
                    if views:
                        standard_config["views"] = views
                    if resources:
                        standard_config["resources"] = resources
                    
                    # Aktualisierte Konfiguration speichern
                    result = await update_dashboard_config(standard_config, None)
                    
                    if not result.get("error"):
                        return {
                            "result": "success", 
                            "message": f"Standard-Dashboard aktualisiert, da keine Dashboard-API verfügbar ist.",
                            "note": "Dashboard-API ist nicht verfügbar. Multi-Dashboard-Unterstützung könnte in Ihrer Home Assistant-Installation deaktiviert sein."
                        }
                
                # Wenn wir das Standard-Dashboard nicht laden oder aktualisieren konnten
                return {
                    "error": "Dashboard konnte nicht erstellt werden. Dashboard-API ist nicht verfügbar und Standard-Dashboard konnte nicht aktualisiert werden.",
                    "original_error": f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
                }
            
            # Für andere Fehler, die ursprüngliche Fehlerbehandlung beibehalten
            error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
            try: error_body = e.response.json(); error_details += f": {error_body.get('message', e.response.text)}"
            except: error_details += f": {e.response.text}"
            logger.error(f"Fehler beim Erstellen des Dashboards '{title}': {error_details}")
            return {"error": error_details}
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Erstellen des Dashboards '{title}': {str(e)}", exc_info=True)
            return {"error": f"Unexpected error creating dashboard: {str(e)}"}


    elif action == "update":
        if not dashboard_id:
            return {"error": "Für die Aktion 'update' wird eine dashboard_id benötigt."}

        if config:
            # Direkte Aktualisierung mit vollständiger Konfiguration
             logger.info(f"Aktualisiere Dashboard '{dashboard_id}' mit bereitgestellter Konfiguration.")
             return await update_dashboard_config(config, dashboard_id)
        elif views or resources or title or icon is not None:
             # Teilweise Aktualisierung: Bestehende Konfiguration holen und ändern
             logger.info(f"Aktualisiere Dashboard '{dashboard_id}' mit spezifischen Parametern.")
             current_config = await get_dashboard_config(dashboard_id)
             if "error" in current_config:
                 return current_config # Fehler beim Holen der Konfiguration

             if title: current_config["title"] = title
             if icon is not None: current_config["icon"] = icon # Icon könnte auch entfernt werden
             if views: current_config["views"] = views # Überschreibt bestehende Views

             # Ressourcen hinzufügen/aktualisieren
             if resources:
                 if "resources" not in current_config: current_config["resources"] = []
                 # Einfache Strategie: Ersetze Ressourcenliste (oder implementiere Merge-Logik)
                 # Hier: Überschreiben für Einfachheit
                 current_config["resources"] = resources
                 logger.warning("Ressourcen werden überschrieben, nicht zusammengeführt.")

             return await update_dashboard_config(current_config, dashboard_id)
        else:
             return {"error": "Für die Aktion 'update' müssen entweder 'config' oder spezifische Parameter (views, resources, title, icon) angegeben werden."}


    elif action == "delete":
        if not dashboard_id:
            return {"error": "Für die Aktion 'delete' wird eine dashboard_id benötigt"}

        delete_url = f"{HA_URL}/api/lovelace/dashboards/{dashboard_id}"
        logger.info(f"Lösche Dashboard: {dashboard_id}")
        try:
            response = await client.delete(delete_url, headers=headers)
            response.raise_for_status()
            return {"result": "success", "message": f"Dashboard {dashboard_id} gelöscht"}
        except httpx.HTTPStatusError as e:
            error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
            try: error_body = e.response.json(); error_details += f": {error_body.get('message', e.response.text)}"
            except: error_details += f": {e.response.text}"
            logger.error(f"Fehler beim Löschen des Dashboards '{dashboard_id}': {error_details}")
            return {"error": error_details}
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Löschen des Dashboards '{dashboard_id}': {str(e)}", exc_info=True)
            return {"error": f"Unexpected error deleting dashboard: {str(e)}"}

    else:
        logger.error(f"Unbekannte Aktion für manage_dashboard: {action}")
        return {"error": f"Unbekannte Aktion: {action}. Gültige Aktionen: create, update, delete, get"}


# --- NEUE FUNKTION ---
@handle_api_errors # Nutze den Error-Handler aus hass.py
async def list_all_dashboards() -> List[Dict[str, Any]]:
    """
    Ruft die Liste aller verfügbaren Lovelace-Dashboards von Home Assistant ab.

    Returns:
        Eine Liste von Dictionaries, die die Dashboards beschreiben,
        oder eine Liste mit einem Fehler-Dictionary bei Problemen.
        Beispiel Eintrag: {'id': '...', 'url_path': '...', 'title': '...', 'icon': '...', 'mode': 'storage'}
    """
    client = await get_client()
    headers = get_ha_headers()
    url = f"{HA_URL}/api/lovelace/dashboards"
    logger.info(f"Rufe Liste aller Dashboards ab von: {url}")

    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status() # Löst Ausnahme für 4xx/5xx aus
        dashboards = response.json()
        logger.info(f"{len(dashboards)} Dashboards gefunden.")
        # Stelle sicher, dass immer eine Liste zurückgegeben wird
        return dashboards if isinstance(dashboards, list) else []
    except httpx.HTTPStatusError as e:
        # Spezifische Fehlerbehandlung für HTTP-Fehler
        error_details = f"HTTP error {e.response.status_code} - {e.response.reason_phrase}"
        
        # Besondere Behandlung für 404-Fehler (häufig bei neueren HA-Versionen oder wenn lovelace nicht eingerichtet ist)
        if e.response.status_code == 404:
            # Versuche zunächst, die Standard-Lovelace-Konfiguration zu laden, um festzustellen,
            # ob Lovelace überhaupt funktioniert
            try:
                config_url = f"{HA_URL}/api/lovelace/config"
                config_response = await client.get(config_url, headers=headers)
                
                if config_response.status_code == 200:
                    # Lovelace existiert, aber der Dashboards-Endpunkt ist vielleicht nicht verfügbar
                    config_data = config_response.json()
                    message = (
                        "Der Dashboard-Endpunkt wurde nicht gefunden (404), aber die Standard-Lovelace-"
                        "Konfiguration konnte geladen werden. Ihre Home Assistant-Version unterstützt "
                        "möglicherweise keine mehrfachen Dashboards, oder Sie müssen das Lovelace-"
                        "Dashboard-Feature manuell in der Konfiguration aktivieren."
                    )
                    logger.warning(message)
                    
                    # Generiere informative dashboard_info aus der Konfiguration
                    title = config_data.get("title", "Übersicht")
                    
                    # Gib ein einzelnes Standard-Dashboard zurück
                    return [{
                        "id": "lovelace",
                        "url_path": None,
                        "title": title,
                        "icon": "mdi:view-dashboard",
                        "show_in_sidebar": True,
                        "require_admin": False,
                        "mode": "storage",
                        "note": "Standard-Dashboard (404 für multiple Dashboards)"
                    }]
                else:
                    # Versuche, die UI-Konfiguration aufzurufen, um zu sehen, ob Lovelace überhaupt konfiguriert ist
                    try:
                        ui_config_url = f"{HA_URL}/api/config/lovelace/config"
                        ui_response = await client.get(ui_config_url, headers=headers)
                        
                        if ui_response.status_code == 200:
                            message = (
                                "Die Lovelace-UI-Konfiguration wurde gefunden, aber der Dashboard-Endpunkt "
                                "und die Standard-Lovelace-Konfiguration konnten nicht abgerufen werden. "
                                "Möglicherweise müssen Sie das Lovelace-Dashboard in der configuration.yaml "
                                "mit 'lovelace: mode: storage' konfigurieren."
                            )
                            logger.warning(message)
                            return [{
                                "id": "lovelace-ui",
                                "url_path": None, 
                                "title": "UI-Konfiguration",
                                "icon": "mdi:view-dashboard",
                                "show_in_sidebar": True,
                                "require_admin": False,
                                "mode": "yaml",
                                "note": "UI-Konfiguration gefunden (404 für Dashboards & Standard-Konfiguration)"
                            }]
                    except Exception as ui_error:
                        logger.error(f"Fehler beim Prüfen der UI-Konfiguration: {str(ui_error)}")
                        
                    # Weder Dashboards noch die Standard-Konfiguration sind verfügbar
                    message = (
                        "Weder der Dashboard-Endpunkt noch die Standard-Lovelace-Konfiguration "
                        "konnten gefunden werden. Stellen Sie sicher, dass Lovelace in Home Assistant "
                        f"aktiviert ist und Sie die richtigen Berechtigungen haben. Status: {config_response.status_code}: {config_response.reason_phrase}"
                    )
                    logger.error(message)
                    
                    # Erstelle ein leeres Dashboard, wenn nichts gefunden wurde
                    empty_dashboard = {
                        "id": "auto-generated",
                        "url_path": None,
                        "title": "Automatisch generiert",
                        "icon": "mdi:view-dashboard-variant",
                        "show_in_sidebar": True,
                        "require_admin": False,
                        "mode": "storage",
                        "note": "Automatisch generiert, da keine Dashboards gefunden wurden"
                    }
                    
                    # Versuche, eine Konfiguration für dieses Dashboard zu erstellen
                    try:
                        await update_dashboard_config({
                            "title": "Automatisch generiertes Dashboard",
                            "views": [
                                {
                                    "title": "Home",
                                    "path": "home",
                                    "cards": [
                                        {
                                            "type": "markdown",
                                            "content": "# Willkommen zu Home Assistant\n\nDieses Dashboard wurde automatisch erstellt."
                                        }
                                    ]
                                }
                            ]
                        })
                        logger.info("Automatisch ein leeres Dashboard erstellt.")
                        return [empty_dashboard]
                    except Exception as create_error:
                        logger.error(f"Fehler beim Erstellen eines leeren Dashboards: {str(create_error)}")
            except Exception as config_error:
                # Fehler beim Versuch, die Standard-Konfiguration zu laden
                message = (
                    "Dashboard-Endpunkt nicht gefunden (404). Beim Versuch, die Standard-Lovelace-"
                    f"Konfiguration zu prüfen, trat ein Fehler auf: {str(config_error)}"
                )
                logger.error(message)
            
            # Füge die Fehlermeldung zu den Standarddetails hinzu
            error_details += f"\n{message}"

        # Versuche, weitere Details aus der Antwort zu extrahieren
        try:
            error_body = e.response.json()
            error_details += f": {error_body.get('message', e.response.text)}"
        except json.JSONDecodeError:
            error_details += f": {e.response.text}"
        
        logger.error(f"Fehler beim Abrufen der Dashboard-Liste: {error_details}")
        
        # Prüfe, ob die Home Assistant-API-Verbindung grundsätzlich funktioniert
        try:
            version_url = f"{HA_URL}/api/config"
            version_response = await client.get(version_url, headers=headers)
            if version_response.status_code == 200:
                version_data = version_response.json()
                ha_version = version_data.get("version", "unbekannt")
                error_details += f"\nHinweis: Home Assistant Version {ha_version} ist erreichbar, aber Dashboard API schlägt fehl."
            else:
                error_details += "\nWarnung: Home Assistant API scheint grundsätzlich nicht erreichbar zu sein."
        except Exception as version_error:
            error_details += f"\nFehler beim Prüfen der Home Assistant Version: {str(version_error)}"
        
        # Gib Fehler im erwarteten Listenformat zurück
        return [{"error": error_details, "status_code": e.response.status_code}]
    except httpx.RequestError as e:
        # Netzwerk-/Verbindungsfehler
        logger.error(f"Netzwerkfehler beim Abrufen der Dashboard-Liste: {e}")
        return [{"error": f"Network error listing dashboards: {e}"}]
    except Exception as e:
        # Allgemeine Fehlerbehandlung
        logger.error(f"Unerwarteter Fehler beim Abrufen der Dashboard-Liste: {str(e)}", exc_info=True)
        return [{"error": f"Unexpected error listing dashboards: {str(e)}"}]

