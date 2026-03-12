from __future__ import annotations

from types import SimpleNamespace

import manus_cli.repl.session as session_mod
from manus_cli.api.models import TaskDetail
from manus_cli.core.errors import APIError


class TestReplSession:
    async def test_handle_prompt_retries_without_stale_task_id(self, monkeypatch):
        """REPL should restart the conversation when the previous task no longer exists."""
        monkeypatch.setattr(
            session_mod,
            "create_prompt_session",
            lambda *args, **kwargs: SimpleNamespace(prompt=lambda: ""),
        )

        session = session_mod.ReplSession(api_key="test-key")
        session.current_task_id = "task-stale"

        create_calls: list[str | None] = []
        info_messages: list[str] = []

        async def fake_create(request):
            create_calls.append(request.task_id)
            if len(create_calls) == 1:
                raise APIError(404, '{"code":5, "message":"task not found", "details":[]}')
            return SimpleNamespace(task_id="task-new")

        async def fake_poll(task_id: str) -> TaskDetail:
            return TaskDetail.model_validate({"id": task_id, "status": "completed", "output": []})

        session.task_service = SimpleNamespace(create=fake_create)
        session.poller = SimpleNamespace(poll=fake_poll)
        session.renderer = SimpleNamespace(
            render_info=info_messages.append,
            render_task_result=lambda task: None,
            render_error=lambda message: None,
        )

        await session._handle_prompt("hello")

        assert create_calls == ["task-stale", None]
        assert session.current_task_id == "task-new"
        assert any("Starting a new conversation" in message for message in info_messages)

    def test_load_task_context_sets_history_and_renders_context(self, monkeypatch):
        """Loading a resumed task should populate local history and render prior messages."""
        monkeypatch.setattr(
            session_mod,
            "create_prompt_session",
            lambda *args, **kwargs: SimpleNamespace(prompt=lambda: ""),
        )

        session = session_mod.ReplSession(api_key="test-key")
        rendered: list[str] = []
        session.renderer = SimpleNamespace(render_task_context=lambda task: rendered.append(task.task_id))

        task = TaskDetail.model_validate(
            {
                "id": "task-ctx",
                "status": "completed",
                "output": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": "Hello from history"}],
                    },
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Hi there"}],
                    },
                ],
            }
        )

        session.load_task_context(task)

        assert session.current_task_id == "task-ctx"
        assert session.history == [
            {"role": "user", "preview": "Hello from history"},
            {"role": "assistant", "preview": "Hi there"},
        ]
        assert rendered == ["task-ctx"]
