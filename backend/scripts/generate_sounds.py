"""Generate Nomly's UI sound effects with the ElevenLabs Sound Effects API.

Development only. The app plays the saved files from frontend/public/audio and
never calls this at request time.

    cd backend
    .\\.venv\\Scripts\\python.exe scripts\\generate_sounds.py          # only missing files
    .\\.venv\\Scripts\\python.exe scripts\\generate_sounds.py --force  # regenerate everything
    .\\.venv\\Scripts\\python.exe scripts\\generate_sounds.py winner   # one sound
"""

import argparse
import sys
from pathlib import Path

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402

SOUND_URL = "https://api.elevenlabs.io/v1/sound-generation"
OUTPUT_DIR = BACKEND_DIR.parent / "frontend" / "public" / "audio"

SOUNDS: dict[str, tuple[str, float, str]] = {
    "like": (
        "swipes/like.mp3",
        0.8,
        "Short satisfying futuristic UI confirmation sound, soft tactile click followed by a warm ascending "
        "two-note chime, clean modern social app interface, subtle and pleasant, approximately 0.8 seconds.",
    ),
    "pass": (
        "swipes/pass.mp3",
        0.6,
        "Short subtle futuristic UI dismissal sound, gentle downward tone with a soft airy whoosh, clean modern "
        "interface, neutral and unobtrusive, approximately 0.6 seconds.",
    ),
    "superlike": (
        "swipes/superlike.mp3",
        1.0,
        "Short premium futuristic UI reward sound, bright crystalline sparkle followed by an energetic ascending "
        "chime, exciting but elegant, polished modern app interface, approximately 1 second.",
    ),
    "veto": (
        "swipes/veto.mp3",
        0.8,
        "Short decisive futuristic UI rejection sound, soft low impact followed by a brief digital pulse, dramatic "
        "but clean and sophisticated, approximately 0.8 seconds.",
    ),
    "join": (
        "multiplayer/join.mp3",
        0.7,
        "Short friendly multiplayer notification sound, soft digital pop followed by a warm subtle chime, modern "
        "social application, welcoming and polished, approximately 0.7 seconds.",
    ),
    "participant-finished": (
        "multiplayer/participant-finished.mp3",
        0.8,
        "Short multiplayer progress confirmation sound, subtle ascending digital tones suggesting completion, "
        "clean futuristic interface, approximately 0.8 seconds.",
    ),
    "matching": (
        "matching/matching.mp3",
        1.5,
        "Short futuristic anticipation sound, several subtle rhythmic digital pulses building into a smooth "
        "ascending tone, premium modern application, exciting but restrained, approximately 1.5 seconds.",
    ),
    "winner": (
        "matching/winner.mp3",
        2.0,
        "Premium celebratory futuristic UI reveal sound, warm crystalline chime, subtle bass impact, elegant "
        "ascending notes, satisfying restaurant recommendation reveal, sophisticated and exciting, "
        "approximately 2 seconds.",
    ),
}


def generate(client: httpx.Client, api_key: str, prompt: str, duration: float) -> bytes:
    response = client.post(
        SOUND_URL,
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": api_key},
        json={
            "text": prompt,
            "duration_seconds": duration,
            "prompt_influence": 0.6,
            "model_id": "eleven_text_to_sound_v2",
        },
    )
    if response.status_code != 200:
        detail = " ".join(response.text.split())[:300].replace(api_key, "***")
        if response.status_code in (401, 403):
            raise PermissionError(f"status={response.status_code} response={detail}")
        raise RuntimeError(f"status={response.status_code} response={detail}")
    if not response.content:
        raise RuntimeError("empty audio")
    return response.content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help=f"Sounds to generate. Default: all. One of {', '.join(SOUNDS)}.")
    parser.add_argument("--force", action="store_true", help="Overwrite files that already exist.")
    args = parser.parse_args()
    unknown = [name for name in args.names if name not in SOUNDS]
    if unknown:
        parser.error(f"unknown sound: {', '.join(unknown)}")

    api_key = get_settings().elevenlabs_api_key.strip()
    if not api_key:
        print("ELEVENLABS_API_KEY is not set in backend/.env.", file=sys.stderr)
        return 1

    failed = 0
    with httpx.Client(timeout=60.0) as client:
        for name in args.names or list(SOUNDS):
            path, duration, prompt = SOUNDS[name]
            target = OUTPUT_DIR / path
            if target.exists() and not args.force:
                print(f"skip     {path} (exists)")
                continue
            try:
                audio = generate(client, api_key, prompt, duration)
            except PermissionError as exc:
                print(f"failed   {path}: {exc}", file=sys.stderr)
                print("The key needs the Sound Effects permission in the ElevenLabs dashboard.", file=sys.stderr)
                return 1
            except (httpx.HTTPError, RuntimeError) as exc:
                failed += 1
                print(f"failed   {path}: {exc if isinstance(exc, RuntimeError) else type(exc).__name__}", file=sys.stderr)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(audio)
            print(f"wrote    {path} ({len(audio) // 1024} KB)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
