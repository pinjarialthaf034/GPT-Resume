"""
CareerCompass AI — Resume API
Resume parsing, AI guidance feedback, secure deletion, and cross-application resume integration.
Authenticated via Supabase Auth JWT. User identity derived exclusively from auth.users.id.
"""
import logging
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from supabase import Client

from backend.ai.gemini_provider import GeminiProvider
from backend.config import get_settings, Settings
from backend.deps import AuthenticatedUser, get_current_user, get_service_supabase
from backend.limiter import limiter
from backend.models.common import APIResponse
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.profile_repo import ProfileRepository
from backend.services.resume_service import ResumeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume", tags=["Resume"])


def _get_service(
    db: Client = Depends(get_service_supabase),
    settings: Settings = Depends(get_settings),
) -> ResumeService:
    ai = GeminiProvider(settings)
    return ResumeService(
        profile_repo=ProfileRepository(db),
        analysis_repo=AnalysisRepository(db),
        ai_provider=ai,
        max_size_bytes=settings.max_resume_size_bytes,
    )


@router.post("/analyze", response_model=APIResponse)
@limiter.limit(f"{get_settings().ai_resume_analysis_rate_limit}/hour")
async def analyze_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ResumeService = Depends(_get_service),
):
    """
    Uploads a resume (PDF/DOCX), parses text, and provides AI career guidance for authenticated user.
    Safe-replace: new analysis is parsed and generated first before persisting.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    
    try:
        content = await file.read()
        result = await service.analyze_resume(
            current_user.id,
            content,
            file.filename,
        )
        return APIResponse(
            success=True,
            message="Resume analyzed successfully",
            data=result,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    finally:
        await file.close()


@router.get("/latest", response_model=APIResponse)
async def get_latest_resume_analysis(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ResumeService = Depends(_get_service),
):
    """Gets the most recent resume analysis for the authenticated user."""
    result = service.get_latest_resume_analysis(current_user.id)
    if not result:
        return APIResponse(success=True, data=None, message="No resume analysis found")
    return APIResponse(success=True, data=result)


@router.delete("", response_model=APIResponse)
async def delete_resume(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: ResumeService = Depends(_get_service),
):
    """
    Secure Resume Deletion:
    Deletes ONLY the authenticated user's resume analysis records.
    Does NOT delete user profile, assessment history, roadmap progress, or chat history.
    """
    success = service.delete_resume_analysis(current_user.id)
    return APIResponse(
        success=success,
        message="Resume analysis records deleted successfully" if success else "Failed to delete resume analysis",
    )


@router.get("/builder-resume", response_model=APIResponse)
async def get_builder_resume(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Client = Depends(get_service_supabase),
):
    """
    Cross-App Integration (Phase 7):
    Retrieves the authenticated user's resume draft(s) created in GPT-Resume builder.
    Derives identity exclusively from verified JWT (WHERE user_id = current_user.id).
    Never trusts client-supplied user or profile IDs.
    """
    try:
        result = (
            db.table("resumes")
            .select("id, user_id, template_id, resume_data, updated_at")
            .eq("user_id", current_user.id)
            .order("updated_at", desc=True)
            .execute()
        )
        resumes = result.data or []
        return APIResponse(
            success=True,
            data=resumes,
            message="Builder resume retrieved successfully" if resumes else "No builder resume found for this user",
        )
    except Exception as e:
        logger.warning(f"Could not fetch builder resume for user {current_user.id}: {e}")
        return APIResponse(success=True, data=[], message="No builder resume found")
