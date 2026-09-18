"""
CareerCompass AI — Career Explorer API
Browse, search, and view career details. Public read access.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from backend.deps import get_service_supabase
from backend.models.common import APIResponse
from backend.repositories.career_repo import CareerRepository

router = APIRouter(prefix="/careers", tags=["Careers"])


def _get_repo(db: Client = Depends(get_service_supabase)) -> CareerRepository:
    return CareerRepository(db)


@router.get("", response_model=APIResponse)
async def list_careers(
    branch: Optional[str] = Query(None, description="Filter by branch (e.g. CSE, ECE)"),
    search: Optional[str] = Query(None, description="Search by career title"),
    limit: int = Query(50, ge=1, le=100),
    repo: CareerRepository = Depends(_get_repo),
):
    """Lists available careers with optional filtering."""
    careers = repo.list_careers(branch=branch, search=search, limit=limit)
    return APIResponse(success=True, data=careers)


@router.get("/{career_id}", response_model=APIResponse)
async def get_career_detail(
    career_id: str,
    repo: CareerRepository = Depends(_get_repo),
):
    """Returns full career details including required skills and related projects."""
    career = repo.get_career_by_id(career_id)
    if not career:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Career not found",
        )
    return APIResponse(success=True, data=career)
