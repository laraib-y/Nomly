from tests.helpers import create_dinner, start_dinner


def test_like_and_pass(client):
    created, restaurants = start_dinner(client)
    code = created["room_code"]
    host_id = created["participant"]["id"]

    liked = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": restaurants[0]["id"], "decision": "like"},
    )
    assert liked.status_code == 201, liked.text
    assert liked.json()["decision"] == "like"

    passed = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": restaurants[1]["id"], "decision": "pass"},
    )
    assert passed.status_code == 201, passed.text
    assert passed.json()["decision"] == "pass"

    deck = client.get(f"/api/sessions/{code}/restaurants", params={"participant_id": host_id}).json()
    assert deck[0]["my_decision"] == "like"
    assert deck[1]["my_decision"] == "pass"
    assert deck[2]["my_decision"] is None


def test_duplicate_swipe_is_rejected(client):
    created, restaurants = start_dinner(client)
    payload = {
        "participant_id": created["participant"]["id"],
        "restaurant_id": restaurants[0]["id"],
        "decision": "like",
    }
    first = client.post(f"/api/sessions/{created['room_code']}/swipes", json=payload)
    assert first.status_code == 201
    second = client.post(f"/api/sessions/{created['room_code']}/swipes", json=payload)
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_invalid_restaurant_and_participant(client):
    created, _restaurants = start_dinner(client)
    code = created["room_code"]
    missing_restaurant = client.post(
        f"/api/sessions/{code}/swipes",
        json={
            "participant_id": created["participant"]["id"],
            "restaurant_id": "11111111-1111-1111-1111-111111111111",
            "decision": "like",
        },
    )
    assert missing_restaurant.status_code == 404

    missing_participant = client.post(
        f"/api/sessions/{code}/swipes",
        json={
            "participant_id": "22222222-2222-2222-2222-222222222222",
            "restaurant_id": _restaurants[0]["id"],
            "decision": "pass",
        },
    )
    assert missing_participant.status_code == 404


def test_swipe_before_start_is_rejected(client):
    created = create_dinner(client)
    response = client.post(
        f"/api/sessions/{created['room_code']}/swipes",
        json={
            "participant_id": created["participant"]["id"],
            "restaurant_id": "11111111-1111-1111-1111-111111111111",
            "decision": "like",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Dinner has not started"
