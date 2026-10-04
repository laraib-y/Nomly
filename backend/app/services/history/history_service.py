import re
from collections import Counter

from app.core.exceptions import NotFoundError
from app.models import Session, User
from app.schemas.ai import DinnerIntent
from app.schemas.history import (
    CuisineCount,
    HistoryDetail,
    HistoryItem,
    HistoryListResponse,
    HistoryStats,
    HistoryWinner,
)
from app.schemas.swipe import ResultsResponse
from app.services.sessions.session_service import SessionService

HISTORY_LIMIT = 100
CUISINE_LIMIT = 6
CUISINE_SPLIT = re.compile(r"[;,/|]")


class HistoryService:
    """Finished dinners owned by one user. Every query is scoped to that user's id."""

    def __init__(self, sessions: SessionService) -> None:
        self.sessions = sessions
        self.db = sessions.db

    def list_for(self, user: User) -> HistoryListResponse:
        dinners = (
            self._owned(user)
            .order_by(Session.created_at.desc(), Session.id.desc())
            .limit(HISTORY_LIMIT)
            .all()
        )
        items = [self._item(dinner, self.sessions.results_for(dinner)) for dinner in dinners]
        return HistoryListResponse(items=items, stats=history_stats(items), cuisines=cuisine_counts(items))

    def detail_for(self, user: User, session_id: str) -> HistoryDetail:
        # Unknown, unfinished, and someone else's dinner all answer the same way.
        dinner = self._owned(user).filter(Session.id == session_id).one_or_none()
        if dinner is None:
            raise NotFoundError("Dinner not found")
        results = self.sessions.results_for(dinner)
        return HistoryDetail(**self._item(dinner, results).model_dump(), results=results)

    def _owned(self, user: User):
        return self.db.query(Session).filter(Session.user_id == user.id, Session.status == "completed")

    def _item(self, dinner: Session, results: ResultsResponse) -> HistoryItem:
        intent = _intent(dinner)
        top = results.top_match
        return HistoryItem(
            session_id=dinner.id,
            created_at=dinner.created_at,
            completed_at=dinner.updated_at,
            description=dinner.description,
            location=intent.location if intent else None,
            group_size=intent.group_size if intent else None,
            participant_count=results.total_participants,
            restaurant_count=len(dinner.restaurant_links),
            winner=None
            if top is None
            else HistoryWinner(
                restaurant_id=top.restaurant_id,
                name=top.name,
                cuisine=top.cuisine,
                rating=top.rating,
                price=top.price,
                address=top.address,
                image_url=top.image_url,
                latitude=top.latitude,
                longitude=top.longitude,
                phone=top.phone,
                website=top.website,
            ),
            satisfaction_percent=top.satisfaction_percent if top else None,
            positives=top.positives if top else None,
        )


def is_strong_match(item: HistoryItem) -> bool:
    """At least two-thirds of the table chose Like or Super Like for the winner."""
    if item.positives is None or item.participant_count <= 0:
        return False
    return item.positives * 3 >= item.participant_count * 2


def history_stats(items: list[HistoryItem]) -> HistoryStats:
    rated = [item.satisfaction_percent for item in items if item.satisfaction_percent is not None]
    sized = [item.participant_count for item in items if item.participant_count > 0]
    return HistoryStats(
        dinners=len(items),
        strong_matches=sum(1 for item in items if is_strong_match(item)),
        average_satisfaction_percent=round(sum(rated) / len(rated)) if rated else None,
        average_group_size=round(sum(sized) / len(sized), 1) if sized else None,
    )


def cuisine_counts(items: list[HistoryItem]) -> list[CuisineCount]:
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for item in items:
        label = _cuisine_label(item.winner.cuisine if item.winner else None)
        if label is None:
            continue
        key = label.lower()
        counts[key] += 1
        labels.setdefault(key, label)
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], labels[pair[0]]))
    return [CuisineCount(label=labels[key], count=count) for key, count in ordered[:CUISINE_LIMIT]]


def _cuisine_label(cuisine: str | None) -> str | None:
    if not cuisine:
        return None
    first = CUISINE_SPLIT.split(cuisine)[0].replace("_", " ").strip()
    if not first or first.lower() == "restaurant":
        return None
    return first[:1].upper() + first[1:]


def _intent(dinner: Session) -> DinnerIntent | None:
    if not dinner.intent_json:
        return None
    try:
        return DinnerIntent.model_validate_json(dinner.intent_json)
    except ValueError:
        return None
