"""Polling coordinator for the Arctic Spa integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ArcticSpaAuthError, ArcticSpaClient, ArcticSpaError
from .const import COMMAND_REFRESH_DELAY, DEFAULT_SCAN_INTERVAL, DOMAIN

if TYPE_CHECKING:
    from . import ArcticSpaConfigEntry

_LOGGER = logging.getLogger(__name__)


class ArcticSpaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch spa status on a timer and after every command."""

    config_entry: ArcticSpaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ArcticSpaConfigEntry,
        client: ArcticSpaClient,
    ) -> None:
        """Initialise the coordinator."""
        self.client = client
        self._cancel_command_refresh: CALLBACK_TYPE | None = None
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Pull the status document."""
        try:
            return await self.client.async_get_status()
        except ArcticSpaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ArcticSpaError as err:
            raise UpdateFailed(str(err)) from err

    @callback
    def async_apply_optimistic(self, **values: Any) -> None:
        """Assume a command took effect, then verify with a delayed refresh.

        The cloud lags the spa by several seconds, so re-reading immediately
        would hand back the old value and make entities flap.
        """
        if self.data is not None:
            self.data.update(values)
            self.async_update_listeners()
        self.async_schedule_command_refresh()

    @callback
    def async_schedule_command_refresh(self) -> None:
        """Queue a single refresh, collapsing bursts of commands into one call."""
        if self._cancel_command_refresh is not None:
            self._cancel_command_refresh()
        self._cancel_command_refresh = async_call_later(
            self.hass, COMMAND_REFRESH_DELAY, self._async_command_refresh
        )

    async def _async_command_refresh(self, _now: datetime) -> None:
        """Run the queued post-command refresh."""
        self._cancel_command_refresh = None
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Cancel any pending refresh on unload."""
        if self._cancel_command_refresh is not None:
            self._cancel_command_refresh()
            self._cancel_command_refresh = None
        await super().async_shutdown()
