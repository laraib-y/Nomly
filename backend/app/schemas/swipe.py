from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.session import ProgressRead


class CreateSwipeRequest(BaseModel):
    participant_id: str = Field(min_length=1, max_length=36)
    restaurant_id: str = Field(min_length=1, max_length=36)
    decision: Literal["like", "pass"]


class RestaurantResult(BaseModel):
    restaurant_id: str
    name: str
    description: str | None
    cuisine: str | None
    price: int | None
    rating: float | None
    address: str | None
    image_url: str | None
    likes: int
    total_participants: int
    compatibility: float
    compatibility_percent: int
    explanation: str


class ResultsResponse(BaseModel):
    room_code: str
    status: str
    total_participants: int
    top_match: RestaurantResult | None
    alternatives: list[RestaurantResult]


class SwipeResponse(BaseModel):
    id: str
    restaurant_id: str
    decision: Literal["like", "pass"]
    progress: ProgressRead
    all_completed: bool
