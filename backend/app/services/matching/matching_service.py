"""Deterministic fair group matching.

Satisfaction is Pass 0, Like 1, Super Like 2. The least-satisfied person is
ranked first, then average satisfaction, then raw enthusiasm. A veto or a
hard limit removes a place from the winning set.

satisfaction_percent is what users see as Group satisfaction: the share of
participants who were positive, (likes + super_likes) / participants. The
ranking does not use it. It keeps sorting on the weighted 0-2 values above,
reported as fairness.average_satisfaction_percent.
"""

import logging
from collections.abc import Sequence

from app.services.matching.constraints import MatchConstraints, elimination_reason
from app.services.matching.explanations import (
    explain_restaurant,
    explain_winner,
    higher_satisfaction,
    reason_lines,
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
        positives = score.likes + score.super_likes
        satisfaction = _percent(positives, total)
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
                compatibility=(positives / total) if total else 0.0,
                compatibility_percent=satisfaction,
                explanation="",
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
                positives=positives,
                satisfaction_percent=satisfaction,
                least_satisfied_percent=round(score.minimum_satisfaction * 50),
                average_satisfaction_percent=round(score.group_satisfaction * 50),
                elimination_reason=blocked,
            )
        )

    ranked.sort(key=_sort_key)
    for position, item in enumerate(ranked, start=1):
        item.rank = position
        item.explanation = explain_restaurant(item)
    if ranked:
        winner = ranked[0]
        winner.explanation = explain_winner(winner, ranked[1:])
        if not winner.eliminated:
            higher = higher_satisfaction(winner, [item for item in ranked[1:] if not item.eliminated])
            if higher:
                balanced = winner.minimum_satisfaction > higher[0].minimum_satisfaction
                winner.highlight = "best_balance" if balanced else "strongest_support"
                for item in higher:
                    item.highlight = "higher_satisfaction"
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


def _percent(part: int, whole: int) -> int:
    if whole <= 0:
        return 0
    return (part * 100 + whole // 2) // whole


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
