"""
Automatisierungslogik für Home Assistant

Dieses Modul bietet Funktionen zur Verwaltung von Home Assistant Automatisierungen,
einschließlich Erstellung, Aktualisierung, Aktivierung und Deaktivierung.
"""
import logging
import json
from typing import Dict, List, Any, Optional, Union

from app.api.client import HomeAssistantAPI
from app.core.utils import filter_dict, group_by

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AutomationManager:
    """
    Verwaltet Automatisierungen in Home Assistant und bietet hilfreiche
    Methoden zur Interaktion mit ihnen.
    """
    
    def __init__(self, api_client: HomeAssistantAPI):
        """
        Initialisiert den AutomationManager.
        
        Args:
            api_client: Eine Instanz des Home Assistant API-Clients
        """
        self.api = api_client
        self._automation_cache = {}
    
    async def get_all_automations(self, use_cache: bool = False) -> List[Dict[str, Any]]:
        """
        Ruft alle Automatisierungen ab.
        
        Args:
            use_cache: Ob der Cache verwendet werden soll (Standard: False)
            
        Returns:
            Eine Liste von Automatisierungs-Dictionaries
        """
        if use_cache and self._automation_cache:
            return list(self._automation_cache.values())
        
        # Hol alle Automatisierungen über die API
        automations = await self.api.get_entities_by_domain("automation")
        
        # Aktualisiere den Cache
        for automation in automations:
            if "entity_id" in automation:
                self._automation_cache[automation["entity_id"]] = automation
        
        return automations
    
    async def get_automation(self, automation_id: str, use_cache: bool = False) -> Dict[str, Any]:
        """
        Ruft eine bestimmte Automatisierung ab.
        
        Args:
            automation_id: Die ID der Automatisierung (kann entity_id oder object_id sein)
            use_cache: Ob der Cache verwendet werden soll (Standard: False)
            
        Returns:
            Ein Dictionary mit den Automatisierungsdaten
        """
        # Füge "automation." Präfix hinzu, wenn notwendig
        entity_id = automation_id if automation_id.startswith("automation.") else f"automation.{automation_id}"
        
        if use_cache and entity_id in self._automation_cache:
            return self._automation_cache[entity_id]
        
        # Hol die Automatisierung über die API
        automation = await self.api.get_state(entity_id)
        
        if automation and "entity_id" in automation:
            self._automation_cache[entity_id] = automation
            
        return automation
    
    async def create_automation(self, 
                               object_id: str, 
                               alias: str,
                               trigger: Union[Dict[str, Any], List[Dict[str, Any]]],
                               action: Union[Dict[str, Any], List[Dict[str, Any]]],
                               condition: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
                               mode: str = "single",
                               description: Optional[str] = None) -> Dict[str, Any]:
        """
        Erstellt eine neue Automatisierung.
        
        Args:
            object_id: Die ID der Automatisierung (ohne "automation." Präfix)
            alias: Der Anzeigename der Automatisierung
            trigger: Der Auslöser (Trigger) der Automatisierung
            action: Die auszuführende Aktion
            condition: Optionale Bedingung für die Ausführung
            mode: Ausführungsmodus (single, parallel, queued, restart)
            description: Optionale Beschreibung der Automatisierung
            
        Returns:
            Die API-Antwort
        """
        # Prüfe, ob die Automation bereits existiert
        entity_id = f"automation.{object_id}"
        existing_automation = await self.api.get_state(entity_id)
        
        if existing_automation and "entity_id" in existing_automation:
            return {"error": f"Automatisierung {entity_id} existiert bereits. Verwende update_automation."}
        
        # Erstelle die Konfigurationsdaten
        config_data = {
            "alias": alias,
            "trigger": trigger if isinstance(trigger, list) else [trigger],
            "action": action if isinstance(action, list) else [action],
            "mode": mode
        }
        
        if condition:
            config_data["condition"] = condition if isinstance(condition, list) else [condition]
            
        if description:
            config_data["description"] = description
        
        # Verwende die configure_component Funktion
        result = await self.api.configure_component("automation", object_id, config_data)
        
        # Wenn erfolgreich, aktualisiere den Cache
        if result.get("success", False):
            # Kurze Verzögerung für die API
            import asyncio
            await asyncio.sleep(0.5)
            
            # Hole die aktualisierte Automatisierung
            updated_automation = await self.api.get_state(entity_id)
            if updated_automation and "entity_id" in updated_automation:
                self._automation_cache[entity_id] = updated_automation
        
        return result
    
    async def update_automation(self, 
                               object_id: str, 
                               config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aktualisiert eine bestehende Automatisierung.
        
        Args:
            object_id: Die ID der Automatisierung (ohne "automation." Präfix)
            config_data: Die neue Konfiguration
            
        Returns:
            Die API-Antwort
        """
        # Prüfe, ob die Automation existiert
        entity_id = f"automation.{object_id}"
        existing_automation = await self.api.get_state(entity_id)
        
        if not existing_automation or "entity_id" not in existing_automation:
            return {"error": f"Automatisierung {entity_id} existiert nicht. Verwende create_automation."}
        
        # Verwende die configure_component Funktion mit update=True
        result = await self.api.configure_component("automation", object_id, config_data, update=True)
        
        # Wenn erfolgreich, aktualisiere den Cache
        if result.get("success", False):
            # Kurze Verzögerung für die API
            import asyncio
            await asyncio.sleep(0.5)
            
            # Hole die aktualisierte Automatisierung
            updated_automation = await self.api.get_state(entity_id)
            if updated_automation and "entity_id" in updated_automation:
                self._automation_cache[entity_id] = updated_automation
        
        return result
    
    async def delete_automation(self, object_id: str) -> Dict[str, Any]:
        """
        Löscht eine Automatisierung.
        
        Args:
            object_id: Die ID der Automatisierung (ohne "automation." Präfix)
            
        Returns:
            Die API-Antwort
        """
        entity_id = f"automation.{object_id}"
        
        # Verwende die delete_component Funktion
        result = await self.api.delete_component("automation", object_id)
        
        # Wenn erfolgreich, entferne aus dem Cache
        if result.get("success", False) and entity_id in self._automation_cache:
            del self._automation_cache[entity_id]
        
        return result
    
    async def toggle_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Schaltet eine Automatisierung ein oder aus.
        
        Args:
            automation_id: Die ID der Automatisierung (kann entity_id oder object_id sein)
            
        Returns:
            Die API-Antwort
        """
        # Füge "automation." Präfix hinzu, wenn notwendig
        entity_id = automation_id if automation_id.startswith("automation.") else f"automation.{automation_id}"
        
        # Rufe den Service auf
        result = await self.api.call_service("automation", "toggle", {"entity_id": entity_id})
        
        # Aktualisiere den Cache
        if result.get("success", False):
            # Kurze Verzögerung für die API
            import asyncio
            await asyncio.sleep(0.5)
            
            # Hole die aktualisierte Automatisierung
            updated_automation = await self.api.get_state(entity_id)
            if updated_automation and "entity_id" in updated_automation:
                self._automation_cache[entity_id] = updated_automation
        
        return result
    
    async def trigger_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Löst eine Automatisierung manuell aus.
        
        Args:
            automation_id: Die ID der Automatisierung (kann entity_id oder object_id sein)
            
        Returns:
            Die API-Antwort
        """
        # Füge "automation." Präfix hinzu, wenn notwendig
        entity_id = automation_id if automation_id.startswith("automation.") else f"automation.{automation_id}"
        
        # Rufe den Service auf
        return await self.api.call_service("automation", "trigger", {"entity_id": entity_id})
    
    async def reload_automations(self) -> Dict[str, Any]:
        """
        Lädt alle Automatisierungen neu.
        
        Returns:
            Die API-Antwort
        """
        # Leere den Cache
        self._automation_cache = {}
        
        # Rufe den Service auf
        return await self.api.call_service("automation", "reload", {})
    
    async def analyze_automations(self) -> Dict[str, Any]:
        """
        Analysiert alle Automatisierungen und liefert Statistiken.
        
        Returns:
            Ein Dictionary mit Statistiken
        """
        automations = await self.get_all_automations()
        
        # Zähle Automatisierungen nach Status
        status_counts = {"on": 0, "off": 0, "unavailable": 0, "other": 0}
        triggers_by_type = {}
        action_types = {}
        domain_counts = {}
        
        for automation in automations:
            # Zähle Status
            state = automation.get("state", "other")
            if state in status_counts:
                status_counts[state] += 1
            else:
                status_counts["other"] += 1
            
            # Analysiere Attribute, wenn vorhanden
            attributes = automation.get("attributes", {})
            
            # Analysiere Trigger
            triggers = attributes.get("trigger", [])
            if not isinstance(triggers, list):
                triggers = [triggers]
                
            for trigger in triggers:
                trigger_type = trigger.get("platform", "unknown")
                if trigger_type in triggers_by_type:
                    triggers_by_type[trigger_type] += 1
                else:
                    triggers_by_type[trigger_type] = 1
            
            # Analysiere Aktionen
            actions = attributes.get("action", [])
            if not isinstance(actions, list):
                actions = [actions]
                
            for action in actions:
                # Extrahiere Service-Domain
                service = action.get("service", "")
                if "." in service:
                    domain = service.split(".", 1)[0]
                    if domain in domain_counts:
                        domain_counts[domain] += 1
                    else:
                        domain_counts[domain] = 1
                
                # Zähle Aktionstypen
                if "service" in action:
                    action_type = "service"
                elif "data_template" in action:
                    action_type = "template"
                elif "condition" in action:
                    action_type = "condition"
                elif "delay" in action:
                    action_type = "delay"
                elif "event" in action:
                    action_type = "event"
                elif "wait_template" in action:
                    action_type = "wait"
                elif "scene" in action:
                    action_type = "scene"
                else:
                    action_type = "other"
                
                if action_type in action_types:
                    action_types[action_type] += 1
                else:
                    action_types[action_type] = 1
        
        # Erstelle die Zusammenfassung
        summary = {
            "total_count": len(automations),
            "status_distribution": status_counts,
            "trigger_types": dict(sorted(triggers_by_type.items(), key=lambda x: x[1], reverse=True)),
            "action_types": dict(sorted(action_types.items(), key=lambda x: x[1], reverse=True)),
            "domains_used": dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)),
            "examples": {
                "on": [a for a in automations if a.get("state") == "on"][:3],
                "off": [a for a in automations if a.get("state") == "off"][:3]
            }
        }
        
        return summary

# Singleton-Instanz
_instance = None

async def get_automation_manager(api_client: Optional[HomeAssistantAPI] = None) -> AutomationManager:
    """
    Gibt eine Singleton-Instanz des AutomationManagers zurück.
    Erstellt eine neue Instanz, wenn noch keine existiert.
    
    Args:
        api_client: Optional ein API-Client, der verwendet werden soll
        
    Returns:
        Eine AutomationManager-Instanz
    """
    global _instance
    
    if _instance is None:
        if api_client is None:
            # Erstelle einen neuen API-Client, wenn keiner angegeben wurde
            from app.api.client import get_api_client
            api_client = await get_api_client()
            
        _instance = AutomationManager(api_client)
        
    return _instance
