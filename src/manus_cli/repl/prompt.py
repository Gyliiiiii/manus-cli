from __future__ import annotations

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML

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
