# Import der neuen Funktionen
from app.simplified_extensions import (
    configure_ha_component, delete_ha_component, 
    set_entity_attributes, manage_dashboard
)

# Diese Tools sollten zur app/server.py hinzugefügt werden

@mcp.tool()
@async_handler("configure_component")
async def configure_component_tool(
    component_type: str,
    object_id: str,
    config_data: Dict[str, Any],
    update: bool = False
) -> Dict[str, Any]:
    """
    Home Assistant Komponente erstellen oder aktualisieren
    
    Eine flexible Funktion, die verwendet werden kann, um verschiedene Arten von
    Home Assistant Komponenten zu konfigurieren wie Automatisierungen, Skripte,
    Szenen und mehr.
    
    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der zu konfigurierenden Komponente
        config_data: Konfigurationsdaten für die Komponente
        update: True für Update, False für Neuanlage
        
    Returns:
        Antwort von Home Assistant
        
    Beispiel - Neue Automatisierung:
    ```
    component_type="automation",
    object_id="lights_at_sunset",
    config_data={
        "alias": "Lichter bei Sonnenuntergang einschalten",
        "description": "Schaltet die Lichter automatisch bei Sonnenuntergang ein",
        "trigger": [
            {
                "platform": "sun",
                "event": "sunset",
                "offset": "+00:30:00"
            }
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {
                    "entity_id": "light.living_room"
                }
            }
        ],
        "mode": "single"
    }
    ```
    
    Beispiel - Neues Skript:
    ```
    component_type="script",
    object_id="evening_routine",
    config_data={
        "alias": "Abendroutine",
        "sequence": [
            {
                "service": "light.turn_on",
                "target": {
                    "entity_id": "light.living_room"
                },
                "data": {
                    "brightness": 150
                }
            },
            {
                "delay": {
                    "minutes": 2
                }
            },
            {
                "service": "media_player.turn_on",
                "target": {
                    "entity_id": "media_player.tv"
                }
            }
        ],
        "mode": "single"
    }
    ```
    
    Beispiel - Neue Szene:
    ```
    component_type="scene",
    object_id="movie_night",
    config_data={
        "name": "Filmabend",
        "entities": {
            "light.living_room": {
                "state": "on",
                "brightness": 50
            },
            "light.kitchen": {
                "state": "off"
            }
        }
    }
    ```
    """
    logger.info(f"Konfiguriere {component_type}: {object_id}")
    return await configure_ha_component(component_type, object_id, config_data, update)

@mcp.tool()
@async_handler("delete_component")
async def delete_component_tool(
    component_type: str,
    object_id: str
) -> Dict[str, Any]:
    """
    Home Assistant Komponente löschen
    
    Args:
        component_type: Art der Komponente (automation, script, scene, etc.)
        object_id: ID der zu löschenden Komponente
        
    Returns:
        Antwort von Home Assistant
        
    Beispiel:
    ```
    component_type="automation",
    object_id="lights_at_sunset"
    ```
    """
    logger.info(f"Lösche {component_type}: {object_id}")
    return await delete_ha_component(component_type, object_id)

@mcp.tool()
@async_handler("set_attributes")
async def set_attributes_tool(
    entity_id: str,
    attributes: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Attribute für eine Home Assistant Entität setzen
    
    Diese Funktion erkennt automatisch den richtigen Service basierend
    auf dem Entity-Typ und den zu setzenden Attributen.
    
    Args:
        entity_id: ID der Entität
        attributes: Zu setzende Attribute
        
    Returns:
        Antwort von Home Assistant
        
    Beispiele:
        Für Lampen:
        ```
        entity_id="light.living_room",
        attributes={"brightness": 255, "rgb_color": [255, 0, 0], "transition": 2}
        ```
        
        Für Klimageräte:
        ```
        entity_id="climate.living_room",
        attributes={"temperature": 22.5, "hvac_mode": "heat"}
        ```
        
        Für Media Player:
        ```
        entity_id="media_player.tv",
        attributes={"volume_level": 0.5, "source": "HDMI 1"}
        ```
    """
    logger.info(f"Setze Attribute für {entity_id}: {attributes}")
    return await set_entity_attributes(entity_id, attributes)

@mcp.tool()
@async_handler("manage_dashboard")
async def manage_dashboard_tool(
    action: str,
    dashboard_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    title: Optional[str] = None,
    icon: Optional[str] = None,
    show_in_sidebar: bool = True,
    views: Optional[List[Dict[str, Any]]] = None,
    resources: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Dashboards in Home Assistant verwalten
    
    Eine flexible Funktion für alle Dashboard-bezogenen Operationen.
    
    Args:
        action: Aktion (create, update, delete, get)
        dashboard_id: ID des Dashboards (optional für get/create)
        config: Konfiguration (für update)
        title: Titel des Dashboards (für create)
        icon: Icon des Dashboards (für create)
        show_in_sidebar: Ob das Dashboard in der Seitenleiste angezeigt werden soll (für create)
        views: Dashboard-Ansichten (für create)
        resources: Benutzerdefinierte Ressourcen/HACS-Module (für create/update)
        
    Returns:
        Antwort von Home Assistant
        
    Beispiele:
        Dashboard abrufen:
        ```
        action="get",
        dashboard_id="wohnzimmer"  # oder None für das Standarddashboard
        ```
        
        Dashboard erstellen:
        ```
        action="create",
        title="Mein Zuhause",
        icon="mdi:home",
        views=[
            {
                "title": "Wohnzimmer",
                "path": "wohnzimmer",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Lichter",
                        "entities": ["light.living_room", "light.floor_lamp"]
                    }
                ]
            }
        ],
        resources=[
            {
                "type": "module",
                "url": "/hacsfiles/mini-graph-card/mini-graph-card.js"
            }
        ]
        ```
        
        Dashboard aktualisieren:
        ```
        action="update",
        dashboard_id="mein_zuhause",
        config={
            "title": "Mein Zuhause",
            "views": [...]
        }
        ```
        
        Dashboard löschen:
        ```
        action="delete",
        dashboard_id="mein_zuhause"
        ```
        
        HACS-Ressourcen hinzufügen:
        ```
        action="update",
        dashboard_id="mein_zuhause",
        resources=[
            {
                "type": "module",
                "url": "/hacsfiles/button-card/button-card.js"
            }
        ]
        ```
    """
    logger.info(f"Verwalte Dashboard - Aktion: {action}, Dashboard ID: {dashboard_id or 'default'}")
    return await manage_dashboard(
        action, dashboard_id, config, title, icon, 
        show_in_sidebar, views, resources
    )

@mcp.prompt()
def create_automation_prompt():
    """
    Begleitet einen Benutzer durch die Erstellung einer Automatisierung
    
    Dieser Prompt bietet eine schrittweise geführte Konversation zum Erstellen
    einer neuen Automatisierung in Home Assistant.
    
    Returns:
        Eine Liste von Nachrichten für die interaktive Konversation
    """
    system_message = """Du bist ein Experte für die Erstellung von Home Assistant Automatisierungen.
Du wirst den Benutzer durch die Erstellung einer Automatisierung mit folgenden Schritten führen:
1. Definiere die Auslösebedingungen (Trigger)
2. Lege fest, welche Aktionen ausgeführt werden sollen
3. Füge optional Bedingungen hinzu
4. Überprüfe und bestätige die Automatisierung"""
    
    user_message = "Ich möchte eine neue Automatisierung für mein Smart Home erstellen. Kannst du mir dabei helfen?"
    
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

@mcp.prompt()
def create_dashboard_prompt():
    """
    Begleitet einen Benutzer durch die Erstellung eines Dashboards
    
    Dieser Prompt bietet eine schrittweise geführte Konversation zum Erstellen
    eines neuen Dashboards in Home Assistant basierend auf den vorhandenen Entitäten.
    
    Returns:
        Eine Liste von Nachrichten für die interaktive Konversation
    """
    system_message = """Du bist ein Experte für die Erstellung von Home Assistant Dashboards.
Du wirst den Benutzer durch die Erstellung eines benutzerfreundlichen Dashboards mit folgenden Schritten führen:
1. Identifizieren, welche Entitäten der Benutzer einbeziehen möchte
2. Logische Gruppierungen von Entitäten vorschlagen (nach Raum, Funktion oder Typ)
3. Geeignete Kartentypen für verschiedene Entitätsgruppen empfehlen
4. Ein gut strukturiertes Dashboard-Layout erstellen
5. Das Dashboard mit dem manage_dashboard-Tool implementieren"""
    
    user_message = "Ich möchte ein neues Dashboard für mein Home Assistant System erstellen, um meine Smart Home Entitäten besser zu organisieren. Kannst du mir dabei helfen?"
    
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]