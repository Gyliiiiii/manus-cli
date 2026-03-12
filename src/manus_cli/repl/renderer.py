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
        self._console.print(
            Panel(
                "[bold]Manus CLI[/bold] - AI Agent Interface\n"
                "Type your prompt to start a task. Use [bold]/help[/bold] for commands.",
                border_style="cyan",
                padding=(1, 2),
            )
        )
