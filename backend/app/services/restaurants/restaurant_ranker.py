"""Score restaurants for the swipe deck.

This is not the group matching engine. It only decides which places are worth
showing before anyone swipes.

Weights are intentionally explicit:

    cuisine match   40
    price fit       25
    location fit    15
    rating          15
    vibe/category    5

A price-2 Japanese request therefore prefers a well-rated price-2 Japanese
restaurant over a slightly higher-rated expensive one. Missing rating, price,
or coordinates stay neutral instead of being invented.
Dietary words such as "vegetarian" only boost a place when the provider already
labeled it that way. They are not a safety guarantee.
"""

from dataclasses import dataclass

from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate
from app.services.restaurants.restaurant_normalizer import distance_meters, valid_coordinate

DECK_LIMIT = 15


@dataclass(frozen=True)
class RankWeights:
    cuisine: float = 40
    price: float = 25
    location: float = 15
    rating: float = 15
    category: float = 5


@dataclass
class ScoredRestaurant:
    restaurant: RestaurantCandidate
    score: float


def apply_hard_constraints(
    restaurants: list[RestaurantCandidate],
    intent: DinnerIntent,
    center: tuple[float, float] | None = None,
) -> list[RestaurantCandidate]:
    """Drop places that miss a reliable budget or radius limit.

    A missing price or coordinate is kept. Incomplete provider data is not
    treated as a violation, and dietary metadata is never used as a medical filter.
    """

    kept: list[RestaurantCandidate] = []
    for restaurant in restaurants:
        if intent.price_level is not None and restaurant.price is not None and restaurant.price > intent.price_level:
            continue
        if center is not None:
            point = valid_coordinate(restaurant.latitude, restaurant.longitude)
            if point is not None and distance_meters(center[0], center[1], point[0], point[1]) > intent.radius:
                continue
        kept.append(restaurant)
    return kept


def cuisine_matches(restaurant: RestaurantCandidate, intent: DinnerIntent) -> bool:
    requested = {_key(cuisine) for cuisine in intent.cuisines}
    if not requested:
        return True
    labels = {_key(restaurant.cuisine or "")}
    labels.update(_key(category) for category in restaurant.categories)
    return any(label and (label in requested or any(label in item or item in label for item in requested)) for label in labels)


def rank_candidates(
    restaurants: list[RestaurantCandidate],
    intent: DinnerIntent,
    center: tuple[float, float] | None = None,
    weights: RankWeights | None = None,
) -> list[ScoredRestaurant]:
    chosen = weights or RankWeights()
    scored = [
        ScoredRestaurant(restaurant, _score(restaurant, intent, center, chosen))
        for restaurant in restaurants
    ]
    scored.sort(key=lambda item: (-item.score, item.restaurant.name.lower()))
    return scored


def select_diverse_deck(scored: list[ScoredRestaurant], limit: int = DECK_LIMIT) -> list[ScoredRestaurant]:
    """Pick a relevant deck, then spread cuisines when more than one is available.

    Hard-constraint filtering happens before this. Diversity never pulls a place
    back in after it was removed.
    """

    if not scored or limit <= 0:
        return []
    groups: dict[str, list[ScoredRestaurant]] = {}
    for item in scored:
        key = _key(item.restaurant.cuisine or "other") or "other"
        groups.setdefault(key, []).append(item)
    for group in groups.values():
        group.sort(key=lambda item: item.score, reverse=True)
    order = sorted(groups, key=lambda key: groups[key][0].score, reverse=True)
    picked: list[ScoredRestaurant] = []
    while len(picked) < limit and any(groups[key] for key in order):
        for key in order:
            if groups[key] and len(picked) < limit:
                picked.append(groups[key].pop(0))
    picked.sort(key=lambda item: (-item.score, item.restaurant.name.lower()))
    return picked


def _score(
    restaurant: RestaurantCandidate,
    intent: DinnerIntent,
    center: tuple[float, float] | None,
    weights: RankWeights,
) -> float:
    return (
        weights.cuisine * _cuisine_factor(restaurant, intent)
        + weights.price * _price_factor(restaurant, intent)
        + weights.location * _location_factor(restaurant, intent, center)
        + weights.rating * _rating_factor(restaurant.rating)
        + weights.category * _category_factor(restaurant, intent)
    )


def _cuisine_factor(restaurant: RestaurantCandidate, intent: DinnerIntent) -> float:
    if not intent.cuisines:
        return 0.6
    return 1.0 if cuisine_matches(restaurant, intent) else 0.0


def _price_factor(restaurant: RestaurantCandidate, intent: DinnerIntent) -> float:
    if intent.price_level is None:
        return 0.7
    if restaurant.price is None:
        return 0.55
    if restaurant.price > intent.price_level:
        return 0.0
    if restaurant.price == intent.price_level:
        return 1.0
    return 0.85


def _location_factor(
    restaurant: RestaurantCandidate,
    intent: DinnerIntent,
    center: tuple[float, float] | None,
) -> float:
    point = valid_coordinate(restaurant.latitude, restaurant.longitude)
    if center is None or point is None or intent.radius <= 0:
        return 0.6
    distance = distance_meters(center[0], center[1], point[0], point[1])
    if distance > intent.radius:
        return 0.0
    return 1 - (distance / intent.radius)


def _rating_factor(rating: float | None) -> float:
    if rating is None:
        return 0.45
    return max(0.0, min(rating, 5.0)) / 5


def _category_factor(restaurant: RestaurantCandidate, intent: DinnerIntent) -> float:
    haystack = " ".join(
        [restaurant.description or "", restaurant.cuisine or "", *restaurant.categories]
    ).lower()
    score = 0.3
    if intent.vibe and intent.vibe.lower() in haystack:
        score = 1.0
    for preference in intent.dietary_preferences:
        if preference and preference.lower() in haystack:
            score = 1.0
    return score


def _key(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").split())
