# Hass-MCP Benutzeranleitung

Diese Anleitung beschreibt, wie du die Hass-MCP Integration mit großen Sprachmodellen (LLMs) und KI-Assistenten verwenden kannst, um deine Home Assistant-Umgebung zu steuern.

## Übersicht

Die Hass-MCP Integration ermöglicht es Sprachmodellen und KI-Assistenten, mit deiner Home Assistant-Instanz zu interagieren. Du kannst natürliche Sprache verwenden, um:

- Den Status von Geräten abzufragen
- Geräte zu steuern (ein-/ausschalten, Helligkeit anpassen, etc.)
- Historiendaten zu analysieren
- Automatisierungen auszuführen und zu verwalten

## Erste Schritte

Nachdem du die [Installation](setup.md) abgeschlossen hast:

1. Stelle sicher, dass dein MCP-Server läuft
2. In deinem bevorzugten KI-Assistenten oder LLM-Chat (z.B. Claude, GPT, Gemini oder andere), verweise auf die MCP-Integration

## Beispielanfragen

Hier sind einige Beispielanfragen, die du an dein Sprachmodell stellen kannst:

### Statusabfragen

- "Sind die Lichter im Wohnzimmer an?"
- "Wie ist die aktuelle Temperatur in der Küche?"
- "Zeige mir den Status aller Lampen im Haus."
- "Ist die Haustür verschlossen?"

### Gerätesteuerung

- "Schalte das Licht im Wohnzimmer ein."
- "Stelle die Helligkeit der Deckenlampe auf 50%."
- "Stelle die Heizung im Schlafzimmer auf 22 Grad."
- "Schalte alle Lichter im Erdgeschoss aus."

### Szenen und Automatisierungen

- "Aktiviere die Szene 'Filmabend'."
- "Erstelle eine neue Automatisierung, die die Lichter einschaltet, wenn ich nach Hause komme."
- "Zeige mir alle aktiven Automatisierungen."

### Informationen und Analysen

- "Wie hat sich die Temperatur im Wohnzimmer in den letzten 24 Stunden entwickelt?"
- "Welche Geräte verbrauchen aktuell am meisten Strom?"
- "Zeige mir eine Übersicht aller Smart-Home-Geräte."

## Tipps für die Verwendung

- Sei so spezifisch wie möglich bei der Benennung von Geräten
- Du kannst den KI-Assistenten bitten, komplexe Aktionen in einzelne Schritte aufzuteilen
- Bei Unsicherheiten kannst du das Sprachmodell bitten, zuerst die verfügbaren Geräte aufzulisten

## Fehlerbehebung

Wenn dein KI-Assistent nicht auf deine Home Assistant-Geräte zugreifen kann:

1. Stelle sicher, dass der MCP-Server läuft
2. Überprüfe, ob dein Home Assistant Token gültig ist
3. Überprüfe die Netzwerkverbindung zwischen dem MCP-Server und Home Assistant
4. Prüfe die Server-Logs auf Fehlermeldungen (`LOG_LEVEL=DEBUG` für detailliertere Logs)

---

*Diese Dokumentation wird kontinuierlich erweitert und aktualisiert.* 