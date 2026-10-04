import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import open_session
from app.core.exceptions import BadRequestError
from app.services.matching.matching_service import MatchingService
from app.services.ai.factory import get_ai_service
from app.services.restaurants.factory import get_restaurant_provider
from app.services.sessions.session_service import SessionService, normalize_room_code
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/sessions/{room_code}")
async def session_socket(websocket: WebSocket, room_code: str, participant_id: str | None = None) -> None:
    logger.info("WebSocket connection requested session_code=%s", room_code)
    try:
        code = normalize_room_code(room_code)
    except BadRequestError:
        logger.info("WebSocket connection rejected session_code=%s reason=invalid_room_code", room_code)
        await _reject(websocket, "Invalid room code")
        return

    try:
        state = _load_state(code)
    except Exception as exc:
        logger.warning(
            "WebSocket connection rejected session_code=%s reason=state_unavailable error_type=%s",
            code,
            type(exc).__name__,
        )
        await _reject(websocket, "Session unavailable", code=1011)
        return

    if state is None:
        logger.info("WebSocket connection rejected session_code=%s reason=session_not_found", code)
        await _reject(websocket, "Session not found")
        return

    logger.info("WebSocket connection accepted session_code=%s session_found=true", code)
    await manager.connect(code, websocket)
    try:
        await websocket.send_json(state)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(code, websocket)
        if participant_id:
            await manager.broadcast(
                code,
                {"type": "participant_left", "participant_id": participant_id},
            )


async def _reject(websocket: WebSocket, detail: str, code: int = 1008) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "error", "detail": detail})
    await websocket.close(code=code)


def _load_state(room_code: str) -> dict | None:
    db = open_session()
    try:
        service = SessionService(
            db=db,
            ai=get_ai_service(),
            restaurants=get_restaurant_provider(),
            matching=MatchingService(),
        )
        return service.state_message(room_code)
    finally:
        db.close()
