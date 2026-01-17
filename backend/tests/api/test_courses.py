import pytest
from httpx import AsyncClient

from app.core.config import settings

# Integration Tests for Courses


@pytest.mark.asyncio()
async def test_create_course_as_teacher(teacher_client: AsyncClient):
    payload = {"title": "Test Course 101", "description": "Integration testing course"}
    response = await teacher_client.post(f"{settings.API_V1_STR}/courses/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == payload["title"]
    assert "id" in data
    assert "owner_id" in data


@pytest.mark.asyncio()
async def test_create_course_permission_denied(student_client: AsyncClient):
    """
    Verify that a student cannot create a course.
    """
    payload = {"title": "Hacker Course", "description": "Should not be allowed"}
    response = await student_client.post(f"{settings.API_V1_STR}/courses/", json=payload)
    # Expect 403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio()
async def test_get_courses(teacher_client: AsyncClient):
    # First create one
    payload = {"title": "My Course", "description": "desc"}
    create_res = await teacher_client.post(f"{settings.API_V1_STR}/courses/", json=payload)
    assert create_res.status_code == 200

    response = await teacher_client.get(f"{settings.API_V1_STR}/courses/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c["title"] == "My Course" for c in data)
