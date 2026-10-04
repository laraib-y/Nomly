from dataclasses import dataclass, field


@dataclass
class MatchRestaurant:
    id: str
    name: str
    cuisine: str | None = None
    price: int | None = None
    rating: float | None = None
    address: str | None = None
    image_url: str | None = None
    description: str | None = None
    categories: tuple[str, ...] = ()
    distance_meters: float | None = None
    relevance: float | None = None


@dataclass
class MatchSwipe:
    participant_id: str
    restaurant_id: str
    decision: str


@dataclass
class RankedRestaurant:
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
    super_likes: int = 0
    passes: int = 0
    vetoes: int = 0
    minimum_satisfaction: float = 0
    group_satisfaction: float = 0
    fairness_score: float = 0
    eliminated: bool = False
    reasons: list[str] = field(default_factory=list)
    relevance: float | None = None
