"""
Event-Handling für Home Assistant

Dieses Modul bietet Funktionen zur Verwaltung von Home Assistant Events,
einschließlich Auslösen von Events und Verarbeiten von Event-Daten.
"""
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Callable, Awaitable

from app.api.client import HomeAssistantAPI

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventManager:
    """
    Verwaltet Events in Home Assistant und bietet hilfreiche
    Methoden zur Interaktion mit ihnen.
    """
    
    def __init__(self, api_client: HomeAssistantAPI):
        """
        Initialisiert den EventManager.
        
        Args:
            api_client: Eine Instanz des Home Assistant API-Clients
        """
        self.api = api_client
        self._available_events = None
        self._event_listeners = {}
    
    async def get_available_events(self, refresh: bool = False) -> List[str]:
        """
        Ruft alle verfügbaren Event-Typen ab.
        
        Args:
            refresh: Ob die Event-Liste aktualisiert werden soll (Standard: False)
            
        Returns:
            Eine Liste von Event-Typen
        """
        if self._available_events is None or refresh:
            events = await self.api.get_events()
            if isinstance(events, list):
                self._available_events = [event["event"] for event in events if "event" in event]
            else:
                # Fallback für den Fall, dass die API ein Fehler-Dictionary zurückgibt
                self._available_events = []
                logger.error(f"Fehler beim Abrufen der Events: {events}")
        
        return self._available_events
    
    async def fire_event(self, event_type: str, event_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Löst ein Event aus.
        
        Args:
            event_type: Der Typ des auszulösenden Events
            event_data: Optionale Daten, die mit dem Event gesendet werden sollen
            
        Returns:
            Die API-Antwort
        """
        return await self.api.fire_event(event_type, event_data or {})
    
    async def fire_state_changed_event(self, entity_id: str, 
                                      new_state: str, 
                                      old_state: Optional[str] = None, 
                                      attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Löst ein state_changed Event aus.
        
        Args:
            entity_id: Die ID der Entität, deren Zustand sich geändert hat
            new_state: Der neue Zustand der Entität
            old_state: Der vorherige Zustand der Entität (optional)
            attributes: Optionale Attribute für den neuen Zustand
            
        Returns:
            Die API-Antwort
        """
        # Hole den aktuellen Zustand, wenn old_state nicht angegeben ist
        if old_state is None:
            current_entity = await self.api.get_state(entity_id)
            if current_entity and "state" in current_entity:
                old_state = current_entity["state"]
            else:
                old_state = "unknown"
        
        # Bereite die Event-Daten vor
        event_data = {
            "entity_id": entity_id,
            "old_state": {
                "entity_id": entity_id,
                "state": old_state,
                "attributes": attributes or {},
                "last_changed": "2022-01-01T00:00:00.000000+00:00"
            },
            "new_state": {
                "entity_id": entity_id,
                "state": new_state,
                "attributes": attributes or {},
                "last_changed": "2022-01-01T00:00:01.000000+00:00"
            }
        }
        
        # Löse das Event aus
        return await self.fire_event("state_changed", event_data)
    
    async def get_logbook_entries(self, 
                                 entity_id: Optional[str] = None, 
                                 hours: int = 24) -> List[Dict[str, Any]]:
        """
        Ruft Logbuch-Einträge ab.
        
        Args:
            entity_id: Optionale ID der Entität, für die Einträge abgerufen werden sollen
            hours: Anzahl der Stunden in der Vergangenheit (Standard: 24)
            
        Returns:
            Eine Liste von Logbuch-Einträgen
        """
        from datetime import datetime, timedelta
        
        # Berechne den Zeitpunkt für den Beginn der Abfrage
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Formatiere das Datum im ISO-Format, das Home Assistant erwartet
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        
        # Rufe die Logbuch-Einträge ab
        entries = await self.api.get_logbook(start_time_str, entity_id)
        
        return entries
    
    async def process_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verarbeitet Event-Daten und bereitet sie für die Anzeige auf.
        
        Args:
            event_data: Die zu verarbeitenden Event-Daten
            
        Returns:
            Aufbereitete Event-Daten
        """
        # Extrahiere wichtige Informationen aus den Event-Daten
        event_type = event_data.get("event_type", "unknown")
        entity_id = event_data.get("entity_id", None)
        
        # Für state_changed Events besondere Aufbereitung
        if event_type == "state_changed":
            old_state = event_data.get("old_state", {}).get("state", "unknown")
            new_state = event_data.get("new_state", {}).get("state", "unknown")
            
            # Füge eine menschenlesbare Beschreibung hinzu
            if entity_id:
                # Hole den freundlichen Namen der Entität, falls verfügbar
                entity = await self.api.get_state(entity_id)
                friendly_name = entity.get("attributes", {}).get("friendly_name", entity_id)
                
                description = f"{friendly_name} hat den Zustand von {old_state} auf {new_state} geändert"
            else:
                description = f"Zustandsänderung von {old_state} auf {new_state}"
                
            return {
                "event_type": event_type,
                "entity_id": entity_id,
                "friendly_name": friendly_name if entity_id else None,
                "old_state": old_state,
                "new_state": new_state,
                "description": description,
                "raw_data": event_data
            }
        
        # Für andere Event-Typen
        return {
            "event_type": event_type,
            "entity_id": entity_id,
            "description": f"Event vom Typ {event_type} empfangen",
            "raw_data": event_data
        }
    
    async def analyze_logbook(self, 
                             hours: int = 24, 
                             entity_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Analysiert Logbuch-Einträge und liefert Statistiken.
        
        Args:
            hours: Anzahl der Stunden, die analysiert werden sollen
            entity_id: Optionale ID einer spezifischen Entität
            
        Returns:
            Eine Zusammenfassung der Analyse
        """
        entries = await self.get_logbook_entries(entity_id, hours)
        
        # Statistiken sammeln
        total_entries = len(entries)
        entries_by_domain = {}
        entries_by_entity = {}
        entries_by_hour = {}
        
        from datetime import datetime
        
        for entry in entries:
            # Zähle Einträge nach Domain
            if "entity_id" in entry:
                domain = entry["entity_id"].split(".", 1)[0]
                if domain in entries_by_domain:
                    entries_by_domain[domain] += 1
                else:
                    entries_by_domain[domain] = 1
                    
                # Zähle Einträge nach Entität
                entity_id = entry["entity_id"]
                if entity_id in entries_by_entity:
                    entries_by_entity[entity_id] += 1
                else:
                    entries_by_entity[entity_id] = 1
            
            # Zähle Einträge nach Stunde
            if "when" in entry:
                try:
                    when = datetime.fromisoformat(entry["when"].replace("Z", "+00:00"))
                    hour = when.hour
                    if hour in entries_by_hour:
                        entries_by_hour[hour] += 1
                    else:
                        entries_by_hour[hour] = 1
                except (ValueError, TypeError):
                    # Ignoriere Datumsfehler
                    pass
        
        # Sortiere die Ergebnisse
        sorted_domains = sorted(entries_by_domain.items(), key=lambda x: x[1], reverse=True)
        sorted_entities = sorted(entries_by_entity.items(), key=lambda x: x[1], reverse=True)
        
        # Stelle sicher, dass alle Stunden repräsentiert sind
        for h in range(24):
            if h not in entries_by_hour:
                entries_by_hour[h] = 0
        
        # Erstelle die Zusammenfassung
        summary = {
            "total_entries": total_entries,
            "period_hours": hours,
            "entries_per_hour": total_entries / hours if hours > 0 else 0,
            "domains": dict(sorted_domains),
            "top_entities": dict(sorted_entities[:10]),  # Top 10 Entitäten
            "hourly_distribution": dict(sorted(entries_by_hour.items())),
            "busiest_hour": max(entries_by_hour.items(), key=lambda x: x[1]) if entries_by_hour else None
        }
        
        return summary
    
    async def render_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Rendert ein Home Assistant Template.
        
        Args:
            template: Das zu rendernde Template
            variables: Optionale Variablen für das Template
            
        Returns:
            Das gerenderte Template
        """
        return await self.api.render_template(template, variables or {})
    
    async def handle_intent(self, text: str, slot_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Verarbeitet eine Intent-Anfrage.
        
        Args:
            text: Der zu verarbeitende Text
            slot_data: Optionale Slot-Daten für den Intent
            
        Returns:
            Die Intent-Antwort
        """
        return await self.api.handle_intent(text, slot_data or {})

# Singleton-Instanz
_instance = None

async def get_event_manager(api_client: Optional[HomeAssistantAPI] = None) -> EventManager:
    """
    Gibt eine Singleton-Instanz des EventManagers zurück.
    Erstellt eine neue Instanz, wenn noch keine existiert.
    
    Args:
        api_client: Optional ein API-Client, der verwendet werden soll
        
    Returns:
        Eine EventManager-Instanz
    """
    global _instance
    
    if _instance is None:
        if api_client is None:
            # Erstelle einen neuen API-Client, wenn keiner angegeben wurde
            from app.api.client import get_api_client
            api_client = await get_api_client()
            
        _instance = EventManager(api_client)
        
    return _instance
