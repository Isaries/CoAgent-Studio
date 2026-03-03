from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.organization import (
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
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


@router.put("/{org_id}", response_model=OrganizationRead)
async def update_organization(
    *,
    session: AsyncSession = Depends(deps.get_session),
    org_id: UUID,
    organization_in: OrganizationUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update an organization. Only accessible by organization members.
    """
    service = OrganizationService(session)
    # Verify access (will raise 403 if not a member)
    org = await service.get_organization(org_id, current_user)

    # Only owner can update
    if org.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organization owner can update")

    update_data = organization_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    session.add(org)
    await session.commit()
    await session.refresh(org)
    return org


@router.delete("/{org_id}", status_code=204)
async def delete_organization(
    *,
    session: AsyncSession = Depends(deps.get_session),
    org_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> None:
    """
    Delete an organization. Only the owner can delete.
    """
    service = OrganizationService(session)
    # Verify access (will raise 403 if not a member)
    org = await service.get_organization(org_id, current_user)

    # Only owner can delete
    if org.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the organization owner can delete")

    await session.delete(org)
    await session.commit()
    return None
