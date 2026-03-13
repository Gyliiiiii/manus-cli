from __future__ import annotations

import json

import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.api.models import (
    AgentProfile,
    CreateTaskRequest,
    FileIdAttachment,
    TaskStatus,
    UpdateTaskRequest,
)
from manus_cli.api.tasks import TaskService


class TestCreateTask:
    async def test_create_uses_official_payload_aliases(self):
        """Task creation should serialize using the official Manus field names."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.post("/tasks").mock(
                return_value=httpx.Response(
                    200,
                    json={"task_id": "task-123", "task_title": "hello"},
                )
            )

            async with ManusClient(api_key="test-key") as client:
                response = await TaskService(client).create(
                    CreateTaskRequest(
                        prompt="Hello",
                        agent_profile=AgentProfile.MAX,
                        task_id="task-prev",
                        attachments=[FileIdAttachment(filename="x.txt", file_id="file-1")],
                    )
                )

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload["prompt"] == "Hello"
        assert payload["agentProfile"] == "manus-1.6-max"
        assert payload["taskId"] == "task-prev"
        assert payload["attachments"] == [{"filename": "x.txt", "file_id": "file-1"}]
        assert "agent_profile" not in payload
        assert response.task_id == "task-123"
        assert response.task_title == "hello"
        assert response.status is TaskStatus.PENDING


class TestUpdateTask:
    async def test_update_task_uses_official_payload_aliases(self):
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.put("/tasks/task-123").mock(
                return_value=httpx.Response(
                    200,
                    json={"task_id": "task-123", "task_title": "Renamed"},
                )
            )

            async with ManusClient(api_key="test-key") as client:
                response = await TaskService(client).update(
                    "task-123",
                    UpdateTaskRequest(
                        title="Renamed",
                        enable_shared=True,
                        enable_visible_in_task_list=False,
                    ),
                )

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload == {
            "title": "Renamed",
            "enableShared": True,
            "enableVisibleInTaskList": False,
        }
        assert response.task_id == "task-123"
        assert response.task_title == "Renamed"
