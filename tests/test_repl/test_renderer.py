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

    def test_render_task_context_shows_history_without_downloading_files(
        self, tmp_path, monkeypatch
    ):
        """Loading prior context should not re-download historical file outputs."""
        monkeypatch.chdir(tmp_path)
        console = Console(record=True)
        renderer = OutputRenderer(console=console)
        task = TaskDetail.model_validate(
            {
                "id": "task-789",
                "status": "completed",
                "output": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Please summarize the report"}],
                    },
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": "Summary is ready."},
                            {
                                "type": "output_file",
                                "fileName": "report.txt",
                                "fileUrl": "https://example.com/report.txt",
                            },
                        ],
                    },
                ],
            }
        )

        renderer.render_task_context(task)

        assert not (tmp_path / "report.txt").exists()
        output = console.export_text()
        assert "Loaded context from task task-789" in output
        assert "Please summarize the report" in output
        assert "report.txt" in output
