"""
Services-Paket für Home Assistant Integration

Dieses Paket enthält Module für die Geschäftslogik der Home Assistant Integration,
einschließlich Entitäten-Verwaltung, Automatisierungen und Event-Handling.
"""
from typing import Dict, Any

# Exportiere die öffentlichen Funktionen
from app.services.entities import get_entity_manager
from app.services.automation import get_automation_manager
from app.services.events import get_event_manager

__all__ = [
    'get_entity_manager',
    'get_automation_manager',
    'get_event_manager'
]
