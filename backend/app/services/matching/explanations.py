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


def elimination_copy(reason: str) -> str:
    if reason == "budget":
        return "This restaurant is above the group's budget."
    if reason == "distance":
        return "This restaurant is outside the group's distance limit."
    if reason == "diet":
        return "This restaurant does not meet a dietary requirement for the group."
    return "This restaurant was eliminated by a group veto."


def special_explanation(
    *,
    name: str,
    likes: int,
    super_likes: int,
    passes: int,
    vetoes: int,
    total: int,
    top: bool,
) -> str:
    positive = likes + super_likes
    parts = [f"{positive} of {total} people were positive about {name}"]
    if super_likes:
        parts.append(f"{super_likes} gave it a Super Like")
    if passes:
        parts.append(f"{passes} passed")
    if vetoes:
        parts.append("somebody vetoed it")
    elif top:
        parts.append("nobody vetoed it")
    sentence = ", ".join(parts)
    if top and passes == 0 and vetoes == 0:
        return f"This was the safest group choice: {sentence}."
    if top:
        return f"The group chose {name} because {sentence}."
    return f"{sentence.capitalize()}."


def reason_lines(
    *,
    likes: int,
    super_likes: int,
    passes: int,
    vetoes: int,
    total: int,
    eliminated: str | None,
) -> list[str]:
    reasons = [f"{likes} of {total} participants liked it"]
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
