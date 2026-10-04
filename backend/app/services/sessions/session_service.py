import json
import logging
import re
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.time import utcnow
from app.models import Participant, Restaurant, Session, SessionRestaurant, Swipe
from app.schemas.ai import DinnerIntent
from app.schemas.restaurant import RestaurantCandidate, RestaurantRead
from app.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    JoinSessionRequest,
    JoinSessionResponse,
    ParticipantRead,
    ProgressRead,
    SessionRead,
    StartSessionRequest,
)
from app.schemas.swipe import CreateSwipeRequest, RestaurantResult, ResultsResponse, SwipeResponse
from app.services.ai.base import AIService
from app.services.ai.mock import MockAIService
from app.services.matching.matching_service import MatchRestaurant, MatchSwipe, MatchingService
from app.services.restaurants.base import RestaurantProvider
from app.services.restaurants.restaurant_search_service import RestaurantSearchService
from app.services.sessions.room_code import generate_room_code

logger = logging.getLogger(__name__)

ROOM_CODE_PATTERN = re.compile(r"^[A-Z0-9]{6}$")
NICKNAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .'\-]{0,23}$")


@dataclass
class SwipeOutcome:
    swipe: SwipeResponse
    results: ResultsResponse | None


class SessionService:
    """Owns dinner sessions, swipes, and when the matching engine runs."""

    def __init__(
        self,
        db: DbSession,
        ai: AIService,
        restaurants: RestaurantProvider,
        matching: MatchingService,
    ) -> None:
        self.db = db
        self.ai = ai
        self.restaurants = restaurants
        self.matching = matching

    def create_session(self, payload: CreateSessionRequest) -> CreateSessionResponse:
        nickname = clean_nickname(payload.nickname)
        description = " ".join(payload.description.split())
        if len(description) < 3:
            raise BadRequestError("Tell the group a little more about dinner")
        location = payload.location.strip() if payload.location and payload.location.strip() else None
        # group_size is only a planning hint. Ranking uses the people who actually join.

        intent = self._parse_intent(description, location)
        updates: dict[str, object] = {}
        if location:
            updates["location"] = location
        if payload.group_size is not None:
            updates["group_size"] = payload.group_size
        if updates:
            intent = intent.model_copy(update=updates)

        candidates = RestaurantSearchService(self.restaurants).build_deck(intent)

        dinner = Session(room_code=self._unique_room_code(), description=description, status="lobby")
        self.db.add(dinner)
        self.db.flush()

        host = Participant(session_id=dinner.id, nickname=nickname)
        self.db.add(host)
        self.db.flush()
        dinner.host_participant_id = host.id
        self._attach_restaurants(dinner, candidates[:15])
        self.db.commit()
        self.db.refresh(dinner)
        self.db.refresh(host)
        return CreateSessionResponse(
            **self._session_read(dinner).model_dump(),
            participant=self._participant_read(host, dinner),
            intent=intent,
        )

    def join_session(self, room_code: str, payload: JoinSessionRequest) -> JoinSessionResponse:
        dinner = self._require_session(room_code)
        if dinner.status != "lobby":
            raise ConflictError("This dinner is no longer accepting new people")
        nickname = clean_nickname(payload.nickname)
        self._ensure_nickname_available(dinner, nickname)
        participant = Participant(session_id=dinner.id, nickname=nickname)
        self.db.add(participant)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("That nickname is already in this room") from None
        self.db.refresh(dinner)
        self.db.refresh(participant)
        return JoinSessionResponse(
            **self._session_read(dinner).model_dump(),
            participant=self._participant_read(participant, dinner),
        )

    def get_session(self, room_code: str) -> SessionRead:
        return self._session_read(self._require_session(room_code))

    def start_session(self, room_code: str, payload: StartSessionRequest) -> SessionRead:
        dinner = self._require_session(room_code)
        participant = self._require_participant(dinner, payload.participant_id)
        if participant.id != dinner.host_participant_id:
            raise ForbiddenError("Only the host can start the dinner")
        if dinner.status == "active":
            raise ConflictError("Dinner has already started")
        if dinner.status == "completed":
            raise ConflictError("This dinner is already finished")
        if self._restaurant_count(dinner) < 1:
            raise ConflictError("Could not find restaurants for this dinner")
        dinner.status = "active"
        dinner.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(dinner)
        return self._session_read(dinner)

    def list_restaurants(self, room_code: str, participant_id: str | None = None) -> list[RestaurantRead]:
        dinner = self._require_session(room_code)
        if dinner.status == "lobby":
            raise ConflictError("Dinner has not started")
        decisions: dict[str, str] = {}
        if participant_id:
            participant = self._require_participant(dinner, participant_id)
            rows = (
                self.db.query(Swipe)
                .filter(Swipe.session_id == dinner.id, Swipe.participant_id == participant.id)
                .all()
            )
            decisions = {row.restaurant_id: row.decision for row in rows}

        links = (
            self.db.query(SessionRestaurant)
            .filter(SessionRestaurant.session_id == dinner.id)
            .order_by(SessionRestaurant.position.asc())
            .all()
        )
        restaurants: list[RestaurantRead] = []
        for link in links:
            place = link.restaurant
            restaurants.append(
                RestaurantRead(
                    id=place.id,
                    name=place.name,
                    description=place.description,
                    cuisine=place.cuisine,
                    categories=_load_categories(place.categories),
                    price=place.price,
                    rating=place.rating,
                    latitude=place.latitude,
                    longitude=place.longitude,
                    address=place.address,
                    image_url=place.image_url,
                    source=place.source,
                    position=link.position,
                    my_decision=decisions.get(place.id),
                )
            )
        return restaurants

    def record_swipe(self, room_code: str, payload: CreateSwipeRequest) -> SwipeOutcome:
        dinner = self._require_session(room_code)
        if dinner.status == "lobby":
            raise ConflictError("Dinner has not started")
        if dinner.status == "completed":
            raise ConflictError("This dinner is already finished")
        participant = self._require_participant(dinner, payload.participant_id)
        link = (
            self.db.query(SessionRestaurant)
            .filter(
                SessionRestaurant.session_id == dinner.id,
                SessionRestaurant.restaurant_id == payload.restaurant_id,
            )
            .one_or_none()
        )
        if link is None:
            raise NotFoundError("That restaurant is not part of this dinner")

        existing = (
            self.db.query(Swipe)
            .filter(
                Swipe.session_id == dinner.id,
                Swipe.participant_id == participant.id,
                Swipe.restaurant_id == payload.restaurant_id,
            )
            .one_or_none()
        )
        if existing is not None:
            raise ConflictError("You already decided on this restaurant")

        swipe = Swipe(
            session_id=dinner.id,
            participant_id=participant.id,
            restaurant_id=payload.restaurant_id,
            decision=payload.decision,
        )
        self.db.add(swipe)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("You already decided on this restaurant") from None

        progress = self._progress(dinner)
        all_completed = progress.total > 0 and progress.finished >= progress.total
        results: ResultsResponse | None = None
        if all_completed:
            dinner.status = "completed"
            dinner.updated_at = utcnow()
            results = self._build_results(dinner)
        self.db.commit()
        self.db.refresh(swipe)
        return SwipeOutcome(
            swipe=SwipeResponse(
                id=swipe.id,
                restaurant_id=swipe.restaurant_id,
                decision=payload.decision,
                progress=progress,
                all_completed=all_completed,
            ),
            results=results,
        )

    def get_results(self, room_code: str) -> ResultsResponse:
        dinner = self._require_session(room_code)
        if dinner.status == "lobby":
            raise ConflictError("Dinner has not started")
        progress = self._progress(dinner)
        if progress.total == 0 or progress.finished < progress.total:
            raise ConflictError("Not everyone has finished swiping")
        if dinner.status != "completed":
            dinner.status = "completed"
            dinner.updated_at = utcnow()
            self.db.commit()
            self.db.refresh(dinner)
        return self._build_results(dinner)

    def state_message(self, room_code: str) -> dict | None:
        try:
            code = normalize_room_code(room_code)
        except BadRequestError:
            return None
        dinner = self.db.query(Session).filter(Session.room_code == code).one_or_none()
        if dinner is None:
            return None
        session = self._session_read(dinner)
        return {
            "type": "state",
            "room_code": session.room_code,
            "status": session.status,
            "participants": [item.model_dump() for item in session.participants],
            "progress": session.progress.model_dump(),
        }

    def _parse_intent(self, description: str, location: str | None) -> DinnerIntent:
        try:
            return self.ai.parse_dinner_request(description, location)
        except Exception:
            logger.warning("AI parsing failed; using the built-in parser", exc_info=True)
            return MockAIService().parse_dinner_request(description, location)

    def _attach_restaurants(self, dinner: Session, candidates: list[RestaurantCandidate]) -> None:
        for position, candidate in enumerate(candidates):
            restaurant = (
                self.db.query(Restaurant)
                .filter(Restaurant.source == candidate.source, Restaurant.external_id == candidate.external_id)
                .one_or_none()
            )
            encoded_categories = json.dumps(candidate.categories) if candidate.categories else None
            if restaurant is None:
                restaurant = Restaurant(
                    external_id=candidate.external_id,
                    name=candidate.name,
                    description=candidate.description,
                    cuisine=candidate.cuisine,
                    categories=encoded_categories,
                    price=candidate.price,
                    rating=candidate.rating,
                    latitude=candidate.latitude,
                    longitude=candidate.longitude,
                    address=candidate.address,
                    image_url=candidate.image_url,
                    source=candidate.source,
                )
                self.db.add(restaurant)
                self.db.flush()
            elif encoded_categories and not restaurant.categories:
                restaurant.categories = encoded_categories
            self.db.add(
                SessionRestaurant(session_id=dinner.id, restaurant_id=restaurant.id, position=position)
            )

    def _build_results(self, dinner: Session) -> ResultsResponse:
        participants = self._participants(dinner)
        links = (
            self.db.query(SessionRestaurant)
            .filter(SessionRestaurant.session_id == dinner.id)
            .order_by(SessionRestaurant.position.asc())
            .all()
        )
        swipes = self.db.query(Swipe).filter(Swipe.session_id == dinner.id).all()
        ranked = self.matching.rank(
            [
                MatchRestaurant(
                    id=link.restaurant.id,
                    name=link.restaurant.name,
                    cuisine=link.restaurant.cuisine,
                    price=link.restaurant.price,
                    rating=link.restaurant.rating,
                    address=link.restaurant.address,
                    image_url=link.restaurant.image_url,
                    description=link.restaurant.description,
                )
                for link in links
            ],
            [
                MatchSwipe(
                    participant_id=swipe.participant_id,
                    restaurant_id=swipe.restaurant_id,
                    decision=swipe.decision,
                )
                for swipe in swipes
            ],
            len(participants),
        )
        results = [_to_result(item) for item in ranked]
        return ResultsResponse(
            room_code=dinner.room_code,
            status="completed",
            total_participants=len(participants),
            top_match=results[0] if results else None,
            alternatives=results[1:],
        )

    def _session_read(self, dinner: Session) -> SessionRead:
        if dinner.host_participant_id is None:
            raise ConflictError("This dinner is missing a host")
        participants = self._participants(dinner)
        status = dinner.status
        if status not in {"lobby", "active", "completed"}:
            status = "lobby"
        return SessionRead(
            id=dinner.id,
            room_code=dinner.room_code,
            description=dinner.description,
            status=status,  # type: ignore[arg-type]
            host_participant_id=dinner.host_participant_id,
            created_at=dinner.created_at,
            updated_at=dinner.updated_at,
            participants=[self._participant_read(person, dinner) for person in participants],
            restaurant_count=self._restaurant_count(dinner),
            progress=self._progress(dinner),
        )

    def _participants(self, dinner: Session) -> list[Participant]:
        return (
            self.db.query(Participant)
            .filter(Participant.session_id == dinner.id)
            .order_by(Participant.created_at.asc(), Participant.nickname.asc())
            .all()
        )

    def _participant_read(self, participant: Participant, dinner: Session) -> ParticipantRead:
        return ParticipantRead(
            id=participant.id,
            nickname=participant.nickname,
            is_host=participant.id == dinner.host_participant_id,
        )

    def _progress(self, dinner: Session) -> ProgressRead:
        total = (
            self.db.query(func.count(Participant.id)).filter(Participant.session_id == dinner.id).scalar() or 0
        )
        restaurant_count = self._restaurant_count(dinner)
        if total == 0 or restaurant_count == 0:
            return ProgressRead(finished=0, total=total)
        rows = (
            self.db.query(Swipe.participant_id, func.count(Swipe.id))
            .filter(Swipe.session_id == dinner.id)
            .group_by(Swipe.participant_id)
            .all()
        )
        finished = sum(1 for _participant_id, count in rows if count >= restaurant_count)
        return ProgressRead(finished=finished, total=total)

    def _restaurant_count(self, dinner: Session) -> int:
        return (
            self.db.query(func.count(SessionRestaurant.id))
            .filter(SessionRestaurant.session_id == dinner.id)
            .scalar()
            or 0
        )

    def _require_session(self, room_code: str) -> Session:
        code = normalize_room_code(room_code)
        dinner = self.db.query(Session).filter(Session.room_code == code).one_or_none()
        if dinner is None:
            raise NotFoundError("Session not found")
        return dinner

    def _require_participant(self, dinner: Session, participant_id: str) -> Participant:
        participant = (
            self.db.query(Participant)
            .filter(Participant.id == participant_id, Participant.session_id == dinner.id)
            .one_or_none()
        )
        if participant is None:
            raise NotFoundError("Participant not found")
        return participant

    def _ensure_nickname_available(self, dinner: Session, nickname: str) -> None:
        existing = (
            self.db.query(Participant)
            .filter(
                Participant.session_id == dinner.id,
                func.lower(Participant.nickname) == nickname.lower(),
            )
            .one_or_none()
        )
        if existing is not None:
            raise ConflictError("That nickname is already in this room")

    def _unique_room_code(self) -> str:
        for _ in range(8):
            code = generate_room_code()
            exists = self.db.query(Session.id).filter(Session.room_code == code).first()
            if exists is None:
                return code
        raise ConflictError("Could not generate a room code. Try again.")


def _load_categories(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if isinstance(item, str)]


def normalize_room_code(value: str) -> str:
    code = value.strip().upper()
    if not ROOM_CODE_PATTERN.fullmatch(code):
        raise BadRequestError("Invalid room code")
    return code


def clean_nickname(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not NICKNAME_PATTERN.fullmatch(cleaned):
        raise BadRequestError("Use a nickname with letters, numbers, spaces, apostrophes, or hyphens")
    return cleaned


def _to_result(item) -> RestaurantResult:
    return RestaurantResult(
        restaurant_id=item.restaurant_id,
        name=item.name,
        description=item.description,
        cuisine=item.cuisine,
        price=item.price,
        rating=item.rating,
        address=item.address,
        image_url=item.image_url,
        likes=item.likes,
        total_participants=item.total_participants,
        compatibility=item.compatibility,
        compatibility_percent=item.compatibility_percent,
        explanation=item.explanation,
    )
