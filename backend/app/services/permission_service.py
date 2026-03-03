from typing import Any, Literal, Union

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.space import Space, UserSpaceLink
from app.models.room import Room
from app.models.user import User, UserRole

Action = Literal["create", "read", "update", "delete", "assign", "list_users", "manage_users", "manage_config"]
Resource = Union[Space, Room, User, None]


class PermissionService:
    async def check(
        self, user: User, action: Action, resource: Resource, session: AsyncSession
    ) -> bool:
        """
        Unified permission check.
        Returns True if authorized, False otherwise.
        """

        # Super Admin has all permissions
        if user.role == UserRole.SUPER_ADMIN:
            return True

        if resource is None:
            if action in ["list_users", "manage_users"]:
                # Only Admin/Super Admin can list/manage users globally
                return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            return False

        if isinstance(resource, Room):
            return await self._check_room_permission(user, action, resource, session)
        elif isinstance(resource, Space):
            return await self._check_space_permission(user, action, resource, session)
        elif isinstance(resource, User):
            # Managing other users
            return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN] or user.id == resource.id

        return False

    async def _check_room_permission(
        self, user: User, action: Action, room: Room, session: AsyncSession
    ) -> bool:  # type: ignore[func-returns-value]
        # Admins can access all rooms
        if user.role == UserRole.ADMIN:
            return True

        space = await session.get(Space, room.space_id)  # type: ignore[func-returns-value]
        if not space:
            return False

        # Space Owner
        if space.owner_id == user.id:
            return True

        # Check User Link (TA or Student)
        statement: Any = select(UserSpaceLink).where(
            UserSpaceLink.user_id == user.id,
            UserSpaceLink.space_id == space.id,
        )
        result = await session.exec(statement)
        link = result.first()

        if not link:
            return False

        if link.role == "ta":
            return True

        if link.role == "student":
            # Student can only READ rooms
            return action == "read"

        return False

    async def _check_space_permission(
        self, user: User, action: Action, space: Space, session: AsyncSession
    ) -> bool:
        if user.role == UserRole.ADMIN:
            return True
        if space.owner_id == user.id:
            return True

        # Custom logic for "manage_config" handled via Space permission?
        # Ideally, we call check(user, "manage_config", space)

        # Check User Link (TA or Student)
        statement: Any = select(UserSpaceLink).where(
            UserSpaceLink.user_id == user.id,
            UserSpaceLink.space_id == space.id,
        )
        result = await session.exec(statement)
        link = result.first()

        if not link:
            return False

        if link.role == "ta":
            return True

        if link.role == "student":
            # Student can only READ space details
            # Cannot manage_config
            if action == "manage_config":
                return False
            return action == "read"


        return False


permission_service = PermissionService()
