from __future__ import annotations

import json

import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.api.models import CreateWebhookRequest, WebhookTarget
from manus_cli.api.webhooks import WebhookService


class TestWebhookService:
    async def test_create_webhook(self):
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.post("/webhooks").mock(
                return_value=httpx.Response(200, json={"webhook_id": "wh_123"})
            )

            async with ManusClient(api_key="test-key") as client:
                response = await WebhookService(client).create(
                    CreateWebhookRequest(webhook=WebhookTarget(url="https://example.com/hook"))
                )

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload == {"webhook": {"url": "https://example.com/hook"}}
        assert response.webhook_id == "wh_123"

    async def test_delete_webhook(self):
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.delete("/webhooks/wh_123").mock(return_value=httpx.Response(204))

            async with ManusClient(api_key="test-key") as client:
                await WebhookService(client).delete("wh_123")
