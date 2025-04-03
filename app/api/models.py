from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EntityState(BaseModel):
    """Zustandsmodell für eine Home Assistant Entität"""
    entity_id: str
    state: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    last_changed: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None


class ServiceDomain(BaseModel):
    """Modell für einen Service-Domainbereich"""
    domain: str
    services: Dict[str, Dict[str, Any]]


class EventType(BaseModel):
    """Modell für einen Event-Typ"""
    event: str
    listener_count: int


class ErrorResponse(BaseModel):
    """Modell für eine Fehlerantwort"""
    error: str
    details: Optional[str] = None


class ConfigResult(BaseModel):
    """Modell für Konfigurationsinformationen"""
    components: List[str]
    config_dir: str
    elevation: int
    latitude: float
    longitude: float
    location_name: str
    time_zone: str
    unit_system: Dict[str, str]
    version: str
    whitelist_external_dirs: List[str]


class HistoryState(BaseModel):
    """Modell für einen historischen Zustandseintrag"""
    entity_id: str
    state: str
    attributes: Dict[str, Any]
    last_changed: datetime
    last_updated: datetime


class LogbookEntry(BaseModel):
    """Modell für einen Logbuch-Eintrag"""
    name: str
    message: str
    domain: str
    entity_id: str
    when: datetime
    context_user_id: Optional[str] = None
    context_event_type: Optional[str] = None


class DomainStats(BaseModel):
    """Statistiken für eine Domain"""
    count: int
    states: Dict[str, int]
    examples: Dict[str, List[str]]
    common_attributes: List[str]


class SystemOverview(BaseModel):
    """Systemübersicht"""
    total_entities: int
    domains: Dict[str, DomainStats]
    areas: Optional[Dict[str, int]] = None


class AutomationInfo(BaseModel):
    """Informationen zu einer Automation"""
    id: str
    entity_id: str
    state: str
    alias: str
    description: Optional[str] = None


class EntityField(str, Enum):
    """Mögliche Felder einer Entität"""
    ENTITY_ID = "entity_id"
    STATE = "state"
    ATTRIBUTES = "attributes"
    LAST_CHANGED = "last_changed"
    LAST_UPDATED = "last_updated"
    CONTEXT = "context"


class APIResponse(BaseModel):
    """Generisches Antwortmodell für API-Antworten"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class LightAttributes(BaseModel):
    """Spezifische Attribute für Lichter"""
    brightness: Optional[int] = None
    color_temp: Optional[int] = None
    rgb_color: Optional[List[int]] = None
    xy_color: Optional[List[float]] = None
    effect: Optional[str] = None
    supported_features: Optional[int] = None
    friendly_name: Optional[str] = None
    icon: Optional[str] = None
    supported_color_modes: Optional[List[str]] = None


class ClimateAttributes(BaseModel):
    """Spezifische Attribute für Klimaanlagen"""
    temperature: Optional[float] = None
    current_temperature: Optional[float] = None
    hvac_mode: Optional[str] = None
    hvac_action: Optional[str] = None
    min_temp: Optional[float] = None
    max_temp: Optional[float] = None
    target_temp_step: Optional[float] = None
    supported_features: Optional[int] = None
    friendly_name: Optional[str] = None
