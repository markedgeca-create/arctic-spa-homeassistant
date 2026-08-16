"""Constants for the Arctic Spa integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "arctic_spa"

MANUFACTURER: Final = "Arctic Spas"
CONFIGURATION_URL: Final = "https://myarcticspa.com/spa/SpaAPIManagement.aspx"

# The public API documents a maximum of 15 status calls per minute. 60 seconds
# leaves plenty of headroom for the extra calls a command triggers.
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 30
MAX_SCAN_INTERVAL: Final = 3600

# Seconds to wait after sending a command before pulling fresh state. The cloud
# needs a moment to round-trip the command to the spa.
COMMAND_REFRESH_DELAY: Final = 12

# Arctic Spas controllers clamp to this range regardless of what is sent.
MIN_TEMP_F: Final = 59
MAX_TEMP_F: Final = 104

PUMP_KEYS: Final = ("pump1", "pump2", "pump3", "pump4", "pump5")
BLOWER_KEYS: Final = ("blower1", "blower2")
