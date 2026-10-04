from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_session_service
from app.models import User
from app.schemas.history import HistoryDetail, HistoryListResponse
from app.services.history.history_service import HistoryService
from app.services.sessions.session_service import SessionService

router = APIRouter()


@router.get("", response_model=HistoryListResponse)
def list_history(
    user: User = Depends(get_current_user),
    sessions: SessionService = Depends(get_session_service),
) -> HistoryListResponse:
    return HistoryService(sessions).list_for(user)


@router.get("/{session_id}", response_model=HistoryDetail)
def history_detail(
    session_id: str,
    user: User = Depends(get_current_user),
    sessions: SessionService = Depends(get_session_service),
) -> HistoryDetail:
    return HistoryService(sessions).detail_for(user, session_id)
