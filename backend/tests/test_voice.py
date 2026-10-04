import httpx
import pytest

from app.api.routes.voice import get_voice_service
from app.main import app
from app.services.voice.elevenlabs import ElevenLabsVoice, VoiceError


TRANSCRIPT = (
    "We're five students looking for cheap Japanese or Korean food around Burnaby. "
    "We want somewhere casual and cozy, within 3 kilometres."
)


def _audio_file(content: bytes = b"RIFF" + b"\x00" * 252, content_type: str = "audio/webm"):
    return {"audio": ("dinner.webm", content, content_type)}


@pytest.fixture(autouse=True)
def _clear_voice_override():
    yield
    app.dependency_overrides.pop(get_voice_service, None)


def test_transcribe_returns_the_elevenlabs_transcript(client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "test-key"
        assert "test-key" not in str(request.url)
        assert request.url.path == "/v1/speech-to-text"
        assert b"scribe_v2" in request.content
        return httpx.Response(200, json={"text": "cheap Korean food in Burnaby"})

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post("/api/voice/transcribe", files=_audio_file())
    assert response.status_code == 200, response.text
    assert response.json() == {"transcript": "cheap Korean food in Burnaby"}
    assert "test-key" not in response.text


def test_transcript_uses_the_existing_session_parser(client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": TRANSCRIPT})

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    spoken = client.post("/api/voice/transcribe", files=_audio_file())
    assert spoken.status_code == 200, spoken.text
    created = client.post(
        "/api/sessions",
        json={
            "description": spoken.json()["transcript"],
            "nickname": "Abdalla",
            "location": "Burnaby",
            "group_size": 5,
        },
    )
    assert created.status_code == 201, created.text
    intent = created.json()["intent"]
    assert intent["location"] == "Burnaby"
    assert intent["cuisines"] == ["Japanese", "Korean"]
    assert intent["price_level"] == 1
    assert intent["group_size"] == 5
    assert intent["vibe"] == "casual and cozy"
    assert intent["radius"] == 3000
    assert created.json()["restaurant_count"] >= 1


def test_elevenlabs_failure_is_a_controlled_error(client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "provider down secret-key"})

    _use_voice(ElevenLabsVoice("secret-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post("/api/voice/transcribe", files=_audio_file())
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "Voice is temporarily unavailable. You can type your dinner plans instead."
    assert "secret-key" not in response.text


def test_missing_elevenlabs_key_fails_without_leaking_configuration(client):
    response = client.post("/api/voice/transcribe", files=_audio_file())
    assert response.status_code == 503, response.text
    assert "api key" not in response.text.lower()
    assert "elevenlabs" not in response.json()["detail"].lower()


def test_invalid_audio_type_is_rejected(client):
    _use_voice(ElevenLabsVoice("test-key"))
    response = client.post(
        "/api/voice/transcribe",
        files={"audio": ("notes.txt", b"this is not audio at all", "text/plain")},
    )
    assert response.status_code == 400, response.text
    assert "not supported" in response.json()["detail"]


def test_empty_recording_is_rejected(client):
    _use_voice(ElevenLabsVoice("test-key"))
    response = client.post("/api/voice/transcribe", files=_audio_file(b"tiny"))
    assert response.status_code == 400, response.text
    assert "empty" in response.json()["detail"]


def test_oversized_audio_is_rejected(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.voice.MAX_AUDIO_BYTES", 32)
    _use_voice(ElevenLabsVoice("test-key"))
    response = client.post("/api/voice/transcribe", files=_audio_file(b"x" * 40))
    assert response.status_code == 400, response.text
    assert "too long" in response.json()["detail"]


def test_empty_transcript_does_not_create_a_session(client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"text": "   "})

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post("/api/voice/transcribe", files=_audio_file())
    assert response.status_code == 400, response.text
    assert "couldn't understand" in response.json()["detail"]


def test_speech_failure_does_not_block_a_typed_session(client):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "busy"})

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    spoken = client.post("/api/voice/speak", json={"text": "Got it. Let's find dinner."})
    assert spoken.status_code == 503, spoken.text
    created = client.post(
        "/api/sessions",
        json={
            "description": "Find Japanese food in Burnaby.",
            "nickname": "Abdalla",
            "location": "Burnaby",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["intent"]["cuisines"] == ["Japanese"]


def test_speak_returns_audio_for_the_winner_announcement(client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "test-key"
        assert "test-key" not in str(request.url)
        assert request.url.path == "/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"
        assert b"Maple Izakaya" in request.content
        return httpx.Response(200, content=b"ID3-fake-mp3")

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post(
        "/api/voice/speak",
        json={"text": "We have a winner. Your group is going to Maple Izakaya."},
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"ID3-fake-mp3"


def test_speak_without_a_key_is_unavailable(client):
    response = client.post("/api/voice/speak", json={"text": "We have a winner."})
    assert response.status_code == 503, response.text
    assert "api key" not in response.text.lower()


def test_speak_timeout_is_a_controlled_error(client):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    _use_voice(ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    response = client.post("/api/voice/speak", json={"text": "We have a winner."})
    assert response.status_code == 503, response.text
    assert response.json()["detail"] == "Voice is temporarily unavailable. You can type your dinner plans instead."


def test_speak_failure_redacts_the_key_from_logs(client, caplog):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"detail": "quota exceeded for secret-key"})

    _use_voice(ElevenLabsVoice("secret-key", client=httpx.Client(transport=httpx.MockTransport(handler))))
    with caplog.at_level("WARNING"):
        response = client.post("/api/voice/speak", json={"text": "We have a winner."})
    assert response.status_code == 503, response.text
    assert "secret-key" not in response.text
    assert "status=402" in caplog.text
    assert "secret-key" not in caplog.text


def test_service_omits_the_key_from_the_request_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["xi-api-key"] == "test-key"
        assert "test-key" not in str(request.url)
        return httpx.Response(200, json={"text": "hello"})

    service = ElevenLabsVoice("test-key", client=httpx.Client(transport=httpx.MockTransport(handler)))
    assert service.transcribe(b"a" * 120, "audio/webm", "dinner.webm") == "hello"


def test_service_raises_when_the_key_is_blank():
    service = ElevenLabsVoice("  ")
    with pytest.raises(VoiceError) as caught:
        service.transcribe(b"a" * 120, "audio/webm", "dinner.webm")
    assert caught.value.code == "unavailable"


def _use_voice(voice: ElevenLabsVoice) -> None:
    app.dependency_overrides[get_voice_service] = lambda: voice
