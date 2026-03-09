from __future__ import annotations

from manus_cli.api.client import ManusClient
from manus_cli.api.models import CreateTaskRequest, CreateTaskResponse, TaskDetail


class TaskService:
    """CRUD operations for Manus tasks."""

    def __init__(self, client: ManusClient) -> None:
        self._client = client

    async def create(self, request: CreateTaskRequest) -> CreateTaskResponse:
        data = await self._client.request(
            "POST", "/tasks", json=request.model_dump(exclude_none=True)
        )
        return CreateTaskResponse.model_validate(data)

    async def get(self, task_id: str) -> TaskDetail:
        data = await self._client.request("GET", f"/tasks/{task_id}")
        return TaskDetail.model_validate(data)

    async def list(self, limit: int = 20, offset: int = 0) -> list[TaskDetail]:
        data = await self._client.request(
            "GET", "/tasks", params={"limit": limit, "offset": offset}
        )
        # API might return {"tasks": [...]} or just [...]
        tasks = data if isinstance(data, list) else data.get("tasks", data.get("data", []))
        return [TaskDetail.model_validate(t) for t in tasks]

    async def delete(self, task_id: str) -> None:
        await self._client.request("DELETE", f"/tasks/{task_id}")
