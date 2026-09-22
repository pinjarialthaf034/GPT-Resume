"""
CareerCompass AI — Analysis API
Career analysis, roadmap, and progress tracking protected by Supabase Auth JWT.
Strict user isolation — only authenticated user's data is accessed or generated.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, status
from supabase import Client

from backend.ai.errors import GeminiConfigError
from backend.ai.gemini_provider import GeminiProvider
from backend.config import get_settings, Settings
from backend.deps import AuthenticatedUser, get_current_user, get_gemini_provider, get_service_supabase
from backend.limiter import limiter
from backend.models.career import AnalysisTrigger, CareerSelectionRequest, RoadmapProgressUpdate
from backend.models.common import APIResponse
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.career_repo import CareerRepository
from backend.repositories.profile_repo import ProfileRepository
from backend.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


def _get_service(
    db: Client = Depends(get_service_supabase),
    settings: Settings = Depends(get_settings),
    ai: GeminiProvider = Depends(get_gemini_provider),
) -> AnalysisService:
    return AnalysisService(
        profile_repo=ProfileRepository(db),
        career_repo=CareerRepository(db),
        analysis_repo=AnalysisRepository(db),
        ai_provider=ai,
    )


@router.post("/career", response_model=APIResponse)
@limiter.limit(f"{get_settings().ai_career_analysis_rate_limit}/hour")
async def run_career_analysis(
    request: Request,
    body: AnalysisTrigger = AnalysisTrigger(),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: AnalysisService = Depends(_get_service),
):
    """
    Triggers career analysis for the verified authenticated user.
    - Returns cached result if valid cache exists for this user (no Gemini call)
    - Calls Gemini ONCE if no valid cache
    - force_regenerate=True bypasses cache
    """
    try:
        result = await service.get_or_create_analysis(
            current_user.id,
            force_regenerate=body.force_regenerate,
        )
        return APIResponse(
            success=True,
            message="Cached analysis" if result.get("is_cached") else "New analysis generated",
            data=result,
        )
    except GeminiConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini configuration error: {str(e)}",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        err_str = str(e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI analysis temporarily unavailable. Please try again. ({err_str[:100]})",
        )


@router.get("/gemini/status", response_model=APIResponse)
async def get_gemini_status(
    settings: Settings = Depends(get_settings),
):
    """
    Returns safe, non-sensitive Gemini configuration status.
    Never exposes API keys or secrets.
    """
    diagnostics = settings.get_gemini_diagnostics()
    return APIResponse(
        success=True,
        message="Gemini configuration status",
        data=diagnostics,
    )


@router.get("/career", response_model=APIResponse)
async def get_latest_analysis(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: AnalysisService = Depends(_get_service),
):
    """Returns the most recent analysis for the authenticated user without triggering a new one."""
    result = await asyncio.to_thread(service.get_latest_analysis, current_user.id)
    if not result:
        return APIResponse(
            success=True,
            data=None,
            message="No analysis found. Run career analysis first.",
        )
    return APIResponse(success=True, data=result)


@router.get("/roadmap", response_model=APIResponse)
async def get_roadmap_progress(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: AnalysisService = Depends(_get_service),
):
    """Returns roadmap with progress for the authenticated user — persisted, not regenerated."""
    result = await asyncio.to_thread(service.get_roadmap_progress, current_user.id)
    return APIResponse(success=True, data=result)


@router.post("/roadmap/progress", response_model=APIResponse)
async def update_roadmap_progress(
    body: RoadmapProgressUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: AnalysisService = Depends(_get_service),
):
    """Marks a roadmap step as complete or incomplete for the authenticated user."""
    try:
        latest = await asyncio.to_thread(service.get_latest_analysis, current_user.id)
        if not latest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No analysis found. Run career analysis first.",
            )
        
        result = await asyncio.to_thread(
            service.update_roadmap_progress,
            latest["id"],
            current_user.id,
            body.step_number,
            body.completed,
        )
        return APIResponse(success=True, data=result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/select-career", response_model=APIResponse)
async def select_career(
    body: CareerSelectionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: AnalysisService = Depends(_get_service),
):
    """
    Selects one career from the Top 3 matches and generates a role-specific roadmap for authenticated user.
    Validates that career_title is strictly among the latest Top 3 matches.
    """
    try:
        result = await service.select_career_and_generate_roadmap(
            profile_id=current_user.id,
            career_title=body.career_title,
        )
        return APIResponse(
            success=True,
            message=f"Roadmap generated for selected career: {body.career_title}",
            data=result,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except GeminiConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini configuration error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate roadmap for selected career: {str(e)}",
        )
