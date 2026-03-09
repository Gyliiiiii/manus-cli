from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from manus_cli.repl.session import ReplSession


@dataclass
class SlashCommand:
    name: str
    description: str
    handler: Callable[[ReplSession, str], Awaitable[None]]


class SlashCommandRegistry:
    def __init__(self):
        self._commands: dict[str, SlashCommand] = {}

    def register(self, name: str, description: str, handler: Callable):
        self._commands[name] = SlashCommand(name=name, description=description, handler=handler)

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name)

    @property
    def commands(self) -> dict[str, SlashCommand]:
        return self._commands

    def names(self) -> list[str]:
        return sorted(self._commands.keys())


def create_default_registry() -> SlashCommandRegistry:
    registry = SlashCommandRegistry()

    async def cmd_exit(session: ReplSession, args: str):
        session.running = False

    async def cmd_clear(session: ReplSession, args: str):
        session.current_task_id = None
        session.renderer.render_info("Conversation cleared.")

    async def cmd_model(session: ReplSession, args: str):
        args = args.strip()
        if not args:
            session.renderer.render_info(f"Current model: {session.agent_profile}")
            return
        from manus_cli.api.models import AgentProfile
        try:
            profile = AgentProfile(args)
            session.agent_profile = profile
            session.renderer.render_info(f"Model switched to: {profile}")
        except ValueError:
            valid = ", ".join(p.value for p in AgentProfile)
            session.renderer.render_error(f"Unknown model. Valid: {valid}")

    async def cmd_status(session: ReplSession, args: str):
        if not session.current_task_id:
            session.renderer.render_info("No active task.")
            return
        task = await session.task_service.get(session.current_task_id)
        session.renderer.render_info(f"Task {task.task_id}: {task.status.value}")

    async def cmd_files(session: ReplSession, args: str):
        from manus_cli.utils.display import print_file_table
        files = await session.file_service.list()
        print_file_table(files)

    async def cmd_attach(session: ReplSession, args: str):
        path = args.strip()
        if not path:
            if session.pending_attachments:
                items = ", ".join(session.pending_attachments)
                session.renderer.render_info(f"Pending attachments: {items}")
            else:
                session.renderer.render_error("Usage: /attach <file_path>")
            return
        from pathlib import Path
        p = Path(path).expanduser()
        if not p.exists():
            session.renderer.render_error(f"File not found: {p}")
            return
        session.pending_attachments.append(str(p))
        session.renderer.render_info(f"Attached: {p.name}")

    async def cmd_help(session: ReplSession, args: str):
        from rich.table import Table
        table = Table(title="Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        for cmd in sorted(session.command_registry.commands.values(), key=lambda c: c.name):
            table.add_row(f"/{cmd.name}", cmd.description)
        session.renderer._console.print(table)

    async def cmd_history(session: ReplSession, args: str):
        if not session.history:
            session.renderer.render_info("No history yet.")
            return
        for i, entry in enumerate(session.history, 1):
            role = entry.get("role", "?")
            preview = entry.get("preview", "")[:60]
            session.renderer._console.print(f"  [dim]{i}.[/dim] [{role}] {preview}")

    registry.register("exit", "Exit the REPL", cmd_exit)
    registry.register("quit", "Exit the REPL", cmd_exit)
    registry.register("clear", "Clear conversation (start new task)", cmd_clear)
    registry.register("model", "Switch model (manus-1.6, lite, max)", cmd_model)
    registry.register("status", "Show current task status", cmd_status)
    registry.register("files", "List uploaded files", cmd_files)
    registry.register("attach", "Attach a file to next prompt", cmd_attach)
    registry.register("help", "Show this help", cmd_help)
    registry.register("history", "Show conversation history", cmd_history)

    return registry
