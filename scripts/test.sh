#!/bin/bash

# Hass-MCP Test-Runner
# Dieses Skript führt Tests für das Hass-MCP Projekt aus

set -e

# Verzeichniswechsel zum Projektroot
cd "$(dirname "$0")/.."
PROJ_ROOT=$(pwd)

echo "=== Hass-MCP Tests ==="
echo "Projektverzeichnis: $PROJ_ROOT"

# Prüfen, ob virtuelle Umgebung existiert
if [ ! -d "venv" ]; then
    echo "Fehler: Virtuelle Umgebung nicht gefunden. Bitte führe zuerst setup.sh aus."
    exit 1
fi

# Virtuelle Umgebung aktivieren
echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate

# Tests mit pytest ausführen
echo "Führe Tests aus..."

# Optionale Parameter für pytest übernehmen
if [ "$#" -gt 0 ]; then
    PYTEST_ARGS="$@"
else
    PYTEST_ARGS="-v"
fi

# Tests ausführen
python -m pytest $PYTEST_ARGS

TEST_STATUS=$?

echo ""
if [ $TEST_STATUS -eq 0 ]; then
    echo "=== Tests erfolgreich abgeschlossen ==="
else
    echo "=== Tests fehlgeschlagen ==="
fi

exit $TEST_STATUS 