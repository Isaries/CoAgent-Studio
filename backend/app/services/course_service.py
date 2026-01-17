from typing import Any, List, Optional, Tuple  # type: ignore
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.course import Course, CourseCreate, CourseUpdate, UserCourseLink
from app.models.user import User, UserRole


class CourseService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_course(self, course_in: CourseCreate, owner: User) -> Course:
        course_data = course_in.model_dump()
        course_data["owner_id"] = owner.id
        course = Course.model_validate(course_data)
        self.session.add(course)
        await self.session.commit()
        await self.session.refresh(course)

        # Auto-enroll creator as teacher
        link = UserCourseLink(user_id=owner.id, course_id=course.id, role="teacher")
        self.session.add(link)
        await self.session.commit()

        return course

    async def get_courses(self, user: User, skip: int = 0, limit: int = 100) -> List[Tuple[Course, Optional[str]]]:
        if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            # Admins see all courses with owner name
            query: Any = (
                select(Course, User.full_name)
                .join(User, col(Course.owner_id) == col(User.id))
                .offset(skip)  # type: ignore
                .limit(limit)
            )
        else:
            # Users see courses they own or are enrolled in
            query = (
                select(Course, User.full_name)
                .join(User, col(Course.owner_id) == col(User.id))
                .distinct()  # type: ignore
                .outerjoin(UserCourseLink, col(Course.id) == col(UserCourseLink.course_id))
                .where(
                    or_(
                        col(Course.owner_id) == user.id,
                        col(UserCourseLink.user_id) == user.id,
                    )
                )
                .offset(skip)
                .limit(limit)
            )

        results = await self.session.exec(query)

        # Format results to include owner_name (handled by endpoint usually, but we help here?)
        # Ideally service returns model or enriched model.
        # For simplicity, returning list of (Course, owner_name) tuples or mapped objects.
        # Let's return the Raw Result for endpoint to process, or process here.
        # Endpoint expects list of CourseRead.

        courses_data = []
        for course, owner_name in results:
            # We can attach owner_name temporarily if needed, or return tuple
            # Let's return tuple
            courses_data.append((course, owner_name))

        return courses_data

    async def get_course_by_id(self, course_id: UUID) -> Optional[Course]:
        return await self.session.get(Course, course_id)

    async def update_course(
        self, course_id: UUID, course_in: CourseUpdate, current_user: User
    ) -> Course:
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Check permissions
        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and course.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        course_data = course.dict(exclude_unset=True)
        update_data = course_in.dict(exclude_unset=True)

        for field in course_data:
            if field in update_data:
                setattr(course, field, update_data[field])

        self.session.add(course)
        await self.session.commit()
        await self.session.refresh(course)
        return course

    async def delete_course(self, course_id: UUID, current_user: User) -> Course:
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Double check permission service-side (Owner-only or Admin)
        if (
            current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            and course.owner_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not enough permissions")

        # Cascade Delete handled by SQLAlchemy/Database
        # We need to ensure we loaded the relationships or that the DB handles it.
        # Since we added `ondelete` cascade in models (via sa_relationship_kwargs), session.delete will trigger queries to delete children OR let DB do it.
        # Actually in async SQLModel without enforcing FK constraints in DB schema manually, SQLAlchemy emits DELETE for children if loaded?
        # Typically `cascade="all, delete-orphan"` in SQLAlchemy ORM works by deleting loaded objects or emitting DELETE statements.

        await self.session.delete(course)
        await self.session.commit()
        return course

    async def enroll_user(
        self,
        course_id: UUID,
        email: Optional[str],
        user_id: Optional[UUID],
        role: str,
        current_user: User,
    ) -> str:
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Permission: Admin, Owner, or TA
        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.session.get(UserCourseLink, (current_user.id, course.id))  # type: ignore[func-returns-value]
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")

        # Find user
        user_to_enroll = None
        if user_id:
            user_to_enroll = await self.session.get(User, user_id)  # type: ignore[func-returns-value]
        elif email:
            user_to_enroll = (
                await self.session.exec(select(User).where(User.email == email))
            ).first()

        if not user_to_enroll:
            raise HTTPException(status_code=404, detail="User not found")

        # Check existing
        link = await self.session.get(UserCourseLink, (user_to_enroll.id, course_id))  # type: ignore[func-returns-value]
        if link:
            return "User already enrolled"

        new_link = UserCourseLink(user_id=user_to_enroll.id, course_id=course_id, role=role)
        self.session.add(new_link)
        await self.session.commit()
        return f"User {user_to_enroll.full_name} enrolled as {role}"

    async def get_members(self, course_id: UUID, current_user: User):
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        # Permission: Admin, Owner, Member
        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )
        if not is_admin_owner:
            link = await self.session.get(UserCourseLink, (current_user.id, course_id))  # type: ignore[func-returns-value]  # type: ignore[func-returns-value]
            if not link:
                raise HTTPException(status_code=403, detail="Not enough permissions")

        query: Any = (
            select(User, UserCourseLink.role)
            .join(UserCourseLink, User.id == UserCourseLink.user_id)  # type: ignore[arg-type]
            .where(UserCourseLink.course_id == course_id)  # type: ignore
        )
        results = await self.session.exec(query)
        members = results.all()

        # Ensure owner included
        # logic handled in endpoint previously, moving logic here or keeping endpoint clean?
        # Let's return the raw list and let endpoint format, OR format here.
        # Format here is cleaner.

        # We need to construct a list of dicts or objects that look like CourseMember
        # But User model is SQLModel.
        # Let's return list of (User, role)

        return members, course.owner_id

    async def update_member_role(
        self, course_id: UUID, user_id: UUID, role: str, current_user: User
    ) -> UserCourseLink:
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )

        if not is_admin_owner:
            # TA check
            link = await self.session.get(UserCourseLink, (current_user.id, course_id))  # type: ignore[func-returns-value]  # type: ignore[func-returns-value]
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            # TA restrictions
            if role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot promote to TA/Teacher")
            target_link = await self.session.get(UserCourseLink, (user_id, course_id))  # type: ignore[func-returns-value]
            if target_link and target_link.role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot modify TAs/Teachers")

        if user_id == course.owner_id:
            raise HTTPException(status_code=400, detail="Cannot change owner role")

        link = await self.session.get(UserCourseLink, (user_id, course_id))  # type: ignore[func-returns-value]  # type: ignore[func-returns-value]
        if not link:
            raise HTTPException(status_code=404, detail="User not enrolled")

        link.role = role
        self.session.add(link)
        await self.session.commit()
        return link

    async def remove_member(self, course_id: UUID, user_id: UUID, current_user: User) -> None:
        course = await self.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        if user_id == course.owner_id:
            raise HTTPException(status_code=400, detail="Cannot remove owner")

        is_admin_owner = (
            current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
            or course.owner_id == current_user.id
        )

        if not is_admin_owner:
            link = await self.session.get(UserCourseLink, (current_user.id, course_id))  # type: ignore[func-returns-value]  # type: ignore[func-returns-value]
            if not link or link.role != "ta":
                raise HTTPException(status_code=403, detail="Not enough permissions")
            target_link = await self.session.get(UserCourseLink, (user_id, course_id))  # type: ignore[func-returns-value]
            if target_link and target_link.role in ["ta", "teacher"]:
                raise HTTPException(status_code=403, detail="TAs cannot remove TAs/Teachers")

        link = await self.session.get(UserCourseLink, (user_id, course_id))  # type: ignore[func-returns-value]
        if not link:
            raise HTTPException(status_code=404, detail="User not found in course")

        await self.session.delete(link)
        await self.session.commit()
