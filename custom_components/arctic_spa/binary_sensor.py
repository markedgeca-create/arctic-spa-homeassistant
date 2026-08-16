"""Binary sensor platform - connectivity, Spa Boy state and faults."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
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
    """Set up the diagnostic binary sensors."""
    coordinator = entry.runtime_data
    status = coordinator.data

    entities: list[BinarySensorEntity] = [
        ArcticSpaConnectivity(coordinator),
        ArcticSpaProblem(coordinator),
    ]
    if "spaboy_connected" in status:
        entities.append(ArcticSpaBoyConnected(coordinator))
    if "spaboy_producing" in status:
        entities.append(ArcticSpaBoyProducing(coordinator))

    async_add_entities(entities)


class ArcticSpaAlwaysAvailable(ArcticSpaEntity, BinarySensorEntity):
    """Base for sensors that must keep reporting while the spa is offline."""

    @property
    def available(self) -> bool:
        """Only the API being unreachable makes these unavailable."""
        return self.coordinator.last_update_success


class ArcticSpaConnectivity(ArcticSpaAlwaysAvailable):
    """Whether the Arctic Spas cloud can currently reach the spa."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "connected")

    @property
    def is_on(self) -> bool | None:
        """Return whether the spa is online."""
        return self._status.get("connected")


class ArcticSpaProblem(ArcticSpaAlwaysAvailable):
    """On whenever the spa reports one or more active error codes."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "problem")

    @property
    def is_on(self) -> bool:
        """Return whether any error is active."""
        return bool(self._status.get("errors"))


class ArcticSpaBoyConnected(ArcticSpaAlwaysAvailable):
    """Whether the Spa Boy water care module is connected."""

    _attr_translation_key = "spaboy_connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "spaboy_connected")

    @property
    def is_on(self) -> bool | None:
        """Return whether Spa Boy is connected."""
        return self._status.get("spaboy_connected")


class ArcticSpaBoyProducing(ArcticSpaEntity, BinarySensorEntity):
    """Whether Spa Boy is actively generating sanitiser."""

    _attr_translation_key = "spaboy_producing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "spaboy_producing")

    @property
    def is_on(self) -> bool | None:
        """Return whether Spa Boy is producing."""
        return self._status.get("spaboy_producing")
