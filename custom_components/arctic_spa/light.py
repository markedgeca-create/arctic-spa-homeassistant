"""Light platform - the spa's cabinet and water lights."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcticSpaConfigEntry
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the spa light if the spa reports one."""
    coordinator = entry.runtime_data
    if "lights" in coordinator.data:
        async_add_entities([ArcticSpaLight(coordinator)])


class ArcticSpaLight(ArcticSpaEntity, LightEntity):
    """On/off control of the spa lights.

    The API exposes no brightness or colour, only a state enum.
    """

    _attr_translation_key = "lights"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the light."""
        super().__init__(coordinator, "lights")

    @property
    def is_on(self) -> bool | None:
        """Return whether the lights are on."""
        value = self._status.get("lights")
        if value is None:
            return None
        return value != "off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the lights on."""
        await self.coordinator.client.async_set_light(True)
        self.coordinator.async_apply_optimistic(lights="on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the lights off."""
        await self.coordinator.client.async_set_light(False)
        self.coordinator.async_apply_optimistic(lights="off")
