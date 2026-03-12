from __future__ import annotations

import httpx
import respx
from rich.console import Console

from manus_cli.api.models import TaskDetail
from manus_cli.repl.renderer import OutputRenderer


class TestOutputRendererDownloads:
    def test_render_task_result_downloads_output_file_to_cwd(
        self, tmp_path, monkeypatch
    ):
        """File outputs should be downloaded into the current working directory."""
        monkeypatch.chdir(tmp_path)
        console = Console(record=True)
        renderer = OutputRenderer(console=console)
        task = TaskDetail.model_validate(
            {
                "id": "task-123",
                "status": "completed",
                "output": [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_file",
                                "fileName": "report.txt",
                                "fileUrl": "https://example.com/report.txt",
                            }
                        ],
                    }
                ],
            }
        )

        with respx.mock:
            respx.get("https://example.com/report.txt").mock(
                return_value=httpx.Response(200, content=b"hello world")
            )
            renderer.render_task_result(task)

        assert (tmp_path / "report.txt").read_bytes() == b"hello world"
        assert "saved to" in console.export_text()

    def test_render_task_result_avoids_overwriting_existing_file(
        self, tmp_path, monkeypatch
    ):
        """Downloaded files should get a unique name when the target already exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "report.txt").write_text("existing", encoding="utf-8")

        renderer = OutputRenderer(console=Console(record=True))
        task = TaskDetail.model_validate(
            {
                "id": "task-456",
                "status": "completed",
                "output": [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_file",
                                "fileName": "report.txt",
                                "fileUrl": "https://example.com/report.txt",
                            }
                        ],
                    }
                ],
            }
        )

        with respx.mock:
            respx.get("https://example.com/report.txt").mock(
                return_value=httpx.Response(200, content=b"new content")
            )
            renderer.render_task_result(task)

        assert (tmp_path / "report.txt").read_text(encoding="utf-8") == "existing"
        assert (tmp_path / "report-1.txt").read_bytes() == b"new content"
