from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.organization import (
    Organization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    UserOrganizationLink,
)
from app.models.user import User

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
    statement = (
        select(Organization)
        .join(UserOrganizationLink)
        .where(UserOrganizationLink.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    result = await session.exec(statement)
    return result.all()


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
    organization = Organization.model_validate(
        organization_in, update={"owner_id": current_user.id}
    )
    session.add(organization)
    await session.commit()
    await session.refresh(organization)

    # Link user as owner
    link = UserOrganizationLink(
        user_id=current_user.id,
        organization_id=organization.id,
        role="owner",
    )
    session.add(link)
    await session.commit()

    return organization


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
    # Check access
    link = await session.get(UserOrganizationLink, (current_user.id, org_id))
    if not link:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    organization = await session.get(Organization, org_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization
