from __future__ import annotations

from manus_cli.api.models import TaskDetail
from manus_cli.core.errors import APIError
from manus_cli.core.poller import TaskPoller


class _FlakyTaskService:
    def __init__(self):
        self.calls = 0

    async def get(self, task_id: str) -> TaskDetail:
        self.calls += 1
        if self.calls == 1:
            raise APIError(404, '{"code":5, "message":"task not found", "details":[]}')
        return TaskDetail.model_validate({"id": task_id, "status": "completed", "output": []})


class TestTaskPoller:
    async def test_poll_retries_transient_not_found_after_create(self):
        """poll should tolerate an initial 404 while the task becomes queryable."""
        service = _FlakyTaskService()
        poller = TaskPoller(
            service,
            initial_interval=0.01,
            backoff_factor=1.0,
            max_interval=0.01,
            timeout=1.0,
            not_found_retry_window=1.0,
        )

        task = await poller.poll("task-123")

        assert task.task_id == "task-123"
        assert service.calls == 2
