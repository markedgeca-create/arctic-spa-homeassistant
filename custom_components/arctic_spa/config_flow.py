"""Config flow for the Arctic Spa integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from hashlib import sha256
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    ArcticSpaAuthError,
    ArcticSpaClient,
    ArcticSpaConnectionError,
    ArcticSpaError,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

if TYPE_CHECKING:
    from . import ArcticSpaConfigEntry

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        )
    }
)


class ArcticSpaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the API-key setup flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the API key and verify it against the status endpoint."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            errors = await self._async_validate(api_key)
            if not errors:
                # The API exposes no spa identifier, so the key itself is the
                # only stable handle. Hash it rather than storing it twice.
                await self.async_set_unique_id(_key_fingerprint(api_key))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Arctic Spa", data={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauth when the stored key stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect a replacement API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            errors = await self._async_validate(api_key)
            if not errors:
                await self.async_set_unique_id(_key_fingerprint(api_key))
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data_updates={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def _async_validate(self, api_key: str) -> dict[str, str]:
        """Return form errors for a candidate API key."""
        client = ArcticSpaClient(async_get_clientsession(self.hass), api_key)
        try:
            await client.async_get_status()
        except ArcticSpaAuthError:
            return {"base": "invalid_auth"}
        except ArcticSpaConnectionError:
            return {"base": "cannot_connect"}
        except ArcticSpaError:
            # The generic form is unhelpful on its own, so record what the API
            # actually said - it lands in Settings > System > Logs.
            _LOGGER.exception("Unexpected error validating the Arctic Spas API key")
            return {"base": "unknown"}
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(entry: ArcticSpaConfigEntry) -> ArcticSpaOptionsFlow:
        """Return the options flow."""
        return ArcticSpaOptionsFlow()


class ArcticSpaOptionsFlow(OptionsFlow):
    """Let the user tune the polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the polling interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _key_fingerprint(api_key: str) -> str:
    """Hash the API key for use as the config entry unique ID."""
    return sha256(api_key.encode("utf-8")).hexdigest()
