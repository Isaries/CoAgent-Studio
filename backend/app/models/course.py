"""Backward compatibility aliases — all models moved to space.py."""

from .space import (
    Space as Course,
)
from .space import (
    SpaceBase as CourseBase,
)
from .space import (
    SpaceCreate as CourseCreate,
)
from .space import (
    SpaceMember as CourseMember,
)
from .space import (
    SpaceMemberUpdate as CourseMemberUpdate,
)
from .space import (
    SpaceRead as CourseRead,
)
from .space import (
    SpaceUpdate as CourseUpdate,
)
from .space import (
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
