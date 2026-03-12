from __future__ import annotations

import asyncio

from typer.testing import CliRunner

import manus_cli.api.client as client_mod
import manus_cli.cli as cli_mod
from manus_cli.api.models import TaskDetail
from manus_cli.cli import app
from manus_cli.core.errors import AuthenticationError


runner = CliRunner()


def _raise_authentication_error() -> str:
    raise AuthenticationError(
        "No API key found. Set MANUS_API_KEY env var or run `manus auth login`."
    )


class TestCliErrorHandling:
    def test_task_list_renders_auth_error_without_traceback(self, monkeypatch):
        """task list should render a friendly auth error instead of a traceback."""
        monkeypatch.setattr(client_mod, "resolve_api_key", _raise_authentication_error)

        result = runner.invoke(app, ["task", "list"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "No API key found" in result.output
        assert "Traceback" not in result.output


class TestResumeCli:
    def test_root_resume_starts_repl_in_resume_mode(self, monkeypatch):
        captured: dict[str, object] = {}

        async def fake_start_repl(model: str, resume: bool = False):
            captured["model"] = model
            captured["resume"] = resume

        monkeypatch.setattr(cli_mod, "_start_repl", fake_start_repl)
        monkeypatch.setattr(cli_mod, "_run_command", lambda command: asyncio.run(command))

        result = runner.invoke(app, ["-r"])

        assert result.exit_code == 0
        assert captured == {"model": "manus-1.6", "resume": True}

    def test_resume_cannot_be_combined_with_prompt(self):
        result = runner.invoke(app, ["-r", "-p", "hello"])

        assert result.exit_code == 1
        assert "Cannot combine --prompt and --resume." in result.output

    def test_resolve_resume_selection_supports_index_and_task_id(self):
        tasks = [
            TaskDetail.model_validate({"id": "task-1", "status": "completed", "output": []}),
            TaskDetail.model_validate({"id": "task-2", "status": "completed", "output": []}),
        ]

        assert cli_mod._resolve_resume_selection("2", tasks) == tasks[1]
        assert cli_mod._resolve_resume_selection("task-1", tasks) == tasks[0]
        assert cli_mod._resolve_resume_selection("99", tasks) is None

    def test_chat_renders_auth_error_without_traceback(self, monkeypatch):
        """chat should render a friendly auth error instead of a traceback."""
        monkeypatch.setattr(client_mod, "resolve_api_key", _raise_authentication_error)

        result = runner.invoke(app, ["chat"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "No API key found" in result.output
        assert "Traceback" not in result.output
