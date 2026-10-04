from datetime import datetime

from pydantic import BaseModel

from app.schemas.swipe import ResultsResponse


class HistoryWinner(BaseModel):
    restaurant_id: str
    name: str
    cuisine: str | None
    rating: float | None
    price: int | None
    address: str | None
    image_url: str | None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    website: str | None = None


class HistoryItem(BaseModel):
    """One finished dinner the signed-in user created. Aggregate numbers only."""

    session_id: str
    created_at: datetime
    completed_at: datetime
    description: str
    location: str | None
    group_size: int | None
    participant_count: int
    restaurant_count: int
    winner: HistoryWinner | None
    satisfaction_percent: int | None
    positives: int | None


class HistoryStats(BaseModel):
    dinners: int
    strong_matches: int
    average_satisfaction_percent: int | None
    average_group_size: float | None


class CuisineCount(BaseModel):
    label: str
    count: int


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    stats: HistoryStats
    cuisines: list[CuisineCount]


class HistoryDetail(HistoryItem):
    results: ResultsResponse
