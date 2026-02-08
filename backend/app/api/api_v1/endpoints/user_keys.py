from typing import List, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.user import User
from app.models.user_api_key import UserAPIKeyRead, UserAPIKeyCreate
from app.services.user_key_service import UserKeyService
from app.core.security import mask_api_key

router = APIRouter()


@router.get("", response_model=List[UserAPIKeyRead])
async def list_user_keys(
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    List my API keys (masked).
    """
    service = UserKeyService(session)
    keys = await service.list_keys(current_user.id)
    
    # Mask keys for response
    response_data = []
    for k in keys:
        read_model = UserAPIKeyRead(
            user_id=k.user_id,
            provider=k.provider,
            alias=k.alias,
            description=k.description,
            id=k.id,
            created_at=k.created_at,
            updated_at=k.updated_at,
            masked_key=mask_api_key(k.encrypted_key)
        )
        response_data.append(read_model)
    
    return response_data


@router.post("", response_model=UserAPIKeyRead)
async def create_user_key(
    data: UserAPIKeyCreate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Add a new API key to wallet.
    """
    service = UserKeyService(session)
    new_key = await service.create_key(data, current_user.id)
    
    # Return with masked key
    from app.core.security import mask_api_key
    # We have the raw key in `data.api_key`, use that to mask for response
    # to avoid decrypt overhead.
    masked = f"{data.api_key[:3]}...{data.api_key[-4:]}" # Simple local masking for immediate response
    
    return UserAPIKeyRead(
        user_id=new_key.user_id,
        provider=new_key.provider,
        alias=new_key.alias,
        description=new_key.description,
        id=new_key.id,
        created_at=new_key.created_at,
        updated_at=new_key.updated_at,
        masked_key=masked
    )


@router.delete("/{key_id}", status_code=204)
async def delete_user_key(
    key_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Remove a key from wallet.
    """
    service = UserKeyService(session)
    await service.delete_key(key_id, current_user.id)
