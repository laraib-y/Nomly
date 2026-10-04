from fastapi import WebSocket


class ConnectionManager:
    """In-memory room fan-out for one API process."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, room_code: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms.setdefault(room_code, set()).add(websocket)

    def disconnect(self, room_code: str, websocket: WebSocket) -> None:
        room = self._rooms.get(room_code)
        if not room:
            return
        room.discard(websocket)
        if not room:
            self._rooms.pop(room_code, None)

    async def broadcast(self, room_code: str, message: dict) -> None:
        dead: list[WebSocket] = []
        for websocket in list(self._rooms.get(room_code, set())):
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(room_code, websocket)


manager = ConnectionManager()
