from __future__ import annotations

from manus_cli.core.errors import (
    APIError,
    AuthenticationError,
    ManusError,
    TaskFailedError,
    TaskTimeoutError,
)


class TestAPIError:
    def test_api_error_message(self):
        """APIError should format status_code and detail into its message."""
        err = APIError(status_code=401, detail="Unauthorized")

        assert err.status_code == 401
        assert err.detail == "Unauthorized"
        assert str(err) == "API error 401: Unauthorized"
        assert isinstance(err, ManusError)


class TestTaskTimeoutError:
    def test_task_timeout_error(self):
        """TaskTimeoutError should capture task_id and elapsed and format message."""
        err = TaskTimeoutError(task_id="task-abc-123", elapsed=45.678)

        assert err.task_id == "task-abc-123"
        assert err.elapsed == 45.678
        assert str(err) == "Task task-abc-123 timed out after 45.7s"
        assert isinstance(err, ManusError)
