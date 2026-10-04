from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.ai import DinnerIntent


class CreateSessionRequest(BaseModel):
    description: str = Field(min_length=3, max_length=500)
    nickname: str = Field(min_length=1, max_length=24)
    location: str | None = Field(default=None, max_length=120)
    group_size: int | None = Field(default=None, ge=1, le=20)


class JoinSessionRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=24)


class StartSessionRequest(BaseModel):
    participant_id: str = Field(min_length=1, max_length=36)


class ParticipantRead(BaseModel):
    id: str
    nickname: str
    is_host: bool


class ProgressRead(BaseModel):
    finished: int
    total: int


class SessionRead(BaseModel):
    id: str
    room_code: str
    description: str
    status: Literal["lobby", "active", "completed"]
    host_participant_id: str
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantRead]
    restaurant_count: int
    progress: ProgressRead


class CreateSessionResponse(SessionRead):
    participant: ParticipantRead
    intent: DinnerIntent


class JoinSessionResponse(SessionRead):
    participant: ParticipantRead
