from typing import Any, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.course import Course, CourseCreate, CourseUpdate, UserCourseLink
from app.models.user import User, UserRole
from app.repositories.course_repo import course_repo


class CourseService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = course_repo

    async def create_course(self, course_in: CourseCreate, owner: User) -> Course:
        course = await self.repo.create(self.session, obj_in=course_in, owner_id=owner.id)

        # Auto-enroll creator as teacher
        await self.repo.create_user_link(
            self.session, user_id=owner.id, course_id=course.id, role="teacher"
        )
        return course

    async def get_courses(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> List[Tuple[Course, Optional[str]]]:
        if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            return await self.repo.get_multi_with_owner(self.session, skip=skip, limit=limit)
        else:
            return await self.repo.get_multi_by_user_with_owner(
                self.session, user_id=user.id, skip=skip, limit=limit
            )

    async def get_course_by_id(self, course_id: UUID) -> Optional[Course]:
        return await self.repo.get(self.session, id=course_id)

    async def update_course(
        self, course_id: UUID, course_in: CourseUpdate, current_user: User
    ) -> Course:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and course.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.update(self.session, db_obj=course, obj_in=course_in)

    async def delete_course(self, course_id: UUID, current_user: User) -> Course:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and course.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        return await self.repo.remove(self.session, id=course_id)

    async def enroll_user(
        self,
        course_id: UUID,
        email: Optional[str],
        user_id: Optional[UUID],
        role: str,
        current_user: User,
    ) -> str:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, course_id=course.id)
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

        link = await self.repo.get_user_link(self.session, user_id=user_to_enroll.id, course_id=course_id)
        if link:
            return "User already enrolled"

        await self.repo.create_user_link(
            self.session, user_id=user_to_enroll.id, course_id=course_id, role=role
        )
        return f"User {user_to_enroll.full_name} enrolled as {role}"

    async def get_members(self, course_id: UUID, current_user: User) -> Tuple[List[Tuple[User, str]], UUID]:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, course_id=course_id)
            if not link:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        members = await self.repo.get_course_members(self.session, course_id=course_id)
        return members, course.owner_id

    async def update_member_role(
        self, course_id: UUID, user_id: UUID, role: str, current_user: User
    ) -> UserCourseLink:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )

        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, course_id=course_id)
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            if role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot promote to TA/Teacher")
            target_link = await self.repo.get_user_link(self.session, user_id=user_id, course_id=course_id)
            if target_link and target_link.role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot modify TAs/Teachers")

        if user_id == course.owner_id:
            raise HTTPException(status_code=400, detail="Cannot change owner role")

        link = await self.repo.get_user_link(self.session, user_id=user_id, course_id=course_id)
        if not link:
            raise HTTPException(status_code=404, detail="User not enrolled")

        link.role = role
        return await self.repo.update_user_link(self.session, link=link)

    async def remove_member(self, course_id: UUID, user_id: UUID, current_user: User) -> None:
        course = await self.repo.get(self.session, id=course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if user_id == course.owner_id:
            raise HTTPException(status_code=400, detail="Cannot remove owner")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )

        if not is_admin_owner:
            link = await self.repo.get_user_link(self.session, user_id=current_user.id, course_id=course_id)
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            target_link = await self.repo.get_user_link(self.session, user_id=user_id, course_id=course_id)
            if target_link and target_link.role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot remove TAs/Teachers")

        link = await self.repo.get_user_link(self.session, user_id=user_id, course_id=course_id)
        if not link:
            raise HTTPException(status_code=404, detail="User not found in course")

        await self.repo.remove_user_link(self.session, link=link)
