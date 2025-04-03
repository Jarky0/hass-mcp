"""
MCP Server Instance

Diese Datei enthält nur die Initialisierung der MCP-Server-Instanz, 
um zirkuläre Importe zwischen app/server.py und app/mcp/server.py zu vermeiden.
"""
import logging

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Server Instanz wird verzögert erstellt, um zirkuläre Importe zu vermeiden
mcp = None

def initialize_mcp():
    """Initialisiert die MCP-Instanz wenn sie benötigt wird"""
    global mcp
    if mcp is None:
        # FastMCP anstelle von direktem Server verwenden
        from fastmcp import FastMCP
        
        # FastMCP Server Instanz erstellen
        # Der Name sollte mit dem in der Claude Desktop Konfiguration übereinstimmen
        mcp = FastMCP(
            name="Hass-MCP",
            debug=True,
            log_level="INFO"
        )
        logger.info("FastMCP Server Instance initialisiert in app/mcp/instance.py")
    return mcp

# Initialisiere MCP direkt beim Import dieser Datei
initialize_mcp() 