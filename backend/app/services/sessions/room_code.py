import secrets

ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 6


def generate_room_code(length: int = ROOM_CODE_LENGTH) -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(length))
