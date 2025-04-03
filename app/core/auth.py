from typing import Dict, Optional, Tuple
import os
import httpx
import logging
import json
from pathlib import Path

from app.core.config import HA_URL, HA_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Datei für die Token-Speicherung
TOKEN_FILE = Path.home() / ".hass-mcp" / "token.json"

async def validate_token(token: str) -> Tuple[bool, Optional[str]]:
    """
    Validiert einen Home Assistant Token durch einen API-Aufruf
    
    Args:
        token: Der zu validierende Token
        
    Returns:
        Tuple aus (ist_gültig, Fehlermeldung)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{HA_URL}/api/", headers=headers)
            
            if response.status_code == 200:
                return True, None
            elif response.status_code == 401:
                return False, "Ungültiger Token oder fehlende Berechtigung"
            else:
                return False, f"HTTP-Fehler: {response.status_code} - {response.reason_phrase}"
    except httpx.ConnectError:
        return False, f"Verbindungsfehler: Kann keine Verbindung zu Home Assistant unter {HA_URL} herstellen"
    except httpx.TimeoutException:
        return False, f"Timeout-Fehler: Home Assistant unter {HA_URL} hat nicht rechtzeitig geantwortet"
    except Exception as e:
        return False, f"Unerwarteter Fehler: {str(e)}"

def save_token(token: str) -> None:
    """Speichert den Token in einer Datei"""
    try:
        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        
        # Speichere den Token verschlüsselt (TODO: Verbesserte Verschlüsselung)
        with open(TOKEN_FILE, "w") as f:
            json.dump({"token": token}, f)
            
        logger.info(f"Token erfolgreich in {TOKEN_FILE} gespeichert")
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Tokens: {str(e)}")

def load_token() -> Optional[str]:
    """Lädt den Token aus einer Datei"""
    try:
        if not os.path.exists(TOKEN_FILE):
            return None
            
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
            return data.get("token")
    except Exception as e:
        logger.error(f"Fehler beim Laden des Tokens: {str(e)}")
        return None

async def get_valid_token() -> Optional[str]:
    """
    Versucht, einen gültigen Token zu erhalten
    
    Prüft zunächst die Umgebungsvariable, dann die gespeicherte Datei
    
    Returns:
        Ein gültiger Token oder None
    """
    # Prüfe zunächst die Umgebungsvariable
    if HA_TOKEN:
        is_valid, error = await validate_token(HA_TOKEN)
        if is_valid:
            return HA_TOKEN
        logger.warning(f"Umgebungstoken ist ungültig: {error}")
    
    # Versuche, den gespeicherten Token zu laden
    token = load_token()
    if token:
        is_valid, error = await validate_token(token)
        if is_valid:
            return token
        logger.warning(f"Gespeicherter Token ist ungültig: {error}")
    
    # Kein gültiger Token gefunden
    return None
