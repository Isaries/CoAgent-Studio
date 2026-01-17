from typing import Any, Literal, Union

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.course import Course, UserCourseLink
from app.models.room import Room
from app.models.user import User, UserRole

Action = Literal["create", "read", "update", "delete", "assign", "list_users", "manage_users", "manage_config"]
Resource = Union[Course, Room, User, None]


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
        elif isinstance(resource, Course):
            return await self._check_course_permission(user, action, resource, session)
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

        course = await session.get(Course, room.course_id)  # type: ignore[func-returns-value]
        if not course:
            return False

        # Course Owner
        if course.owner_id == user.id:
            return True

        # Check User Link (TA or Student)
        statement: Any = select(UserCourseLink).where(
            UserCourseLink.user_id == user.id,
            UserCourseLink.course_id == course.id,
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

    async def _check_course_permission(
        self, user: User, action: Action, course: Course, session: AsyncSession
    ) -> bool:
        if user.role == UserRole.ADMIN:
            return True
        if course.owner_id == user.id:
            return True

        # Custom logic for "manage_config" handled via Course permission?
        # Ideally, we call check(user, "manage_config", course)

        # Check User Link (TA or Student)
        statement: Any = select(UserCourseLink).where(
            UserCourseLink.user_id == user.id,
            UserCourseLink.course_id == course.id,
        )
        result = await session.exec(statement)
        link = result.first()

        if not link:
            return False

        if link.role == "ta":
            return True

        if link.role == "student":
            # Student can only READ course details
            # Cannot manage_config
            if action == "manage_config":
                return False
            return action == "read"


        return False


permission_service = PermissionService()
