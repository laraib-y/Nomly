from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.time import utcnow
from app.models import AuthSession, Session, User
from tests.helpers import DINNER

PASSWORD = "correct horse battery"
ALICE = {"email": "Alice@Example.com", "password": PASSWORD, "display_name": "Alice"}
BOB = {"email": "bob@example.com", "password": "another strong pass", "display_name": "Bob"}
EVIL = "https://evil.example"


@pytest.fixture
def other_client(client: TestClient) -> TestClient:
    """A second browser with its own cookie jar, talking to the same app and database."""
    return TestClient(client.app)


def register(client: TestClient, account: dict = ALICE) -> dict:
    response = client.post("/api/auth/register", json=account)
    assert response.status_code == 201, response.text
    return response.json()


def db():
    assert database.SessionLocal is not None
    return database.SessionLocal()


def finish_dinner(client: TestClient, host_likes_first: bool = True, guest_likes_first: bool = True, **overrides):
    """Host plus one guest swipe every card. Returns the created dinner body."""
    created = client.post("/api/sessions", json={**DINNER, "nickname": "Hostie", **overrides})
    assert created.status_code == 201, created.text
    body = created.json()
    code = body["room_code"]
    host = body["participant"]["id"]
    guest = client.post(f"/api/sessions/{code}/join", json={"nickname": "Sarah"}).json()["participant"]["id"]
    assert client.post(f"/api/sessions/{code}/start", json={"participant_id": host}).status_code == 200
    restaurants = client.get(f"/api/sessions/{code}/restaurants").json()
    for participant, likes_first in ((host, host_likes_first), (guest, guest_likes_first)):
        for index, restaurant in enumerate(restaurants):
            decision = "like" if index == 0 and likes_first else "pass"
            response = client.post(
                f"/api/sessions/{code}/swipes",
                json={"participant_id": participant, "restaurant_id": restaurant["id"], "decision": decision},
            )
            assert response.status_code == 201, response.text
    return body


# Registration


def test_register_returns_user_and_sets_secure_cookie(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=ALICE)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "display_name", "created_at"}
    assert body["email"] == "alice@example.com"
    assert body["display_name"] == "Alice"
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("nomly_session=")
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()
    assert "Max-Age=2592000" in cookie
    token = cookie.split(";")[0].split("=", 1)[1]
    assert token not in response.text
    assert PASSWORD not in response.text
    assert "password" not in response.text


def test_password_is_stored_as_argon2id_hash_and_token_is_hashed(client: TestClient) -> None:
    response = client.post("/api/auth/register", json=ALICE)
    token = response.cookies["nomly_session"]
    with db() as session:
        user = session.query(User).one()
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
        stored = session.query(AuthSession).one()
        assert stored.token_hash != token
        assert len(stored.token_hash) == 64


def test_duplicate_email_is_rejected_case_insensitively(client: TestClient, other_client: TestClient) -> None:
    register(client)
    response = other_client.post("/api/auth/register", json={**ALICE, "email": " alice@EXAMPLE.com "})
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with that email already exists"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"password": "short"}, "at least 8 characters"),
        ({"password": "        "}, "only spaces"),
        ({"password": "x" * 129}, "at most 128"),
        ({"email": "not-an-email"}, "valid email"),
        ({"display_name": "   "}, "what to call you"),
    ],
)
def test_invalid_registration_is_rejected(client: TestClient, overrides: dict, message: str) -> None:
    response = client.post("/api/auth/register", json={**ALICE, **overrides})
    assert response.status_code == 400
    assert message in response.json()["detail"]
    assert "nomly_session" not in response.headers.get("set-cookie", "")
    with db() as session:
        assert session.query(User).count() == 0


# Login, /me, logout


def test_login_success_restores_session(client: TestClient, other_client: TestClient) -> None:
    register(client)
    response = other_client.post("/api/auth/login", json={"email": "ALICE@example.com", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert "HttpOnly" in response.headers["set-cookie"]
    me = other_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["display_name"] == "Alice"


def test_login_failure_is_generic(client: TestClient, other_client: TestClient) -> None:
    register(client)
    wrong = other_client.post("/api/auth/login", json={"email": ALICE["email"], "password": "wrong password"})
    unknown = other_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"] == "Email or password is incorrect"
    assert "set-cookie" not in wrong.headers
    assert other_client.get("/api/auth/me").status_code == 401


def test_me_requires_a_session(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("nomly_session", "made-up-token")
    assert client.get("/api/auth/me").status_code == 401


def test_logout_revokes_the_token_on_the_server(client: TestClient) -> None:
    register(client)
    token = client.cookies["nomly_session"]
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    assert 'nomly_session=""' in response.headers["set-cookie"] or "Max-Age=0" in response.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("nomly_session", token)
    assert client.get("/api/auth/me").status_code == 401
    with db() as session:
        assert session.query(AuthSession).count() == 0


def test_expired_session_is_rejected(client: TestClient) -> None:
    register(client)
    with db() as session:
        row = session.query(AuthSession).one()
        row.expires_at = utcnow() - timedelta(seconds=1)
        session.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_login_is_rate_limited(client: TestClient) -> None:
    register(client)
    statuses = [
        client.post("/api/auth/login", json={"email": ALICE["email"], "password": "nope nope"}).status_code
        for _ in range(11)
    ]
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_register_is_rate_limited(client: TestClient) -> None:
    statuses = [
        client.post("/api/auth/register", json={**ALICE, "email": f"user{index}@example.com"}).status_code
        for index in range(6)
    ]
    assert statuses[:5] == [201] * 5
    assert statuses[5] == 429


def test_cross_site_writes_are_rejected(client: TestClient) -> None:
    blocked = client.post("/api/auth/register", json=ALICE, headers={"Origin": EVIL})
    assert blocked.status_code == 403
    allowed = client.post("/api/auth/register", json=ALICE, headers={"Origin": "http://localhost:3000"})
    assert allowed.status_code == 201
    forged = client.post("/api/sessions", json=DINNER, headers={"Origin": EVIL})
    assert forged.status_code == 403
    assert client.post("/api/auth/logout", headers={"Origin": EVIL}).status_code == 403
    assert client.get("/api/auth/me").status_code == 200


# Dinner ownership


def test_authenticated_dinner_is_owned_and_guest_dinner_is_not(client: TestClient, other_client: TestClient) -> None:
    user = register(client)
    mine = client.post("/api/sessions", json=DINNER)
    guest = other_client.post("/api/sessions", json=DINNER)
    assert mine.status_code == guest.status_code == 201
    assert "user_id" not in mine.json()
    with db() as session:
        assert session.get(Session, mine.json()["id"]).user_id == user["id"]
        assert session.get(Session, guest.json()["id"]).user_id is None


def test_guest_multiplayer_still_works_without_accounts(client: TestClient) -> None:
    body = finish_dinner(client)
    results = client.get(f"/api/sessions/{body['room_code']}/results")
    assert results.status_code == 200
    assert results.json()["top_match"]["satisfaction_percent"] == 100


def test_signed_in_guest_joining_does_not_take_ownership(client: TestClient, other_client: TestClient) -> None:
    register(client)
    created = client.post("/api/sessions", json=DINNER).json()
    register(other_client, BOB)
    joined = other_client.post(f"/api/sessions/{created['room_code']}/join", json={"nickname": "Bobby"})
    assert joined.status_code == 201
    with db() as session:
        owner = session.get(Session, created["id"]).user_id
    assert owner == client.get("/api/auth/me").json()["id"]


# History


def test_history_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/history").status_code == 401
    assert client.get("/api/history/00000000-0000-0000-0000-000000000000").status_code == 401


def test_empty_history(client: TestClient) -> None:
    register(client)
    response = client.get("/api/history")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "stats": {"dinners": 0, "strong_matches": 0, "average_satisfaction_percent": None, "average_group_size": None},
        "cuisines": [],
    }


def test_unfinished_dinners_are_not_history(client: TestClient) -> None:
    register(client)
    lobby = client.post("/api/sessions", json=DINNER).json()
    assert client.get("/api/history").json()["items"] == []
    assert client.get(f"/api/history/{lobby['id']}").status_code == 404


def test_history_lists_finished_dinners_newest_first_with_accurate_stats(client: TestClient) -> None:
    register(client)
    first = finish_dinner(client)
    second = finish_dinner(client, guest_likes_first=False, location="Vancouver", group_size=3)
    with db() as session:
        session.get(Session, first["id"]).created_at = utcnow() - timedelta(days=3)
        session.commit()

    response = client.get("/api/history")
    assert response.status_code == 200
    body = response.json()
    assert [item["session_id"] for item in body["items"]] == [second["id"], first["id"]]

    newest, oldest = body["items"]
    assert oldest["satisfaction_percent"] == 100
    assert oldest["positives"] == 2
    assert oldest["location"] == "Burnaby"
    assert oldest["group_size"] == 5
    assert newest["satisfaction_percent"] == 50
    assert newest["location"] == "Vancouver"
    assert newest["group_size"] == 3
    for item in body["items"]:
        assert item["participant_count"] == 2
        assert item["restaurant_count"] >= 1
        assert item["description"] == DINNER["description"]
        assert item["winner"]["name"]
        assert item["winner"]["restaurant_id"]

    assert body["stats"] == {
        "dinners": 2,
        "strong_matches": 1,
        "average_satisfaction_percent": 75,
        "average_group_size": 2.0,
    }
    assert sum(entry["count"] for entry in body["cuisines"]) <= 2
    for entry in body["cuisines"]:
        assert entry["label"] and entry["label"].lower() != "restaurant"


def test_history_detail_matches_live_results(client: TestClient) -> None:
    register(client)
    body = finish_dinner(client)
    live = client.get(f"/api/sessions/{body['room_code']}/results").json()
    response = client.get(f"/api/history/{body['id']}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["session_id"] == body["id"]
    assert detail["results"] == live
    assert detail["winner"]["name"] == live["top_match"]["name"]
    assert detail["satisfaction_percent"] == live["top_match"]["satisfaction_percent"] == 100
    assert detail["participant_count"] == 2


def test_history_never_reveals_participants(client: TestClient) -> None:
    register(client)
    body = finish_dinner(client)
    listing = client.get("/api/history").text
    detail = client.get(f"/api/history/{body['id']}").text
    for text in (listing, detail):
        assert "Hostie" not in text
        assert "Sarah" not in text
        assert body["participant"]["id"] not in text
        assert "nickname" not in text
        assert "password" not in text


def test_user_a_cannot_access_user_b_history(client: TestClient, other_client: TestClient) -> None:
    register(client, ALICE)
    alice_dinner = finish_dinner(client)
    register(other_client, BOB)
    bob_dinner = finish_dinner(other_client)

    alice_list = client.get("/api/history").json()["items"]
    bob_list = other_client.get("/api/history").json()["items"]
    assert [item["session_id"] for item in alice_list] == [alice_dinner["id"]]
    assert [item["session_id"] for item in bob_list] == [bob_dinner["id"]]

    stolen = other_client.get(f"/api/history/{alice_dinner['id']}")
    missing = other_client.get("/api/history/00000000-0000-0000-0000-000000000000")
    assert stolen.status_code == missing.status_code == 404
    assert stolen.json() == missing.json() == {"detail": "Dinner not found"}
    assert client.get(f"/api/history/{bob_dinner['id']}").status_code == 404
    assert client.get(f"/api/history/{alice_dinner['id']}").status_code == 200


def test_guest_dinners_are_nobodys_history(client: TestClient, other_client: TestClient) -> None:
    guest_dinner = finish_dinner(other_client)
    register(client)
    assert client.get("/api/history").json()["items"] == []
    assert client.get(f"/api/history/{guest_dinner['id']}").status_code == 404


def test_history_survives_logout_and_login(client: TestClient) -> None:
    register(client)
    body = finish_dinner(client)
    client.post("/api/auth/logout")
    assert client.get("/api/history").status_code == 401
    client.post("/api/auth/login", json={"email": ALICE["email"], "password": PASSWORD})
    assert [item["session_id"] for item in client.get("/api/history").json()["items"]] == [body["id"]]
