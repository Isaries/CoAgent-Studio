import os
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.models.user import User, UserCreate, UserRole, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: str) -> Optional[User]:
        # Support UUID or str
        # But User.id is UUID.
        try:
            return await self.session.get(User, UUID(user_id))
        except Exception:
            return None

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        query = select(User).offset(skip).limit(limit)
        results = await self.session.exec(query)
        return results.all()

    async def search_users(self, q: str, limit: int = 10) -> List[User]:
        query = (
            select(User)
            .where(
                or_(User.email.contains(q), User.full_name.contains(q), User.username.contains(q))
            )
            .limit(limit)
        )
        result = await self.session.exec(query)
        return result.all()

    async def create_user(self, user_in: UserCreate, current_user: User) -> User:
        # Permission: Only Super Admin creates Admins
        if (
            user_in.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and current_user.role != "super_admin"
        ):
            raise HTTPException(
                status_code=403, detail="Only Super Admins can create Admin accounts"
            )

        # Check existing
        conditions = []
        if user_in.email:
            conditions.append(User.email == user_in.email)
        if user_in.username:
            conditions.append(User.username == user_in.username)

        if conditions:
            query = select(User).where(or_(*conditions))
            if (await self.session.exec(query)).first():
                raise HTTPException(status_code=400, detail="User already exists")

        user = User.model_validate(user_in)
        if user_in.password:
            user.hashed_password = security.get_password_hash(user_in.password)

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user_id: str, user_in: UserUpdate, current_user: User) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Permissions check logic copied from endpoint
        # 1. Super Admin cannot change their own role downgrade check
        user_data = user.dict(exclude_unset=True)
        update_data = user_in.dict(exclude_unset=True)

        if (
            user.id == current_user.id
            and update_data.get("role")
            and current_user.role == "super_admin"
            and update_data["role"] != "super_admin"
        ):
            raise HTTPException(status_code=400, detail="Super Admins cannot change their own role")

        # 2. Modify other admins
        if (
            user.id != current_user.id
            and user.role in ["admin", "super_admin"]
            and current_user.role != "super_admin"
        ):
            raise HTTPException(status_code=403, detail="Only Super Admins can modify other Admins")

        # 3. Promote to admin
        if (
            update_data.get("role") in ["admin", "super_admin"]
            and current_user.role != "super_admin"
        ):
            raise HTTPException(
                status_code=403, detail="Only Super Admins can promote users to Admin"
            )

        # Password handling
        if update_data.get("password"):
            update_data["hashed_password"] = security.get_password_hash(update_data["password"])
            del update_data["password"]

        for field in user_data:
            if field in update_data:
                setattr(user, field, update_data[field])

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user_me(self, user_in: UserUpdate, current_user: User) -> User:
        user_data = current_user.dict(exclude_unset=True)
        update_data = user_in.dict(exclude_unset=True)

        # Security restrictions
        if "role" in update_data:
            del update_data["role"]
        if "email" in update_data:
            del update_data["email"]

        if update_data.get("password"):
            current_user.hashed_password = security.get_password_hash(update_data["password"])
            del update_data["password"]

        for field in user_data:
            if field in update_data:
                setattr(current_user, field, update_data[field])

        self.session.add(current_user)
        await self.session.commit()
        await self.session.refresh(current_user)
        return current_user

    async def delete_user(self, user_id: str, current_user: User) -> User:
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        if user.role in ["admin", "super_admin"] and current_user.role != "super_admin":
            raise HTTPException(
                status_code=403, detail="Only Super Admins can delete Admin accounts"
            )

        self.session.delete(user)
        await self.session.commit()
        return user

    async def upload_avatar(self, file: UploadFile, current_user: User) -> User:
        # Validate
        if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
            raise HTTPException(status_code=400, detail="Invalid file type")

        file_size_limit = 2 * 1024 * 1024

        # Path resolution - tricky without dependency injection of config
        # Assuming relative path from THIS file.
        # this file: backend/app/services/user_service.py
        # static: backend/static/avatars
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        static_dir = os.path.join(base_dir, "static", "avatars")

        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        file_extension = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(static_dir, filename)

        real_file_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                real_file_size += len(chunk)
                if real_file_size > file_size_limit:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(status_code=400, detail="File too large")
                buffer.write(chunk)

        relative_path = f"/static/avatars/{filename}"
        current_user.avatar_url = relative_path
        self.session.add(current_user)
        await self.session.commit()
        await self.session.refresh(current_user)
        return current_user
