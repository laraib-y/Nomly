from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.services.matching.models import MatchSwipe
from app.services.matching.preferences import SATISFACTION, PreferenceType


@dataclass(frozen=True)
class RestaurantScore:
    likes: int
    super_likes: int
    passes: int
    vetoes: int
    group_satisfaction: float
    minimum_satisfaction: float
    decisions: list[str]


def score_restaurants(
    restaurant_ids: Sequence[str],
    swipes: Sequence[MatchSwipe],
    participant_count: int,
) -> dict[str, RestaurantScore]:
    """Score every restaurant against the same group.

    A person who did not choose a place counts as unsatisfied there, so a
    couple of likes cannot look unanimous.
    """

    people = list(dict.fromkeys(swipe.participant_id for swipe in swipes))
    total = participant_count if participant_count > 0 else len(people)
    by_place: dict[str, dict[str, str]] = defaultdict(dict)
    for swipe in swipes:
        by_place[swipe.restaurant_id][swipe.participant_id] = swipe.decision

    scored: dict[str, RestaurantScore] = {}
    for restaurant_id in restaurant_ids:
        choices = by_place.get(restaurant_id, {})
        values: list[float] = []
        for person in people:
            decision = choices.get(person, PreferenceType.PASS)
            if decision == PreferenceType.VETO:
                values.append(0.0)
            else:
                values.append(SATISFACTION.get(PreferenceType(decision), 0.0))
        if len(values) < total:
            values.extend([0.0] * (total - len(values)))
        likes = sum(1 for choice in choices.values() if choice == PreferenceType.LIKE)
        super_likes = sum(1 for choice in choices.values() if choice == PreferenceType.SUPER_LIKE)
        vetoes = sum(1 for choice in choices.values() if choice == PreferenceType.VETO)
        passes = max(total - likes - super_likes - vetoes, 0)
        if total <= 0:
            group = 0.0
            floor = 0.0
        else:
            group = sum(values[:total]) / total
            floor = min(values[:total])
        scored[restaurant_id] = RestaurantScore(
            likes=likes,
            super_likes=super_likes,
            passes=passes,
            vetoes=vetoes,
            group_satisfaction=group,
            minimum_satisfaction=floor,
            decisions=list(choices.values()),
        )
    return scored
