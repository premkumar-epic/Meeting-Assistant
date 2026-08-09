from __future__ import annotations

from pydantic import BaseModel, Field


class MeetingListItem(BaseModel):
    id: int = Field(..., description="Unique meeting database ID")
    filename: str = Field(..., description="Processed audio filename")
    duration: float = Field(..., description="Total audio duration in seconds")
    summary: str = Field(..., description="Concise summary of the meeting")
    created_at: str = Field(..., description="Database insertion timestamp")


class ActionItem(BaseModel):
    id: int
    text: str
    assignee: str


class Entity(BaseModel):
    text: str
    label: str


class MeetingDetailResponse(BaseModel):
    id: int
    filename: str
    duration: float
    transcript: str
    summary: str
    action_items: list[ActionItem]
    entities: list[Entity]
    created_at: str


class ProcessMeetingResponse(BaseModel):
    job_id: str
    status: str
    progress: int


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatQuestionRequest(BaseModel):
    question: str = Field(..., max_length=1000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatAnswerResponse(BaseModel):
    answer: str


class ActiveModelConfigRequest(BaseModel):
    asr_provider: str
    asr_model: str
    summarizer_model: str
    llm_model: str


class ModelDownloadRequest(BaseModel):
    model_type: str
    model_id: str



