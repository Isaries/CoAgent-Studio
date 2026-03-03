from typing import Any, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.space import Space, SpaceCreate, SpaceUpdate, UserSpaceLink
from app.models.user import User, UserRole
from app.repositories.space_repo import space_repo


class SpaceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = space_repo

    async def create_space(self, space_in: SpaceCreate, owner: User) -> Space:
        space = await self.repo.create(self.session, obj_in=space_in, owner_id=owner.id)

        # Auto-enroll creator as space_owner
        await self.repo.create_user_link(
            self.session, user_id=owner.id, space_id=space.id, role="space_owner"
        )
        return space

    async def get_spaces(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Space, Optional[str]]]:
        if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return await self.repo.get_multi_with_owner(self.session, skip=skip, limit=limit)
        else:
            return await self.repo.get_multi_by_user_with_owner(
                self.session, user_id=user.id, skip=skip, limit=limit
            )

    async def get_space_by_id(self, space_id: UUID) -> Optional[Space]:
        return await self.repo.get(self.session, id=space_id)

    async def update_space(
        self, space_id: UUID, space_in: SpaceUpdate, current_user: User
    ) -> Space:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and space.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.update(self.session, db_obj=space, obj_in=space_in)

    async def delete_space(self, space_id: UUID, current_user: User) -> Space:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and space.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.remove(self.session, id=space_id)

    async def enroll_user(
        self,
        space_id: UUID,
        email: Optional[str],
        user_id: Optional[UUID],
        role: str,
        current_user: User,
    ) -> str:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or space.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, space_id=space.id)
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")

        user_to_enroll = None
        if user_id:
             # In a real 3-tier we'd use UserRepo, but since it's simple we use session.get here or basic SQL
             user_to_enroll = await self.session.get(User, user_id)
        elif email:
            user_to_enroll = await self.repo.get_user_by_email(self.session, email=email)

        if not user_to_enroll:
            raise HTTPException(status_code=404, detail="User not found")

        link = await self.repo.get_user_link(self.session, user_id=user_to_enroll.id, space_id=space_id)
        if link:
            return "User already enrolled"

        await self.repo.create_user_link(
            self.session, user_id=user_to_enroll.id, space_id=space_id, role=role
        )
        return f"User {user_to_enroll.full_name} enrolled as {role}"

    async def get_members(self, space_id: UUID, current_user: User) -> Tuple[List[Tuple[User, str]], UUID]:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or space.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, space_id=space_id)
            if not link:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        members = await self.repo.get_space_members(self.session, space_id=space_id)
        return members, space.owner_id

    async def update_member_role(
        self, space_id: UUID, user_id: UUID, role: str, current_user: User
    ) -> UserSpaceLink:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or space.owner_id == current_user.id
        )

        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, space_id=space_id)
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            if role in ["ta", "space_owner"]:
                raise HTTPException(status_code=403, detail="TAs cannot promote to TA/Space Owner")
            target_link = await self.repo.get_user_link(self.session, user_id=user_id, space_id=space_id)
            if target_link and target_link.role in ["ta", "space_owner"]:
                raise HTTPException(status_code=403, detail="TAs cannot modify TAs/Space Owners")

        if user_id == space.owner_id:
            raise HTTPException(status_code=400, detail="Cannot change owner role")

        link = await self.repo.get_user_link(self.session, user_id=user_id, space_id=space_id)
        if not link:
            raise HTTPException(status_code=404, detail="User not enrolled")

        link.role = role
        return await self.repo.update_user_link(self.session, link=link)

    async def remove_member(self, space_id: UUID, user_id: UUID, current_user: User) -> None:
        space = await self.repo.get(self.session, id=space_id)
        if not space:
            raise HTTPException(status_code=404, detail="Space not found")

        if user_id == space.owner_id:
            raise HTTPException(status_code=400, detail="Cannot remove owner")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or space.owner_id == current_user.id
        )

        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, space_id=space_id)
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            target_link = await self.repo.get_user_link(self.session, user_id=user_id, space_id=space_id)
            if target_link and target_link.role in ["ta", "space_owner"]:
                raise HTTPException(status_code=403, detail="TAs cannot remove TAs/Space Owners")

        link = await self.repo.get_user_link(self.session, user_id=user_id, space_id=space_id)
        if not link:
            raise HTTPException(status_code=404, detail="User not found in space")

        await self.repo.remove_user_link(self.session, link=link)
