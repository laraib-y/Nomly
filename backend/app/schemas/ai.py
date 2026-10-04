from pydantic import BaseModel, Field, field_validator


class DinnerIntent(BaseModel):
    """Structured search parameters produced by an AI service.

    Callers persist and query with this model only. Raw model text never
    becomes SQL.
    """

    group_size: int | None = Field(default=None, ge=1, le=20)
    cuisines: list[str] = Field(default_factory=list)
    price_level: int | None = Field(default=None, ge=1, le=4)
    location: str | None = Field(default=None, max_length=120)
    radius: int = Field(default=5000, ge=500, le=50000)
    vibe: str | None = Field(default=None, max_length=40)
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

    @field_validator("price_level", mode="before")
    @classmethod
    def coerce_price(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return value

    @field_validator("location", "vibe", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            text = " ".join(value.strip().split())
            return text or None
        return value
