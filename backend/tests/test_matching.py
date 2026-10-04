import pytest

from app.services.matching.matching_service import MatchRestaurant, MatchSwipe, rank_restaurants
from tests.helpers import create_dinner


def test_four_of_five_likes_is_80_percent():
    restaurant = MatchRestaurant(id="r1", name="Kinjo Sushi", rating=4.6)
    swipes = [
        MatchSwipe("p1", "r1", "like"),
        MatchSwipe("p2", "r1", "like"),
        MatchSwipe("p3", "r1", "like"),
        MatchSwipe("p4", "r1", "like"),
        MatchSwipe("p5", "r1", "pass"),
    ]
    ranked = rank_restaurants([restaurant], swipes, participant_count=5)
    assert ranked[0].likes == 4
    assert ranked[0].total_participants == 5
    assert ranked[0].compatibility == pytest.approx(0.8)
    assert ranked[0].compatibility_percent == 80
    assert ranked[0].explanation == "This restaurant was liked by most of your group."


def test_ranking_order_and_ties():
    restaurants = [
        MatchRestaurant(id="low", name="Low Match", rating=5.0),
        MatchRestaurant(id="same-lower-rating", name="Same Lower", rating=4.0),
        MatchRestaurant(id="same-higher-rating", name="Same Higher", rating=4.9),
    ]
    swipes = []
    for participant in ("p1", "p2", "p3", "p4"):
        swipes.append(MatchSwipe(participant, "same-lower-rating", "like"))
        swipes.append(MatchSwipe(participant, "same-higher-rating", "like"))
    swipes.append(MatchSwipe("p5", "same-lower-rating", "pass"))
    swipes.append(MatchSwipe("p5", "same-higher-rating", "pass"))
    swipes.append(MatchSwipe("p1", "low", "like"))
    swipes.append(MatchSwipe("p2", "low", "like"))

    ranked = rank_restaurants(restaurants, swipes, participant_count=5)
    assert [item.restaurant_id for item in ranked] == [
        "same-higher-rating",
        "same-lower-rating",
        "low",
    ]
    assert ranked[0].compatibility_percent == 80
    assert ranked[2].compatibility_percent == 40


def test_equal_scores_break_ties_by_name():
    restaurants = [
        MatchRestaurant(id="b", name="Bravo", rating=4.0),
        MatchRestaurant(id="a", name="Alpha", rating=4.0),
    ]
    swipes = [
        MatchSwipe("p1", "a", "like"),
        MatchSwipe("p1", "b", "like"),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=1)
    assert [item.name for item in ranked] == ["Alpha", "Bravo"]
    assert ranked[0].compatibility_percent == 100


def test_passes_do_not_count_as_likes():
    ranked = rank_restaurants(
        [MatchRestaurant(id="a", name="A", rating=4.2)],
        [MatchSwipe("p1", "a", "pass"), MatchSwipe("p2", "a", "like")],
        participant_count=2,
    )
    assert ranked[0].likes == 1
    assert ranked[0].compatibility_percent == 50


def test_zero_participants():
    ranked = rank_restaurants(
        [MatchRestaurant(id="a", name="A", rating=4.0)],
        [],
        participant_count=0,
    )
    assert ranked[0].compatibility == 0
    assert ranked[0].compatibility_percent == 0


def test_api_reports_80_percent_for_four_of_five(client):
    created = create_dinner(client)
    code = created["room_code"]
    people = [created["participant"]["id"]]
    for nickname in ("Sarah", "Omar", "Ahmed", "Lina"):
        joined = client.post(f"/api/sessions/{code}/join", json={"nickname": nickname})
        assert joined.status_code == 201, joined.text
        people.append(joined.json()["participant"]["id"])

    started = client.post(f"/api/sessions/{code}/start", json={"participant_id": people[0]})
    assert started.status_code == 200, started.text
    restaurants = client.get(f"/api/sessions/{code}/restaurants").json()
    focus = restaurants[0]["id"]

    for index, participant_id in enumerate(people):
        decision = "pass" if index == len(people) - 1 else "like"
        for restaurant in restaurants:
            choice = decision if restaurant["id"] == focus else "like"
            response = client.post(
                f"/api/sessions/{code}/swipes",
                json={
                    "participant_id": participant_id,
                    "restaurant_id": restaurant["id"],
                    "decision": choice,
                },
            )
            assert response.status_code == 201, response.text

    results = client.get(f"/api/sessions/{code}/results")
    assert results.status_code == 200, results.text
    body = results.json()
    ranked = [body["top_match"], *body["alternatives"]]
    match = next(item for item in ranked if item["restaurant_id"] == focus)
    assert match["likes"] == 4
    assert match["total_participants"] == 5
    assert match["compatibility_percent"] == 80
    assert body["top_match"]["compatibility_percent"] == 100
    assert "most of your group" in match["explanation"] or "strongest agreement" in match["explanation"]
