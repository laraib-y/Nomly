from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.models import User
from app.services.ai.factory import get_ai_service
from app.services.auth.auth_service import AuthService
from app.services.matching.matching_service import MatchingService
from app.services.restaurants.factory import get_restaurant_provider
from app.services.sessions.session_service import SessionService


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    settings = get_settings()
    return SessionService(
        db=db,
        ai=get_ai_service(settings),
        restaurants=get_restaurant_provider(settings),
        matching=MatchingService(),
    )


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db=db, session_days=get_settings().auth_session_days)


def auth_token(request: Request) -> str | None:
    return request.cookies.get(get_settings().auth_cookie_name)


def get_optional_user(request: Request, auth: AuthService = Depends(get_auth_service)) -> User | None:
    return auth.user_for_token(auth_token(request))


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise UnauthorizedError()
    return user
