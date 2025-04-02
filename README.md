# Erweiterte Funktionen für Claude

Hass-MCP bietet jetzt erweiterte Funktionen, mit denen Claude und andere LLMs direkte Änderungen an der Home Assistant Konfiguration vornehmen können:

## Vereinfachte, flexible Tools

- `configure_component`: Universelle Funktion zum Erstellen oder Aktualisieren jeder Home Assistant Komponente (Automatisierungen, Skripte, Szenen)
- `delete_component`: Löschen einer beliebigen Home Assistant Komponente
- `set_attributes`: Flexible Entitätssteuerung mit automatischer Service-Erkennung
- `manage_dashboard`: Umfassende Funktion zur Dashboard-Verwaltung (erstellen, aktualisieren, löschen, abrufen)

Diese vereinfachten Tools bieten die gleiche Funktionalität wie die vorherigen Funktionen, sind jedoch flexibler und einfacher zu verwenden.

## Geführte Konversationen

- `create_automation_prompt`: Führt den Benutzer durch die Erstellung einer Automatisierung
- `create_dashboard_prompt`: Begleitet den Benutzer bei der Erstellung eines angepassten Dashboards

## Nutzungsbeispiele

```
# Automatisierung erstellen
configure_component(
    component_type="automation",
    object_id="lights_at_sunset",
    config_data={
        "alias": "Lichter bei Sonnenuntergang einschalten",
        "description": "Schaltet die Lichter automatisch bei Sonnenuntergang ein",
        "trigger": [
            {"platform": "sun", "event": "sunset", "offset": "+00:30:00"}
        ],
        "action": [
            {
                "service": "light.turn_on",
                "target": {"entity_id": "light.living_room"}
            }
        ],
        "mode": "single"
    }
)

# Attribute einer Lampe setzen
set_attributes(
    entity_id="light.living_room",
    attributes={"brightness": 255, "rgb_color": [255, 0, 0], "transition": 2}
)

# Dashboard erstellen (inkl. HACS-Karten)
manage_dashboard(
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
                },
                {
                    "type": "custom:mini-graph-card",
                    "name": "Temperatur",
                    "entities": ["sensor.wohnzimmer_temperatur"],
                    "hours_to_show": 24
                }
            ]
        }
    ],
    resources=[
        {"type": "module", "url": "/hacsfiles/mini-graph-card/mini-graph-card.js"}
    ]
)
```