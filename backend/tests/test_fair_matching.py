from app.services.matching.constraints import MatchConstraints
from app.services.matching.matching_service import MatchRestaurant, MatchSwipe, rank_restaurants
from tests.helpers import create_dinner, start_dinner


def _people(count: int) -> list[str]:
    return [f"p{index}" for index in range(count)]


def _votes(restaurant_id: str, decisions: list[str]) -> list[MatchSwipe]:
    return [MatchSwipe(f"p{index}", restaurant_id, decision) for index, decision in enumerate(decisions)]


def test_super_like_outranks_the_same_number_of_plain_likes():
    restaurants = [
        MatchRestaurant(id="plain", name="Plain", rating=4.0),
        MatchRestaurant(id="strong", name="Strong", rating=4.0),
    ]
    swipes = [
        *_votes("plain", ["like", "like", "like", "pass", "pass"]),
        *_votes("strong", ["super_like", "like", "like", "pass", "pass"]),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=5)
    assert [item.restaurant_id for item in ranked] == ["strong", "plain"]
    assert ranked[0].super_likes == 1
    assert "Super Like" in ranked[0].explanation
    assert "p0" not in ranked[0].explanation


def test_five_likes_beat_two_super_likes_and_three_passes():
    restaurants = [
        MatchRestaurant(id="loud", name="Loud"),
        MatchRestaurant(id="balanced", name="Balanced"),
    ]
    swipes = [
        *_votes("loud", ["super_like", "super_like", "pass", "pass", "pass"]),
        *_votes("balanced", ["like", "like", "like", "like", "like"]),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=5)
    assert ranked[0].restaurant_id == "balanced"
    assert ranked[0].fairness_score > ranked[1].fairness_score
    assert ranked[0].minimum_satisfaction == 1
    assert ranked[1].minimum_satisfaction == 0


def test_veto_overrides_super_like_and_cannot_win():
    restaurants = [
        MatchRestaurant(id="blocked", name="Blocked", rating=5),
        MatchRestaurant(id="ok", name="Okay", rating=3),
    ]
    swipes = [
        MatchSwipe("p0", "blocked", "veto"),
        MatchSwipe("p1", "blocked", "super_like"),
        MatchSwipe("p2", "blocked", "like"),
        MatchSwipe("p3", "blocked", "like"),
        MatchSwipe("p4", "blocked", "like"),
        *_votes("ok", ["like", "like", "like", "pass", "pass"]),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=5)
    assert ranked[0].restaurant_id == "ok"
    blocked = next(item for item in ranked if item.restaurant_id == "blocked")
    assert blocked.eliminated is True
    assert blocked.explanation == "This restaurant was eliminated by a group veto."
    assert "p0" not in " ".join(blocked.reasons)


def test_hard_constraints_cannot_win():
    restaurants = [
        MatchRestaurant(id="pricey", name="Pricey", price=4, rating=5),
        MatchRestaurant(id="far", name="Far", distance_meters=9000, rating=5),
        MatchRestaurant(id="meat", name="Meat", cuisine="Japanese", categories=("Japanese",), rating=5),
        MatchRestaurant(id="bowl", name="Bowl", cuisine="Vegetarian", categories=("Vegetarian",), price=1, distance_meters=1000),
    ]
    swipes = []
    for restaurant in restaurants:
        swipes.extend(_votes(restaurant.id, ["like", "like", "like", "like", "like"]))
    ranked = rank_restaurants(
        restaurants,
        swipes,
        participant_count=5,
        constraints=MatchConstraints(price_level=2, dietary_preferences=("vegetarian",), radius_meters=5000),
    )
    assert ranked[0].restaurant_id == "bowl"
    by_id = {item.restaurant_id: item for item in ranked}
    assert by_id["pricey"].eliminated is True
    assert "budget" in by_id["pricey"].explanation
    assert by_id["far"].eliminated is True
    assert "distance" in by_id["far"].explanation
    assert by_id["meat"].eliminated is True
    assert "dietary" in by_id["meat"].explanation


def test_tie_break_is_deterministic():
    restaurants = [
        MatchRestaurant(id="b", name="Bravo", rating=4, relevance=1),
        MatchRestaurant(id="a", name="Alpha", rating=4, relevance=3),
        MatchRestaurant(id="c", name="Charlie", rating=4, relevance=3),
    ]
    swipes = []
    for restaurant_id in ("a", "b", "c"):
        swipes.extend(_votes(restaurant_id, ["like", "like"]))
    first = rank_restaurants(restaurants, swipes, participant_count=2)
    second = rank_restaurants(restaurants, swipes, participant_count=2)
    assert [item.restaurant_id for item in first] == ["a", "c", "b"]
    assert [item.restaurant_id for item in second] == [item.restaurant_id for item in first]


def test_explanation_reports_counts_without_names():
    ranked = rank_restaurants(
        [MatchRestaurant(id="a", name="Han River BBQ")],
        _votes("a", ["super_like", "super_like", "like", "like", "pass"]),
        participant_count=5,
    )
    winner = ranked[0]
    assert winner.likes == 2
    assert winner.super_likes == 2
    assert winner.passes == 1
    assert winner.vetoes == 0
    assert winner.total_participants == 5
    assert any("strongly preferred" in reason for reason in winner.reasons)
    assert "Abdalla" not in winner.explanation
    assert "p0" not in winner.explanation


def test_super_like_and_veto_limits(client):
    created, restaurants = start_dinner(client)
    code = created["room_code"]
    host_id = created["participant"]["id"]
    first = restaurants[0]["id"]
    second = restaurants[1]["id"]

    liked = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": first, "decision": "super_like"},
    )
    assert liked.status_code == 201, liked.text
    assert liked.json()["super_like_remaining"] is False
    assert liked.json()["veto_remaining"] is True

    again = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": second, "decision": "super_like"},
    )
    assert again.status_code == 409
    assert "Super Like" in again.json()["detail"]

    veto = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": second, "decision": "veto"},
    )
    assert veto.status_code == 201, veto.text
    second_veto = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": restaurants[2]["id"], "decision": "veto"},
    )
    assert second_veto.status_code == 409
    assert "Veto" in second_veto.json()["detail"]

    invalid = client.post(
        f"/api/sessions/{code}/swipes",
        json={"participant_id": host_id, "restaurant_id": restaurants[3]["id"], "decision": "maybe"},
    )
    assert invalid.status_code == 422


def test_veto_removes_the_favorite_from_the_winner(client):
    created = create_dinner(client)
    code = created["room_code"]
    people = [created["participant"]["id"]]
    for nickname in ("Sarah", "Omar"):
        joined = client.post(f"/api/sessions/{code}/join", json={"nickname": nickname})
        people.append(joined.json()["participant"]["id"])
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": people[0]}).status_code == 200
    restaurants = client.get(f"/api/sessions/{code}/restaurants").json()
    favorite = restaurants[0]["id"]
    backup = restaurants[1]["id"]

    for person in people:
        for restaurant in restaurants:
            if person == people[0] and restaurant["id"] == favorite:
                decision = "veto"
            elif restaurant["id"] in {favorite, backup}:
                decision = "like"
            else:
                decision = "pass"
            response = client.post(
                f"/api/sessions/{code}/swipes",
                json={"participant_id": person, "restaurant_id": restaurant["id"], "decision": decision},
            )
            assert response.status_code == 201, response.text

    body = client.get(f"/api/sessions/{code}/results").json()
    assert body["top_match"]["restaurant_id"] != favorite
    ranked = [body["top_match"], *body["alternatives"]]
    blocked = next(item for item in ranked if item["restaurant_id"] == favorite)
    assert blocked["eliminated"] is True
    assert "Sarah" not in blocked["explanation"]
    assert "veto" in blocked["explanation"]


def test_matching_order_does_not_depend_on_call_order():
    restaurants = [
        MatchRestaurant(id="z", name="Zed", rating=1),
        MatchRestaurant(id="m", name="Middle", rating=1),
    ]
    swipes = _votes("z", ["like"]) + _votes("m", ["like"])
    assert rank_restaurants(restaurants, swipes, 1)[0].restaurant_id == "m"
    assert rank_restaurants(list(reversed(restaurants)), swipes, 1)[0].restaurant_id == "m"
