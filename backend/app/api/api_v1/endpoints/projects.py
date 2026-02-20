from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.organization import UserOrganizationLink
from app.models.project import Project, ProjectCreate, ProjectRead, ProjectUpdate, UserProjectLink
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[ProjectRead])
async def read_projects(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
    org_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve projects user is a member of. Optionally filter by organization.
    """
    query = select(Project).join(UserProjectLink).where(UserProjectLink.user_id == current_user.id)
    if org_id:
        query = query.where(Project.organization_id == org_id)
        
    statement = query.offset(skip).limit(limit)
    result = await session.exec(statement)
    return result.all()


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
    # Verify org access
    org_link = await session.get(UserOrganizationLink, (current_user.id, project_in.organization_id))
    if not org_link or org_link.role not in ["super_admin", "admin", "owner", "member"]:
        raise HTTPException(status_code=403, detail="Not enough permissions in organization")

    project = Project.model_validate(project_in)
    session.add(project)
    await session.commit()
    await session.refresh(project)

    # Link user as project admin
    link = UserProjectLink(
        user_id=current_user.id,
        project_id=project.id,
        role="admin",
    )
    session.add(link)
    await session.commit()

    return project


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
    # Check access
    link = await session.get(UserProjectLink, (current_user.id, project_id))
    if not link:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
