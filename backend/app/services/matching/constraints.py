from dataclasses import dataclass

from app.services.matching.models import MatchRestaurant
from app.services.matching.preferences import PreferenceType


@dataclass(frozen=True)
class MatchConstraints:
    """Authoritative limits from the dinner intent. Missing values are not violations."""

    price_level: int | None = None
    dietary_preferences: tuple[str, ...] = ()
    radius_meters: int | None = None


def elimination_reason(
    restaurant: MatchRestaurant,
    decisions: list[str],
    constraints: MatchConstraints,
) -> str | None:
    """Return why a restaurant cannot win, or None when it stays eligible.

    Budget, distance, and diet are checked before a veto. A missing price,
    distance, or label is not treated as a violation.
    """

    if _over_budget(restaurant, constraints):
        return "budget"
    if _too_far(restaurant, constraints):
        return "distance"
    if _misses_diet(restaurant, constraints):
        return "diet"
    if any(decision == PreferenceType.VETO for decision in decisions):
        return "veto"
    return None


def _over_budget(restaurant: MatchRestaurant, constraints: MatchConstraints) -> bool:
    if constraints.price_level is None or restaurant.price is None:
        return False
    return restaurant.price > constraints.price_level


def _too_far(restaurant: MatchRestaurant, constraints: MatchConstraints) -> bool:
    if constraints.radius_meters is None or restaurant.distance_meters is None:
        return False
    return restaurant.distance_meters > constraints.radius_meters


def _misses_diet(restaurant: MatchRestaurant, constraints: MatchConstraints) -> bool:
    if not constraints.dietary_preferences:
        return False
    haystack = " ".join(
        [
            restaurant.cuisine or "",
            restaurant.description or "",
            *restaurant.categories,
        ]
    ).lower()
    if not haystack.strip():
        return False
    return any(preference.lower() not in haystack for preference in constraints.dietary_preferences)
