from __future__ import annotations

import httpx

from manus_cli.core.auth import resolve_api_key
from manus_cli.core.errors import APIError

BASE_URL = "https://api.manus.ai/v1"


class ManusClient:
    """Async HTTP client for the Manus API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or resolve_api_key()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={"API_KEY": self._api_key},
                timeout=30.0,
            )
        return self._client

    async def request(self, method: str, path: str, **kwargs: object) -> object:
        """Send an HTTP request and return the parsed JSON response."""
        client = await self._get_client()
        response = await client.request(method, path, **kwargs)
        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise APIError(response.status_code, str(detail))
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self) -> ManusClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
