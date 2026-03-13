from __future__ import annotations

from manus_cli.api.client import ManusClient
from manus_cli.api.models import CreateWebhookRequest, CreateWebhookResponse


class WebhookService:
    """Webhook operations via the Manus API."""

    def __init__(self, client: ManusClient) -> None:
        self._client = client

    async def create(self, request: CreateWebhookRequest) -> CreateWebhookResponse:
        data = await self._client.request(
            "POST",
            "/webhooks",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return CreateWebhookResponse.model_validate(data)

    async def delete(self, webhook_id: str) -> None:
        await self._client.request("DELETE", f"/webhooks/{webhook_id}")
