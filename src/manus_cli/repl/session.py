from __future__ import annotations

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession as PTSession

from manus_cli.api.client import ManusClient
from manus_cli.api.tasks import TaskService
from manus_cli.api.files import FileService
from manus_cli.api.models import CreateTaskRequest, AgentProfile, OutputText
from manus_cli.core.poller import TaskPoller
from manus_cli.core.errors import ManusError
from manus_cli.repl.renderer import OutputRenderer
from manus_cli.repl.commands import SlashCommandRegistry, create_default_registry
from manus_cli.repl.prompt import create_prompt_session


class ReplSession:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.client = ManusClient(api_key=api_key)
        self.task_service = TaskService(self.client)
        self.file_service = FileService(self.client)
        self.poller = TaskPoller(self.task_service)
        self.renderer = OutputRenderer()
        self.command_registry = create_default_registry()
        self.prompt_session: PTSession = create_prompt_session(self.command_registry.names())

        self.agent_profile = AgentProfile(model) if model else AgentProfile.MANUS_1_6
        self.current_task_id: str | None = None
        self.pending_attachments: list[str] = []
        self.history: list[dict] = []
        self.running = True

    async def run(self) -> None:
        self.renderer.render_welcome()
        try:
            while self.running:
                try:
                    user_input = await asyncio.to_thread(self.prompt_session.prompt)
                except (EOFError, KeyboardInterrupt):
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    await self._handle_slash_command(user_input)
                else:
                    await self._handle_prompt(user_input)
        finally:
            await self.client.close()

    async def _handle_slash_command(self, raw: str) -> None:
        parts = raw[1:].split(None, 1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        command = self.command_registry.get(cmd_name)
        if command:
            await command.handler(self, args)
        else:
            self.renderer.render_error(f"Unknown command: /{cmd_name}. Type /help for available commands.")

    async def _handle_prompt(self, prompt: str) -> None:
        # Upload any pending attachments
        attachment_ids: list[str] = []
        for path_str in self.pending_attachments:
            try:
                file_info = await self.file_service.upload(Path(path_str))
                attachment_ids.append(file_info.file_id)
                self.renderer.render_info(f"Uploaded: {file_info.file_name}")
            except ManusError as e:
                self.renderer.render_error(f"Upload failed: {e}")
        self.pending_attachments.clear()

        # Create task
        request = CreateTaskRequest(
            prompt=prompt,
            agent_profile=self.agent_profile,
            task_id=self.current_task_id,
            attachments=attachment_ids,
        )

        try:
            response = await self.task_service.create(request)
            self.history.append({"role": "user", "preview": prompt})

            # Poll for result
            task = await self.poller.poll(response.task_id)
            self.current_task_id = task.task_id

            # Render output
            self.renderer.render_task_result(task)

            # Save to history
            if task.output:
                text_parts = []
                for msg in task.output:
                    for c in msg.content:
                        if isinstance(c, OutputText):
                            text_parts.append(c.text)
                preview = " ".join(text_parts)[:60]
                self.history.append({"role": "assistant", "preview": preview})
        except ManusError as e:
            self.renderer.render_error(str(e))
