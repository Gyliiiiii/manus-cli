from __future__ import annotations

from manus_cli.api.models import (
    AgentProfile,
    CreateTaskRequest,
    CreditUsage,
    FileInfo,
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

    def test_create_task_request_uses_api_aliases(self):
        """Task creation payload should serialize to the official API field names."""
        req = CreateTaskRequest(
            prompt="Hello, world!",
            agent_profile=AgentProfile.LITE,
            task_mode="sync",
            task_id="task-123",
        )

        data = req.model_dump(exclude_none=True, by_alias=True)

        assert data["agentProfile"] == "manus-1.6-lite"
        assert data["taskMode"] == "sync"
        assert data["taskId"] == "task-123"
        assert "agent_profile" not in data


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
        assert detail.instructions is None
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

    def test_task_detail_flat_output_item(self):
        """Flat output items should be wrapped into a message content list."""
        raw = {
            "id": "tid-004",
            "status": "completed",
            "output": [{"type": "text", "text": "Hello"}],
        }

        detail = TaskDetail.model_validate(raw)

        assert len(detail.output) == 1
        assert len(detail.output[0].content) == 1
        assert detail.output[0].content[0].text == "Hello"

    def test_task_detail_official_file_output_shape(self):
        """Official file output items should validate without requiring a file_id."""
        raw = {
            "id": "tid-005",
            "status": "completed",
            "output": [
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_file",
                            "fileName": "report.txt",
                            "fileUrl": "https://example.com/report.txt",
                            "mimeType": "text/plain",
                        }
                    ],
                }
            ],
        }

        detail = TaskDetail.model_validate(raw)
        item = detail.output[0].content[0]

        assert item.file_name == "report.txt"
        assert item.url == "https://example.com/report.txt"
        assert item.file_id is None

    def test_task_detail_accepts_instructions_field(self):
        """TaskDetail should preserve the original instructions when provided by the API."""
        detail = TaskDetail.model_validate(
            {
                "id": "tid-006",
                "status": "completed",
                "instructions": "Continue the previous discussion",
                "output": [],
            }
        )

        assert detail.instructions == "Continue the previous discussion"

    def test_file_info_accepts_official_aliases(self):
        """FileInfo should parse id/filename fields from the API."""
        info = FileInfo.model_validate(
            {"id": "file-123", "filename": "report.txt", "size": 128}
        )

        assert info.file_id == "file-123"
        assert info.file_name == "report.txt"
        assert info.file_size == 128


class TestTaskStatusEnum:
    def test_task_status_enum(self):
        """TaskStatus members should equal their string values."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"

        # StrEnum values can be used as plain strings
        assert TaskStatus("completed") is TaskStatus.COMPLETED

    def test_agent_profile_enum(self):
        """AgentProfile values should match the Manus API contract."""
        assert AgentProfile.MANUS_1_6 == "manus-1.6"
        assert AgentProfile.LITE == "manus-1.6-lite"
        assert AgentProfile.MAX == "manus-1.6-max"
