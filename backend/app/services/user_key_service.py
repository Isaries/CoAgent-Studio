from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import encrypt_api_key, decrypt_api_key, mask_api_key
from app.models.user_api_key import UserAPIKey, UserAPIKeyCreate
from app.models.user import User


class UserKeyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_keys(self, user_id: UUID) -> List[UserAPIKey]:
        query = select(UserAPIKey).where(UserAPIKey.user_id == user_id)
        result = await self.session.exec(query)
        return result.all()

    async def create_key(self, data: UserAPIKeyCreate, user_id: UUID) -> UserAPIKey:
        # Check for duplicates? Maybe alias must be unique per user.
        # Let's enforce alias uniqueness for user convenience.
        query = select(UserAPIKey).where(
            UserAPIKey.user_id == user_id, 
            UserAPIKey.alias == data.alias
        )
        existing = (await self.session.exec(query)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Key with this alias already exists.")

        encrypted = encrypt_api_key(data.api_key)
        
        new_key = UserAPIKey(
            user_id=user_id,
            provider=data.provider,
            alias=data.alias,
            description=data.description,
            encrypted_key=encrypted
        )
        
        self.session.add(new_key)
        await self.session.commit()
        await self.session.refresh(new_key)
        return new_key

    async def delete_key(self, key_id: UUID, user_id: UUID) -> None:
        key = await self.session.get(UserAPIKey, key_id)
        if not key or key.user_id != user_id:
            raise HTTPException(status_code=404, detail="Key not found")
            
        await self.session.delete(key)
        await self.session.commit()
    
    async def get_decrypted_key(self, key_id: UUID, user_id: UUID) -> str:
        """Retrieve decrypted key for usage. Strict ownership check."""
        key = await self.session.get(UserAPIKey, key_id)
        if not key:
            raise HTTPException(status_code=404, detail="Key not found")
        
        # In future, if we share agents, we might need a system-level override here,
        # but for direct user usage, strict id match is safe.
        # But wait, LLMService calling this might act on behalf of the user.
        if key.user_id != user_id:
             raise HTTPException(status_code=403, detail="Access denied to this key")
             
        return decrypt_api_key(key.encrypted_key)
