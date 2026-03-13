from __future__ import annotations

import asyncio
from types import SimpleNamespace

from typer.testing import CliRunner

import manus_cli.api.client as client_mod
import manus_cli.cli as cli_mod
import manus_cli.repl.prompt as prompt_mod
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

    async def test_select_resume_task_uses_interactive_selector(self, monkeypatch):
        tasks = [
            TaskDetail.model_validate({"id": "task-1", "status": "completed", "output": []}),
            TaskDetail.model_validate({"id": "task-2", "status": "running", "output": []}),
        ]

        async def fake_list(limit: int = 20):
            assert limit == 20
            return tasks

        async def fake_get(task_id: str):
            assert task_id == "task-2"
            return tasks[1]

        async def fake_select_resume_task_interactively(items):
            assert items == tasks
            return "task-2"

        monkeypatch.setattr(prompt_mod, "supports_interactive_resume_selector", lambda: True)
        monkeypatch.setattr(
            prompt_mod,
            "select_resume_task_interactively",
            fake_select_resume_task_interactively,
        )

        session = SimpleNamespace(
            task_service=SimpleNamespace(list=fake_list, get=fake_get),
        )

        selected, cancelled = await cli_mod._select_resume_task(session)

        assert cancelled is False
        assert selected == tasks[1]

    async def test_select_resume_task_falls_back_to_text_prompt(self, monkeypatch):
        tasks = [
            TaskDetail.model_validate({"id": "task-1", "status": "completed", "output": []}),
            TaskDetail.model_validate({"id": "task-2", "status": "running", "output": []}),
        ]

        async def fake_list(limit: int = 20):
            return tasks

        async def fake_get(task_id: str):
            assert task_id == "task-1"
            return tasks[0]

        monkeypatch.setattr(prompt_mod, "supports_interactive_resume_selector", lambda: False)
        monkeypatch.setattr(cli_mod.console, "input", lambda prompt: "1")

        session = SimpleNamespace(
            task_service=SimpleNamespace(list=fake_list, get=fake_get),
        )

        selected, cancelled = await cli_mod._select_resume_task(session)

        assert cancelled is False
        assert selected == tasks[0]

    def test_chat_renders_auth_error_without_traceback(self, monkeypatch):
        """chat should render a friendly auth error instead of a traceback."""
        monkeypatch.setattr(client_mod, "resolve_api_key", _raise_authentication_error)

        result = runner.invoke(app, ["chat"])

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "No API key found" in result.output
        assert "Traceback" not in result.output


class TestApiCoverageCli:
    def test_task_update_requires_at_least_one_field(self):
        result = runner.invoke(app, ["task", "update", "task-1"])

        assert result.exit_code == 1
        assert "Provide at least one update field" in result.output

    def test_task_update_parses_new_flags(self, monkeypatch):
        captured: dict[str, object] = {}

        async def fake_task_update(task_id: str, title: str | None, share: bool | None, visible: bool | None):
            captured["task_id"] = task_id
            captured["title"] = title
            captured["share"] = share
            captured["visible"] = visible

        monkeypatch.setattr(cli_mod, "_task_update", fake_task_update)
        monkeypatch.setattr(cli_mod, "_run_command", lambda command: asyncio.run(command))

        result = runner.invoke(
            app,
            ["task", "update", "task-1", "--title", "Renamed", "--share", "--hidden"],
        )

        assert result.exit_code == 0
        assert captured == {
            "task_id": "task-1",
            "title": "Renamed",
            "share": True,
            "visible": False,
        }

    def test_new_command_groups_are_available(self):
        project_help = runner.invoke(app, ["project", "--help"])
        webhook_help = runner.invoke(app, ["webhook", "--help"])

        assert project_help.exit_code == 0
        assert "create" in project_help.output
        assert "list" in project_help.output

        assert webhook_help.exit_code == 0
        assert "create" in webhook_help.output
        assert "delete" in webhook_help.output
