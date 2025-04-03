"""
Entitätenverwaltung für Home Assistant

Dieses Modul bietet Funktionen zum Verwalten von Home Assistant Entitäten,
einschließlich Statusabfragen, Filterung und Gruppierung.
"""
import logging
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
import re

from app.api.client import HomeAssistantAPI
from app.core.utils import filter_dict, group_by

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EntityManager:
    """
    Verwaltet Entitäten in Home Assistant und bietet hilfreiche
    Methoden zur Interaktion mit ihnen.
    """
    
    def __init__(self, api_client: HomeAssistantAPI):
        """
        Initialisiert den EntityManager.
        
        Args:
            api_client: Eine Instanz des Home Assistant API-Clients
        """
        self.api = api_client
        self._entity_cache = {}
        self._last_update = None
        self._domain_mapping = {}
    
    async def get_entity(self, entity_id: str, use_cache: bool = False) -> Dict[str, Any]:
        """
        Ruft eine bestimmte Entität ab.
        
        Args:
            entity_id: Die ID der abzurufenden Entität (z.B. 'light.living_room')
            use_cache: Ob der Cache verwendet werden soll (Standard: False)
            
        Returns:
            Ein Dictionary mit den Entitätsdaten
        """
        if use_cache and entity_id in self._entity_cache:
            return self._entity_cache[entity_id]
        
        entity = await self.api.get_state(entity_id)
        
        if entity and "entity_id" in entity:
            self._entity_cache[entity_id] = entity
            
        return entity
    
    async def get_entities(self, 
                          domain: Optional[str] = None, 
                          area: Optional[str] = None,
                          state: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ruft Entitäten mit optionaler Filterung ab.
        
        Args:
            domain: Optionaler Domain-Filter (z.B. 'light', 'switch', 'sensor')
            area: Optionaler Bereichsfilter (z.B. 'Wohnzimmer', 'Küche')
            state: Optionaler Statusfilter (z.B. 'on', 'off')
            
        Returns:
            Eine Liste von Entitäts-Dictionaries
        """
        entities = await self.api.get_states()
        
        if domain:
            entities = [e for e in entities if e["entity_id"].split(".", 1)[0] == domain]
            
        if area:
            area_lower = area.lower()
            entities = [e for e in entities if 
                        "attributes" in e and 
                        "friendly_name" in e["attributes"] and 
                        area_lower in e["attributes"]["friendly_name"].lower()]
            
        if state:
            entities = [e for e in entities if e["state"] == state]
            
        # Aktualisiere den Cache
        for entity in entities:
            if "entity_id" in entity:
                self._entity_cache[entity["entity_id"]] = entity
                
        return entities
    
    async def search_entities(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Sucht nach Entitäten, die der Abfrage entsprechen.
        
        Args:
            query: Die Suchabfrage
            limit: Maximale Anzahl der Ergebnisse
            
        Returns:
            Eine Liste von übereinstimmenden Entitäten
        """
        entities = await self.api.get_states()
        query_lower = query.lower()
        
        matches = []
        for entity in entities:
            entity_id = entity["entity_id"].lower()
            friendly_name = entity.get("attributes", {}).get("friendly_name", "").lower()
            
            score = 0
            # Genaue Übereinstimmung mit Entity-ID
            if query_lower in entity_id:
                score += 3
                if entity_id.startswith(query_lower):
                    score += 2
                    
            # Übereinstimmung mit friendly_name
            if query_lower in friendly_name:
                score += 2
                if friendly_name.startswith(query_lower):
                    score += 2
                    
            # Übereinstimmung mit Attributen
            for attr_name, attr_value in entity.get("attributes", {}).items():
                if isinstance(attr_value, str) and query_lower in attr_value.lower():
                    score += 1
            
            if score > 0:
                matches.append((entity, score))
        
        # Sortiere nach Score in absteigender Reihenfolge
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Begrenze die Anzahl der Ergebnisse
        return [item[0] for item in matches[:limit]]
    
    async def get_domains(self) -> List[str]:
        """
        Ruft alle verfügbaren Domains ab.
        
        Returns:
            Eine Liste aller verfügbaren Domains
        """
        entities = await self.api.get_states()
        domains = set()
        
        for entity in entities:
            if "entity_id" in entity:
                domain = entity["entity_id"].split(".", 1)[0]
                domains.add(domain)
                
        return sorted(list(domains))
    
    async def get_domain_statistics(self, domain: str) -> Dict[str, Any]:
        """
        Liefert Statistiken für eine bestimmte Domain.
        
        Args:
            domain: Die zu analysierende Domain (z.B. 'light', 'switch')
            
        Returns:
            Ein Dictionary mit Statistiken (Anzahl, Zustände, Beispiele)
        """
        entities = await self.get_entities(domain=domain)
        
        if not entities:
            return {
                "domain": domain,
                "count": 0,
                "states": {},
                "examples": {},
                "attributes": []
            }
        
        # Zähle Zustände
        state_counts = {}
        for entity in entities:
            state = entity["state"]
            if state in state_counts:
                state_counts[state] += 1
            else:
                state_counts[state] = 1
        
        # Gruppiere nach Zuständen für Beispiele
        entities_by_state = {}
        for entity in entities:
            state = entity["state"]
            if state not in entities_by_state:
                entities_by_state[state] = []
            
            lean_entity = {
                "entity_id": entity["entity_id"],
                "state": state
            }
            
            # Füge friendly_name hinzu, falls vorhanden
            if "attributes" in entity and "friendly_name" in entity["attributes"]:
                if "attributes" not in lean_entity:
                    lean_entity["attributes"] = {}
                lean_entity["friendly_name"] = entity["attributes"]["friendly_name"]
                
            entities_by_state[state].append(lean_entity)
        
        # Sammle bis zu 3 Beispiele für jeden Zustand
        examples = {}
        for state, state_entities in entities_by_state.items():
            examples[state] = state_entities[:3]
        
        # Sammle häufige Attribute
        attribute_counts = {}
        for entity in entities:
            if "attributes" in entity:
                for attr in entity["attributes"]:
                    if attr in attribute_counts:
                        attribute_counts[attr] += 1
                    else:
                        attribute_counts[attr] = 1
        
        # Sortiere Attribute nach Häufigkeit
        sorted_attributes = sorted(
            [(attr, count) for attr, count in attribute_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "domain": domain,
            "count": len(entities),
            "states": state_counts,
            "examples": examples,
            "attributes": sorted_attributes[:10]  # Top 10 Attribute
        }
    
    async def control_entity(self, entity_id: str, action: str, **kwargs) -> Dict[str, Any]:
        """
        Steuert eine Entität.
        
        Args:
            entity_id: Die ID der zu steuernden Entität
            action: Die auszuführende Aktion ('on', 'off', 'toggle', etc.)
            **kwargs: Zusätzliche Parameter für den Service-Aufruf
            
        Returns:
            Das Ergebnis des Service-Aufrufs
        """
        domain = entity_id.split(".", 1)[0]
        
        # Mapping von Aktionen zu Services
        action_map = {
            "on": "turn_on",
            "off": "turn_off",
            "toggle": "toggle",
            "open": "open_cover",
            "close": "close_cover",
            "stop": "stop_cover"
        }
        
        # Domain-spezifische Service-Anpassungen
        domain_services = {
            "cover": {
                "on": "open_cover",
                "off": "close_cover"
            },
            "vacuum": {
                "on": "start",
                "off": "return_to_base"
            }
        }
        
        # Bestimme den zu verwendenden Service
        if domain in domain_services and action in domain_services[domain]:
            service = domain_services[domain][action]
        elif action in action_map:
            service = action_map[action]
        else:
            # Verwende die Aktion direkt als Service, wenn keine Zuordnung gefunden wurde
            service = action
        
        # Füge entity_id zu den Kwargs hinzu
        service_data = {"entity_id": entity_id, **kwargs}
        
        # Rufe den Service auf
        result = await self.api.call_service(domain, service, service_data)
        
        # Aktualisiere den Cache, wenn der Aufruf erfolgreich war
        if isinstance(result, dict) and result.get("success", False):
            await asyncio.sleep(0.5)  # Kurze Verzögerung, um die Aktualisierung des Zustands zu ermöglichen
            updated_entity = await self.api.get_state(entity_id)
            if updated_entity and "entity_id" in updated_entity:
                self._entity_cache[entity_id] = updated_entity
        
        return result
    
    async def get_state_history(self, entity_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Ruft den Verlauf des Zustands einer Entität ab.
        
        Args:
            entity_id: Die ID der Entität
            hours: Anzahl der Stunden in der Vergangenheit (Standard: 24)
            
        Returns:
            Eine Liste von Zustandsänderungen
        """
        # Diese Funktion verwendet die History-API von Home Assistant
        history = await self.api.get_history(entity_id, hours)
        return history

# Singleton-Instanz
_instance = None

async def get_entity_manager(api_client: Optional[HomeAssistantAPI] = None) -> EntityManager:
    """
    Gibt eine Singleton-Instanz des EntityManagers zurück.
    Erstellt eine neue Instanz, wenn noch keine existiert.
    
    Args:
        api_client: Optional ein API-Client, der verwendet werden soll
        
    Returns:
        Eine EntityManager-Instanz
    """
    global _instance
    
    if _instance is None:
        if api_client is None:
            # Erstelle einen neuen API-Client, wenn keiner angegeben wurde
            from app.api.client import get_api_client
            api_client = await get_api_client()
            
        _instance = EntityManager(api_client)
        
    return _instance
