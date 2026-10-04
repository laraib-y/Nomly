from abc import ABC, abstractmethod

from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate


class RestaurantProviderError(Exception):
    """Expected failure from a restaurant source, such as a missing key or HTTP error."""


class RestaurantProvider(ABC):
    """Finds restaurant candidates for one dinner session."""

    @abstractmethod
    def search(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        raise NotImplementedError

    def collect(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        """Return candidates before deck selection. Providers override this."""

        return self.search(intent)
