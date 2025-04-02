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

# (configure_ha_component, delete_ha_component, set_entity_attributes)
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

