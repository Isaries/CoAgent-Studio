from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.core.audit_service import log_change
from app.core.security import mask_api_key
from app.models.user import User
from app.models.user_api_key import UserAPIKey, UserAPIKeyRead, UserAPIKeyCreate
from app.services.user_key_service import UserKeyService

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
            is_active=k.is_active,
            schedule_config=k.schedule_config,
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


# ============================================================
# Key Scheduling & Availability Controls
# ============================================================

class KeyScheduleUpdate(BaseModel):
    is_active: Optional[bool] = None
    schedule_config: Optional[Dict[str, Any]] = None


@router.put("/{key_id}/schedule")
async def update_key_schedule(
    key_id: UUID,
    data: KeyScheduleUpdate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """Update is_active toggle and/or schedule_config for an API key."""
    key = await session.get(UserAPIKey, key_id)
    if not key:
        raise HTTPException(404, "API Key not found")
    if key.user_id != current_user.id:
        raise HTTPException(403, "Not your key")

    old_values = {
        "is_active": key.is_active,
        "schedule_config": key.schedule_config,
    }

    from datetime import datetime
    if data.is_active is not None:
        key.is_active = data.is_active
    if data.schedule_config is not None:
        key.schedule_config = data.schedule_config
    key.updated_at = datetime.utcnow()

    session.add(key)

    await log_change(
        session,
        entity_type="api_key",
        entity_id=str(key_id),
        action="update_schedule",
        actor_id=current_user.id,
        old_value=old_values,
        new_value={
            "is_active": key.is_active,
            "schedule_config": key.schedule_config,
        },
    )

    await session.commit()
    return {
        "message": "Schedule updated",
        "is_active": key.is_active,
        "schedule_config": key.schedule_config,
    }
