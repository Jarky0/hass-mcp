# App module initialization
# This file ensures the app package is properly initialized

# Import main modules
from app import config
from app import hass
from app import server
from app import simplified_extensions  # Import our simplified extensions

# Export version info
__version__ = "0.4.0"  # Version für die vereinfachte Funktionalität