# Hass-MCP API-Dokumentation

Diese Dokumentation beschreibt die API-Komponenten, die von der Hass-MCP Integration verwendet werden.

## Home Assistant API-Client

Der Home Assistant API-Client (`app/api/client.py`) stellt eine abstrahierte Schnittstelle zur Home Assistant REST API bereit.

### Hauptfunktionen

- **Statusabfragen** für Home Assistant Entitäten
- **Steuerungsbefehle** für Geräte und Dienste
- **Historiendaten** für Entitäten abrufen
- **Konfigurationsverwaltung** für Home Assistant

## MCP Tools

Die MCP Tools (`app/mcp/tools.py`) bieten eine Schnittstelle für Large Language Models (LLMs) und KI-Assistenten zur Interaktion mit Home Assistant.

### Verfügbare Tools

- **Entity Management**: Abfragen und Steuern von Home Assistant Entitäten
- **System Management**: Konfiguration und Kontrolle der Home Assistant Instanz
- **Automatisierungstools**: Interaktion mit Home Assistant Automatisierungen

## Ressourcen

Die MCP Ressourcen (`app/mcp/resources.py`) stellen strukturierte Daten für LLMs und KI-Assistenten bereit.

---

*Diese Dokumentation wird kontinuierlich erweitert und aktualisiert.* 