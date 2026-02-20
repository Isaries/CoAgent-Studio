from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.organization import (
    OrganizationCreate,
    OrganizationRead,
)
from app.models.user import User
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.get("", response_model=List[OrganizationRead])
async def read_organizations(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve organizations user is a member of.
    """
    service = OrganizationService(session)
    return await service.get_organizations_for_user(current_user, skip=skip, limit=limit)


@router.post("", response_model=OrganizationRead)
async def create_organization(
    *,
    session: AsyncSession = Depends(deps.get_session),
    organization_in: OrganizationCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new organization. User becomes owner.
    """
    service = OrganizationService(session)
    return await service.create_organization(organization_in, current_user)


@router.get("/{org_id}", response_model=OrganizationRead)
async def read_organization(
    *,
    session: AsyncSession = Depends(deps.get_session),
    org_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get organization by ID.
    """
    service = OrganizationService(session)
    return await service.get_organization(org_id, current_user)
