from __future__ import annotations

import asyncio
import time

from rich.live import Live
from rich.spinner import Spinner

from manus_cli.api.models import TaskDetail, TaskStatus
from manus_cli.api.tasks import TaskService
from manus_cli.core.errors import TaskFailedError, TaskTimeoutError


class TaskPoller:
    def __init__(
        self,
        task_service: TaskService,
        initial_interval: float = 2.0,
        backoff_factor: float = 1.5,
        max_interval: float = 10.0,
        timeout: float = 600.0,
    ):
        self._task_service = task_service
        self._initial_interval = initial_interval
        self._backoff_factor = backoff_factor
        self._max_interval = max_interval
        self._timeout = timeout

    async def poll(self, task_id: str) -> TaskDetail:
        """Poll a task until terminal state. Shows Rich spinner with incremental output."""
        interval = self._initial_interval
        start = time.monotonic()
        last_output_len = 0

        spinner = Spinner("dots", text="Waiting for task to start...")

        with Live(spinner, refresh_per_second=10, transient=True):
            while True:
                elapsed = time.monotonic() - start
                if elapsed > self._timeout:
                    raise TaskTimeoutError(task_id, elapsed)

                task = await self._task_service.get(task_id)

                # Update spinner with incremental output preview
                if task.output:
                    text_parts = []
                    for msg in task.output:
                        for c in msg.content:
                            if hasattr(c, "text"):
                                text_parts.append(c.text)
                    full_text = "\n".join(text_parts)
                    if len(full_text) > last_output_len:
                        preview = full_text[last_output_len:][:80].replace("\n", " ")
                        spinner.update(text=f"[dim]{preview}...[/dim]")
                        last_output_len = len(full_text)

                if task.status == TaskStatus.COMPLETED:
                    return task
                if task.status == TaskStatus.FAILED:
                    raise TaskFailedError(task_id)

                # Update spinner status text
                if task.status == TaskStatus.RUNNING:
                    spinner.update(text=f"Task running... ({elapsed:.0f}s)")

                await asyncio.sleep(interval)
                interval = min(interval * self._backoff_factor, self._max_interval)
