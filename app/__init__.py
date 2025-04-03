# App module initialization
# This file ensures the app package is properly initialized

# Import core modules first
from app import config

# Export version info
__version__ = "0.4.0"  # Version für die vereinfachte Funktionalität

# Expose 'mcp' module to avoid circular imports
from app import mcp

# Modules with potential circular dependencies will be imported on-demand
# This ensures that circular imports are avoided
def _lazy_import():
    # These imports will be done only when needed
    # and not during package initialization
    from app import hass
    from app import server
    from app import simplified_extensions
    return (hass, server, simplified_extensions)