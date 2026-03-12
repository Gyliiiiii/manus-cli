from __future__ import annotations

from types import SimpleNamespace

import manus_cli.repl.prompt as prompt_mod
from manus_cli.api.models import TaskDetail


class TestResumePrompt:
    def test_format_resume_task_label_includes_preview_metadata(self):
        task = TaskDetail.model_validate(
            {
                "id": "task-1234567890abcdef",
                "status": "completed",
                "created_at": "2026-03-12T16:52:00Z",
                "output": [
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "Summarized quarterly report"}],
                    }
                ],
            }
        )

        label = prompt_mod.format_resume_task_label(task, 2)

        assert " 2." in label
        assert "Summarized quarterly report" in label
        assert "[completed]" in label
        assert "2026-03-12 16:52" in label
        assert "task-123...abcdef" in label

    async def test_select_resume_task_interactively_returns_selected_id(self, monkeypatch):
        seen: dict[str, object] = {}
        tasks = [
            TaskDetail.model_validate({"id": "task-1", "status": "completed", "output": []}),
            TaskDetail.model_validate({"id": "task-2", "status": "running", "output": []}),
        ]

        async def fake_run_async():
            return "task-2"

        def fake_radiolist_dialog(**kwargs):
            seen.update(kwargs)
            return SimpleNamespace(run_async=fake_run_async)

        monkeypatch.setattr(prompt_mod, "radiolist_dialog", fake_radiolist_dialog)

        selected = await prompt_mod.select_resume_task_interactively(tasks)

        assert selected == "task-2"
        assert seen["title"] == "Resume Conversation"
        assert len(seen["values"]) == 2
        assert seen["values"][1][0] == "task-2"
