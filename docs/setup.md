# Hass-MCP Setup-Anleitung

Diese Anleitung beschreibt die Installation und Einrichtung der Hass-MCP Integration für Home Assistant.

## Voraussetzungen

- Python 3.9 oder höher
- Zugriff auf eine laufende Home Assistant-Instanz
- Home Assistant Long-Lived Access Token
- Docker (optional, für Container-basierte Installation)

## Installation

### Option 1: Lokale Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/yourusername/hass-mcp.git
   cd hass-mcp
   ```

2. Virtuelle Umgebung erstellen und aktivieren:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unter Windows: venv\Scripts\activate
   ```

3. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

4. Umgebungsvariablen konfigurieren:
   ```bash
   cp .env.example .env
   # Bearbeite .env mit deinen Home Assistant-Zugangsdaten
   ```

### Option 2: Docker-Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/yourusername/hass-mcp.git
   cd hass-mcp
   ```

2. Docker-Container bauen:
   ```bash
   docker build -t hass-mcp .
   ```

3. Container ausführen:
   ```bash
   docker run -i --rm -e HA_URL=http://your-homeassistant-url:8123 -e HA_TOKEN=your_access_token --network=host hass-mcp:latest
   ```

## Konfiguration

### Home Assistant Access Token erstellen

1. In Home Assistant, navigiere zu deinem Benutzerprofil (klicke auf deinen Namen in der unteren linken Ecke)
2. Scrolle nach unten zu "Long-Lived Access Tokens"
3. Klicke auf "Create Token", gib einen Namen ein und kopiere den generierten Token

### Umgebungsvariablen

Die folgenden Umgebungsvariablen müssen in der .env-Datei oder als Docker-Umgebungsvariablen konfiguriert werden:

#### Erforderliche Variablen
- `HA_URL`: URL deiner Home Assistant-Instanz (z.B. `http://homeassistant.local:8123`)
- `HA_TOKEN`: Dein Long-Lived Access Token

#### Optionale Variablen
- `MCP_ENABLED`: MCP-Server aktivieren/deaktivieren (Standard: `True`)
- `MCP_PORT`: Port für den MCP-Server (Standard: `3000`) 
- `LOG_LEVEL`: Logging-Level (Standard: `INFO`)

## Erste Schritte

### MCP-Server starten

Nach erfolgreicher Installation kannst du den MCP-Server starten:

```bash
# Bei lokaler Installation
python -m app

# Oder über Docker (wie oben beschrieben)
```

---

*Weitere Informationen zur Verwendung findest du in der [Benutzeranleitung](usage.md).* 