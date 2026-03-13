from __future__ import annotations

from pathlib import Path

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from manus_cli.api.models import OutputFile, OutputText, TaskDetail

console = Console()


class OutputRenderer:
    def __init__(self, console: Console | None = None):
        self._console = console or Console()

    def render_task_result(self, task: TaskDetail) -> None:
        """Render a completed task's output."""
        if not task.output:
            self._console.print("[dim]No output[/dim]")
            return

        has_content = False
        for msg in task.output:
            for item in msg.content:
                has_content = True
                if isinstance(item, OutputText):
                    self._render_text(item.text)
                elif isinstance(item, OutputFile):
                    self._render_file(item)

        if not has_content:
            self._console.print("[dim]No output[/dim]")
            return

        if task.credit_usage:
            self._console.print(
                f"\n[dim]Credits: {task.credit_usage.total_credits:.2f} "
                f"(in: {task.credit_usage.input_credits:.2f}, "
                f"out: {task.credit_usage.output_credits:.2f})[/dim]"
            )

    def render_task_context(self, task: TaskDetail, max_messages: int | None = None) -> None:
        """Render resumed context in a compact terminal-friendly layout."""
        created = (task.created_at or "unknown time").replace("T", " ").replace("Z", "")
        created = created[:16]
        task_id = self._short_task_id(task.task_id)
        divider = "─" * self._context_line_width()
        self._console.print(
            f"[bold]Resumed Conversation[/bold] [dim]{task.status.value} | {created} | {task_id}[/dim]"
        )
        self._console.print(f"[dim]{divider}[/dim]")

        preview_width = self._context_preview_width()
        entries = self._context_entries(task, preview_width=preview_width)
        if not entries:
            self._console.print("[dim]No prior conversation found for this task.[/dim]")
            return

        window_size = self._context_window_size(total_entries=len(entries), explicit_max=max_messages)
        hidden_count = max(0, len(entries) - window_size)
        if hidden_count:
            self._console.print(f"[dim]... {hidden_count} earlier messages hidden[/dim]")

        role_colors = {"user": "cyan", "assistant": "green", "system": "yellow"}
        role_labels = {"user": "you", "assistant": "assistant", "system": "system"}
        for role, preview in entries[-window_size:]:
            color = role_colors.get(role, "white")
            label = role_labels.get(role, role)
            self._console.print(f"[bold {color}]{label:>9}[/bold {color}]  {preview}")

        self._console.print("[dim]Continue by typing your next message.[/dim]")

    def _render_text(self, text: str) -> None:
        md = Markdown(text)
        self._console.print(Panel(md, border_style="blue", padding=(1, 2)))

    def _render_file(self, file: OutputFile) -> None:
        meta_parts = []
        download_path = self._download_file(file)
        if download_path:
            meta_parts.append(f"saved to {download_path}")
        if file.file_id:
            meta_parts.append(file.file_id)
        if file.url and not download_path:
            meta_parts.append(file.url)
        meta_text = f" [dim]{' | '.join(meta_parts)}[/dim]" if meta_parts else ""
        self._console.print(
            f"  [bold green]📎 {file.file_name}[/bold green]{meta_text}"
        )

    def _render_file_reference(self, file: OutputFile) -> None:
        meta_parts = []
        if file.file_id:
            meta_parts.append(file.file_id)
        if file.url:
            meta_parts.append(file.url)
        meta_text = f" [dim]{' | '.join(meta_parts)}[/dim]" if meta_parts else ""
        self._console.print(
            f"  [bold green]📎 {file.file_name}[/bold green]{meta_text}"
        )

    def _context_entries(self, task: TaskDetail, preview_width: int) -> list[tuple[str, str]]:
        entries: list[tuple[str, str]] = []
        if task.instructions and not task.output:
            preview = self._truncate_inline(task.instructions, max_width=preview_width)
            return [("user", preview)]

        for msg in task.output:
            parts: list[str] = []
            for item in msg.content:
                if isinstance(item, OutputText):
                    text = self._truncate_inline(item.text, max_width=preview_width)
                    if text:
                        parts.append(text)
                elif isinstance(item, OutputFile):
                    parts.append(f"[file] {item.file_name}")
            preview = self._truncate_inline(" ".join(parts), max_width=preview_width)
            if preview:
                entries.append((msg.role, preview))
        return entries

    def _truncate_inline(self, text: str, max_width: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= max_width:
            return compact
        return f"{compact[: max_width - 3]}..."

    def _short_task_id(self, task_id: str) -> str:
        if len(task_id) <= 24:
            return task_id
        return f"{task_id[:10]}...{task_id[-8:]}"

    def _context_line_width(self) -> int:
        width = self._console.size.width
        return max(40, min(120, width))

    def _context_preview_width(self) -> int:
        width = self._console.size.width
        # Reserve room for role label and paddings.
        return max(40, min(140, width - 16))

    def _context_window_size(self, total_entries: int, explicit_max: int | None) -> int:
        if explicit_max is not None:
            return max(1, explicit_max)
        height = self._console.size.height
        # Title + divider + summary + hint consume ~6 lines.
        available = max(4, height - 6)
        return min(total_entries, min(12, available))

    def _download_file(self, file: OutputFile) -> Path | None:
        if not file.url:
            return None

        file_name = Path(file.file_name).name or "download"
        target_path = self._resolve_download_path(Path.cwd() / file_name)

        try:
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                with client.stream("GET", file.url) as response:
                    response.raise_for_status()
                    with target_path.open("wb") as output:
                        for chunk in response.iter_bytes():
                            output.write(chunk)
        except Exception as exc:
            if target_path.exists():
                target_path.unlink(missing_ok=True)
            self.render_error(f"Failed to download {file.file_name}: {exc}")
            return None

        return target_path.resolve()

    def _resolve_download_path(self, target_path: Path) -> Path:
        if not target_path.exists():
            return target_path

        stem = target_path.stem
        suffix = target_path.suffix
        counter = 1
        while True:
            candidate = target_path.with_name(f"{stem}-{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1

    def render_info(self, message: str) -> None:
        self._console.print(f"[dim]{message}[/dim]")

    def render_error(self, message: str) -> None:
        self._console.print(f"[bold red]Error:[/bold red] {message}")

    def render_welcome(self) -> None:
        self._console.print("[bold]Manus CLI[/bold] [dim]Type a prompt or run /help[/dim]")
