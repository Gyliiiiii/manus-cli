from __future__ import annotations

import json

import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.api.models import CreateProjectRequest
from manus_cli.api.projects import ProjectService


class TestProjectService:
    async def test_create_project(self):
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.post("/projects").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "proj-1",
                        "name": "Workspace",
                        "instruction": "Always cite sources",
                        "created_at": 1735689600,
                    },
                )
            )

            async with ManusClient(api_key="test-key") as client:
                project = await ProjectService(client).create(
                    CreateProjectRequest(name="Workspace", instruction="Always cite sources")
                )

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload == {"name": "Workspace", "instruction": "Always cite sources"}
        assert project.project_id == "proj-1"
        assert project.created_at == "2025-01-01T00:00:00Z"

    async def test_list_projects_reads_data_shape(self):
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.get("/projects").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "data": [
                            {"id": "proj-1", "name": "Workspace"},
                            {"id": "proj-2", "name": "Personal"},
                        ]
                    },
                )
            )

            async with ManusClient(api_key="test-key") as client:
                projects = await ProjectService(client).list(limit=2)

        assert [p.project_id for p in projects] == ["proj-1", "proj-2"]
