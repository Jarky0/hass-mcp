#!/bin/bash

# Hass-MCP Setup-Skript
# Dieses Skript richtet eine Entwicklungsumgebung für Hass-MCP ein

set -e

# Verzeichniswechsel zum Projektroot
cd "$(dirname "$0")/.."
PROJ_ROOT=$(pwd)

echo "=== Hass-MCP Setup ==="
echo "Projektverzeichnis: $PROJ_ROOT"

# Prüfen, ob Python installiert ist
if ! command -v python3 &> /dev/null; then
    echo "Fehler: Python 3 ist nicht installiert. Bitte installiere Python 3.9 oder höher."
    exit 1
fi

# Python-Version prüfen
PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python-Version: $PY_VERSION"

# Venv erstellen, falls nicht vorhanden
if [ ! -d "venv" ]; then
    echo "Erstelle virtuelle Umgebung..."
    python3 -m venv venv
fi

# Venv aktivieren
echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate

# Abhängigkeiten installieren
echo "Installiere Abhängigkeiten..."
pip install -r requirements.txt

# .env-Datei erstellen, falls nicht vorhanden
if [ ! -f ".env" ]; then
    echo "Erstelle .env-Datei aus Vorlage..."
    cp .env.example .env
    echo "WICHTIG: Bitte bearbeite .env und füge deine Home Assistant-Zugangsdaten hinzu."
fi

echo "=== Setup abgeschlossen ==="
echo "Um die virtuelle Umgebung zu aktivieren, führe aus:"
echo "  source venv/bin/activate"
echo ""
echo "Um den MCP-Server zu starten, führe aus:"
echo "  python -m app"

# Berechtigungen setzen
chmod +x scripts/*.sh

exit 0 