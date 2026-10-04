import logging

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.core.config import get_settings
from app.core.exceptions import AppError, BadRequestError
from app.schemas.voice import SpeakRequest, TranscriptRead
from app.services.voice.elevenlabs import ElevenLabsVoice, VoiceError

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_AUDIO_BYTES = 8 * 1024 * 1024
MIN_AUDIO_BYTES = 100

_ALLOWED_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/ogg",
    "audio/flac",
    "video/webm",
}

_EXTENSIONS = {
    "audio/webm": "webm",
    "video/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
}


def get_voice_service() -> ElevenLabsVoice:
    settings = get_settings()
    return ElevenLabsVoice(
        api_key=settings.elevenlabs_api_key,
        stt_model=settings.elevenlabs_stt_model,
        tts_model=settings.elevenlabs_tts_model,
        voice_id=settings.elevenlabs_tts_voice_id,
    )


@router.post("/transcribe", response_model=TranscriptRead)
async def transcribe_audio(
    audio: UploadFile = File(...),
    voice: ElevenLabsVoice = Depends(get_voice_service),
) -> TranscriptRead:
    media_type = _media_type(audio.content_type)
    if media_type not in _ALLOWED_TYPES:
        raise BadRequestError("That recording format is not supported. Try again or type your dinner plans instead.")
    payload = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(payload) > MAX_AUDIO_BYTES:
        raise BadRequestError("That recording is too long. Try a shorter one or type your dinner plans instead.")
    if len(payload) < MIN_AUDIO_BYTES:
        raise BadRequestError("That recording was empty. Try again or type your dinner plans instead.")
    filename = f"dinner.{_EXTENSIONS[media_type]}"
    try:
        transcript = voice.transcribe(payload, media_type, filename)
    except VoiceError as exc:
        _raise_voice_error(exc)
    return TranscriptRead(transcript=transcript)


@router.post("/speak")
def speak_text(
    payload: SpeakRequest,
    voice: ElevenLabsVoice = Depends(get_voice_service),
) -> Response:
    try:
        audio = voice.speak(payload.text)
    except VoiceError as exc:
        _raise_voice_error(exc)
    return Response(content=audio, media_type="audio/mpeg")


def _media_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _raise_voice_error(exc: VoiceError) -> None:
    if exc.code == "empty":
        raise BadRequestError("We couldn't understand that recording. Try again or type your dinner plans instead.")
    raise AppError(503, "Voice is temporarily unavailable. You can type your dinner plans instead.")
