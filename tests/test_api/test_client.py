from __future__ import annotations

import pytest
import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.core.errors import APIError


class TestRequestSuccess:
    async def test_request_success(self):
        """A successful GET should return the parsed JSON body."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.get("/tasks").mock(
                return_value=httpx.Response(
                    200,
                    json={"tasks": [{"task_id": "t1", "status": "pending"}]},
                )
            )

            async with ManusClient(api_key="test-key") as client:
                result = await client.request("GET", "/tasks")

        assert result == {"tasks": [{"task_id": "t1", "status": "pending"}]}

    async def test_request_handles_no_content(self):
        """A 204 response should not attempt JSON parsing."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.delete("/tasks/t1").mock(return_value=httpx.Response(204))

            async with ManusClient(api_key="test-key") as client:
                result = await client.request("DELETE", "/tasks/t1")

        assert result == {}


class TestRequestRaisesAPIError:
    async def test_request_raises_api_error(self):
        """A 401 response should raise APIError with status and detail."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.get("/tasks").mock(
                return_value=httpx.Response(
                    401,
                    json={"detail": "Invalid API key"},
                )
            )

            async with ManusClient(api_key="bad-key") as client:
                with pytest.raises(APIError) as exc_info:
                    await client.request("GET", "/tasks")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid API key"
