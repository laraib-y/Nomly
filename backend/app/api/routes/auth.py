from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import auth_token, get_auth_service, get_current_user
from app.core.config import get_settings
from app.core.exceptions import TooManyRequestsError
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth.auth_service import AuthService, user_read
from app.services.auth.rate_limit import login_limiter, register_limiter

router = APIRouter()

TOO_MANY = "Too many attempts. Wait a few minutes and try again."


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> UserRead:
    if not register_limiter.hit(f"ip:{_client_ip(request)}"):
        raise TooManyRequestsError(TOO_MANY)
    signed_in = auth.register(payload)
    _set_cookie(response, signed_in.token)
    return user_read(signed_in.user)


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth: AuthService = Depends(get_auth_service),
) -> UserRead:
    email = payload.email.strip().lower()
    if not login_limiter.hit(f"ip:{_client_ip(request)}|{email}"):
        raise TooManyRequestsError(TOO_MANY)
    signed_in = auth.login(payload)
    _set_cookie(response, signed_in.token)
    return user_read(signed_in.user)


@router.post("/logout", status_code=204)
def logout(request: Request, auth: AuthService = Depends(get_auth_service)) -> Response:
    auth.logout(auth_token(request))
    settings = get_settings()
    response = Response(status_code=204)
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        httponly=True,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        secure=settings.cookie_secure,
    )
    return response


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return user_read(user)


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.auth_cookie_name,
        token,
        max_age=settings.auth_session_days * 24 * 60 * 60,
        path="/",
        httponly=True,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
        secure=settings.cookie_secure,
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
