"""Number platform - filtration schedule settings."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcticSpaConfigEntry
from .api import ArcticSpaClient
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity


@dataclass(frozen=True, kw_only=True)
class ArcticSpaNumberEntityDescription(NumberEntityDescription):
    """Describes an Arctic Spa number."""

    status_key: str
    set_fn: Callable[[ArcticSpaClient, int], Awaitable[None]]


NUMBERS: tuple[ArcticSpaNumberEntityDescription, ...] = (
    ArcticSpaNumberEntityDescription(
        key="filter_frequency",
        translation_key="filter_frequency",
        status_key="filter_frequency",
        entity_category=EntityCategory.CONFIG,
        mode=NumberMode.BOX,
        native_min_value=1,
        native_max_value=24,
        native_step=1,
        set_fn=lambda client, value: client.async_set_filter(frequency=value),
    ),
    ArcticSpaNumberEntityDescription(
        key="filter_duration",
        translation_key="filter_duration",
        status_key="filter_duration",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        native_min_value=1,
        native_max_value=24,
        native_step=1,
        set_fn=lambda client, value: client.async_set_filter(duration=value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up filtration settings the spa reports."""
    coordinator = entry.runtime_data
    async_add_entities(
        ArcticSpaNumber(coordinator, description)
        for description in NUMBERS
        if description.status_key in coordinator.data
    )


class ArcticSpaNumber(ArcticSpaEntity, NumberEntity):
    """A writable filtration setting."""

    entity_description: ArcticSpaNumberEntityDescription

    def __init__(
        self,
        coordinator: ArcticSpaCoordinator,
        description: ArcticSpaNumberEntityDescription,
    ) -> None:
        """Initialise the number."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current setting."""
        return self._status.get(self.entity_description.status_key)

    async def async_set_native_value(self, value: float) -> None:
        """Write a new setting."""
        description = self.entity_description
        new_value = int(round(value))
        await description.set_fn(self.coordinator.client, new_value)
        self.coordinator.async_apply_optimistic(**{description.status_key: new_value})
