from app.services.sessions.room_code import ROOM_CODE_ALPHABET
from tests.helpers import create_dinner


def test_create_session_and_room_code(client):
    body = create_dinner(client)

    assert body["status"] == "lobby"
    assert body["description"].startswith("We want somewhere casual")
    assert body["participant"]["nickname"] == "Abdalla"
    assert body["participant"]["is_host"] is True
    assert body["host_participant_id"] == body["participant"]["id"]
    assert len(body["room_code"]) == 6
    assert all(character in ROOM_CODE_ALPHABET for character in body["room_code"])
    assert body["intent"]["location"] == "Burnaby"
    assert body["intent"]["cuisines"] == ["Japanese", "Korean"]
    assert body["intent"]["price_level"] == 2
    assert body["intent"]["vibe"] == "casual"
    assert 10 <= body["restaurant_count"] <= 15


def test_room_codes_are_unique(client):
    first = create_dinner(client)
    second = create_dinner(client, nickname="Sarah")
    assert first["room_code"] != second["room_code"]


def test_join_and_retrieve_session(client):
    created = create_dinner(client)
    code = created["room_code"]

    joined = client.post(f"/api/sessions/{code.lower()}/join", json={"nickname": "Sarah"})
    assert joined.status_code == 201, joined.text
    body = joined.json()
    assert body["participant"]["nickname"] == "Sarah"
    assert body["participant"]["is_host"] is False
    assert [person["nickname"] for person in body["participants"]] == ["Abdalla", "Sarah"]

    fetched = client.get(f"/api/sessions/{code}")
    assert fetched.status_code == 200
    assert len(fetched.json()["participants"]) == 2


def test_duplicate_nickname_is_rejected(client):
    created = create_dinner(client)
    response = client.post(
        f"/api/sessions/{created['room_code']}/join",
        json={"nickname": " abdalla "},
    )
    assert response.status_code == 409
    assert "nickname" in response.json()["detail"].lower()


def test_invalid_room_code(client):
    response = client.post("/api/sessions/nope/join", json={"nickname": "Sarah"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid room code"


def test_missing_session(client):
    response = client.get("/api/sessions/ZZZZZZ")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"


def test_only_host_can_start(client):
    created = create_dinner(client)
    code = created["room_code"]
    joined = client.post(f"/api/sessions/{code}/join", json={"nickname": "Sarah"})
    assert joined.status_code == 201

    rejected = client.post(
        f"/api/sessions/{code}/start",
        json={"participant_id": joined.json()["participant"]["id"]},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "Only the host can start the dinner"

    unknown = client.post(
        f"/api/sessions/{code}/start",
        json={"participant_id": "11111111-1111-1111-1111-111111111111"},
    )
    assert unknown.status_code == 404


def test_host_starts_dinner(client):
    created = create_dinner(client)
    code = created["room_code"]

    blocked = client.get(f"/api/sessions/{code}/restaurants")
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "Dinner has not started"

    started = client.post(
        f"/api/sessions/{code}/start",
        json={"participant_id": created["participant"]["id"]},
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "active"

    again = client.post(
        f"/api/sessions/{code}/start",
        json={"participant_id": created["participant"]["id"]},
    )
    assert again.status_code == 409

    restaurants = client.get(f"/api/sessions/{code}/restaurants")
    assert restaurants.status_code == 200
    deck = restaurants.json()
    assert 10 <= len(deck) <= 15
    assert [item["position"] for item in deck] == list(range(len(deck)))
    again_deck = client.get(f"/api/sessions/{code}/restaurants").json()
    assert [item["id"] for item in again_deck] == [item["id"] for item in deck]


def test_join_after_start_is_rejected(client):
    created = create_dinner(client)
    client.post(
        f"/api/sessions/{created['room_code']}/start",
        json={"participant_id": created["participant"]["id"]},
    )
    response = client.post(f"/api/sessions/{created['room_code']}/join", json={"nickname": "Omar"})
    assert response.status_code == 409
