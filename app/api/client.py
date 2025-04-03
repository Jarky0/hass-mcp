import httpx
from typing import Dict, Any, Optional, List, Union
import logging
import json
import os
import functools
import inspect
from app.core.utils import SimpleCache

# Konfiguration
from app.core.config import HA_URL, HA_TOKEN, get_ha_headers

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HomeAssistantAPI:
    """
    Home Assistant API-Client zur Kommunikation mit der Home Assistant REST API
    """
    def __init__(self):
        self.base_url = HA_URL
        self.headers = get_ha_headers()
        self.client = None
        
        # Caches für verschiedene Datentypen
        self.entity_cache = SimpleCache(ttl_seconds=5)  # Kurze TTL für Entitätszustände
        self.config_cache = SimpleCache(ttl_seconds=60) # Längere TTL für Konfigurationen
    
    async def setup(self):
        """Initialisiert die HTTP-Session"""
        if self.client is None:
            logger.debug("Creating new HTTP client")
            self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """Schließt die HTTP-Session"""
        if self.client:
            logger.debug("Closing HTTP client")
            await self.client.aclose()
            self.client = None
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Allgemeine Methode für API-Anfragen
        
        Args:
            method: HTTP-Methode (GET, POST, etc.)
            endpoint: API-Endpunkt (relativ zur Basis-URL)
            data: Optional zu sendende Daten
            
        Returns:
            Antwort des API-Endpunkts als Dict/List oder Error-Dict
        """
        if not self.client:
            await self.setup()
        
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        try:
            if not HA_TOKEN:
                return {"error": "No Home Assistant token provided. Please set HA_TOKEN in .env file."}
            
            if method.upper() == "GET":
                response = await self.client.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, headers=self.headers)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {"error": f"Connection error: Cannot connect to Home Assistant at {self.base_url}"}
        except httpx.TimeoutException:
            return {"error": f"Timeout error: Home Assistant at {self.base_url} did not respond in time"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code} - {e.response.reason_phrase}"}
        except httpx.RequestError as e:
            return {"error": f"Error connecting to Home Assistant: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    async def get_states(self) -> List[Dict[str, Any]]:
        """Ruft alle Zustände von Home Assistant ab"""
        return await self._request("GET", "states")
    
    async def get_state(self, entity_id: str) -> Dict[str, Any]:
        """Ruft den Zustand einer bestimmten Entität ab"""
        return await self._request("GET", f"states/{entity_id}")
    
    async def set_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Setzt den Zustand einer Entität"""
        data = {"state": state}
        if attributes:
            data["attributes"] = attributes
        return await self._request("POST", f"states/{entity_id}", data)
    
    async def call_service(self, domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ruft einen Home Assistant Service auf"""
        return await self._request("POST", f"services/{domain}/{service}", data or {})
    
    async def get_config(self) -> Dict[str, Any]:
        """Ruft die Home Assistant Konfiguration ab"""
        cache_key = "config"
        cached = self.config_cache.get(cache_key)
        if cached:
            return cached
        
        result = await self._request("GET", "config")
        if "error" not in result:
            self.config_cache.set(cache_key, result)
        return result
    
    async def get_events(self) -> List[Dict[str, Any]]:
        """Ruft verfügbare Events ab"""
        return await self._request("GET", "events")
    
    async def get_services(self) -> Dict[str, Dict[str, Any]]:
        """Ruft verfügbare Services ab"""
        return await self._request("GET", "services")
    
    async def get_history(self, timestamp: Optional[str] = None, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Ruft Verlaufsdaten ab"""
        endpoint = "history/period"
        if timestamp:
            endpoint += f"/{timestamp}"
        if entity_id:
            endpoint += f"?filter_entity_id={entity_id}"
        return await self._request("GET", endpoint)
    
    async def get_logbook(self, timestamp: Optional[str] = None, entity_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Ruft Logbuch-Einträge ab"""
        endpoint = "logbook"
        if timestamp:
            endpoint += f"/{timestamp}"
        if entity_id:
            endpoint += f"?entity_id={entity_id}"
        return await self._request("GET", endpoint)
    
    async def render_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Rendert ein Home Assistant Template"""
        data = {"template": template}
        if variables:
            data["variables"] = variables
        return await self._request("POST", "template", data)
    
    async def check_config(self) -> Dict[str, Any]:
        """Überprüft die Home Assistant Konfiguration"""
        return await self._request("POST", "config/core/check_config")
    
    async def restart(self) -> Dict[str, Any]:
        """Startet Home Assistant neu"""
        return await self._request("POST", "services/homeassistant/restart")
    
    async def reload_core_config(self) -> Dict[str, Any]:
        """Lädt die Core-Konfiguration neu"""
        return await self._request("POST", "services/homeassistant/reload_core_config")
    
    async def reload_automation(self) -> Dict[str, Any]:
        """Lädt Automatisierungen neu"""
        return await self._request("POST", "services/automation/reload")
