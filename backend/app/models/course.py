"""Backward compatibility aliases — all models moved to space.py."""

from .space import (
    Space as Course,
    SpaceBase as CourseBase,
    SpaceCreate as CourseCreate,
    SpaceRead as CourseRead,
    SpaceUpdate as CourseUpdate,
    SpaceMember as CourseMember,
    SpaceMemberUpdate as CourseMemberUpdate,
    UserSpaceLink as UserCourseLink,
)

__all__ = [
    "Course",
    "CourseBase",
    "CourseCreate",
    "CourseRead",
    "CourseUpdate",
    "CourseMember",
    "CourseMemberUpdate",
    "UserCourseLink",
]
