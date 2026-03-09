class ManusError(Exception):
    """Base exception for all manus-cli errors."""


class AuthenticationError(ManusError):
    """Raised when API key is missing or invalid."""


class APIError(ManusError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class TaskFailedError(ManusError):
    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"Task {task_id} ended in failed state")


class TaskTimeoutError(ManusError):
    def __init__(self, task_id: str, elapsed: float) -> None:
        self.task_id = task_id
        self.elapsed = elapsed
        super().__init__(f"Task {task_id} timed out after {elapsed:.1f}s")
