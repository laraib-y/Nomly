from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.session import ProgressRead


PreferenceValue = Literal["like", "pass", "super_like", "veto"]


class CreateSwipeRequest(BaseModel):
    participant_id: str = Field(min_length=1, max_length=36)
    restaurant_id: str = Field(min_length=1, max_length=36)
    decision: PreferenceValue


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
    super_likes: int = 0
    passes: int = 0
    vetoes: int = 0
    total_participants: int
    compatibility: float
    compatibility_percent: int
    minimum_satisfaction: float = 0
    group_satisfaction: float = 0
    fairness_score: float = 0
    eliminated: bool = False
    reasons: list[str] = Field(default_factory=list)
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
    decision: PreferenceValue
    progress: ProgressRead
    all_completed: bool
    super_like_remaining: bool = True
    veto_remaining: bool = True
    super_likes_used: int = 0
    vetoes_used: int = 0
