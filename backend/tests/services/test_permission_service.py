from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.models.course import Course
from app.models.room import Room
from app.models.user import User, UserRole
from app.services.permission_service import permission_service


@pytest.mark.asyncio()
async def test_admin_permissions():
    user = User(id=uuid4(), role=UserRole.ADMIN)
    session = AsyncMock()

    # Check random room
    room = Room(id=uuid4(), course_id=uuid4())
    assert await permission_service.check(user, "read", room, session) is True
    assert await permission_service.check(user, "delete", room, session) is True


@pytest.mark.asyncio()
async def test_course_owner_permissions():
    user = User(id=uuid4(), role=UserRole.TEACHER)
    course = Course(id=uuid4(), owner_id=user.id)
    room = Room(id=uuid4(), course_id=course.id)

    session = AsyncMock()
    # Mocking session.get calls
    # If checking room, it fetches course.
    session.get.return_value = course

    # Check Room access
    assert await permission_service.check(user, "read", room, session) is True
    assert await permission_service.check(user, "delete", room, session) is True

    # Check Course access
    assert await permission_service.check(user, "update", course, session) is True


@pytest.mark.asyncio()
async def test_unauthorized_access():
    user = User(id=uuid4(), role=UserRole.STUDENT)
    other_user = User(id=uuid4(), role=UserRole.TEACHER)
    course = Course(id=uuid4(), owner_id=other_user.id)
    room = Room(id=uuid4(), course_id=course.id)

    session = AsyncMock()
    session.get.return_value = course

    # Mock exec for TA check (returns nothing)
    mock_result = Mock()
    mock_result.first.return_value = None
    session.exec.return_value = mock_result

    assert await permission_service.check(user, "read", room, session) is False
