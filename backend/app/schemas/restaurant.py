from pydantic import BaseModel, Field


class RestaurantCandidate(BaseModel):
    """Normalized restaurant from any provider, before it is stored."""

    external_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    cuisine: str | None = None
    categories: list[str] = Field(default_factory=list)
    price: int | None = Field(default=None, ge=1, le=4)
    rating: float | None = Field(default=None, ge=0, le=5)
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    image_url: str | None = None
    source: str = Field(min_length=1, max_length=32)


class RestaurantRead(BaseModel):
    id: str
    name: str
    description: str | None
    cuisine: str | None
    categories: list[str] = Field(default_factory=list)
    price: int | None
    rating: float | None
    latitude: float | None
    longitude: float | None
    address: str | None
    image_url: str | None
    source: str
    position: int
    my_decision: str | None = None
