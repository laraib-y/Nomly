import threading

from tests.helpers import create_dinner


def _wait_for(websocket, event_type: str, limit: int = 8) -> dict:
    seen = []
    for _ in range(limit):
        message = websocket.receive_json()
        seen.append(message)
        if message.get("type") == event_type:
            return message
    raise AssertionError(f"Did not see {event_type}. Saw {seen}")


def _run(function):
    errors: list[BaseException] = []

    def wrapper() -> None:
        try:
            function()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the test thread
            errors.append(exc)

    thread = threading.Thread(target=wrapper)
    thread.start()
    thread.join(timeout=15)
    assert not thread.is_alive(), "background request did not finish"
    if errors:
        raise errors[0]


def test_participant_joined(client):
    created = create_dinner(client)
    code = created["room_code"]

    with client.websocket_connect(f"/ws/sessions/{code}") as websocket:
        state = websocket.receive_json()
        assert state["type"] == "state"
        assert state["status"] == "lobby"
        assert state["participants"][0]["nickname"] == "Abdalla"

        def join() -> None:
            response = client.post(f"/api/sessions/{code}/join", json={"nickname": "Sarah"})
            assert response.status_code == 201, response.text

        _run(join)
        event = _wait_for(websocket, "participant_joined")
        assert event["participant"]["nickname"] == "Sarah"
        assert event["participant_count"] == 2


def test_participant_left(client):
    created = create_dinner(client)
    code = created["room_code"]
    host_id = created["participant"]["id"]

    with client.websocket_connect(f"/ws/sessions/{code}?participant_id={host_id}") as watcher:
        assert watcher.receive_json()["type"] == "state"
        with client.websocket_connect(f"/ws/sessions/{code}?participant_id=guest-socket") as guest:
            assert guest.receive_json()["type"] == "state"
        event = _wait_for(watcher, "participant_left")
        assert event["participant_id"] == "guest-socket"


def test_dinner_started(client):
    created = create_dinner(client)
    code = created["room_code"]
    host_id = created["participant"]["id"]

    with client.websocket_connect(f"/ws/sessions/{code}") as websocket:
        assert websocket.receive_json()["type"] == "state"

        def start() -> None:
            response = client.post(f"/api/sessions/{code}/start", json={"participant_id": host_id})
            assert response.status_code == 200, response.text

        _run(start)
        event = _wait_for(websocket, "dinner_started")
        assert event["status"] == "active"
        assert 10 <= event["restaurant_count"] <= 15


def test_swipe_progress_completion_and_results(client):
    created = create_dinner(client, nickname="Abdalla")
    code = created["room_code"]
    host_id = created["participant"]["id"]
    sarah = client.post(f"/api/sessions/{code}/join", json={"nickname": "Sarah"}).json()["participant"]["id"]
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": host_id}).status_code == 200
    restaurants = client.get(f"/api/sessions/{code}/restaurants").json()

    with client.websocket_connect(f"/ws/sessions/{code}?participant_id={host_id}") as websocket:
        assert websocket.receive_json()["type"] == "state"

        def swipe_all() -> None:
            for participant_id in (host_id, sarah):
                for restaurant in restaurants:
                    response = client.post(
                        f"/api/sessions/{code}/swipes",
                        json={
                            "participant_id": participant_id,
                            "restaurant_id": restaurant["id"],
                            "decision": "like",
                        },
                    )
                    assert response.status_code == 201, response.text

        _run(swipe_all)
        progress = _wait_for(websocket, "swipe_progress", limit=40)
        assert progress["total"] == 2
        assert progress["finished"] <= progress["total"]
        completed = _wait_for(websocket, "all_completed", limit=40)
        assert completed["finished"] == 2
        assert completed["total"] == 2
        ready = _wait_for(websocket, "results_ready", limit=5)
        assert ready["top_match"]["compatibility_percent"] == 100
        assert ready["top_match"]["likes"] == 2
        assert "Sarah liked" not in str(ready)
