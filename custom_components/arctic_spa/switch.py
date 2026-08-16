"""Switch platform - pumps, blowers and the spa's on/off features."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import ArcticSpaConfigEntry
from .api import ArcticSpaClient
from .const import BLOWER_KEYS, PUMP_KEYS
from .coordinator import ArcticSpaCoordinator
from .entity import ArcticSpaEntity


@dataclass(frozen=True, kw_only=True)
class ArcticSpaSwitchEntityDescription(SwitchEntityDescription):
    """Describes an Arctic Spa switch."""

    status_key: str
    set_fn: Callable[[ArcticSpaClient, bool], Awaitable[None]]
    # Value written into the cached status document for optimistic updates.
    on_value: Any = "on"
    off_value: Any = "off"


FEATURE_SWITCHES: tuple[ArcticSpaSwitchEntityDescription, ...] = (
    ArcticSpaSwitchEntityDescription(
        key="sds",
        translation_key="sds",
        status_key="sds",
        set_fn=lambda client, state: client.async_set_sds(state),
    ),
    ArcticSpaSwitchEntityDescription(
        key="yess",
        translation_key="yess",
        status_key="yess",
        set_fn=lambda client, state: client.async_set_yess(state),
    ),
    ArcticSpaSwitchEntityDescription(
        key="fogger",
        translation_key="fogger",
        status_key="fogger",
        set_fn=lambda client, state: client.async_set_fogger(state),
    ),
    ArcticSpaSwitchEntityDescription(
        key="filter_suspension",
        translation_key="filter_suspension",
        status_key="filter_suspension",
        entity_category=EntityCategory.CONFIG,
        set_fn=lambda client, state: client.async_set_filter(suspension=state),
        on_value=True,
        off_value=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ArcticSpaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches for whatever hardware this spa reports."""
    coordinator = entry.runtime_data
    status = coordinator.data
    entities: list[SwitchEntity] = []

    for index, key in enumerate(PUMP_KEYS, start=1):
        if key in status:
            entities.append(ArcticSpaPumpSwitch(coordinator, key, str(index)))

    for index, key in enumerate(BLOWER_KEYS, start=1):
        if key in status:
            entities.append(ArcticSpaBlowerSwitch(coordinator, key, str(index)))

    entities.extend(
        ArcticSpaFeatureSwitch(coordinator, description)
        for description in FEATURE_SWITCHES
        if description.status_key in status
    )

    # Filtration and Easy Mode accept commands but are never echoed back in the
    # status document, so they are tracked optimistically instead.
    entities.append(ArcticSpaFiltrationSwitch(coordinator))
    entities.append(ArcticSpaEasyModeSwitch(coordinator))

    async_add_entities(entities)


class ArcticSpaFeatureSwitch(ArcticSpaEntity, SwitchEntity):
    """A switch backed by a status field."""

    entity_description: ArcticSpaSwitchEntityDescription

    def __init__(
        self,
        coordinator: ArcticSpaCoordinator,
        description: ArcticSpaSwitchEntityDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the current state from the status document."""
        value = self._status.get(self.entity_description.status_key)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        return value != "off"

    async def _async_set(self, state: bool) -> None:
        """Send the command and assume it worked."""
        description = self.entity_description
        await description.set_fn(self.coordinator.client, state)
        self.coordinator.async_apply_optimistic(
            **{
                description.status_key: (
                    description.on_value if state else description.off_value
                )
            }
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the feature on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the feature off."""
        await self._async_set(False)


class ArcticSpaPumpSwitch(ArcticSpaEntity, SwitchEntity):
    """A jet pump.

    Pump 1 is a two-speed circulation pump; the rest are single-speed. Turning
    a pump "on" always requests high, which is what the app's button does.
    """

    _attr_translation_key = "pump"

    def __init__(
        self, coordinator: ArcticSpaCoordinator, status_key: str, number: str
    ) -> None:
        """Initialise the pump switch."""
        super().__init__(coordinator, status_key)
        self._status_key = status_key
        self._number = number
        self._attr_translation_placeholders = {"number": number}

    @property
    def is_on(self) -> bool | None:
        """Return whether the pump is running at any speed."""
        value = self._status.get(self._status_key)
        if value is None:
            return None
        return value != "off"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw speed so two-speed pumps are readable."""
        return {"speed": self._status.get(self._status_key)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Run the pump on high."""
        await self.coordinator.client.async_set_pump(self._number, "high")
        self.coordinator.async_apply_optimistic(**{self._status_key: "high"})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the pump."""
        await self.coordinator.client.async_set_pump(self._number, "off")
        self.coordinator.async_apply_optimistic(**{self._status_key: "off"})


class ArcticSpaBlowerSwitch(ArcticSpaEntity, SwitchEntity):
    """An air blower."""

    _attr_translation_key = "blower"

    def __init__(
        self, coordinator: ArcticSpaCoordinator, status_key: str, number: str
    ) -> None:
        """Initialise the blower switch."""
        super().__init__(coordinator, status_key)
        self._status_key = status_key
        self._number = number
        self._attr_translation_placeholders = {"number": number}

    @property
    def is_on(self) -> bool | None:
        """Return whether the blower is running."""
        value = self._status.get(self._status_key)
        if value is None:
            return None
        return value != "off"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the blower on."""
        await self.coordinator.client.async_set_blower(self._number, True)
        self.coordinator.async_apply_optimistic(**{self._status_key: "on"})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the blower off."""
        await self.coordinator.client.async_set_blower(self._number, False)
        self.coordinator.async_apply_optimistic(**{self._status_key: "off"})


class ArcticSpaWriteOnlySwitch(ArcticSpaEntity, SwitchEntity, RestoreEntity):
    """A switch for a command the API never reports back.

    State is whatever was last commanded, restored across restarts, and marked
    assumed so the UI shows separate on/off buttons rather than a toggle that
    might be lying.
    """

    _attr_assumed_state = True

    def __init__(self, coordinator: ArcticSpaCoordinator, key: str) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, key)
        self._is_on: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last commanded state."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == STATE_ON

    @property
    def is_on(self) -> bool | None:
        """Return the last commanded state."""
        return self._is_on

    async def _async_send(self, state: bool) -> None:
        """Send the command - implemented per feature."""
        raise NotImplementedError

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the feature on."""
        await self._async_send(True)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the feature off."""
        await self._async_send(False)
        self._is_on = False
        self.async_write_ha_state()


class ArcticSpaFiltrationSwitch(ArcticSpaWriteOnlySwitch):
    """Master on/off for the filtration cycle."""

    _attr_translation_key = "filtration"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the filtration switch."""
        super().__init__(coordinator, "filtration")

    async def _async_send(self, state: bool) -> None:
        """Enable or disable filtering."""
        await self.coordinator.client.async_set_filter(state=state)


class ArcticSpaEasyModeSwitch(ArcticSpaWriteOnlySwitch):
    """Easy Mode - the spa's simplified low-energy operating mode."""

    _attr_translation_key = "easy_mode"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ArcticSpaCoordinator) -> None:
        """Initialise the Easy Mode switch."""
        super().__init__(coordinator, "easy_mode")

    async def _async_send(self, state: bool) -> None:
        """Turn Easy Mode on or off."""
        await self.coordinator.client.async_set_easy_mode(state)
