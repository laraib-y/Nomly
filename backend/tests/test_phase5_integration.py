import json

from app.core import database
from app.models import Restaurant
from app.services.restaurants.embeddings import MockEmbeddingProvider
from tests.helpers import create_dinner


def test_semantic_deck_still_matches_the_group(client):
    embedder = MockEmbeddingProvider()
    db = database.SessionLocal()
    db.add(
        Restaurant(
            external_id="mock-sora-donburi",
            name="Sora Donburi",
            source="mock",
            cuisine="Japanese",
            price=2,
            rating=4.3,
            description="Rice bowls and a quiet counter.",
            address="5055 Kingsway, Burnaby",
            embedding_json=json.dumps(embedder.embed_text("cozy and quiet")),
        )
    )
    db.add(
        Restaurant(
            external_id="mock-seoul-night",
            name="Seoul Night Kitchen",
            source="mock",
            cuisine="Korean",
            price=2,
            rating=4.4,
            description="Late bowls, fried chicken, and a lively but unfussy dining room.",
            address="4700 Kingsway, Burnaby",
            embedding_json=json.dumps(embedder.embed_text("lively nightclub")),
        )
    )
    db.commit()
    db.close()

    created = create_dinner(
        client,
        description=(
            "We're five students looking for not too expensive Korean or Japanese food around Burnaby. "
            "We want somewhere cozy and quiet where we can actually talk."
        ),
    )
    code = created["room_code"]
    assert created["intent"]["location"] == "Burnaby"
    assert set(created["intent"]["cuisines"]) == {"Japanese", "Korean"}
    assert created["intent"]["price_level"] == 2
    assert created["intent"]["vibe"] == "cozy and quiet"
    assert "embedding" not in created

    people = [created["participant"]["id"]]
    for nickname in ("Sarah", "Omar"):
        joined = client.post(f"/api/sessions/{code}/join", json={"nickname": nickname})
        assert joined.status_code == 201, joined.text
        people.append(joined.json()["participant"]["id"])
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": people[0]}).status_code == 200

    restaurants = client.get(f"/api/sessions/{code}/restaurants").json()
    names = [item["name"] for item in restaurants]
    assert names[0] == "Sora Donburi"
    assert names.index("Sora Donburi") < names.index("Seoul Night Kitchen")
    assert "Palace Korean" not in names
    assert "Yoru Omakase" not in names
    assert all(item["price"] is None or item["price"] <= 2 for item in restaurants)
    assert all(item["cuisine"] in {"Japanese", "Korean"} for item in restaurants)
    assert all("cosine" not in json.dumps(item).lower() for item in restaurants)

    for person in people:
        for restaurant in restaurants:
            response = client.post(
                f"/api/sessions/{code}/swipes",
                json={"participant_id": person, "restaurant_id": restaurant["id"], "decision": "like"},
            )
            assert response.status_code == 201, response.text

    body = client.get(f"/api/sessions/{code}/results").json()
    assert body["top_match"]["restaurant_id"]
    assert body["top_match"]["eliminated"] is False
    assert "cosine" not in body["top_match"]["explanation"].lower()
    assert "Sarah" not in body["top_match"]["explanation"]
