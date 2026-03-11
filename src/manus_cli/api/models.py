from __future__ import annotations

from enum import StrEnum

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentProfile(StrEnum):
    MANUS_1_6 = "manus-1.6"
    LITE = "manus-1.6-lite"
    MAX = "manus-1.6-max"


class CreateTaskRequest(_Base):
    prompt: str
    agent_profile: AgentProfile = Field(
        default=AgentProfile.MANUS_1_6, alias="agentProfile"
    )
    task_mode: str | None = Field(default=None, alias="taskMode")
    task_id: str | None = Field(default=None, alias="taskId")  # for multi-turn continuation
    attachments: list[str] = Field(default_factory=list)  # file IDs


class CreateTaskResponse(_Base):
    task_id: str = Field(alias="id")
    status: TaskStatus = TaskStatus.PENDING


class OutputText(_Base):
    type: str = "text"
    text: str


class OutputFile(_Base):
    type: str = "file"
    file_id: str | None = Field(default=None, alias="id")
    file_name: str = Field(alias="fileName")
    url: str | None = Field(default=None, alias="fileUrl")
    mime_type: str | None = Field(default=None, alias="mimeType")


class OutputMessage(_Base):
    role: str = "assistant"
    content: list[OutputText | OutputFile] = Field(default_factory=list)


class CreditUsage(_Base):
    input_credits: float = 0
    output_credits: float = 0
    total_credits: float = 0


class TaskDetail(_Base):
    task_id: str = Field(alias="id")
    status: TaskStatus = TaskStatus.PENDING
    output: list[OutputMessage] = Field(default_factory=list)
    credit_usage: CreditUsage | None = None
    created_at: str | None = None
    updated_at: str | None = None
    error: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # credit_usage can be a plain int/float from the API
            cu = data.get("credit_usage")
            if isinstance(cu, (int, float)):
                data["credit_usage"] = {"total_credits": cu}
            # output: normalize list of raw dicts into OutputMessage-friendly dicts
            out = data.get("output")
            if isinstance(out, list):
                messages = []
                for item in out:
                    if isinstance(item, dict):
                        if "content" in item or "role" in item:
                            messages.append(item)
                        else:
                            messages.append({"role": "assistant", "content": [item]})
                    else:
                        messages.append({"content": []})
                data["output"] = messages
            elif isinstance(out, dict):
                if "content" in out or "role" in out:
                    data["output"] = [out]
                else:
                    data["output"] = [{"role": "assistant", "content": [out]}]
        return data


class FileInfo(_Base):
    file_id: str = Field(alias="id")
    file_name: str = Field(alias="filename")
    file_size: int | None = Field(default=None, alias="size")
    url: str | None = None
    created_at: str | None = None


class PresignedUpload(_Base):
    file_id: str = Field(alias="id")
    file_name: str | None = Field(default=None, alias="filename")
    upload_url: str
