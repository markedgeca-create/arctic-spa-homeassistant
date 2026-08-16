"""Sensor platform - water chemistry, filtration state and error codes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcticSpaConfigEntry
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity

# Values the API documents for ph_status / orp_status and filter_status.
CHEMISTRY_STATES = ["LOW", "CAUTION_LOW", "OK", "CAUTION_HIGH", "HIGH"]
FILTER_STATES = [
    "Idle",
    "Purge",
    "Filtering",
    "Suspended",
    "Overtemperature",
    "Resuming",
    "Boost",
    "Sanitize",
]


@dataclass(frozen=True, kw_only=True)
class ArcticSpaSensorEntityDescription(SensorEntityDescription):
    """Describes an Arctic Spa sensor."""

    status_key: str
    value_fn: Callable[[Any], Any] = lambda value: value


SENSORS: tuple[ArcticSpaSensorEntityDescription, ...] = (
    ArcticSpaSensorEntityDescription(
        key="temperature",
        status_key="temperatureF",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ArcticSpaSensorEntityDescription(
        key="ph",
        translation_key="ph",
        status_key="ph",
        device_class=SensorDeviceClass.PH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ArcticSpaSensorEntityDescription(
        key="orp",
        translation_key="orp",
        status_key="orp",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ArcticSpaSensorEntityDescription(
        key="ph_status",
        translation_key="ph_status",
        status_key="ph_status",
        device_class=SensorDeviceClass.ENUM,
        options=CHEMISTRY_STATES,
    ),
    ArcticSpaSensorEntityDescription(
        key="orp_status",
        translation_key="orp_status",
        status_key="orp_status",
        device_class=SensorDeviceClass.ENUM,
        options=CHEMISTRY_STATES,
    ),
    ArcticSpaSensorEntityDescription(
        key="filter_status",
        translation_key="filter_status",
        status_key="filter_status",
        device_class=SensorDeviceClass.ENUM,
        options=FILTER_STATES,
    ),
    ArcticSpaSensorEntityDescription(
        key="filter_duration_sensor",
        translation_key="filter_duration_sensor",
        status_key="filter_duration",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_registry_enabled_default=False,
    ),
    ArcticSpaSensorEntityDescription(
        key="filter_frequency_sensor",
        translation_key="filter_frequency_sensor",
        status_key="filter_frequency",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors for the fields this spa reports."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        ArcticSpaSensor(coordinator, description)
        for description in SENSORS
        if description.status_key in coordinator.data
    ]
    entities.append(ArcticSpaErrorSensor(coordinator))
    async_add_entities(entities)


class ArcticSpaSensor(ArcticSpaEntity, SensorEntity):
    """A read-only value from the status document."""

    entity_description: ArcticSpaSensorEntityDescription

    def __init__(
        self,
        coordinator: ArcticSpaCoordinator,
        description: ArcticSpaSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the value, or None while the field is missing."""
        value = self._status.get(self.entity_description.status_key)
        if value is None:
            return None
        return self.entity_description.value_fn(value)


class ArcticSpaErrorSensor(ArcticSpaEntity, SensorEntity):
    """Active spa error codes, e.g. a FLO (flow) fault.

    The state is the first active code so it is glanceable and can be used
    directly in a notification; the full list is on the attributes.
    """

    _attr_translation_key = "error"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the error sensor."""
        super().__init__(coordinator, "error")

    @property
    def available(self) -> bool:
        """Stay available when the spa is offline so faults remain readable."""
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> str:
        """Return the first active error code, or 'none'."""
        errors = self._status.get("errors") or []
        return errors[0] if errors else "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose every active error code."""
        errors = self._status.get("errors") or []
        return {"errors": errors, "error_count": len(errors)}
