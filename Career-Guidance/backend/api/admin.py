"""
CareerCompass AI — Admin API
Protected routes for managing careers, skills, and reference data.
Requires verified Supabase admin authorization (HTTP 401 for unauthenticated, 403 for unauthorized).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from backend.deps import AuthenticatedUser, get_service_supabase, require_admin
from backend.models.career import CareerBase
from backend.models.common import APIResponse
from backend.repositories.career_repo import CareerRepository

router = APIRouter(
    prefix="/admin", 
    tags=["Admin"],
    dependencies=[Depends(require_admin)]
)


def _get_repo(db: Client = Depends(get_service_supabase)) -> CareerRepository:
    return CareerRepository(db)


class CareerCreate(CareerBase):
    pass


class SkillCreate(BaseModel):
    name: str
    category: str


@router.post("/careers", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_career(
    body: CareerCreate,
    admin_user: AuthenticatedUser = Depends(require_admin),
    repo: CareerRepository = Depends(_get_repo),
):
    """Admin only: Create a new career."""
    career = repo.create_career(body.model_dump())
    return APIResponse(success=True, message="Career created", data=career)


@router.put("/careers/{career_id}", response_model=APIResponse)
async def update_career(
    career_id: str,
    body: CareerCreate,
    admin_user: AuthenticatedUser = Depends(require_admin),
    repo: CareerRepository = Depends(_get_repo),
):
    """Admin only: Update a career."""
    career = repo.update_career(career_id, body.model_dump(exclude={"id"}))
    return APIResponse(success=True, message="Career updated", data=career)


@router.delete("/careers/{career_id}", response_model=APIResponse)
async def delete_career(
    career_id: str,
    admin_user: AuthenticatedUser = Depends(require_admin),
    repo: CareerRepository = Depends(_get_repo),
):
    """Admin only: Delete a career."""
    success = repo.delete_career(career_id)
    if not success:
        raise HTTPException(status_code=404, detail="Career not found")
    return APIResponse(success=True, message="Career deleted")


@router.post("/skills", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    body: SkillCreate,
    admin_user: AuthenticatedUser = Depends(require_admin),
    repo: CareerRepository = Depends(_get_repo),
):
    """Admin only: Create a new skill."""
    skill = repo.create_skill(body.model_dump())
    return APIResponse(success=True, message="Skill created", data=skill)


@router.put("/skills/{skill_id}", response_model=APIResponse)
async def update_skill(
    skill_id: str,
    body: SkillCreate,
    admin_user: AuthenticatedUser = Depends(require_admin),
    repo: CareerRepository = Depends(_get_repo),
):
    """Admin only: Update a skill."""
    skill = repo.update_skill(skill_id, body.model_dump())
    return APIResponse(success=True, message="Skill updated", data=skill)
