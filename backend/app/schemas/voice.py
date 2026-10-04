from pydantic import BaseModel, Field


class TranscriptRead(BaseModel):
    transcript: str


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=400)
