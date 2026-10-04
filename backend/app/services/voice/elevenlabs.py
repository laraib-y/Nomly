"""ElevenLabs speech-to-text and optional spoken replies.

The API key stays in this service. Callers receive VoiceError and never see
the key, the request URL, or the raw provider body.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_STT_MODEL = "scribe_v2"
DEFAULT_TTS_MODEL = "eleven_flash_v2_5"
DEFAULT_TTS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"


class VoiceError(Exception):
    """ElevenLabs could not produce a usable transcript or audio clip."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ElevenLabsVoice:
    def __init__(
        self,
        api_key: str,
        stt_model: str = DEFAULT_STT_MODEL,
        tts_model: str = DEFAULT_TTS_MODEL,
        voice_id: str = DEFAULT_TTS_VOICE_ID,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self.stt_model = stt_model or DEFAULT_STT_MODEL
        self.tts_model = tts_model or DEFAULT_TTS_MODEL
        self.voice_id = voice_id or DEFAULT_TTS_VOICE_ID
        self._client = client

    def transcribe(self, audio: bytes, content_type: str, filename: str) -> str:
        self._require_key()
        media_type = content_type.split(";", 1)[0].strip() or "application/octet-stream"
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            response = client.post(
                STT_URL,
                headers={"xi-api-key": self.api_key},
                data={"model_id": self.stt_model},
                files={"file": (filename, audio, media_type)},
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "ElevenLabs transcription failed status=%s model=%s response=%s",
                exc.response.status_code,
                self.stt_model,
                _safe_body(exc.response.text, self.api_key),
            )
            raise VoiceError("unavailable") from None
        except httpx.HTTPError as exc:
            logger.warning(
                "ElevenLabs transcription failed model=%s error_type=%s",
                self.stt_model,
                type(exc).__name__,
            )
            raise VoiceError("unavailable") from None
        finally:
            if owns_client:
                client.close()

        text = body.get("text") if isinstance(body, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise VoiceError("empty")
        return " ".join(text.split())

    def speak(self, text: str) -> bytes:
        self._require_key()
        cleaned = " ".join(text.split())
        if not cleaned:
            raise VoiceError("empty")
        url = TTS_URL.format(voice_id=self.voice_id)
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=30.0)
        try:
            response = client.post(
                url,
                headers={"xi-api-key": self.api_key, "Accept": "audio/mpeg"},
                json={"text": cleaned, "model_id": self.tts_model},
            )
            response.raise_for_status()
            audio = response.content
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "ElevenLabs speech failed status=%s model=%s response=%s",
                exc.response.status_code,
                self.tts_model,
                _safe_body(exc.response.text, self.api_key),
            )
            raise VoiceError("unavailable") from None
        except httpx.HTTPError as exc:
            logger.warning(
                "ElevenLabs speech failed model=%s error_type=%s",
                self.tts_model,
                type(exc).__name__,
            )
            raise VoiceError("unavailable") from None
        finally:
            if owns_client:
                client.close()
        if not audio:
            raise VoiceError("empty")
        return audio

    def _require_key(self) -> None:
        if not self.api_key.strip():
            logger.warning("ElevenLabs request skipped because the API key is not configured")
            raise VoiceError("unavailable")


def _safe_body(text: str, api_key: str) -> str:
    clipped = " ".join(text.split())[:300]
    if api_key:
        clipped = clipped.replace(api_key, "***")
    return clipped
