from __future__ import annotations

import json

import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.api.models import AgentProfile, CreateTaskRequest, TaskStatus
from manus_cli.api.tasks import TaskService


class TestCreateTask:
    async def test_create_uses_official_payload_aliases(self):
        """Task creation should serialize using the official Manus field names."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.post("/tasks").mock(
                return_value=httpx.Response(
                    200,
                    json={"id": "task-123", "status": "pending"},
                )
            )

            async with ManusClient(api_key="test-key") as client:
                response = await TaskService(client).create(
                    CreateTaskRequest(
                        prompt="Hello",
                        agent_profile=AgentProfile.MAX,
                        task_id="task-prev",
                    )
                )

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload["prompt"] == "Hello"
        assert payload["agentProfile"] == "manus-1.6-max"
        assert payload["taskId"] == "task-prev"
        assert "agent_profile" not in payload
        assert response.task_id == "task-123"
        assert response.status is TaskStatus.PENDING
