import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.core.time import utcnow
from app.models import AuthSession, User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth.passwords import hash_password, needs_rehash, verify_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
MAX_PASSWORD = 128
LOGIN_FAILED = "Email or password is incorrect"


@dataclass
class SignedIn:
    user: User
    token: str


class AuthService:
    """Accounts and signed-in browsers. Tokens are random; only their hash is stored."""

    def __init__(self, db: DbSession, session_days: int = 30) -> None:
        self.db = db
        self.session_days = session_days

    def register(self, payload: RegisterRequest) -> SignedIn:
        email = clean_email(payload.email)
        display_name = clean_display_name(payload.display_name)
        check_password(payload.password)
        if self.db.query(User.id).filter(User.email == email).first() is not None:
            raise ConflictError("An account with that email already exists")
        user = User(email=email, password_hash=hash_password(payload.password), display_name=display_name)
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise ConflictError("An account with that email already exists") from None
        token = self._open_session(user)
        self.db.commit()
        self.db.refresh(user)
        return SignedIn(user=user, token=token)

    def login(self, payload: LoginRequest) -> SignedIn:
        email = payload.email.strip().lower()
        user = self.db.query(User).filter(User.email == email).one_or_none()
        if not verify_password(user.password_hash if user else None, payload.password) or user is None:
            raise UnauthorizedError(LOGIN_FAILED, code="invalid_credentials")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)
        self.db.query(AuthSession).filter(
            AuthSession.user_id == user.id,
            AuthSession.expires_at <= utcnow(),
        ).delete(synchronize_session=False)
        token = self._open_session(user)
        self.db.commit()
        self.db.refresh(user)
        return SignedIn(user=user, token=token)

    def logout(self, token: str | None) -> None:
        if not token:
            return
        self.db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).delete(
            synchronize_session=False
        )
        self.db.commit()

    def user_for_token(self, token: str | None) -> User | None:
        if not token or len(token) > 128:
            return None
        row = self.db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).one_or_none()
        if row is None:
            return None
        if row.expires_at <= utcnow():
            self.db.delete(row)
            self.db.commit()
            return None
        return row.user

    def _open_session(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        self.db.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_token(token),
                expires_at=utcnow() + timedelta(days=self.session_days),
            )
        )
        return token


def user_read(user: User) -> UserRead:
    return UserRead(id=user.id, email=user.email, display_name=user.display_name, created_at=user.created_at)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise BadRequestError("Enter a valid email address")
    return email


def clean_display_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise BadRequestError("Tell us what to call you")
    if len(name) > 40:
        raise BadRequestError("Keep your name to 40 characters or fewer")
    return name


def check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise BadRequestError(f"Use a password with at least {MIN_PASSWORD} characters")
    if len(password) > MAX_PASSWORD:
        raise BadRequestError(f"Use a password with at most {MAX_PASSWORD} characters")
    if not password.strip():
        raise BadRequestError("Your password can't be only spaces")
