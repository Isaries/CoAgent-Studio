from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, SQLModel

from app.api import deps
from app.models.user import User, UserRole
from app.models.course import Course, CourseCreate, CourseRead, CourseUpdate, UserCourseLink, CourseMember, CourseMemberUpdate

router = APIRouter()

@router.post("/", response_model=CourseRead)
async def create_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_in: CourseCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Create new course.
    Allowed: Admin, Teacher.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.TEACHER]:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    course_data = course_in.model_dump()
    course_data["owner_id"] = current_user.id
    course = Course.model_validate(course_data)
    session.add(course)
    await session.commit()
    await session.refresh(course)
    
    # Auto-enroll creator as teacher
    link = UserCourseLink(
        user_id=current_user.id,
        course_id=course.id,
        role="teacher"
    )
    session.add(link)
    await session.commit()
    
    return course

@router.get("/", response_model=List[CourseRead])
async def read_courses(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Retrieve courses.
    For MVP: list all courses. Later: filter by enrollment.
    """
    query = select(Course).offset(skip).limit(limit)
    result = await session.exec(query)
    return result.all()

@router.get("/{course_id}", response_model=CourseRead)
async def read_course(
    course_id: UUID,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get course by ID.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseRead)
async def update_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    course_in: CourseUpdate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Update a course.
    Allowed: Admin, or Owner (Teacher).
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check permissions
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    course_data = course.dict(exclude_unset=True)
    update_data = course_in.dict(exclude_unset=True)
    
    for field in course_data:
        if field in update_data:
            setattr(course, field, update_data[field])
            
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course

@router.delete("/{course_id}", response_model=CourseRead)
async def delete_course(
    *,
    session: AsyncSession = Depends(deps.get_session),
    course_id: UUID,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Delete a course.
    Allowed: Admin, or Owner (Teacher).
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await session.delete(course)
    await session.commit()
    return course

class EnrollmentRequest(SQLModel):
    user_email: str
    role: str = "student"

@router.post("/{course_id}/enroll")
async def enroll_user(
    course_id: UUID,
    enrollment: EnrollmentRequest,
    session: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(deps.get_current_user),
):
    """
    Enroll a user by email into a course.
    """
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    # Find user
    query = select(User).where(User.email == enrollment.user_email)
    result = await session.exec(query)
    user_to_enroll = result.first()
    
    if not user_to_enroll:
        raise HTTPException(status_code=404, detail="User email not found")
        
    # Check if already enrolled
    link = await session.get(UserCourseLink, (user_to_enroll.id, course_id))
    if link:
        return {"message": "User already enrolled"}
        
    # Create Link
    new_link = UserCourseLink(user_id=user_to_enroll.id, course_id=course_id, role=enrollment.role)
    session.add(new_link)
    await session.commit()
    
    return {"message": f"User {user_to_enroll.email} enrolled as {enrollment.role}"}

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
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    # Check permissions (Owner or Admin or TA in this course)
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    is_owner = course.owner_id == current_user.id
    
    if not (is_admin or is_owner):
        # Check if TA
        link = await session.get(UserCourseLink, (current_user.id, course_id))
        if not link or link.role != "ta":
             raise HTTPException(status_code=403, detail="Not enough permissions")

    # Query members
    query = (
        select(User, UserCourseLink.role)
        .join(UserCourseLink, User.id == UserCourseLink.user_id)
        .where(UserCourseLink.course_id == course_id)
    )
    results = await session.exec(query)
    
    members = []
    for user, role in results:
        members.append(CourseMember(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            role=role
        ))
        
    return members

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
    course = await session.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN] and course.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    link = await session.get(UserCourseLink, (user_id, course_id))
    if not link:
        raise HTTPException(status_code=404, detail="User is not enrolled in this course")
        
    link.role = member_update.role
    session.add(link)
    await session.commit()
    
    return {"message": "Role updated"}