from __future__ import annotations

import manus_cli.repl.prompt as prompt_mod
from manus_cli.api.models import TaskDetail


class TestResumePrompt:
    def test_format_resume_task_label_includes_preview_with_index(self):
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
        assert "completed" not in label
        assert "2026-03-12" not in label

    def test_format_resume_task_meta_includes_status_created_task_id(self):
        task = TaskDetail.model_validate(
            {
                "id": "task-1234567890abcdef",
                "status": "completed",
                "created_at": "2026-03-12T16:52:00Z",
                "output": [],
            }
        )

        meta = prompt_mod.format_resume_task_meta(task)

        assert "completed" in meta
        assert "2026-03-12 16:52" in meta
        assert "task-123...abcdef" in meta

    def test_render_resume_selector_marks_selected_item(self, monkeypatch):
        tasks = [
            TaskDetail.model_validate({"id": "task-1", "status": "completed", "output": []}),
            TaskDetail.model_validate({"id": "task-2", "status": "running", "output": []}),
        ]
        monkeypatch.setattr(prompt_mod, "_resume_selector_visible_count", lambda: 5)

        fragments = prompt_mod._render_resume_selector(tasks, selected_index=1, window_start=0)
        rendered = "".join(text for _, text in fragments)

        assert "Resume Conversation" in rendered
        assert "❯  2. (no preview)" in rendered
        assert "running | unknown time | task-2" in rendered
