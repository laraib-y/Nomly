"""Deterministic fair group matching.

Likes still decide a normal round. A veto removes a place from the winning
set, a super like raises satisfaction, and the least-satisfied person breaks
ties before raw enthusiasm does.
"""

import logging
from collections.abc import Sequence

from app.services.matching.constraints import MatchConstraints, elimination_reason
from app.services.matching.explanations import (
    elimination_copy,
    explain,
    explain_top,
    reason_lines,
    special_explanation,
)
from app.services.matching.fairness import fairness_score
from app.services.matching.models import MatchRestaurant, MatchSwipe, RankedRestaurant
from app.services.matching.scoring import score_restaurants

logger = logging.getLogger(__name__)

__all__ = [
    "MatchRestaurant",
    "MatchSwipe",
    "MatchingService",
    "RankedRestaurant",
    "rank_restaurants",
]


class MatchingService:
    def rank(
        self,
        restaurants: Sequence[MatchRestaurant],
        swipes: Sequence[MatchSwipe],
        participant_count: int,
        constraints: MatchConstraints | None = None,
    ) -> list[RankedRestaurant]:
        return rank_restaurants(restaurants, swipes, participant_count, constraints)


def rank_restaurants(
    restaurants: Sequence[MatchRestaurant],
    swipes: Sequence[MatchSwipe],
    participant_count: int,
    constraints: MatchConstraints | None = None,
) -> list[RankedRestaurant]:
    limits = constraints or MatchConstraints()
    total = max(participant_count, 0)
    scores = score_restaurants([restaurant.id for restaurant in restaurants], swipes, total)
    ranked: list[RankedRestaurant] = []

    for restaurant in restaurants:
        score = scores[restaurant.id]
        blocked = elimination_reason(restaurant, score.decisions, limits)
        compatibility = (score.likes / total) if total else 0.0
        classic = blocked is None and score.super_likes == 0 and score.vetoes == 0
        explanation = explain(score.likes, total) if classic else _explanation(restaurant, score, total, blocked, top=False)
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
                likes=score.likes,
                total_participants=total,
                compatibility=compatibility,
                compatibility_percent=_percent(score.likes, total),
                explanation=explanation,
                super_likes=score.super_likes,
                passes=score.passes,
                vetoes=score.vetoes,
                minimum_satisfaction=score.minimum_satisfaction,
                group_satisfaction=score.group_satisfaction,
                fairness_score=fairness_score(score.minimum_satisfaction),
                eliminated=blocked is not None,
                reasons=reason_lines(
                    likes=score.likes,
                    super_likes=score.super_likes,
                    passes=score.passes,
                    vetoes=score.vetoes,
                    total=total,
                    eliminated=blocked,
                ),
                relevance=restaurant.relevance,
            )
        )

    ranked.sort(key=_sort_key)
    if ranked and ranked[0].super_likes == 0 and ranked[0].vetoes == 0 and not ranked[0].eliminated:
        ranked[0].explanation = explain_top(ranked[0].likes, ranked[0].total_participants)
    elif ranked:
        winner = ranked[0]
        score = scores[winner.restaurant_id]
        blocked = "veto" if winner.vetoes else None
        if winner.eliminated and winner.vetoes:
            blocked = "veto"
        ranked[0].explanation = _explanation(
            next(restaurant for restaurant in restaurants if restaurant.id == winner.restaurant_id),
            score,
            total,
            _blocked_reason(winner, restaurants, limits, score),
            top=True,
        )
    if ranked:
        logger.info(
            "Matching complete. participants=%s evaluated=%s eligible=%s vetoed=%s winner=%s",
            total,
            len(ranked),
            sum(1 for item in ranked if not item.eliminated),
            sum(1 for item in ranked if item.vetoes),
            ranked[0].restaurant_id,
        )
    return ranked


def _blocked_reason(winner: RankedRestaurant, restaurants: Sequence[MatchRestaurant], limits: MatchConstraints, score) -> str | None:
    restaurant = next(item for item in restaurants if item.id == winner.restaurant_id)
    return elimination_reason(restaurant, score.decisions, limits)


def _explanation(restaurant: MatchRestaurant, score, total: int, blocked: str | None, *, top: bool) -> str:
    if blocked:
        return elimination_copy(blocked)
    return special_explanation(
        name=restaurant.name,
        likes=score.likes,
        super_likes=score.super_likes,
        passes=score.passes,
        vetoes=score.vetoes,
        total=total,
        top=top,
    )


def _percent(likes: int, total: int) -> int:
    if total <= 0:
        return 0
    return (likes * 100 + total // 2) // total


def _sort_key(item: RankedRestaurant) -> tuple:
    rating = item.rating if item.rating is not None else -1.0
    relevance = item.relevance if item.relevance is not None else -1.0
    return (
        item.eliminated,
        -item.minimum_satisfaction,
        -item.group_satisfaction,
        -item.super_likes,
        -item.likes,
        -relevance,
        -rating,
        item.restaurant_id,
    )
