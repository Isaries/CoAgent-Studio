from typing import Literal, Union

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.course import Course, UserCourseLink
from app.models.room import Room
from app.models.user import User, UserRole

Action = Literal["create", "read", "update", "delete", "assign", "list_users", "manage_users"]
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
    ) -> bool:
        # Admins can access all rooms
        if user.role == UserRole.ADMIN:
            return True

        course = await session.get(Course, room.course_id)
        if not course:
            return False

        # Course Owner
        if course.owner_id == user.id:
            return True

        # TA Check
        statement = select(UserCourseLink).where(
            UserCourseLink.user_id == user.id,
            UserCourseLink.course_id == course.id,
            UserCourseLink.role == "ta",
        )
        result = await session.exec(statement)
        is_ta = result.first() is not None

        if is_ta:
            # TAs can Read, Update, Assign, Delete rooms within their course
            return True

        # Students? (If action is 'read', maybe? But rooms.py endpoints seem to be for management)
        # Regular students usually don't hit /api/v1/rooms/{id} for management,
        # but they do need to access chat.
        # However, the rooms.py endpoints are CRUD for Room object (create, update, delete, assign).
        # Normal usage for chat is via /api/v1/chat/... which calls validation logic inside get_room_messages.
        # But rooms.py read_rooms (list) might be used by students?
        # Let's check rooms.py read_rooms.

        return False

    async def _check_course_permission(
        self, user: User, action: Action, course: Course, session: AsyncSession
    ) -> bool:
        if user.role == UserRole.ADMIN:
            return True
        if course.owner_id == user.id:
            return True

        # TA Check for Course?
        statement = select(UserCourseLink).where(
            UserCourseLink.user_id == user.id,
            UserCourseLink.course_id == course.id,
            UserCourseLink.role == "ta",
        )
        result = await session.exec(statement)
        is_ta = result.first() is not None
        if is_ta:
            return True

        return False


permission_service = PermissionService()
