from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.project import ProjectCreate, ProjectRead
from app.models.user import User
from app.services.project_service import ProjectService

router = APIRouter()


@router.get("", response_model=List[ProjectRead])
async def read_projects(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
    org_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve projects user is a member of. Optionally filter by organization.
    """
    service = ProjectService(session)
    return await service.get_projects_for_user(current_user, org_id=org_id, skip=skip, limit=limit)


@router.post("", response_model=ProjectRead)
async def create_project(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_in: ProjectCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new project inside an organization.
    """
    service = ProjectService(session)
    return await service.create_project(project_in, current_user)


@router.get("/{project_id}", response_model=ProjectRead)
async def read_project(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get project by ID.
    """
    service = ProjectService(session)
    return await service.get_project(project_id, current_user)
