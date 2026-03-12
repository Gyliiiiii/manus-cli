from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import radiolist_dialog

from manus_cli.utils.display import task_preview

if TYPE_CHECKING:
    from manus_cli.api.models import TaskDetail

HISTORY_FILE = Path.home() / ".manus" / "history"


def create_prompt_session(slash_commands: list[str] | None = None) -> PromptSession:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    commands = slash_commands or []
    completer = WordCompleter(
        [f"/{cmd}" for cmd in commands],
        sentence=True,
    ) if commands else None

    return PromptSession(
        history=FileHistory(str(HISTORY_FILE)),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        message=HTML("<b>manus&gt;</b> "),
        multiline=False,
        enable_history_search=True,
    )


def supports_interactive_resume_selector() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def format_resume_task_label(task: TaskDetail, index: int) -> str:
    preview = task_preview(task, max_width=48) or "(no preview)"
    created = (task.created_at or "unknown time").replace("T", " ").replace("Z", "")
    created = created[:16]
    task_id = task.task_id
    if len(task_id) > 18:
        task_id = f"{task_id[:8]}...{task_id[-6:]}"
    return f"{index:>2}. {preview} [{task.status.value}] {created} {task_id}"


async def select_resume_task_interactively(tasks: list[TaskDetail]) -> str | None:
    values = [
        (task.task_id, format_resume_task_label(task, idx))
        for idx, task in enumerate(tasks, 1)
    ]
    app = radiolist_dialog(
        title="Resume Conversation",
        text="Use ↑/↓ to choose a task, Tab to switch buttons, Enter to confirm.",
        values=values,
        ok_text="Resume",
        cancel_text="Cancel",
    )
    return await app.run_async()
