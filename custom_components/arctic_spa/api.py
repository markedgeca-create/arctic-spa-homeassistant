"""Thin async client for the Arctic Spas public API.

Endpoints and payload shapes are taken from the published OpenAPI definition at
https://api.myarcticspa.com/docs. Everything is a PUT with a tiny JSON body
except the status read, which is a GET.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientSession

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://api.myarcticspa.com/v2/spa"
REQUEST_TIMEOUT = 30


class ArcticSpaError(Exception):
    """Base error for the Arctic Spas API."""


class ArcticSpaAuthError(ArcticSpaError):
    """The API key was rejected."""


class ArcticSpaRateLimitError(ArcticSpaError):
    """Too many requests were sent (HTTP 429)."""


class ArcticSpaConnectionError(ArcticSpaError):
    """The API could not be reached."""


class ArcticSpaClient:
    """Minimal client covering the whole v2 spa control surface."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialise the client with a shared aiohttp session."""
        self._session = session
        self._headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Send a request and translate transport/HTTP failures into our errors."""
        url = f"{API_BASE}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    raise ArcticSpaAuthError(
                        f"Arctic Spas rejected the API key (HTTP {response.status})"
                    )
                if response.status == 429:
                    raise ArcticSpaRateLimitError(
                        "Arctic Spas rate limit hit (HTTP 429); "
                        "increase the polling interval"
                    )
                if response.status == 503:
                    raise ArcticSpaConnectionError(
                        "The spa is unreachable from the Arctic Spas cloud (HTTP 503)"
                    )
                if response.status >= 400:
                    body = await response.text()
                    raise ArcticSpaError(f"HTTP {response.status} from {path}: {body}")

                if response.status == 204 or not response.content_length:
                    # Control endpoints answer 200/202 with an empty body.
                    text = await response.text()
                    if not text.strip():
                        return None
                    return None
                return await response.json(content_type=None)
        except TimeoutError as err:
            raise ArcticSpaConnectionError(f"Timeout talking to {path}") from err
        except asyncio.TimeoutError as err:  # pragma: no cover - py<3.11 alias
            raise ArcticSpaConnectionError(f"Timeout talking to {path}") from err
        except ClientError as err:
            raise ArcticSpaConnectionError(f"Error talking to {path}: {err}") from err

    async def async_get_status(self) -> dict[str, Any]:
        """GET /v2/spa/status - the single read endpoint.

        Keys are only present for hardware the spa actually has, which is what
        drives which entities this integration creates.
        """
        data = await self._request("GET", "/status")
        if not isinstance(data, dict):
            raise ArcticSpaError("Unexpected status payload from Arctic Spas")
        return data

    async def async_set_temperature(self, setpoint_f: int) -> None:
        """PUT /v2/spa/temperature."""
        await self._request("PUT", "/temperature", {"setpointF": int(setpoint_f)})

    async def async_set_light(self, state: bool) -> None:
        """PUT /v2/spa/lights."""
        await self._request("PUT", "/lights", {"state": _on_off(state)})

    async def async_set_pump(self, pump: str, state: str) -> None:
        """PUT /v2/spa/pumps/{pump}; state is off, low, high or on."""
        await self._request("PUT", f"/pumps/{pump}", {"state": state})

    async def async_set_blower(self, blower: str, state: bool) -> None:
        """PUT /v2/spa/blowers/{blower}."""
        await self._request("PUT", f"/blowers/{blower}", {"state": _on_off(state)})

    async def async_set_sds(self, state: bool) -> None:
        """PUT /v2/spa/sds - Silent Dual Speed pump mode."""
        await self._request("PUT", "/sds", {"state": _on_off(state)})

    async def async_set_yess(self, state: bool) -> None:
        """PUT /v2/spa/yess - Your Energy Savings System."""
        await self._request("PUT", "/yess", {"state": _on_off(state)})

    async def async_set_fogger(self, state: bool) -> None:
        """PUT /v2/spa/fogger."""
        await self._request("PUT", "/fogger", {"state": _on_off(state)})

    async def async_set_easy_mode(self, state: bool) -> None:
        """PUT /v2/spa/easymode - write only, not reported back in status."""
        await self._request("PUT", "/easymode", {"state": _on_off(state)})

    async def async_boost(self) -> None:
        """PUT /v2/spa/boost - fires a one-shot boost cycle, no body."""
        await self._request("PUT", "/boost")

    async def async_set_filter(
        self,
        *,
        state: bool | None = None,
        frequency: int | None = None,
        duration: int | None = None,
        suspension: bool | None = None,
    ) -> None:
        """PUT /v2/spa/filter - every field is optional and applied independently."""
        body: dict[str, Any] = {}
        if state is not None:
            body["state"] = _on_off(state)
        if frequency is not None:
            body["frequency"] = int(frequency)
        if duration is not None:
            body["duration"] = int(duration)
        if suspension is not None:
            body["suspension"] = suspension
        if not body:
            return
        await self._request("PUT", "/filter", body)


def _on_off(state: bool) -> str:
    """Map a boolean to the API's string enum."""
    return "on" if state else "off"
