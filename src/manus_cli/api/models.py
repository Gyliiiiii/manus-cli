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
    LITE = "lite"
    MAX = "max"


class CreateTaskRequest(_Base):
    prompt: str
    agent_profile: AgentProfile = AgentProfile.MANUS_1_6
    task_mode: str | None = None
    task_id: str | None = None  # for multi-turn continuation
    attachments: list[str] = Field(default_factory=list)  # file IDs


class CreateTaskResponse(_Base):
    task_id: str = Field(alias="id")
    status: TaskStatus = TaskStatus.PENDING


class OutputText(_Base):
    type: str = "text"
    text: str


class OutputFile(_Base):
    type: str = "file"
    file_id: str
    file_name: str
    url: str | None = None


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
                        messages.append(item)
                    else:
                        messages.append({"content": []})
                data["output"] = messages
            elif isinstance(out, dict):
                # single message dict -> wrap in list
                data["output"] = [out]
        return data


class FileInfo(_Base):
    file_id: str
    file_name: str
    file_size: int | None = None
    url: str | None = None
    created_at: str | None = None


class PresignedUpload(_Base):
    file_id: str
    upload_url: str
