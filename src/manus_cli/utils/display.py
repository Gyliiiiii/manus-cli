from __future__ import annotations

from rich.console import Console
from rich.table import Table

from manus_cli.api.models import FileInfo, TaskDetail


def print_task_table(tasks: list[TaskDetail], console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title="Tasks")
    table.add_column("Task ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Created", style="dim")
    table.add_column("Preview", max_width=50)

    status_colors = {
        "pending": "yellow",
        "running": "blue",
        "completed": "green",
        "failed": "red",
    }

    for task in tasks:
        status_style = status_colors.get(task.status.value, "white")
        preview = ""
        if task.output:
            for msg in task.output:
                for item in msg.content:
                    if hasattr(item, "text"):
                        preview = item.text[:50].replace("\n", " ")
                        break
                if preview:
                    break
        table.add_row(
            task.task_id,
            f"[{status_style}]{task.status.value}[/{status_style}]",
            task.created_at or "",
            preview,
        )

    console.print(table)


def print_file_table(files: list[FileInfo], console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title="Files")
    table.add_column("File ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Size", justify="right")
    table.add_column("Created", style="dim")

    for f in files:
        size_str = _format_size(f.file_size) if f.file_size else ""
        table.add_row(f.file_id, f.file_name, size_str, f.created_at or "")

    console.print(table)


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
