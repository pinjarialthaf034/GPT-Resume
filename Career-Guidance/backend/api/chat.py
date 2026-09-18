"""
CareerCompass AI — Chat API
Real Gemini-powered career chatbot with session persistence protected by Supabase Auth JWT.
User identity derived exclusively from auth.users.id.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import Client

from backend.ai.gemini_provider import GeminiProvider
from backend.config import get_settings, Settings
from backend.deps import AuthenticatedUser, get_current_user, get_service_supabase
from backend.limiter import limiter
from backend.models.career import ChatMessageCreate
from backend.models.common import APIResponse
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.chat_repo import ChatRepository
from backend.repositories.profile_repo import ProfileRepository
from backend.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


def _get_service(
    db: Client = Depends(get_service_supabase),
    settings: Settings = Depends(get_settings),
) -> ChatService:
    ai = GeminiProvider(settings)
    return ChatService(
        profile_repo=ProfileRepository(db),
        analysis_repo=AnalysisRepository(db),
        chat_repo=ChatRepository(db),
        ai_provider=ai,
        max_context_tokens=settings.chat_max_context_tokens,
    )


@router.post("/send", response_model=APIResponse)
@limiter.limit(f"{get_settings().ai_chat_rate_limit}/hour")
async def send_message(
    request: Request,
    body: ChatMessageCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    """Sends a message to the AI career counselor and returns the response for the authenticated user."""
    try:
        result = await service.send_message(
            current_user.id,
            body.message,
            body.session_id,
        )
        return APIResponse(success=True, data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/history/{session_id}", response_model=APIResponse)
async def get_history(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    """Returns conversation history for a session belonging to the authenticated user."""
    messages = service.get_history(current_user.id, session_id)
    return APIResponse(success=True, data={"session_id": session_id, "messages": messages})


@router.get("/sessions", response_model=APIResponse)
async def list_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    """Lists all chat sessions belonging to the authenticated user."""
    sessions = service.list_sessions(current_user.id)
    return APIResponse(success=True, data=sessions)
