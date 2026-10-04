from abc import ABC, abstractmethod

from app.schemas.ai import DinnerIntent


class AIService(ABC):
    """Turns a natural-language dinner request into validated search parameters."""

    @abstractmethod
    def parse_dinner_request(self, description: str, location: str | None = None) -> DinnerIntent:
        raise NotImplementedError
