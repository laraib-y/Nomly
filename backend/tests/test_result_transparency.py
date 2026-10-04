"""Phase 6.2 / 6.2.1: one meaning for every number on the results screen.

satisfaction_percent (Group satisfaction) = (likes + super_likes) / participants
positives = likes + super_likes
The fairness ranking still uses the weighted values (Pass 0, Like 1, Super Like 2),
reported as fairness.least_satisfied_percent and fairness.average_satisfaction_percent.
"""

import pytest

from app.services.matching.constraints import MatchConstraints
from app.services.matching.matching_service import MatchRestaurant, MatchSwipe, rank_restaurants
from tests.helpers import create_dinner


def _votes(restaurant_id: str, decisions: list[str], offset: int = 0) -> list[MatchSwipe]:
    return [MatchSwipe(f"p{index + offset}", restaurant_id, decision) for index, decision in enumerate(decisions)]


@pytest.mark.parametrize(
    ("decisions", "positives", "likes", "super_likes", "passes", "percent", "weighted_average", "least"),
    [
        (["like", "like", "like"], 3, 3, 0, 0, 100, 50, 50),
        (["like", "like", "super_like"], 3, 2, 1, 0, 100, 67, 50),
        (["like", "like", "pass"], 2, 2, 0, 1, 67, 33, 0),
        (["like", "pass", "pass"], 1, 1, 0, 2, 33, 17, 0),
        (["super_like", "super_like", "super_like"], 3, 0, 3, 0, 100, 100, 100),
        (["super_like", "pass", "pass"], 1, 0, 1, 2, 33, 33, 0),
        (["pass", "pass", "pass"], 0, 0, 0, 3, 0, 0, 0),
    ],
)
def test_group_satisfaction_is_share_of_positive_participants(
    decisions, positives, likes, super_likes, passes, percent, weighted_average, least
):
    item = rank_restaurants([MatchRestaurant(id="a", name="A")], _votes("a", decisions), participant_count=3)[0]
    assert item.positives == positives == item.likes + item.super_likes
    assert item.likes == likes
    assert item.super_likes == super_likes
    assert item.passes == passes
    assert item.satisfaction_percent == percent == item.compatibility_percent
    assert f"{positives} of 3 were positive" in item.explanation
    # The weighted values the ranking sorts on are unchanged.
    assert item.group_satisfaction == pytest.approx((likes + 2 * super_likes) / 3)
    assert item.average_satisfaction_percent == weighted_average
    assert item.least_satisfied_percent == least


def test_missing_choice_counts_as_a_pass():
    item = rank_restaurants([MatchRestaurant(id="a", name="A")], _votes("a", ["like", "like"]), participant_count=3)[0]
    assert item.passes == 1
    assert item.satisfaction_percent == 67


def test_ranking_order_is_unchanged_by_the_display_metric():
    restaurants = [
        MatchRestaurant(id="loud", name="Loud Grill", rating=5.0),
        MatchRestaurant(id="calm", name="Calm Kitchen", rating=3.0),
        MatchRestaurant(id="mild", name="Mild Diner", rating=4.0),
    ]
    swipes = [
        *_votes("loud", ["super_like"] * 6 + ["pass"]),
        *_votes("calm", ["like"] * 6 + ["super_like"]),
        *_votes("mild", ["like"] * 7),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=7)
    assert [item.restaurant_id for item in ranked] == ["calm", "mild", "loud"]
    assert [item.group_satisfaction for item in ranked] == pytest.approx([8 / 7, 1.0, 12 / 7])
    assert [item.minimum_satisfaction for item in ranked] == [1, 1, 0]


def test_balanced_winner_shows_100_percent_over_86_percent_that_someone_passed_on():
    restaurants = [
        MatchRestaurant(id="loud", name="Loud Grill", rating=5.0),
        MatchRestaurant(id="calm", name="Calm Kitchen", rating=3.0),
    ]
    swipes = [
        *_votes("loud", ["super_like"] * 6 + ["pass"]),
        *_votes("calm", ["like"] * 6 + ["super_like"]),
    ]
    winner, other = rank_restaurants(restaurants, swipes, participant_count=7)
    assert winner.restaurant_id == "calm"
    assert winner.satisfaction_percent == 100
    assert other.satisfaction_percent == 86
    assert winner.highlight is None
    assert other.highlight is None
    assert "Calm Kitchen was the most balanced choice: everyone was positive about it." in winner.explanation
    assert "7 of 7 were positive (6 Likes, 1 Super Like, 0 Passes)" in winner.explanation
    # Weighted average (what the old percentage showed) still favors Loud Grill; balance decides.
    assert other.average_satisfaction_percent == 86 > winner.average_satisfaction_percent == 57


def test_higher_group_satisfaction_can_still_lose_to_stronger_support():
    restaurants = [
        MatchRestaurant(id="wide", name="Wide Bistro", rating=5.0),
        MatchRestaurant(id="keen", name="Keen Taqueria", rating=3.0),
    ]
    swipes = [
        *_votes("wide", ["like", "like", "like", "pass"]),
        *_votes("keen", ["super_like", "super_like", "pass", "pass"]),
    ]
    winner, other = rank_restaurants(restaurants, swipes, participant_count=4)
    assert winner.restaurant_id == "keen"
    assert (winner.satisfaction_percent, other.satisfaction_percent) == (50, 75)
    assert (winner.average_satisfaction_percent, other.average_satisfaction_percent) == (50, 38)
    assert winner.least_satisfied_percent == other.least_satisfied_percent == 0
    assert winner.highlight == "strongest_support"
    assert other.highlight == "higher_satisfaction"
    assert "Wide Bistro had higher group satisfaction (75% vs 50%)" in winner.explanation
    assert "Keen Taqueria had stronger overall support" in winner.explanation
    assert "2 Super Likes" in winner.explanation
    assert "nobody has to settle for" not in winner.explanation
    assert "everyone was positive" not in winner.explanation
    for index in range(4):
        assert f"p{index}" not in winner.explanation + other.explanation


def test_100_percent_loses_only_when_it_breaks_a_group_limit():
    restaurants = [
        MatchRestaurant(id="sky", name="Sky Tower", price=4, rating=5.0),
        MatchRestaurant(id="local", name="Local Noodle", price=1, rating=4.0),
        MatchRestaurant(id="corner", name="Corner Cafe", price=1, rating=4.0),
    ]
    swipes = [
        *_votes("sky", ["super_like"] * 3),
        *_votes("local", ["like", "like", "pass"]),
        *_votes("corner", ["like", "pass", "pass"]),
    ]
    ranked = rank_restaurants(restaurants, swipes, participant_count=3, constraints=MatchConstraints(price_level=2))
    winner = ranked[0]
    other = next(item for item in ranked if item.restaurant_id == "sky")
    assert winner.restaurant_id == "local"
    assert winner.satisfaction_percent == 67
    assert other.satisfaction_percent == 100
    assert other.eliminated is True
    assert other.elimination_reason == "budget"
    assert other.highlight is None
    assert "highest group satisfaction among eligible options" in winner.explanation
    assert "Sky Tower scored higher (100%) but was not eligible: it is above the group's budget" in winner.explanation


def test_vetoed_favorite_is_explained_without_saying_who():
    restaurants = [MatchRestaurant(id="fav", name="Favorite"), MatchRestaurant(id="ok", name="Okay")]
    swipes = [
        MatchSwipe("p0", "fav", "veto"),
        MatchSwipe("p1", "fav", "super_like"),
        MatchSwipe("p2", "fav", "super_like"),
        *_votes("ok", ["like", "like", "pass"]),
    ]
    winner, blocked = rank_restaurants(restaurants, swipes, participant_count=3)
    assert winner.restaurant_id == "ok"
    assert blocked.eliminated is True
    assert blocked.elimination_reason == "veto"
    assert blocked.passes == 0
    assert blocked.positives == 2
    assert blocked.satisfaction_percent == winner.satisfaction_percent == 67
    assert "veto" in blocked.explanation
    assert "p0" not in winner.explanation + blocked.explanation


def test_clear_winner_claims_highest_satisfaction():
    restaurants = [MatchRestaurant(id="a", name="Alpha"), MatchRestaurant(id="b", name="Bravo")]
    swipes = [*_votes("a", ["like", "like", "like", "pass"]), *_votes("b", ["like", "like", "pass", "pass"])]
    winner = rank_restaurants(restaurants, swipes, participant_count=4)[0]
    assert winner.restaurant_id == "a"
    assert winner.highlight is None
    assert winner.explanation.startswith("Alpha had the highest group satisfaction (75%).")


def test_tied_group_satisfaction_names_stronger_support():
    restaurants = [MatchRestaurant(id="a", name="Alpha"), MatchRestaurant(id="b", name="Bravo")]
    swipes = [*_votes("a", ["super_like", "like", "like"]), *_votes("b", ["like", "like", "like"])]
    winner, other = rank_restaurants(restaurants, swipes, participant_count=3)
    assert winner.restaurant_id == "a"
    assert winner.satisfaction_percent == other.satisfaction_percent == 100
    assert winner.explanation.startswith(
        "Alpha tied with Bravo on group satisfaction (100%) and had stronger overall support, with 1 Super Like."
    )
    assert "highest group satisfaction" not in winner.explanation


def test_exact_tie_says_a_fixed_tie_break_was_used():
    restaurants = [MatchRestaurant(id="b", name="Bravo"), MatchRestaurant(id="a", name="Alpha")]
    swipes = [*_votes("a", ["like", "like"]), *_votes("b", ["like", "like"])]
    first = rank_restaurants(restaurants, swipes, participant_count=2)
    second = rank_restaurants(list(reversed(restaurants)), swipes, participant_count=2)
    assert first[0].restaurant_id == second[0].restaurant_id == "a"
    assert first[0].explanation == second[0].explanation
    assert "fixed tie-break" in first[0].explanation


def test_api_results_are_consistent_aggregate_and_identical_for_everyone(client):
    created = create_dinner(client, nickname="Abdalla", group_size=3)
    code = created["room_code"]
    people = {"Abdalla": created["participant"]["id"]}
    for nickname in ("Sarah", "Omar"):
        people[nickname] = client.post(f"/api/sessions/{code}/join", json={"nickname": nickname}).json()["participant"]["id"]
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": people["Abdalla"]}).status_code == 200
    deck = client.get(f"/api/sessions/{code}/restaurants").json()
    favorite, steady = deck[0]["id"], deck[1]["id"]

    for nickname, participant_id in people.items():
        for restaurant in deck:
            if restaurant["id"] == favorite:
                decision = "super_like" if nickname == "Abdalla" else "like"
            elif restaurant["id"] == steady:
                decision = "like"
            else:
                decision = "pass"
            response = client.post(
                f"/api/sessions/{code}/swipes",
                json={"participant_id": participant_id, "restaurant_id": restaurant["id"], "decision": decision},
            )
            assert response.status_code == 201, response.text

    first = client.get(f"/api/sessions/{code}/results")
    second = client.get(f"/api/sessions/{code}/results")
    assert first.status_code == 200, first.text
    assert first.json() == second.json()
    body = first.json()
    ranked = [body["top_match"], *body["alternatives"]]

    assert body["top_match"]["restaurant_id"] == favorite
    top = body["top_match"]
    assert (top["positives"], top["likes"], top["super_likes"], top["passes"]) == (3, 2, 1, 0)
    assert top["satisfaction_percent"] == 100
    assert top["fairness"] == {"least_satisfied_percent": 50, "average_satisfaction_percent": 67}
    assert top["rank"] == 1

    for position, item in enumerate(ranked, start=1):
        total = item["total_participants"]
        assert item["rank"] == position
        assert item["positives"] == item["likes"] + item["super_likes"]
        assert item["likes"] + item["super_likes"] + item["passes"] + item["vetoes"] == total
        assert item["satisfaction_percent"] == (item["positives"] * 100 + total // 2) // total
        assert item["compatibility_percent"] == item["satisfaction_percent"]
        weighted = (item["likes"] + 2 * item["super_likes"]) / (2 * total) * 100
        assert item["fairness"]["average_satisfaction_percent"] == round(weighted)
        if not item["eliminated"]:
            assert f"{item['positives']} of {total} were positive" in item["explanation"]

    text = first.text
    for nickname, participant_id in people.items():
        assert nickname not in text
        assert participant_id not in text
