"""Base entity for the Arctic Spa integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONFIGURATION_URL, DOMAIN, MANUFACTURER
from .coordinator import ArcticSpaCoordinator


class ArcticSpaEntity(CoordinatorEntity[ArcticSpaCoordinator]):
    """Common device info and availability handling."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ArcticSpaCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer=MANUFACTURER,
            name="Arctic Spa",
            model="Hot Tub",
            configuration_url=CONFIGURATION_URL,
        )

    @property
    def _status(self) -> dict[str, Any]:
        """Return the latest status document."""
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        """Control entities are unavailable while the spa is offline.

        `connected` false means the cloud has the spa registered but cannot
        reach it, so commands would be silently dropped.
        """
        return super().available and self._status.get("connected") is not False
