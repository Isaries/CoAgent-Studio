from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.models.course import (
    CourseCreate,
    CourseMember,
    CourseMemberUpdate,
    CourseRead,
    CourseUpdate,
)
from app.models.user import User, UserRole
from app.services.course_service import CourseService
from pydantic import BaseModel

router = APIRouter()


@router.post("/", response_model=CourseRead)
async def create_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_in: CourseCreate,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Create new course.
    Allowed: Admin, Teacher.
    """
    service = CourseService(session)
    return await service.create_course(course_in, current_user)


@router.get("/", response_model=List[CourseRead])
async def read_courses(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve courses r.
    Admins see all. Others see owned or enrolled.
    """
    service = CourseService(session)
    results = await service.get_courses(current_user, skip, limit)

    courses = []
    for course, owner_name in results:
        course_read = CourseRead.model_validate(course)
        course_read.owner_name = owner_name
        courses.append(course_read)

    return courses


@router.get("/{course_id}", response_model=CourseRead)
async def read_course(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user), # Dependency checks for valid user, but we will pass it 
) -> Any:
    """
    Get course by ID.
    """
    service = CourseService(session)
    course = await service.get_course_by_id(course_id)
    # The actual check for access to get_course_by_id is slightly permissive, usually anyone can GET a course they have an ID to 
    # if we wanted strict read checks, we'd add it to service. 
    # Legacy code checked `permission_service("read")`. Let's assume CourseService can handle it if needed.
    from fastapi import HTTPException
    from app.services.permission_service import permission_service
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if not await permission_service.check(current_user, "read", course, session):
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    return course


@router.put("/{course_id}", response_model=CourseRead)
async def update_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    course_in: CourseUpdate,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Update a course.
    Allowed: Admin, or Owner (Teacher).
    """
    service = CourseService(session)
    return await service.update_course(course_id, course_in, current_user)


@router.delete("/{course_id}", response_model=CourseRead)
async def delete_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    current_user: User = Depends(deps.require_role([UserRole.ADMIN, UserRole.TEACHER])),
) -> Any:
    """
    Delete a course.
    Allowed: Admin, or Owner (Teacher).
    """
    service = CourseService(session)
    return await service.delete_course(course_id, current_user)


class EnrollmentRequest(BaseModel):
    user_email: Optional[str] = None
    user_id: Optional[UUID] = None
    role: str = "student"


@router.post("/{course_id}/enroll")
async def enroll_user(
    course_id: UUID,
    enrollment: EnrollmentRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Enroll a user by email or ID into a course.
    """
    service = CourseService(session)
    message = await service.enroll_user(
        course_id, enrollment.user_email, enrollment.user_id, enrollment.role, current_user
    )
    return {"message": message}


@router.get("/{course_id}/members", response_model=List[CourseMember])
async def read_course_members(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get all members (students and TAs) of a course.
    Allowed: Admin, Teacher (Owner/TA).
    """
    service = CourseService(session)
    members_list, owner_id = await service.get_members(course_id, current_user)

    members_dict = {}
    for user, role in members_list:
        members_dict[user.id] = CourseMember(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=role,
        )

    # In modern 3-tier, the service would ensure owner is fetched and returned. 
    # For now, if owner is missing from list we fetch just like legacy.
    if owner_id in members_dict:
        members_dict[owner_id].role = "teacher"
    else:
        owner = await session.get(User, owner_id)
        if owner:
            members_dict[owner.id] = CourseMember(
                user_id=owner.id,
                email=owner.email,
                full_name=owner.full_name,
                avatar_url=owner.avatar_url,
                role="teacher",
            )

    return list(members_dict.values())


@router.put("/{course_id}/members/{user_id}", response_model=Any)
async def update_course_member_role(
    course_id: UUID,
    user_id: UUID,
    member_update: CourseMemberUpdate,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a member's role in a course (e.g. promote to TA).
    Allowed: Admin, Owner.
    """
    service = CourseService(session)
    await service.update_member_role(course_id, user_id, member_update.role, current_user)
    return {"message": "Role updated"}


@router.delete("/{course_id}/members/{user_id}")
async def remove_course_member(
    course_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Remove a user from a course.
    Allowed: Admin, Owner, TA (Student only).
    """
    service = CourseService(session)
    await service.remove_member(course_id, user_id, current_user)
    return {"message": "User removed from course"}
