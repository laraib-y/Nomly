from pydantic import BaseModel, Field, field_validator

# Geoapify filters use meters. Parsers leave radius empty unless the user
# stated a distance; restaurant search applies this default itself.
DEFAULT_SEARCH_RADIUS_METERS = 5000


class DinnerIntent(BaseModel):
    """Structured search parameters produced by an AI service.

    Missing preferences stay null or empty. Callers persist and query with
    this model only. Raw model text never becomes SQL.
    """

    group_size: int | None = Field(default=None, ge=1, le=20)
    cuisines: list[str] = Field(default_factory=list)
    price_level: int | None = Field(default=None, ge=1, le=4)
    location: str | None = Field(default=None, max_length=120)
    radius: int | None = Field(default=None, ge=500, le=50000)
    vibe: str | None = Field(default=None, max_length=80)
    dietary_preferences: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @field_validator("cuisines", mode="before")
    @classmethod
    def coerce_cuisines(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            raise ValueError("cuisines must be a list of strings")
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text[:40])
        return cleaned[:6]

    @field_validator("dietary_preferences", mode="before")
    @classmethod
    def coerce_diets(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in value.split(",")]
        if not isinstance(value, list):
            raise ValueError("dietary_preferences must be a list of strings")
        cleaned: list[str] = []
        for item in value:
            text = str(item).strip().lower()
            if text and text not in cleaned:
                cleaned.append(text[:40])
        return cleaned[:6]

    @field_validator("price_level", "group_size", "radius", mode="before")
    @classmethod
    def coerce_optional_int(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"", "null", "none"}:
                return None
            if text.isdigit():
                return int(text)
        return value

    @field_validator("location", "vibe", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            text = " ".join(value.strip().split())
            return text or None
        return value


def search_radius_meters(intent: DinnerIntent) -> int:
    """Radius the restaurant search should use.

    A null intent radius means the user did not choose one. Search keeps its
    own default instead of storing that default as if the user said it.
    """

    if intent.radius is None:
        return DEFAULT_SEARCH_RADIUS_METERS
    return intent.radius


def apply_explicit_fields(
    intent: DinnerIntent,
    *,
    location: str | None = None,
    group_size: int | None = None,
) -> DinnerIntent:
    """Explicit form fields win over anything extracted from the description."""

    updates: dict[str, object] = {}
    if location is not None and location.strip():
        updates["location"] = " ".join(location.split())
    if group_size is not None:
        updates["group_size"] = group_size
    if not updates:
        return intent
    return intent.model_copy(update=updates)
