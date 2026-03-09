from __future__ import annotations

from pathlib import Path

import httpx

from manus_cli.api.client import ManusClient
from manus_cli.api.models import FileInfo, PresignedUpload


class FileService:
    """File upload/download operations via the Manus API."""

    def __init__(self, client: ManusClient) -> None:
        self._client = client

    async def create_upload(self, file_name: str) -> PresignedUpload:
        """Request a presigned upload URL for a new file."""
        data = await self._client.request(
            "POST", "/files", json={"file_name": file_name}
        )
        return PresignedUpload.model_validate(data)

    async def upload(self, file_path: Path) -> FileInfo:
        """Create a presigned upload URL, upload the file, and return file info."""
        presigned = await self.create_upload(file_path.name)
        async with httpx.AsyncClient() as upload_client:
            with open(file_path, "rb") as f:
                resp = await upload_client.put(presigned.upload_url, content=f.read())
                resp.raise_for_status()
        return FileInfo(file_id=presigned.file_id, file_name=file_path.name)

    async def list(self, limit: int = 20) -> list[FileInfo]:
        """List uploaded files."""
        data = await self._client.request("GET", "/files", params={"limit": limit})
        files = data if isinstance(data, list) else data.get("files", data.get("data", []))
        return [FileInfo.model_validate(f) for f in files]

    async def get(self, file_id: str) -> FileInfo:
        """Get metadata for a single file."""
        data = await self._client.request("GET", f"/files/{file_id}")
        return FileInfo.model_validate(data)

    async def delete(self, file_id: str) -> None:
        """Delete an uploaded file."""
        await self._client.request("DELETE", f"/files/{file_id}")
