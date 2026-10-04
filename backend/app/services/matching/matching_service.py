"""Deterministic group matching.

The ranking lives here on purpose. Fairness rules, ranked choice, and
travel-time tie breaks can replace `rank_restaurants` later without
changing the HTTP API.
"""

from collections.abc import Sequence
from dataclasses import dataclass


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


class MatchingService:
    def rank(
        self,
        restaurants: Sequence[MatchRestaurant],
        swipes: Sequence[MatchSwipe],
        participant_count: int,
    ) -> list[RankedRestaurant]:
        return rank_restaurants(restaurants, swipes, participant_count)


def rank_restaurants(
    restaurants: Sequence[MatchRestaurant],
    swipes: Sequence[MatchSwipe],
    participant_count: int,
) -> list[RankedRestaurant]:
    """Rank by compatibility, then likes, then rating.

    compatibility = likes / total participants.
    """

    likes_by_restaurant = _like_counts(swipes)
    ranked: list[RankedRestaurant] = []
    total = max(participant_count, 0)

    for restaurant in restaurants:
        likes = likes_by_restaurant.get(restaurant.id, 0)
        compatibility = (likes / total) if total else 0.0
        percent = _percent(likes, total)
        ranked.append(
            RankedRestaurant(
                restaurant_id=restaurant.id,
                name=restaurant.name,
                description=restaurant.description,
                cuisine=restaurant.cuisine,
                price=restaurant.price,
                rating=restaurant.rating,
                address=restaurant.address,
                image_url=restaurant.image_url,
                likes=likes,
                total_participants=total,
                compatibility=compatibility,
                compatibility_percent=percent,
                explanation=explain(likes, total),
            )
        )

    ranked.sort(key=_sort_key)
    if ranked:
        ranked[0].explanation = explain_top(ranked[0].likes, ranked[0].total_participants)
    return ranked


def explain(likes: int, total: int) -> str:
    if total > 0 and likes == total:
        return "Everyone in your group liked this restaurant."
    if total > 0 and likes * 2 >= total:
        return "This restaurant was liked by most of your group."
    if likes == 0:
        return "Nobody in the group liked this restaurant."
    return "Some of your group liked this restaurant."


def explain_top(likes: int, total: int) -> str:
    if total > 0 and likes == total:
        return "Everyone in your group liked this restaurant."
    if total > 0 and likes * 2 >= total:
        return "This restaurant was liked by most of your group."
    if likes > 0:
        return "This restaurant had the strongest agreement in your group."
    return "Nobody agreed on a favorite, so this was the closest option."


def _like_counts(swipes: Sequence[MatchSwipe]) -> dict[str, int]:
    counts: dict[str, int] = {}
    seen: set[tuple[str, str]] = set()
    for swipe in swipes:
        key = (swipe.participant_id, swipe.restaurant_id)
        if key in seen or swipe.decision != "like":
            seen.add(key)
            continue
        seen.add(key)
        counts[swipe.restaurant_id] = counts.get(swipe.restaurant_id, 0) + 1
    return counts


def _percent(likes: int, total: int) -> int:
    if total <= 0:
        return 0
    return (likes * 100 + total // 2) // total


def _sort_key(item: RankedRestaurant) -> tuple:
    rating = item.rating if item.rating is not None else -1.0
    return (-item.compatibility, -item.likes, -rating, item.name.lower())
