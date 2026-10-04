from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.database import open_session
from app.core.exceptions import BadRequestError
from app.services.matching.matching_service import MatchingService
from app.services.ai.factory import get_ai_service
from app.services.restaurants.factory import get_restaurant_provider
from app.services.sessions.session_service import SessionService, normalize_room_code
from app.websocket.manager import manager

router = APIRouter()


@router.websocket("/ws/sessions/{room_code}")
async def session_socket(websocket: WebSocket, room_code: str, participant_id: str | None = None) -> None:
    try:
        code = normalize_room_code(room_code)
    except BadRequestError:
        await websocket.accept()
        await websocket.send_json({"type": "error", "detail": "Invalid room code"})
        await websocket.close(code=1008)
        return

    state = _load_state(code)
    if state is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "detail": "Session not found"})
        await websocket.close(code=1008)
        return

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
