from __future__ import annotations

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
        url_text = f" ({file.url})" if file.url else ""
        self._console.print(
            f"  [bold green]📎 {file.file_name}[/bold green] [dim]{file.file_id}{url_text}[/dim]"
        )

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
