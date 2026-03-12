from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

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


def _format_resume_task_id(task_id: str) -> str:
    if len(task_id) > 18:
        return f"{task_id[:8]}...{task_id[-6:]}"
    return task_id


def _format_resume_task_preview(task: TaskDetail, max_width: int = 64) -> str:
    preview = task_preview(task, max_width=max_width) or "(no preview)"
    return " ".join(preview.split())


def format_resume_task_label(task: TaskDetail, index: int) -> str:
    return f"{index:>2}. {_format_resume_task_preview(task)}"


def format_resume_task_meta(task: TaskDetail) -> str:
    created = (task.created_at or "unknown time").replace("T", " ").replace("Z", "")
    created = created[:16]
    return f"{task.status.value} | {created} | {_format_resume_task_id(task.task_id)}"


def _resume_selector_visible_count() -> int:
    default_rows = 24
    try:
        rows = get_app().output.get_size().rows
    except Exception:
        rows = default_rows
    # Header/footer takes ~9 lines, each item takes 2 lines.
    return max(3, (rows - 9) // 2)


def _resume_selector_width() -> int:
    default_columns = 80
    try:
        columns = get_app().output.get_size().columns
    except Exception:
        columns = default_columns
    return max(48, min(96, columns - 2))


def _render_resume_selector(
    tasks: list[TaskDetail],
    selected_index: int,
    window_start: int,
) -> list[tuple[str, str]]:
    visible_count = _resume_selector_visible_count()
    window_end = min(len(tasks), window_start + visible_count)
    divider = "─" * _resume_selector_width()
    selected_task = tasks[selected_index]

    fragments: list[tuple[str, str]] = [
        ("class:title", "Resume Conversation\n"),
        ("class:divider", f"{divider}\n"),
        ("class:hint", "Use ↑/↓ (or j/k) to navigate | Enter to resume | Esc to cancel\n"),
        ("class:divider", f"{divider}\n"),
    ]

    for idx in range(window_start, window_end):
        task = tasks[idx]
        is_selected = idx == selected_index
        marker = "❯" if is_selected else " "
        marker_style = "class:selected-marker" if is_selected else "class:item-marker"
        index_style = "class:selected-index" if is_selected else "class:item-index"
        title_style = "class:selected-title" if is_selected else "class:item-title"
        meta_style = "class:selected-meta" if is_selected else "class:item-meta"
        preview = _format_resume_task_preview(task)

        fragments.append((marker_style, f"{marker} "))
        fragments.append((index_style, f"{idx + 1:>2}. "))
        fragments.append((title_style, f"{preview}\n"))
        fragments.append((meta_style, f"    {format_resume_task_meta(task)}\n"))

    fragments.append(("class:divider", f"{divider}\n"))
    fragments.append(
        (
            "class:footer",
            f"Showing {window_start + 1}-{window_end} of {len(tasks)} | "
            f"Selected {_format_resume_task_id(selected_task.task_id)} ({selected_index + 1}/{len(tasks)})\n",
        )
    )

    return fragments


async def select_resume_task_interactively(tasks: list[TaskDetail]) -> str | None:
    selected_index = 0
    window_start = 0

    def ensure_visible() -> None:
        nonlocal window_start
        visible_count = _resume_selector_visible_count()
        if selected_index < window_start:
            window_start = selected_index
        elif selected_index >= window_start + visible_count:
            window_start = selected_index - visible_count + 1

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _move_up(event) -> None:
        nonlocal selected_index
        if selected_index <= 0:
            return
        selected_index -= 1
        ensure_visible()
        event.app.invalidate()

    @kb.add("down")
    @kb.add("j")
    def _move_down(event) -> None:
        nonlocal selected_index
        if selected_index >= len(tasks) - 1:
            return
        selected_index += 1
        ensure_visible()
        event.app.invalidate()

    @kb.add("enter")
    def _confirm(event) -> None:
        event.app.exit(result=tasks[selected_index].task_id)

    @kb.add("home")
    def _go_home(event) -> None:
        nonlocal selected_index
        selected_index = 0
        ensure_visible()
        event.app.invalidate()

    @kb.add("end")
    def _go_end(event) -> None:
        nonlocal selected_index
        selected_index = len(tasks) - 1
        ensure_visible()
        event.app.invalidate()

    @kb.add("pageup")
    def _page_up(event) -> None:
        nonlocal selected_index
        step = _resume_selector_visible_count()
        selected_index = max(0, selected_index - step)
        ensure_visible()
        event.app.invalidate()

    @kb.add("pagedown")
    def _page_down(event) -> None:
        nonlocal selected_index
        step = _resume_selector_visible_count()
        selected_index = min(len(tasks) - 1, selected_index + step)
        ensure_visible()
        event.app.invalidate()

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("q")
    def _cancel(event) -> None:
        event.app.exit(result=None)

    control = FormattedTextControl(
        text=lambda: _render_resume_selector(tasks, selected_index, window_start),
        focusable=True,
        key_bindings=kb,
    )
    window = Window(content=control, always_hide_cursor=True)

    app = Application(
        layout=Layout(window, focused_element=window),
        full_screen=False,
        erase_when_done=True,
        mouse_support=False,
        style=Style.from_dict(
            {
                "title": "bold ansicyan",
                "divider": "ansibrightblack",
                "hint": "ansibrightblack",
                "item-marker": "ansibrightblack",
                "item-index": "ansibrightblack",
                "item-title": "",
                "item-meta": "ansibrightblack",
                "selected-marker": "bold ansicyan",
                "selected-index": "bold",
                "selected-title": "bold",
                "selected-meta": "",
                "footer": "ansibrightblack",
            }
        ),
    )
    return await app.run_async()
