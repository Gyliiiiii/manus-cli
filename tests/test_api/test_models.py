from __future__ import annotations

from manus_cli.api.models import (
    AgentProfile,
    CreateTaskRequest,
    CreditUsage,
    OutputMessage,
    TaskDetail,
    TaskStatus,
)


class TestCreateTaskRequestDefaults:
    def test_create_task_request_defaults(self):
        """CreateTaskRequest should populate defaults for optional fields."""
        req = CreateTaskRequest(prompt="Hello, world!")

        assert req.prompt == "Hello, world!"
        assert req.agent_profile == AgentProfile.MANUS_1_6
        assert req.task_mode is None
        assert req.task_id is None
        assert req.attachments == []


class TestTaskDetailParsing:
    def test_task_detail_parsing(self):
        """TaskDetail should parse a full JSON-like dict including nested models."""
        raw = {
            "id": "tid-001",
            "status": "completed",
            "output": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Done!"},
                    ],
                }
            ],
            "credit_usage": {
                "input_credits": 1.5,
                "output_credits": 2.5,
                "total_credits": 4.0,
            },
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:01:00Z",
            "error": None,
        }

        detail = TaskDetail.model_validate(raw)

        assert detail.task_id == "tid-001"
        assert detail.status == TaskStatus.COMPLETED
        assert len(detail.output) == 1
        assert len(detail.output[0].content) == 1
        assert detail.output[0].content[0].text == "Done!"
        assert detail.credit_usage is not None
        assert detail.credit_usage.total_credits == 4.0
        assert detail.created_at == "2025-01-01T00:00:00Z"
        assert detail.error is None

    def test_task_detail_single_output_dict(self):
        """TaskDetail should wrap a single output dict into a list."""
        raw = {
            "id": "tid-003",
            "status": "completed",
            "output": {
                "role": "assistant",
                "content": [{"type": "text", "text": "Hi"}],
            },
        }
        detail = TaskDetail.model_validate(raw)
        assert len(detail.output) == 1
        assert detail.output[0].content[0].text == "Hi"

    def test_task_detail_credit_usage_as_int(self):
        """TaskDetail should handle credit_usage as a plain integer."""
        raw = {"id": "tid-002", "status": "completed", "credit_usage": 0}
        detail = TaskDetail.model_validate(raw)
        assert detail.credit_usage is not None
        assert detail.credit_usage.total_credits == 0


class TestTaskStatusEnum:
    def test_task_status_enum(self):
        """TaskStatus members should equal their string values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

        # StrEnum values can be used as plain strings
        assert TaskStatus("completed") is TaskStatus.COMPLETED
