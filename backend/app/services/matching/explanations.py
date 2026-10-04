"""Aggregate-only wording for match results.

Every sentence is built from counts and from the same values the ranking
sorts on. Nothing here names a participant or reveals one person's choice.
"""

from collections.abc import Sequence

from app.services.matching.models import RankedRestaurant


def elimination_copy(reason: str | None) -> str:
    if reason == "budget":
        return "This restaurant is above the group's budget."
    if reason == "distance":
        return "This restaurant is outside the group's distance limit."
    if reason == "diet":
        return "This restaurant does not meet a dietary requirement for the group."
    return "This restaurant was eliminated by a group veto."


def vote_summary(*, likes: int, super_likes: int, passes: int, total: int) -> str:
    positives = likes + super_likes
    breakdown = ", ".join(
        [_count(likes, "Like"), _count(super_likes, "Super Like"), _count(passes, "Pass", "Passes")]
    )
    return f"{positives} of {total} were positive ({breakdown})."


def explain_restaurant(item: RankedRestaurant) -> str:
    if item.eliminated:
        return elimination_copy(item.elimination_reason)
    return vote_summary(
        likes=item.likes,
        super_likes=item.super_likes,
        passes=item.passes,
        total=item.total_participants,
    )


def explain_winner(winner: RankedRestaurant, others: Sequence[RankedRestaurant]) -> str:
    """Say why the winner beat the rest, using the ranking's own order of criteria."""

    if winner.eliminated:
        return f"No restaurant met every group limit, so this was the closest option. {elimination_copy(winner.elimination_reason)}"

    counts = vote_summary(
        likes=winner.likes,
        super_likes=winner.super_likes,
        passes=winner.passes,
        total=winner.total_participants,
    )
    eligible = [item for item in others if not item.eliminated]
    higher = higher_satisfaction(winner, eligible)
    if higher:
        best = higher[0]
        lead = (
            f"{best.name} had higher group satisfaction ({best.satisfaction_percent}% vs "
            f"{winner.satisfaction_percent}%), but {_why_it_lost(winner, best)}"
        )
        return f"{lead} {counts} Nobody vetoed it."

    runner = eligible[0] if eligible else None
    blocked = [item for item in others if item.eliminated and item.satisfaction_percent > winner.satisfaction_percent]
    lead = _lead(winner, runner, has_others=bool(others), qualifier=" among eligible options" if blocked else "")
    if blocked:
        best = max(blocked, key=lambda item: item.satisfaction_percent)
        lead += (
            f" {best.name} scored higher ({best.satisfaction_percent}%) but was not eligible: "
            f"{_not_eligible(best.elimination_reason)}."
        )
    return f"{lead} {counts} Nobody vetoed it."


def higher_satisfaction(winner: RankedRestaurant, eligible: Sequence[RankedRestaurant]) -> list[RankedRestaurant]:
    """Eligible alternatives that out-scored the winner on satisfaction, best first."""

    higher = [item for item in eligible if item.satisfaction_percent > winner.satisfaction_percent]
    return sorted(higher, key=lambda item: -item.satisfaction_percent)


def reason_lines(
    *,
    likes: int,
    super_likes: int,
    passes: int,
    vetoes: int,
    total: int,
    eliminated: str | None,
) -> list[str]:
    reasons = [f"{likes + super_likes} of {total} participants were positive"]
    if super_likes:
        reasons.append(f"{super_likes} participants strongly preferred it")
    if passes:
        reasons.append(f"{passes} participants passed")
    if vetoes:
        reasons.append("A group veto eliminated it")
    else:
        reasons.append("Nobody vetoed it")
    if eliminated == "budget":
        reasons.append("It is above the group's budget")
    elif eliminated == "distance":
        reasons.append("It is outside the group's distance limit")
    elif eliminated == "diet":
        reasons.append("It does not meet a dietary requirement")
    elif eliminated is None:
        reasons.append("It stayed inside the group's hard limits")
    return reasons


def _lead(winner: RankedRestaurant, runner: RankedRestaurant | None, *, has_others: bool, qualifier: str) -> str:
    name = winner.name
    if runner is None:
        return f"{name} was the only option that met every group limit." if has_others else f"{name} was the only option."

    percent = winner.satisfaction_percent
    if winner.minimum_satisfaction > runner.minimum_satisfaction:
        if winner.least_satisfied_percent == 100:
            return f"{name} was the strongest choice{qualifier}: everyone gave it a Super Like."
        return f"{name} was the most balanced choice{qualifier}: everyone was positive about it."
    if percent > runner.satisfaction_percent:
        return f"{name} had the highest group satisfaction{qualifier} ({percent}%)."
    if winner.group_satisfaction > runner.group_satisfaction:
        return (
            f"{name} tied with {runner.name} on group satisfaction ({percent}%) and had stronger overall support, "
            f"with {_count(winner.super_likes, 'Super Like')}."
        )
    deciding = _tie_break(winner, runner)
    if deciding:
        return f"{name} tied with {runner.name} on group satisfaction and overall support, and {deciding}."
    return f"{name} tied with {runner.name} on every measure, so Nomly used its fixed tie-break."


def _why_it_lost(winner: RankedRestaurant, other: RankedRestaurant) -> str:
    """Finish 'X had higher group satisfaction, but ...' with the criterion that ranked the winner first."""

    name = winner.name
    if winner.minimum_satisfaction > other.minimum_satisfaction:
        unhappy = f"{_count(other.passes, 'person', 'people')} passed on it" if other.passes else "it was less balanced"
        return f"{unhappy}. Nomly favors the option nobody has to settle for, and everyone was positive about {name}."
    if winner.group_satisfaction > other.group_satisfaction:
        return (
            f"{name} had stronger overall support. Nomly counts a Super Like as a stronger vote than a Like, "
            f"and {name} got {_count(winner.super_likes, 'Super Like')}."
        )
    deciding = _tie_break(winner, other)
    if deciding:
        return f"the two tied on overall support, and {name} {deciding}."
    return "the two tied on overall support, so Nomly used its fixed tie-break."


def _tie_break(winner: RankedRestaurant, other: RankedRestaurant) -> str:
    if winner.super_likes > other.super_likes:
        return "had more Super Likes"
    if winner.likes > other.likes:
        return "had more Likes"
    if (winner.relevance or -1.0) > (other.relevance or -1.0):
        return "was the closer match to what you asked for"
    if (winner.rating if winner.rating is not None else -1.0) > (other.rating if other.rating is not None else -1.0):
        return "has the higher rating"
    return ""


def _not_eligible(reason: str | None) -> str:
    if reason == "budget":
        return "it is above the group's budget"
    if reason == "distance":
        return "it is outside the group's distance limit"
    if reason == "diet":
        return "it does not meet a dietary requirement"
    return "it was removed by a group veto"


def _count(value: int, one: str, many: str | None = None) -> str:
    return f"{value} {one if value == 1 else (many or one + 's')}"
