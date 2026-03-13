from __future__ import annotations

from rich.console import Console
from rich.table import Table

from manus_cli.api.models import FileInfo, ProjectInfo, TaskDetail


def task_preview(task: TaskDetail, max_width: int = 50) -> str:
    if task.output:
        for msg in task.output:
            for item in msg.content:
                if hasattr(item, "text"):
                    return item.text[:max_width].replace("\n", " ")
    return ""


def print_task_table(
    tasks: list[TaskDetail],
    console: Console | None = None,
    show_index: bool = False,
) -> None:
    console = console or Console()
    table = Table(title="Tasks")
    if show_index:
        table.add_column("#", style="dim", justify="right", no_wrap=True)
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

    for idx, task in enumerate(tasks, 1):
        status_style = status_colors.get(task.status.value, "white")
        row = []
        if show_index:
            row.append(str(idx))
        row.extend([
            task.task_id,
            f"[{status_style}]{task.status.value}[/{status_style}]",
            task.created_at or "",
            task_preview(task),
        ])
        table.add_row(*row)

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


def print_project_table(projects: list[ProjectInfo], console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title="Projects")
    table.add_column("Project ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Instruction", max_width=60)
    table.add_column("Created", style="dim")

    for project in projects:
        table.add_row(
            project.project_id,
            project.name,
            project.instruction or "",
            project.created_at or "",
        )

    console.print(table)


def _format_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
