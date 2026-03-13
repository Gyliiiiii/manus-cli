from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Optional

import typer
from rich.console import Console

from manus_cli import __version__

if TYPE_CHECKING:
    from manus_cli.api.models import TaskDetail

app = typer.Typer(
    name="manus",
    help="CLI for Manus AI Agent API",
    no_args_is_help=False,
    invoke_without_command=True,
)
auth_app = typer.Typer(help="Authentication commands")
task_app = typer.Typer(help="Task management commands")
file_app = typer.Typer(help="File management commands")
project_app = typer.Typer(help="Project management commands")
webhook_app = typer.Typer(help="Webhook management commands")
config_app = typer.Typer(help="Configuration commands")

app.add_typer(auth_app, name="auth")
app.add_typer(task_app, name="task")
app.add_typer(file_app, name="file")
app.add_typer(project_app, name="project")
app.add_typer(webhook_app, name="webhook")
app.add_typer(config_app, name="config")

console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"manus-cli {__version__}")
        raise typer.Exit()


def _run_command(command: Awaitable[None]) -> None:
    from manus_cli.core.errors import ManusError
    from manus_cli.repl.renderer import OutputRenderer

    try:
        asyncio.run(command)
    except ManusError as e:
        OutputRenderer().render_error(str(e))
        raise typer.Exit(1)


def _resolve_resume_selection(choice: str, tasks: list[TaskDetail]) -> TaskDetail | None:
    if not choice:
        return None
    if choice.isdigit():
        index = int(choice)
        if 1 <= index <= len(tasks):
            return tasks[index - 1]
        return None
    for task in tasks:
        if task.task_id == choice:
            return task
    return None


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="One-shot prompt"),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume a recent task"),
    model: str = typer.Option("manus-1.6", "--model", "-m", help="Agent profile"),
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True
    ),
):
    if ctx.invoked_subcommand is not None:
        return
    if prompt and resume:
        console.print("[red]Cannot combine --prompt and --resume.[/red]")
        raise typer.Exit(1)
    if prompt:
        asyncio.run(_one_shot(prompt, model))
    else:
        _run_command(_start_repl(model, resume=resume))


async def _one_shot(prompt: str, model: str):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.models import AgentProfile, CreateTaskRequest
    from manus_cli.api.tasks import TaskService
    from manus_cli.core.errors import ManusError
    from manus_cli.core.poller import TaskPoller
    from manus_cli.repl.renderer import OutputRenderer

    renderer = OutputRenderer()
    try:
        async with ManusClient() as client:
            task_service = TaskService(client)
            poller = TaskPoller(task_service)

            request = CreateTaskRequest(
                prompt=prompt,
                agent_profile=AgentProfile(model),
            )
            response = await task_service.create(request)
            task = await poller.poll(response.task_id)
            renderer.render_task_result(task)
    except ManusError as e:
        renderer.render_error(str(e))
        raise typer.Exit(1)


async def _select_resume_task(session, limit: int = 20) -> tuple[TaskDetail | None, bool]:
    from manus_cli.repl.prompt import (
        format_resume_task_label,
        format_resume_task_meta,
        select_resume_task_interactively,
        supports_interactive_resume_selector,
    )

    tasks = await session.task_service.list(limit=limit)
    if not tasks:
        return None, False

    if supports_interactive_resume_selector():
        selected_id = await select_resume_task_interactively(tasks)
        if not selected_id:
            return None, True
        task = await session.task_service.get(selected_id)
        return task, False

    console.print("[bold]Resume Conversation[/bold]")
    console.print("[dim]Choose a task number or paste a task id. Press Enter to cancel.[/dim]")
    for idx, task in enumerate(tasks, 1):
        console.print(format_resume_task_label(task, idx))
        console.print(f"[dim]   {format_resume_task_meta(task)}[/dim]")

    prompt = "resume> "

    while True:
        choice = (await asyncio.to_thread(console.input, prompt)).strip()
        if not choice:
            return None, True
        selected = _resolve_resume_selection(choice, tasks)
        if selected:
            task = await session.task_service.get(selected.task_id)
            return task, False

        console.print("[red]Invalid selection. Enter a listed number or exact task id.[/red]")


async def _start_repl(model: str, resume: bool = False):
    from manus_cli.repl.session import ReplSession

    session = ReplSession(model=model)
    startup_messages: list[str] = []
    startup_task: TaskDetail | None = None

    if resume:
        selected_task, cancelled = await _select_resume_task(session)
        if cancelled:
            console.print("[yellow]Resume cancelled.[/yellow]")
            await session.client.close()
            return
        if selected_task is None:
            startup_messages.append("No recent tasks found to resume. Starting a new conversation.")
        else:
            session.load_task_context(selected_task, render=False)
            startup_task = selected_task

    await session.run(startup_messages=startup_messages, startup_task=startup_task)


@app.command()
def run(
    prompt: str = typer.Argument(..., help="Task prompt"),
    model: str = typer.Option("manus-1.6", "--model", "-m"),
):
    """Run a one-shot task."""
    asyncio.run(_one_shot(prompt, model))


@app.command()
def chat(
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume a recent task"),
    model: str = typer.Option("manus-1.6", "--model", "-m"),
):
    """Start interactive REPL session."""
    _run_command(_start_repl(model, resume=resume))


# --- Auth commands ---


@auth_app.command("login")
def auth_login():
    """Authenticate with your Manus API key."""
    from manus_cli.core.config import load_config, save_config

    console.print("[bold]Manus CLI Login[/bold]\n")

    # Check if already logged in
    config = load_config()
    if config.api_key:
        masked = config.api_key[:4] + "****" + config.api_key[-4:]
        console.print(f"Already logged in (key: {masked})")
        overwrite = typer.confirm("Overwrite with a new key?", default=False)
        if not overwrite:
            raise typer.Exit()

    console.print("Get your API key from: [link=https://manus.ai/settings]https://manus.ai/settings[/link]\n")
    api_key = typer.prompt("API Key", hide_input=True)

    if not api_key.strip():
        console.print("[red]API key cannot be empty.[/red]")
        raise typer.Exit(1)

    # Validate key by making a test request
    async def _validate(key: str) -> bool:
        from manus_cli.api.client import ManusClient
        try:
            async with ManusClient(api_key=key) as client:
                await client.request("GET", "/tasks", params={"limit": 1})
            return True
        except Exception:
            return False

    console.print("[dim]Validating API key...[/dim]")
    valid = asyncio.run(_validate(api_key.strip()))

    if not valid:
        console.print("[yellow]Warning: Could not validate API key (API may be unreachable). Saving anyway.[/yellow]")

    config.api_key = api_key.strip()
    save_config(config)
    console.print("[green]Logged in successfully![/green]")


@auth_app.command("logout")
def auth_logout():
    """Remove saved API key."""
    from manus_cli.core.config import load_config, save_config

    config = load_config()
    if not config.api_key:
        console.print("[dim]Not logged in.[/dim]")
        raise typer.Exit()

    config.api_key = None
    save_config(config)
    console.print("[green]Logged out. API key removed from config.[/green]")


@auth_app.command("status")
def auth_status():
    """Show current authentication status."""
    import os

    from manus_cli.core.config import load_config

    config = load_config()
    env_key = os.environ.get("MANUS_API_KEY")

    if env_key:
        masked = env_key[:4] + "****" + env_key[-4:]
        console.print(f"[green]Authenticated[/green] via MANUS_API_KEY env var (key: {masked})")
    elif config.api_key:
        masked = config.api_key[:4] + "****" + config.api_key[-4:]
        console.print(f"[green]Authenticated[/green] via config file (key: {masked})")
    else:
        console.print("[red]Not authenticated.[/red] Run [bold]manus auth login[/bold] to log in.")


# --- Task commands ---


@task_app.command("list")
def task_list(
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """List recent tasks."""
    _run_command(_task_list(limit))


async def _task_list(limit: int):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.tasks import TaskService
    from manus_cli.utils.display import print_task_table

    async with ManusClient() as client:
        tasks = await TaskService(client).list(limit=limit)
        print_task_table(tasks)


@task_app.command("get")
def task_get(task_id: str = typer.Argument(..., help="Task ID")):
    """Get task details."""
    _run_command(_task_get(task_id))


async def _task_get(task_id: str):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.tasks import TaskService
    from manus_cli.repl.renderer import OutputRenderer

    async with ManusClient() as client:
        task = await TaskService(client).get(task_id)
        OutputRenderer().render_task_result(task)


@task_app.command("delete")
def task_delete(task_id: str = typer.Argument(...)):
    """Delete a task."""
    _run_command(_task_delete(task_id))


async def _task_delete(task_id: str):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.tasks import TaskService

    async with ManusClient() as client:
        await TaskService(client).delete(task_id)
        console.print(f"[green]Task {task_id} deleted.[/green]")


@task_app.command("update")
def task_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    title: str | None = typer.Option(None, "--title", help="New task title"),
    share: bool | None = typer.Option(
        None,
        "--share/--no-share",
        help="Enable or disable public sharing",
    ),
    visible: bool | None = typer.Option(
        None,
        "--visible/--hidden",
        help="Control whether the task appears in task list",
    ),
):
    """Update task metadata."""
    _run_command(_task_update(task_id, title=title, share=share, visible=visible))


async def _task_update(
    task_id: str,
    title: str | None,
    share: bool | None,
    visible: bool | None,
):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.models import UpdateTaskRequest
    from manus_cli.api.tasks import TaskService

    if title is None and share is None and visible is None:
        console.print("[red]Provide at least one update field (--title, --share/--no-share, --visible/--hidden).[/red]")
        raise typer.Exit(1)

    async with ManusClient() as client:
        result = await TaskService(client).update(
            task_id,
            UpdateTaskRequest(
                title=title,
                enable_shared=share,
                enable_visible_in_task_list=visible,
            ),
        )

    summary = result.task_title or title or "updated"
    console.print(f"[green]Task {result.task_id} updated.[/green] {summary}")


# --- File commands ---


@file_app.command("upload")
def file_upload(path: Path = typer.Argument(..., help="File path to upload")):
    """Upload a file."""
    _run_command(_file_upload(path))


async def _file_upload(path: Path):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.files import FileService

    if not path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        raise typer.Exit(1)
    async with ManusClient() as client:
        info = await FileService(client).upload(path)
        console.print(f"[green]Uploaded:[/green] {info.file_name} (ID: {info.file_id})")


@file_app.command("list")
def file_list(limit: int = typer.Option(20, "--limit", "-n")):
    """List uploaded files."""
    _run_command(_file_list(limit))


async def _file_list(limit: int):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.files import FileService
    from manus_cli.utils.display import print_file_table

    async with ManusClient() as client:
        files = await FileService(client).list(limit=limit)
        print_file_table(files)


# --- Project commands ---


@project_app.command("list")
def project_list(limit: int = typer.Option(100, "--limit", "-n")):
    """List projects."""
    _run_command(_project_list(limit))


async def _project_list(limit: int):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.projects import ProjectService
    from manus_cli.utils.display import print_project_table

    async with ManusClient() as client:
        projects = await ProjectService(client).list(limit=limit)
        print_project_table(projects)


@project_app.command("create")
def project_create(
    name: str = typer.Argument(..., help="Project name"),
    instruction: str | None = typer.Option(
        None,
        "--instruction",
        help="Default instruction applied to tasks in this project",
    ),
):
    """Create a project."""
    _run_command(_project_create(name=name, instruction=instruction))


async def _project_create(name: str, instruction: str | None):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.models import CreateProjectRequest
    from manus_cli.api.projects import ProjectService

    async with ManusClient() as client:
        project = await ProjectService(client).create(
            CreateProjectRequest(name=name, instruction=instruction)
        )
    console.print(f"[green]Project created:[/green] {project.name} (ID: {project.project_id})")


# --- Webhook commands ---


@webhook_app.command("create")
def webhook_create(url: str = typer.Argument(..., help="Webhook URL")):
    """Create a webhook."""
    _run_command(_webhook_create(url))


async def _webhook_create(url: str):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.models import CreateWebhookRequest, WebhookTarget
    from manus_cli.api.webhooks import WebhookService

    async with ManusClient() as client:
        webhook = await WebhookService(client).create(
            CreateWebhookRequest(webhook=WebhookTarget(url=url))
        )
    console.print(f"[green]Webhook created:[/green] {webhook.webhook_id}")


@webhook_app.command("delete")
def webhook_delete(webhook_id: str = typer.Argument(..., help="Webhook ID")):
    """Delete a webhook."""
    _run_command(_webhook_delete(webhook_id))


async def _webhook_delete(webhook_id: str):
    from manus_cli.api.client import ManusClient
    from manus_cli.api.webhooks import WebhookService

    async with ManusClient() as client:
        await WebhookService(client).delete(webhook_id)
    console.print(f"[green]Webhook {webhook_id} deleted.[/green]")


# --- Config commands ---


@config_app.command("set")
def config_set(
    key: str = typer.Argument(
        ..., help="Config key (api_key, default_model, timeout)"
    ),
    value: str = typer.Argument(..., help="Config value"),
):
    """Set a configuration value."""
    from manus_cli.core.config import load_config, save_config

    config = load_config()
    if key == "api_key":
        config.api_key = value
    elif key == "default_model":
        config.default_model = value
    elif key == "timeout":
        config.timeout = int(value)
    else:
        console.print(
            f"[red]Unknown key: {key}. Valid: api_key, default_model, timeout[/red]"
        )
        raise typer.Exit(1)
    save_config(config)
    display = "****" if key == "api_key" else value
    console.print(f"[green]Set {key} = {display}[/green]")


@config_app.command("get")
def config_get(key: str = typer.Argument(...)):
    """Get a configuration value."""
    from manus_cli.core.config import load_config

    config = load_config()
    val = getattr(config, key, None)
    if val is None and key not in ("api_key", "default_model", "timeout"):
        console.print(f"[red]Unknown key: {key}[/red]")
        raise typer.Exit(1)
    if key == "api_key" and val:
        val = val[:4] + "****"
    console.print(f"{key} = {val}")


@config_app.command("show")
def config_show():
    """Show all configuration."""
    from manus_cli.core.config import load_config

    config = load_config()
    api_display = (config.api_key[:4] + "****") if config.api_key else "not set"
    console.print(f"api_key = {api_display}")
    console.print(f"default_model = {config.default_model}")
    console.print(f"timeout = {config.timeout}")


def app_main():
    app()
