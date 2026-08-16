"""The Arctic Spa integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ArcticSpaClient
from .coordinator import ArcticSpaCoordinator

type ArcticSpaConfigEntry = ConfigEntry[ArcticSpaCoordinator]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ArcticSpaConfigEntry) -> bool:
    """Set up Arctic Spa from a config entry."""
    client = ArcticSpaClient(async_get_clientsession(hass), entry.data[CONF_API_KEY])
    coordinator = ArcticSpaCoordinator(hass, entry, client)

    # The first status document decides which entities exist, so it has to
    # succeed before platforms are forwarded.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArcticSpaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ArcticSpaConfigEntry) -> None:
    """Reload when options (polling interval) change."""
    await hass.config_entries.async_reload(entry.entry_id)
