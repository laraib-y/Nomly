"""Turn a dinner intent into one stored restaurant deck."""

import logging
import re

from app.core.exceptions import BadRequestError, ConflictError
from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate
from app.services.restaurants.base import RestaurantProvider, RestaurantProviderError
from app.services.restaurants.mock import MockRestaurantProvider
from app.services.restaurants.restaurant_normalizer import dedupe_restaurants
from app.services.restaurants.restaurant_ranker import (
    apply_hard_constraints,
    cuisine_matches,
    rank_candidates,
    select_diverse_deck,
)

logger = logging.getLogger(__name__)


class RestaurantSearchService:
    """Provider results are normalized, deduped, filtered, ranked, then diversified.

    The deck is built once per dinner. Swiping reads the stored list and does not
    call Geoapify again.
    """

    def __init__(self, provider: RestaurantProvider, fallback: RestaurantProvider | None = None) -> None:
        self.provider = provider
        self.fallback = fallback or MockRestaurantProvider()

    def build_deck(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        _validate_location(intent)
        logger.info(
            "Restaurant search started. cuisines=%s price=%s location=%s radius=%s",
            intent.cuisines or ["any"],
            intent.price_level,
            intent.location or "unspecified",
            intent.radius,
        )
        raw = self._load_candidates(intent)
        deduped = dedupe_restaurants(raw)
        constrained = apply_hard_constraints(deduped, intent)
        ranked = rank_candidates(constrained, intent)
        if intent.cuisines:
            matched = [item for item in ranked if cuisine_matches(item.restaurant, intent)]
            if matched:
                ranked = matched
            else:
                logger.info("No cuisine matches for %s. Using the best nearby places.", intent.cuisines)
        deck = [item.restaurant for item in select_diverse_deck(ranked)]
        logger.info("Provider returned %s candidates", len(raw))
        logger.info("After deduplication: %s", len(deduped))
        logger.info("After hard constraints: %s", len(constrained))
        logger.info("After ranking: %s", len(ranked))
        logger.info("Restaurant deck ready: %s", len(deck))
        if not deck:
            raise ConflictError(
                "Could not find restaurants for this dinner",
                code="NO_RESTAURANTS_FOUND",
            )
        return deck

    def _load_candidates(self, intent: DinnerIntent) -> list[RestaurantCandidate]:
        try:
            found = self.provider.collect(intent)
        except RestaurantProviderError as exc:
            logger.warning("Restaurant provider unavailable (%s). Using mock restaurants.", exc)
            return self.fallback.collect(intent)
        if found:
            return found
        if isinstance(self.provider, MockRestaurantProvider):
            return found
        logger.warning("Restaurant provider returned no places. Using mock restaurants.")
        return self.fallback.collect(intent)


def _validate_location(intent: DinnerIntent) -> None:
    if intent.location is None:
        return
    if not re.search(r"[A-Za-z]", intent.location):
        raise BadRequestError(
            "Enter a city or neighbourhood to search.",
            code="INVALID_LOCATION",
        )
