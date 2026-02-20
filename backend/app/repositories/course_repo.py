from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.course import (
    Course,
    CourseCreate,
    CourseUpdate,
    UserCourseLink,
)
from app.models.user import User
from app.repositories.base_repo import BaseRepository


class RepositoryCourse(BaseRepository[Course, CourseCreate, CourseUpdate]):
    async def get_multi_with_owner(
        self, session: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Course, Optional[str]]]:
        """Get all courses with owner name, used for admins."""
        query = (
            select(Course, User.full_name)
            .join(User, col(Course.owner_id) == col(User.id))
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def get_multi_by_user_with_owner(
        self, session: AsyncSession, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Course, Optional[str]]]:
        """Get courses owned by or enrolled in by a user."""
        query = (
            select(Course, User.full_name)
            .join(User, col(Course.owner_id) == col(User.id))
            .distinct()
            .outerjoin(UserCourseLink, col(Course.id) == col(UserCourseLink.course_id))
            .where(
                or_(
                    col(Course.owner_id) == user_id,
                    col(UserCourseLink.user_id) == user_id,
                )
            )
            .offset(skip)
            .limit(limit)
        )
        result = await session.exec(query)
        return result.all()

    async def get_user_link(
        self, session: AsyncSession, *, user_id: UUID, course_id: UUID
    ) -> Optional[UserCourseLink]:
        return await session.get(UserCourseLink, (user_id, course_id))

    async def create_user_link(
        self, session: AsyncSession, *, user_id: UUID, course_id: UUID, role: str
    ) -> UserCourseLink:
        link = UserCourseLink(
            user_id=user_id,
            course_id=course_id,
            role=role,
        )
        session.add(link)
        await session.commit()
        return link

    async def get_course_members(
        self, session: AsyncSession, *, course_id: UUID
    ) -> List[Tuple[User, str]]:
        query = (
            select(User, UserCourseLink.role)
            .join(UserCourseLink, User.id == UserCourseLink.user_id)
            .where(UserCourseLink.course_id == course_id)
        )
        result = await session.exec(query)
        return result.all()

    async def get_user_by_email(self, session: AsyncSession, *, email: str) -> Optional[User]:
         return (await session.exec(select(User).where(User.email == email))).first()
         
    async def update_user_link(self, session: AsyncSession, *, link: UserCourseLink) -> UserCourseLink:
        session.add(link)
        await session.commit()
        await session.refresh(link)
        return link
        
    async def remove_user_link(self, session: AsyncSession, *, link: UserCourseLink) -> None:
        await session.delete(link)
        await session.commit()

course_repo = RepositoryCourse(Course)
