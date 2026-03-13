from __future__ import annotations

from manus_cli.api.client import ManusClient
from manus_cli.api.models import CreateProjectRequest, ProjectInfo


class ProjectService:
    """Project operations via the Manus API."""

    def __init__(self, client: ManusClient) -> None:
        self._client = client

    async def create(self, request: CreateProjectRequest) -> ProjectInfo:
        data = await self._client.request(
            "POST",
            "/projects",
            json=request.model_dump(exclude_none=True, by_alias=True),
        )
        return ProjectInfo.model_validate(data)

    async def list(self, limit: int = 100) -> list[ProjectInfo]:
        data = await self._client.request("GET", "/projects", params={"limit": limit})
        projects = data if isinstance(data, list) else data.get("projects", data.get("data", []))
        return [ProjectInfo.model_validate(project) for project in projects]
