"""Button platform - one-shot spa commands."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
    """Set up the boost button."""
    async_add_entities([ArcticSpaBoostButton(entry.runtime_data)])


class ArcticSpaBoostButton(ArcticSpaEntity, ButtonEntity):
    """Kick off a boost (extra filtration and sanitisation) cycle."""

    _attr_translation_key = "boost"

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the button."""
        super().__init__(coordinator, "boost")

    async def async_press(self) -> None:
        """Start a boost cycle."""
        await self.coordinator.client.async_boost()
        self.coordinator.async_schedule_command_refresh()
