"""Select platform - two-speed pump control."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcticSpaConfigEntry
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity

# Pump 1 is the only pump the API accepts a "low" speed for.
PUMP_SPEEDS = ["off", "low", "high"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the pump 1 speed selector."""
    coordinator = entry.runtime_data
    if "pump1" in coordinator.data:
        async_add_entities([ArcticSpaPumpSpeed(coordinator)])


class ArcticSpaPumpSpeed(ArcticSpaEntity, SelectEntity):
    """Speed selector for the two-speed circulation pump."""

    _attr_translation_key = "pump_speed"
    _attr_options = PUMP_SPEEDS

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the selector."""
        super().__init__(coordinator, "pump1_speed")

    @property
    def current_option(self) -> str | None:
        """Return the pump's current speed."""
        value = self._status.get("pump1")
        return value if value in PUMP_SPEEDS else None

    async def async_select_option(self, option: str) -> None:
        """Set the pump speed."""
        await self.coordinator.client.async_set_pump("1", option)
        self.coordinator.async_apply_optimistic(pump1=option)
