def fairness_score(minimum_satisfaction: float) -> float:
    """How safe the place is for the least-satisfied person.

    Satisfaction is 0 for a pass, 1 for a like, and 2 for a super like.
    The floor is what stops a loud minority from beating a meal everyone accepts.
    """

    return minimum_satisfaction
