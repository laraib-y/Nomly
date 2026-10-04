from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.services.ai.factory import get_ai_service
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
