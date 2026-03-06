from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.models.user import User, UserRole
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


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    project_in: ProjectUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a project. Requires project membership.
    """
    service = ProjectService(session)
    # Verify access (will raise 403 if not a member)
    project = await service.get_project(project_id, current_user)

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    *,
    session: AsyncSession = Depends(deps.get_session),
    project_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete a project. Requires project membership.
    """
    service = ProjectService(session)
    # Verify access (will raise 403 if not a member)
    project = await service.get_project(project_id, current_user)

    # Only project owner or admin can delete
    if project.owner_id != current_user.id and current_user.role not in [
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    ]:
        raise HTTPException(
            status_code=403, detail="Only the project owner or admin can delete this project"
        )

    await session.delete(project)
    await session.commit()
    return None
