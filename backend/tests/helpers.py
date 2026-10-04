from fastapi.testclient import TestClient

DINNER = {
    "description": "We want somewhere casual around Burnaby, not too expensive, preferably Japanese or Korean.",
    "nickname": "Abdalla",
    "location": "Burnaby",
    "group_size": 5,
}


def create_dinner(client: TestClient, **overrides) -> dict:
    payload = {**DINNER, **overrides}
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def start_dinner(client: TestClient, session: dict | None = None) -> tuple[dict, list[dict]]:
    body = session or create_dinner(client)
    started = client.post(
        f"/api/sessions/{body['room_code']}/start",
        json={"participant_id": body["participant"]["id"]},
    )
    assert started.status_code == 200, started.text
    restaurants = client.get(
        f"/api/sessions/{body['room_code']}/restaurants",
        params={"participant_id": body["participant"]["id"]},
    )
    assert restaurants.status_code == 200, restaurants.text
    return body, restaurants.json()
