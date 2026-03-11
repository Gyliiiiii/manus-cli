from __future__ import annotations

import json

import httpx
import respx

from manus_cli.api.client import ManusClient
from manus_cli.api.files import FileService


class TestCreateUpload:
    async def test_create_upload_uses_filename_and_parses_aliases(self):
        """File upload creation should follow the official filename/id schema."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            route = router.post("/files").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "id": "file-123",
                        "filename": "report.txt",
                        "upload_url": "https://example.com/upload",
                    },
                )
            )

            async with ManusClient(api_key="test-key") as client:
                upload = await FileService(client).create_upload("report.txt")

        payload = json.loads(route.calls.last.request.content.decode())
        assert payload == {"filename": "report.txt"}
        assert upload.file_id == "file-123"
        assert upload.file_name == "report.txt"
        assert upload.upload_url == "https://example.com/upload"


class TestListFiles:
    async def test_list_files_accepts_official_shape(self):
        """File listing should parse id/filename fields from the API."""
        with respx.mock(base_url="https://api.manus.ai/v1") as router:
            router.get("/files").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "files": [
                            {
                                "id": "file-123",
                                "filename": "report.txt",
                                "size": 128,
                            }
                        ]
                    },
                )
            )

            async with ManusClient(api_key="test-key") as client:
                files = await FileService(client).list()

        assert len(files) == 1
        assert files[0].file_id == "file-123"
        assert files[0].file_name == "report.txt"
        assert files[0].file_size == 128
