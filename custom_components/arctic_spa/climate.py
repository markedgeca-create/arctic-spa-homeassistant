"""Climate platform - the spa's heater setpoint."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ArcticSpaConfigEntry
from .const import MAX_TEMP_F, MIN_TEMP_F
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the spa thermostat."""
    async_add_entities([ArcticSpaThermostat(entry.runtime_data)])


class ArcticSpaThermostat(ArcticSpaEntity, ClimateEntity):
    """The spa heater, exposed as a heat-only thermostat."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_target_temperature_step = 1
    _attr_min_temp = MIN_TEMP_F
    _attr_max_temp = MAX_TEMP_F

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the thermostat."""
        super().__init__(coordinator, "thermostat")

    @property
    def current_temperature(self) -> float | None:
        """Return the measured water temperature."""
        return self._status.get("temperatureF")

    @property
    def target_temperature(self) -> float | None:
        """Return the configured setpoint."""
        return self._status.get("setpointF")

    @property
    def hvac_action(self) -> HVACAction | None:
        """Infer heating vs. idle - the API reports no heater relay state."""
        current = self._status.get("temperatureF")
        target = self._status.get("setpointF")
        if current is None or target is None:
            return None
        return HVACAction.HEATING if current < target else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set a new setpoint.

        Home Assistant hands this value over already converted into the
        entity's unit (Fahrenheit), so it only needs rounding.
        """
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        setpoint = int(round(temperature))
        await self.coordinator.client.async_set_temperature(setpoint)
        self.coordinator.async_apply_optimistic(setpointF=setpoint)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Accept the only supported mode; the spa cannot be switched off."""
