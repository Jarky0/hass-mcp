from typing import Dict, Any, Optional, List, Callable, TypeVar
import functools
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type variable for generic functions
F = TypeVar('F', bound=Callable[..., Any])

class SimpleCache:
    """Einfaches In-Memory-Cache-System für API-Anfragen"""
    
    def __init__(self, ttl_seconds: int = 30):
        self.cache = {}
        self.ttl_seconds = ttl_seconds
        
    def get(self, key: str) -> Optional[Any]:
        """Versuche, einen Wert aus dem Cache zu holen"""
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
