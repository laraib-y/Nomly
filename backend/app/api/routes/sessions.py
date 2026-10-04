import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_session_service
from app.schemas.restaurant import RestaurantRead
from app.schemas.session import (
    CreateSessionRequest,
    CreateSessionResponse,
    JoinSessionRequest,
    JoinSessionResponse,
    SessionRead,
    StartSessionRequest,
)
from app.schemas.swipe import CreateSwipeRequest, ResultsResponse, SwipeResponse
from app.services.sessions.session_service import SessionService
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=CreateSessionResponse, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> CreateSessionResponse:
    return service.create_session(payload)


@router.post("/{room_code}/join", response_model=JoinSessionResponse, status_code=201)
async def join_session(
    room_code: str,
    payload: JoinSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> JoinSessionResponse:
    body = service.join_session(room_code, payload)
    await _publish(
        body.room_code,
        {
            "type": "participant_joined",
            "participant": {"id": body.participant.id, "nickname": body.participant.nickname},
            "participant_count": len(body.participants),
        },
    )
    return body


@router.get("/{room_code}", response_model=SessionRead)
def get_session(room_code: str, service: SessionService = Depends(get_session_service)) -> SessionRead:
    return service.get_session(room_code)


@router.post("/{room_code}/start", response_model=SessionRead)
async def start_session(
    room_code: str,
    payload: StartSessionRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionRead:
    body = service.start_session(room_code, payload)
    await _publish(
        body.room_code,
        {
            "type": "dinner_started",
            "status": body.status,
            "restaurant_count": body.restaurant_count,
        },
    )
    return body


@router.get("/{room_code}/restaurants", response_model=list[RestaurantRead])
def list_restaurants(
    room_code: str,
    participant_id: str | None = Query(default=None),
    service: SessionService = Depends(get_session_service),
) -> list[RestaurantRead]:
    return service.list_restaurants(room_code, participant_id)


@router.post("/{room_code}/swipes", response_model=SwipeResponse, status_code=201)
async def create_swipe(
    room_code: str,
    payload: CreateSwipeRequest,
    service: SessionService = Depends(get_session_service),
) -> SwipeResponse:
    outcome = service.record_swipe(room_code, payload)
    code = room_code.strip().upper()
    if outcome.swipe.all_completed:
        await _publish(
            code,
            {
                "type": "all_completed",
                "finished": outcome.swipe.progress.finished,
                "total": outcome.swipe.progress.total,
            },
        )
        top = outcome.results.top_match if outcome.results else None
        await _publish(
            code,
            {
                "type": "results_ready",
                "top_match": None
                if top is None
                else {
                    "name": top.name,
                    "compatibility_percent": top.compatibility_percent,
                    "likes": top.likes,
                    "total_participants": top.total_participants,
                },
            },
        )
    else:
        await _publish(
            code,
            {
                "type": "swipe_progress",
                "finished": outcome.swipe.progress.finished,
                "total": outcome.swipe.progress.total,
            },
        )
    return outcome.swipe


@router.get("/{room_code}/results", response_model=ResultsResponse)
def get_results(room_code: str, service: SessionService = Depends(get_session_service)) -> ResultsResponse:
    return service.get_results(room_code)


async def _publish(room_code: str, message: dict) -> None:
    try:
        await manager.broadcast(room_code, message)
    except Exception:
        logger.exception("WebSocket broadcast failed for room %s", room_code)
