from enum import Enum


class PreferenceType(str, Enum):
    """One participant's decision on one restaurant."""

    PASS = "pass"
    LIKE = "like"
    SUPER_LIKE = "super_like"
    VETO = "veto"


# Pass is unsatisfied, a like is satisfied, a super like is twice that.
# A veto is not a score. It removes the restaurant from the winning set.
SATISFACTION = {
    PreferenceType.PASS: 0.0,
    PreferenceType.LIKE: 1.0,
    PreferenceType.SUPER_LIKE: 2.0,
}


def quota_key(decision: str, restaurant_id: str) -> str:
    """One super like and one veto per person. Ordinary decisions stay per restaurant."""

    if decision == PreferenceType.SUPER_LIKE:
        return "super_like"
    if decision == PreferenceType.VETO:
        return "veto"
    return f"standard:{restaurant_id}"
