import httpx
from typing import Dict, Any, Optional, List, TypeVar, Callable, Awaitable, Union, cast
import functools
import inspect
import logging
import json
import os

from app.config import HA_URL, HA_TOKEN, get_ha_headers

# Type variable for generic functions
F = TypeVar('F', bound=Callable[..., Any])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a generic type for our API function return values
T = TypeVar('T')

# HTTP client
_client: Optional[httpx.AsyncClient] = None

# Default field sets for different verbosity levels
# Lean fields for standard requests (optimized for token efficiency)
DEFAULT_LEAN_FIELDS = ["entity_id", "state", "attr.friendly_name"]

# Common fields that are typically needed for entity operations
DEFAULT_STANDARD_FIELDS = ["entity_id", "state", "attributes", "last_updated"]

# Domain-specific important attributes to include in lean responses
DOMAIN_IMPORTANT_ATTRIBUTES = {
    "light": ["brightness", "color_temp", "color_mode", "rgb_color"],
    "switch": ["device_class", "icon"],
    "binary_sensor": ["device_class", "is_on"],
    "sensor": ["unit_of_measurement", "device_class", "state_class"],
    "climate": ["temperature", "current_temperature", "hvac_mode", "hvac_action"],
    "cover": ["current_position", "current_tilt_position"],
    "media_player": ["media_title", "media_artist", "volume_level", "source"],
    "camera": ["entity_picture"],
}

# Einfaches Cache-System
class SimpleCache:
    """Einfaches In-Memory-Cache-System für API-Anfragen"""
    
    def __init__(self, ttl_seconds: int = 30):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        """Versuche, einen Wert aus dem Cache zu holen"""
        import time
        
        if key not in self.cache:
            return None
            
        timestamp, value = self.cache[key]
        current_time = time.time()
        
        # Prüfe, ob der Cache-Eintrag abgelaufen ist
        if current_time - timestamp > self.ttl_seconds:
            # Eintrag ist abgelaufen, entferne ihn
            del self.cache[key]
            return None
            
        return value
        
    def set(self, key: str, value: Any) -> None:
        """Speichere einen Wert im Cache"""
        import time
        
        self.cache[key] = (time.time(), value)
        
    def invalidate(self, key_prefix: str = None) -> None:
        """Invalidiere Cache-Einträge basierend auf einem Präfix"""
        if key_prefix is None:
            # Lösche den gesamten Cache
            self.cache.clear()
        else:
            # Lösche alle Einträge, die mit dem Präfix beginnen
            keys_to_delete = [k for k in self.cache.keys() if k.startswith(key_prefix)]
            for key in keys_to_delete:
                del self.cache[key]

# Initialisiere die Cache-Instanz
# Lange TTL für Konfigurationsdaten, kurze TTL für Zustandsdaten
entity_cache = SimpleCache(ttl_seconds=5)  # Kurze TTL für Entitätszustände
config_cache = SimpleCache(ttl_seconds=60) # Längere TTL für Konfigurationen

# Hilfsfunktion zum Erstellen eines Cache-Schlüssels
def make_cache_key(base_key: str, *args, **kwargs) -> str:
    """Erstelle einen eindeutigen Cache-Schlüssel basierend auf Funktion und Argumenten"""
    # Konvertiere args und kwargs in einen stabilen String
    args_str = '_'.join(str(a) for a in args)
    kwargs_str = '_'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    # Kombiniere alles zu einem eindeutigen Schlüssel
    return f"{base_key}_{args_str}_{kwargs_str}"

# Dekorator für cachable Funktionen
def cacheable(cache_instance, key_prefix: str, use_cache: bool = True):
    """Dekorator zum Cachen von Funktionsaufrufen"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extrahiere den cache-Parameter, wenn vorhanden, sonst Standard
            should_use_cache = kwargs.pop('use_cache', use_cache)
            
            if not should_use_cache:
                # Cache überspringen, wenn explizit deaktiviert
                return await func(*args, **kwargs)
            
            # Erstelle einen Cache-Schlüssel
            cache_key = make_cache_key(key_prefix, *args, **kwargs)
            
            # Versuche, aus dem Cache zu holen
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__} - {cache_key}")
                return cached_result
            
            # Cache-Miss, rufe die Funktion auf
            logger.debug(f"Cache miss for {func.__name__} - {cache_key}")
            result = await func(*args, **kwargs)
            
            # Speichere das Ergebnis im Cache, außer bei Fehlern
            if isinstance(result, dict) and result.get('error'):
                # Fehler nicht cachen
                logger.debug(f"Not caching error result for {func.__name__}")
            else:
                cache_instance.set(cache_key, result)
            
            return result
        return wrapper
    return decorator

def handle_api_errors(func: F) -> F:
    """
    Decorator to handle common error cases for Home Assistant API calls
    
    Args:
        func: The async function to decorate
        
    Returns:
        Wrapped function that handles errors
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Determine return type from function annotation
        return_type = inspect.signature(func).return_annotation
        is_dict_return = 'Dict' in str(return_type)
        is_list_return = 'List' in str(return_type)
        
        # Prepare error formatters based on return type
        def format_error(msg: str) -> Any:
            if is_dict_return:
                return {"error": msg}
            elif is_list_return:
                return [{"error": msg}]
            else:
                return msg
        
        try:
            # Check if token is available
            if not HA_TOKEN:
                return format_error("No Home Assistant token provided. Please set HA_TOKEN in .env file.")
            
            # Call the original function
            return await func(*args, **kwargs)
        except httpx.ConnectError:
            return format_error(f"Connection error: Cannot connect to Home Assistant at {HA_URL}")
        except httpx.TimeoutException:
            return format_error(f"Timeout error: Home Assistant at {HA_URL} did not respond in time")
        except httpx.HTTPStatusError as e:
            return format_error(f"HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
        except httpx.RequestError as e:
            return format_error(f"Error connecting to Home Assistant: {str(e)}")
        except Exception as e:
            return format_error(f"Unexpected error: {str(e)}")
    
    return cast(F, wrapper)

# Persistent HTTP client
async def get_client() -> httpx.AsyncClient:
    """Get a persistent httpx client for Home Assistant API calls"""
    global _client
    if _client is None:
        logger.debug("Creating new HTTP client")
        _client = httpx.AsyncClient(timeout=10.0)
    return _client

async def cleanup_client() -> None:
    """Close the HTTP client when shutting down"""
    global _client
    if _client:
        logger.debug("Closing HTTP client")
        await _client.aclose()
        _client = None

# Direct entity retrieval function
async def get_all_entity_states() -> Dict[str, Dict[str, Any]]:
    """Fetch all entity states from Home Assistant"""
    client = await get_client()
    response = await client.get(f"{HA_URL}/api/states", headers=get_ha_headers())
    response.raise_for_status()
    entities = response.json()
    
    # Create a mapping for easier access
    return {entity["entity_id"]: entity for entity in entities}

def filter_fields(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Filter entity data to only include requested fields
    
    This function helps reduce token usage by returning only requested fields.
    
    Args:
        data: The complete entity data dictionary
        fields: List of fields to include in the result
               - "state": Include the entity state
               - "attributes": Include all attributes
               - "attr.X": Include only attribute X (e.g. "attr.brightness")
               - "context": Include context data
               - "last_updated"/"last_changed": Include timestamp fields
    
    Returns:
        A filtered dictionary with only the requested fields
    """
    if not fields:
        return data
        
    result = {"entity_id": data["entity_id"]}
    
    for field in fields:
        if field == "state":
            result["state"] = data.get("state")
        elif field == "attributes":
            result["attributes"] = data.get("attributes", {})
        elif field.startswith("attr.") and len(field) > 5:
            attr_name = field[5:]
            attributes = data.get("attributes", {})
            if attr_name in attributes:
                if "attributes" not in result:
                    result["attributes"] = {}
                result["attributes"][attr_name] = attributes[attr_name]
        elif field == "context":
            if "context" in data:
                result["context"] = data["context"]
        elif field in ["last_updated", "last_changed"]:
            if field in data:
                result[field] = data[field]
    
    return result

# API Functions
@handle_api_errors
@cacheable(config_cache, "get_hass_version")
async def get_hass_version() -> str:
    """Get the Home Assistant version from the API"""
    client = await get_client()
    response = await client.get(f"{HA_URL}/api/config", headers=get_ha_headers())
    response.raise_for_status()
    data = response.json()
    return data.get("version", "unknown")

@handle_api_errors
@cacheable(entity_cache, "get_entity_state")
async def get_entity_state(
    entity_id: str,
    fields: Optional[List[str]] = None,
    lean: bool = False,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Get the state of a Home Assistant entity
    
    Args:
        entity_id: The entity ID to get
        fields: Optional list of specific fields to include in the response
        lean: If True, returns a token-efficient version with minimal fields
              (overridden by fields parameter if provided)
        use_cache: Whether to use cached data if available
    
    Returns:
        Entity state dictionary, optionally filtered to include only specified fields
    """
    # Fetch directly
    client = await get_client()
    response = await client.get(
        f"{HA_URL}/api/states/{entity_id}", 
        headers=get_ha_headers()
    )
    response.raise_for_status()
    entity_data = response.json()
    
    # Apply field filtering if requested
    if fields:
        # User-specified fields take precedence
        return filter_fields(entity_data, fields)
    elif lean:
        # Build domain-specific lean fields
        lean_fields = DEFAULT_LEAN_FIELDS.copy()
        
        # Add domain-specific important attributes
        domain = entity_id.split('.')[0]
        if domain in DOMAIN_IMPORTANT_ATTRIBUTES:
            for attr in DOMAIN_IMPORTANT_ATTRIBUTES[domain]:
                lean_fields.append(f"attr.{attr}")
        
        return filter_fields(entity_data, lean_fields)
    else:
        # Return full entity data
        return entity_data

@handle_api_errors
@cacheable(entity_cache, "get_entities")
async def get_entities(
    domain: Optional[str] = None, 
    search_query: Optional[str] = None, 
    limit: int = 100,
    fields: Optional[List[str]] = None,
    lean: bool = True,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Get a list of all entities from Home Assistant with optional filtering and search
    
    Args:
        domain: Optional domain to filter entities by (e.g., 'light', 'switch')
        search_query: Optional case-insensitive search term to filter by entity_id, friendly_name or other attributes
        limit: Maximum number of entities to return (default: 100)
        fields: Optional list of specific fields to include in each entity
        lean: If True (default), returns token-efficient versions with minimal fields
        use_cache: Whether to use cached data if available
    
    Returns:
        List of entity dictionaries, optionally filtered by domain and search terms,
        and optionally limited to specific fields
    """
    # Get all entities directly
    client = await get_client()
    response = await client.get(f"{HA_URL}/api/states", headers=get_ha_headers())
    response.raise_for_status()
    entities = response.json()
    
    # Filter by domain if specified
    if domain:
        entities = [entity for entity in entities if entity["entity_id"].startswith(f"{domain}.")]
    
    # Search if query is provided
    if search_query and search_query.strip():
        search_term = search_query.lower().strip()
        filtered_entities = []
        
        for entity in entities:
            # Search in entity_id
            if search_term in entity["entity_id"].lower():
                filtered_entities.append(entity)
                continue
                
            # Search in friendly_name
            friendly_name = entity.get("attributes", {}).get("friendly_name", "").lower()
            if friendly_name and search_term in friendly_name:
                filtered_entities.append(entity)
                continue
                
            # Search in other common attributes (state, area_id, etc.)
            if search_term in entity.get("state", "").lower():
                filtered_entities.append(entity)
                continue
                
            # Search in other attributes
            for attr_name, attr_value in entity.get("attributes", {}).items():
                # Check if attribute value can be converted to string
                if isinstance(attr_value, (str, int, float, bool)):
                    if search_term in str(attr_value).lower():
                        filtered_entities.append(entity)
                        break
        
        entities = filtered_entities
    
    # Apply the limit
    if limit > 0 and len(entities) > limit:
        entities = entities[:limit]
    
    # Apply field filtering if requested
    if fields or lean:
        # Prepare the fields to include
        if fields:
            # User-specified fields
            include_fields = fields
        else:
            # Default lean fields
            include_fields = DEFAULT_LEAN_FIELDS.copy()
            
        # Filter each entity
        filtered_entities = []
        for entity in entities:
            # For domain-specific attributes in lean mode
            if lean and not fields:
                domain = entity["entity_id"].split('.')[0]
                if domain in DOMAIN_IMPORTANT_ATTRIBUTES:
                    # Add domain-specific fields for this entity
                    entity_fields = include_fields.copy()
                    for attr in DOMAIN_IMPORTANT_ATTRIBUTES[domain]:
                        entity_fields.append(f"attr.{attr}")
                    filtered_entities.append(filter_fields(entity, entity_fields))
                else:
                    # Use default lean fields
                    filtered_entities.append(filter_fields(entity, include_fields))
            else:
                # Use the same fields for all entities
                filtered_entities.append(filter_fields(entity, include_fields))
        
        return filtered_entities
    else:
        # Return full entity data
        return entities

@handle_api_errors
async def call_service(domain: str, service: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Call a Home Assistant service"""
    if data is None:
        data = {}
    
    client = await get_client()
    response = await client.post(
        f"{HA_URL}/api/services/{domain}/{service}", 
        headers=get_ha_headers(),
        json=data
    )
    response.raise_for_status()
    
    # Invalidate cache after service calls as they might change entity states
    global _entities_timestamp
    _entities_timestamp = 0
    
    return response.json()

@handle_api_errors
async def summarize_domain(domain: str, example_limit: int = 3) -> Dict[str, Any]:
    """
    Generate a summary of entities in a domain
    
    Args:
        domain: The domain to summarize (e.g., 'light', 'switch')
        example_limit: Maximum number of examples to include for each state
        
    Returns:
        Dictionary with summary information
    """
    entities = await get_entities(domain=domain)
    
    # Check if we got an error response
    if isinstance(entities, dict) and "error" in entities:
        return entities  # Just pass through the error
    
    try:
        # Initialize summary data
        total_count = len(entities)
        state_counts = {}
        state_examples = {}
        attributes_summary = {}
        
        # Process entities to build the summary
        for entity in entities:
            state = entity.get("state", "unknown")
            
            # Count states
            if state not in state_counts:
                state_counts[state] = 0
                state_examples[state] = []
            state_counts[state] += 1
            
            # Add examples (up to the limit)
            if len(state_examples[state]) < example_limit:
                example = {
                    "entity_id": entity["entity_id"],
                    "friendly_name": entity.get("attributes", {}).get("friendly_name", entity["entity_id"])
                }
                state_examples[state].append(example)
            
            # Collect attribute keys for summary
            for attr_key in entity.get("attributes", {}):
                if attr_key not in attributes_summary:
                    attributes_summary[attr_key] = 0
                attributes_summary[attr_key] += 1
        
        # Create the summary
        summary = {
            "domain": domain,
            "total_count": total_count,
            "state_distribution": state_counts,
            "examples": state_examples,
            "common_attributes": sorted(
                [(k, v) for k, v in attributes_summary.items()], 
                key=lambda x: x[1], 
                reverse=True
            )[:10]  # Top 10 most common attributes
        }
        
        return summary
    except Exception as e:
        return {"error": f"Error generating domain summary: {str(e)}"}

@handle_api_errors
async def get_automations() -> List[Dict[str, Any]]:
    """Get a list of all automations from Home Assistant"""
    # Reuse the get_entities function with domain filtering
    automation_entities = await get_entities(domain="automation")
    
    # Check if we got an error response
    if isinstance(automation_entities, dict) and "error" in automation_entities:
        return automation_entities  # Just pass through the error
    
    # Process automation entities
    result = []
    try:
        for entity in automation_entities:
            # Extract relevant information
            automation_info = {
                "id": entity["entity_id"].split(".")[1],
                "entity_id": entity["entity_id"],
                "state": entity["state"],
                "alias": entity["attributes"].get("friendly_name", entity["entity_id"]),
            }
            
            # Add any additional attributes that might be useful
            if "last_triggered" in entity["attributes"]:
                automation_info["last_triggered"] = entity["attributes"]["last_triggered"]
            
            result.append(automation_info)
    except (TypeError, KeyError) as e:
        # Handle errors in processing the entities
        return {"error": f"Error processing automation entities: {str(e)}"}
        
    return result

@handle_api_errors
async def reload_automations() -> Dict[str, Any]:
    """Reload all automations in Home Assistant"""
    return await call_service("automation", "reload", {})

@handle_api_errors
async def restart_home_assistant() -> Dict[str, Any]:
    """Restart Home Assistant"""
    return await call_service("homeassistant", "restart", {})

@handle_api_errors
async def get_hass_error_log() -> Dict[str, Any]:
    """
    Get the Home Assistant error log for troubleshooting
    
    Returns:
        A dictionary containing:
        - log_text: The full error log text
        - error_count: Number of ERROR entries found
        - warning_count: Number of WARNING entries found
        - integration_mentions: Map of integration names to mention counts
        - error: Error message if retrieval failed
    """
    try:
        # Call the Home Assistant API error_log endpoint
        url = f"{HA_URL}/api/error_log"
        headers = get_ha_headers()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                log_text = response.text
                
                # Count errors and warnings
                error_count = log_text.count("ERROR")
                warning_count = log_text.count("WARNING")
                
                # Extract integration mentions
                import re
                integration_mentions = {}
                
                # Look for patterns like [mqtt], [zwave], etc.
                for match in re.finditer(r'\[([a-zA-Z0-9_]+)\]', log_text):
                    integration = match.group(1).lower()
                    if integration not in integration_mentions:
                        integration_mentions[integration] = 0
                    integration_mentions[integration] += 1
                
                return {
                    "log_text": log_text,
                    "error_count": error_count,
                    "warning_count": warning_count,
                    "integration_mentions": integration_mentions
                }
            else:
                return {
                    "error": f"Error retrieving error log: {response.status_code} {response.reason_phrase}",
                    "details": response.text,
                    "log_text": "",
                    "error_count": 0,
                    "warning_count": 0,
                    "integration_mentions": {}
                }
    except Exception as e:
        logger.error(f"Error retrieving Home Assistant error log: {str(e)}")
        return {
            "error": f"Error retrieving error log: {str(e)}",
            "log_text": "",
            "error_count": 0,
            "warning_count": 0,
            "integration_mentions": {}
        }

@handle_api_errors
@cacheable(entity_cache, "get_entity_history")
async def get_entity_history(entity_id: str, hours: int = 24, minimal: bool = False, use_cache: bool = True) -> Dict[str, Any]:
    """
    Get the history of an entity's state changes from Home Assistant
    
    Args:
        entity_id: The entity ID to get history for
        hours: Number of hours of history to retrieve (default: 24)
        minimal: If True, reduces response size by filtering attributes
                 and limiting the number of data points
        use_cache: Whether to use cached data if available
    
    Returns:
        Dictionary containing:
        - entity_id: The requested entity ID
        - states: List of state records with timestamp and value
        - count: Number of state changes
        - first_changed: Earliest timestamp in the history
        - last_changed: Latest timestamp in the history
        - statistics: Summary statistics (min, max, avg) if applicable
    """
    try:
        # Verify the entity exists first
        current = await get_entity_state(entity_id, detailed=True)
        if isinstance(current, dict) and "error" in current:
            return {
                "entity_id": entity_id,
                "error": current["error"],
                "states": [],
                "count": 0
            }
        
        # Calculate the start time (now - hours)
        from datetime import datetime, timedelta
        import urllib.parse
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Format timestamps for the API
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()
        
        # Encode entity_id for URL
        encoded_entity_id = urllib.parse.quote(entity_id)
        
        # Build URL with timestamp filter
        url = f"{HA_URL}/api/history/period/{start_time_str}?filter_entity_id={encoded_entity_id}&end_time={end_time_str}"
        
        # Get history from API
        client = await get_client()
        response = await client.get(url, headers=get_ha_headers(), timeout=30)
        response.raise_for_status()
        history_data = response.json()
        
        # History API returns a list of lists, with each inner list containing
        # the state history for a single entity
        if not history_data or not isinstance(history_data, list) or len(history_data) == 0:
            return {
                "entity_id": entity_id,
                "states": [],
                "count": 0,
                "note": "No history data found for this entity in the specified time range."
            }
        
        # Get the state history for our entity (should be the first/only item)
        entity_history = history_data[0] if len(history_data) > 0 else []
        
        # Process the history data
        states = []
        first_changed = None
        last_changed = None
        
        # For minimal mode and large datasets, we'll sample the data
        max_points = 100 if minimal else 1000
        sample_rate = max(1, len(entity_history) // max_points) if len(entity_history) > max_points else 1
        
        # For numeric data, track statistics
        numeric_data = []
        is_numeric = False
        
        for i, state_record in enumerate(entity_history):
            # In minimal mode with large datasets, sample the data
            if minimal and i % sample_rate != 0 and i != len(entity_history) - 1:
                continue
                
            # Extract basic state info
            state = state_record.get("state")
            last_changed = state_record.get("last_changed")
            
            if first_changed is None:
                first_changed = last_changed
            
            # Check if state is numeric for statistics
            try:
                numeric_value = float(state)
                numeric_data.append(numeric_value)
                is_numeric = True
            except (ValueError, TypeError):
                pass
            
            # Create the state record
            state_entry = {
                "state": state,
                "last_changed": last_changed
            }
            
            # In minimal mode, filter attributes to save tokens
            if minimal:
                # Include only essential attributes
                filtered_attrs = {}
                full_attrs = state_record.get("attributes", {})
                
                # Keep only important attributes
                essential_attrs = ["unit_of_measurement", "friendly_name", "device_class"]
                for attr in essential_attrs:
                    if attr in full_attrs:
                        filtered_attrs[attr] = full_attrs[attr]
                
                if filtered_attrs:
                    state_entry["attributes"] = filtered_attrs
            else:
                # Include all attributes
                state_entry["attributes"] = state_record.get("attributes", {})
            
            states.append(state_entry)
        
        # Prepare the result
        result = {
            "entity_id": entity_id,
            "states": states,
            "count": len(states)
        }
        
        # Add timestamp range if available
        if first_changed:
            result["first_changed"] = first_changed
        if last_changed:
            result["last_changed"] = last_changed
            
        # Add statistics for numeric data
        if is_numeric and len(numeric_data) > 0:
            result["statistics"] = {
                "min": min(numeric_data),
                "max": max(numeric_data),
                "avg": sum(numeric_data) / len(numeric_data),
                "count": len(numeric_data)
            }
            
            # Check if this is an important sensor type from its attributes
            domain = entity_id.split(".")[0]
            attributes = current.get("attributes", {})
            device_class = attributes.get("device_class")
            unit = attributes.get("unit_of_measurement", "")
            
            # Add more detailed statistics for specific entity types
            # This is generalized to work with any sensor, not just energy-specific ones
            if domain == "sensor" and len(numeric_data) > 1:
                # Calculate change and trend (for any numeric sensor)
                first_val = numeric_data[0] 
                last_val = numeric_data[-1]
                change = last_val - first_val
                
                # Add change info regardless of sensor type
                result["statistics"]["change"] = change
                
                # Add a simple trend indicator
                if abs(change) < 0.01 * max(abs(first_val), 0.01):  # Less than 1% change
                    trend = "stable"
                else:
                    trend = "increasing" if change > 0 else "decreasing"
                    
                result["statistics"]["trend"] = trend
                
                # For unit-based analysis (works for any unit, not just energy)
                if unit:
                    result["statistics"]["unit"] = unit
                    
                    # Calculate period averages for any sensor
                    # This works for temperature, humidity, power, etc.
                    if hours <= 24:
                        result["statistics"]["daily_avg"] = sum(numeric_data) / len(numeric_data)
                    elif hours <= 168:  # 7 days
                        result["statistics"]["weekly_avg"] = sum(numeric_data) / len(numeric_data)
        
                # Add device class if available
                if device_class:
                    result["statistics"]["device_class"] = device_class
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving history for {entity_id}: {str(e)}", exc_info=True)
        return {
            "entity_id": entity_id,
            "error": f"Error retrieving history: {str(e)}",
            "states": [],
            "count": 0
        }

@handle_api_errors
async def get_system_overview() -> Dict[str, Any]:
    """
    Get a comprehensive overview of the entire Home Assistant system
    
    Returns:
        A dictionary containing:
        - total_entities: Total count of all entities
        - domains: Dictionary of domains with their entity counts and state distributions
        - domain_samples: Representative sample entities for each domain (2-3 per domain)
        - domain_attributes: Common attributes for each domain
        - area_distribution: Entities grouped by area (if available)
    """
    try:
        # Get ALL entities with minimal fields for efficiency
        # We retrieve all entities since API calls don't consume tokens, only responses do
        client = await get_client()
        response = await client.get(f"{HA_URL}/api/states", headers=get_ha_headers())
        response.raise_for_status()
        all_entities_raw = response.json()
        
        # Apply lean formatting to reduce token usage in the response
        all_entities = []
        for entity in all_entities_raw:
            domain = entity["entity_id"].split(".")[0]
            
            # Start with basic lean fields
            lean_fields = ["entity_id", "state", "attr.friendly_name"]
            
            # Add domain-specific important attributes
            if domain in DOMAIN_IMPORTANT_ATTRIBUTES:
                for attr in DOMAIN_IMPORTANT_ATTRIBUTES[domain]:
                    lean_fields.append(f"attr.{attr}")
            
            # Filter and add to result
            all_entities.append(filter_fields(entity, lean_fields))
        
        # Initialize overview structure
        overview = {
            "total_entities": len(all_entities),
            "domains": {},
            "domain_samples": {},
            "domain_attributes": {},
            "area_distribution": {}
        }
        
        # Group entities by domain
        domain_entities = {}
        for entity in all_entities:
            domain = entity["entity_id"].split(".")[0]
            if domain not in domain_entities:
                domain_entities[domain] = []
            domain_entities[domain].append(entity)
        
        # Process each domain
        for domain, entities in domain_entities.items():
            # Count entities in this domain
            count = len(entities)
            
            # Collect state distribution
            state_distribution = {}
            for entity in entities:
                state = entity.get("state", "unknown")
                if state not in state_distribution:
                    state_distribution[state] = 0
                state_distribution[state] += 1
            
            # Store domain information
            overview["domains"][domain] = {
                "count": count,
                "states": state_distribution
            }
            
            # Select representative samples (2-3 per domain)
            sample_limit = min(3, count)
            samples = []
            for i in range(sample_limit):
                entity = entities[i]
                samples.append({
                    "entity_id": entity["entity_id"],
                    "state": entity.get("state", "unknown"),
                    "friendly_name": entity.get("attributes", {}).get("friendly_name", entity["entity_id"])
                })
            overview["domain_samples"][domain] = samples
            
            # Collect common attributes for this domain
            attribute_counts = {}
            for entity in entities:
                for attr in entity.get("attributes", {}):
                    if attr not in attribute_counts:
                        attribute_counts[attr] = 0
                    attribute_counts[attr] += 1
            
            # Get top 5 most common attributes for this domain
            common_attributes = sorted(attribute_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            overview["domain_attributes"][domain] = [attr for attr, count in common_attributes]
            
            # Group by area if available
            for entity in entities:
                area_id = entity.get("attributes", {}).get("area_id", "Unknown")
                area_name = entity.get("attributes", {}).get("area_name", area_id)
                
                if area_name not in overview["area_distribution"]:
                    overview["area_distribution"][area_name] = {}
                
                if domain not in overview["area_distribution"][area_name]:
                    overview["area_distribution"][area_name][domain] = 0
                    
                overview["area_distribution"][area_name][domain] += 1
        
        # Add summary information
        overview["domain_count"] = len(domain_entities)
        overview["most_common_domains"] = sorted(
            [(domain, len(entities)) for domain, entities in domain_entities.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return overview
    except Exception as e:
        logger.error(f"Error generating system overview: {str(e)}")
        return {"error": f"Error generating system overview: {str(e)}"}
