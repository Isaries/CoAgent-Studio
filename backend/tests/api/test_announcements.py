"""
Integration tests for Announcement CRUD endpoints.

URL prefix (from api.py): /api/v1/announcements

Routes tested:
  POST   /announcements/                       - create announcement
  GET    /announcements/?space_id={space_id}   - list announcements for a space
  GET    /announcements/{announcement_id}      - get single announcement
  PUT    /announcements/{announcement_id}      - update announcement (owner or admin)
  DELETE /announcements/{announcement_id}      - delete announcement (owner or admin)

Permission model:
  - SUPER_ADMIN / ADMIN can always create
  - Space owner can create
  - Student (not owner, not TA) gets 403 on create
  - Only the author or admin can update/delete
"""

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.space import Space
from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_space(db_session: AsyncSession, owner_id) -> Space:
    """Seed a Space owned by owner_id and return it."""
    space = Space(title="Announcement Test Space", owner_id=owner_id)
    db_session.add(space)
    await db_session.flush()
    await db_session.refresh(space)
    return space


def _announcement_payload(space_id: str) -> dict:
    return {
        "title": "Important Notice",
        "content": "Please read the updated syllabus.",
        "space_id": space_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio()
async def test_create_announcement(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Super admin can create an announcement for a space."""
    space = await _create_space(db_session, mock_superuser.id)

    response = await superuser_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=_announcement_payload(str(space.id)),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Important Notice"
    assert data["content"] == "Please read the updated syllabus."
    assert data["space_id"] == str(space.id)
    assert data["author_id"] == str(mock_superuser.id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio()
async def test_list_announcements(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Authenticated user can list announcements for a space by passing space_id as query param."""
    space = await _create_space(db_session, mock_superuser.id)

    # Create two announcements
    await superuser_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json={**_announcement_payload(str(space.id)), "title": "Notice A"},
    )
    await superuser_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json={**_announcement_payload(str(space.id)), "title": "Notice B"},
    )

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/announcements/",
        params={"space_id": str(space.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    titles = [a["title"] for a in data]
    assert "Notice A" in titles
    assert "Notice B" in titles


@pytest.mark.asyncio()
async def test_get_announcement(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """Can retrieve a specific announcement by ID."""
    space = await _create_space(db_session, mock_superuser.id)

    create_resp = await superuser_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=_announcement_payload(str(space.id)),
    )
    assert create_resp.status_code == 200
    announcement_id = create_resp.json()["id"]

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/announcements/{announcement_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == announcement_id
    assert data["title"] == "Important Notice"


@pytest.mark.asyncio()
async def test_get_announcement_not_found(superuser_client: AsyncClient):
    """Requesting a non-existent announcement returns 404."""
    response = await superuser_client.get(
        f"{settings.API_V1_STR}/announcements/00000000-0000-0000-0000-000000000099"
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_update_announcement_as_owner(
    teacher_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher,
):
    """The announcement's author can update it."""
    # Teacher owns the space
    space = await _create_space(db_session, mock_teacher.id)

    create_resp = await teacher_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=_announcement_payload(str(space.id)),
    )
    assert create_resp.status_code == 200
    announcement_id = create_resp.json()["id"]

    update_payload = {
        "title": "Updated Notice",
        "content": "Updated content here.",
    }
    response = await teacher_client.put(
        f"{settings.API_V1_STR}/announcements/{announcement_id}",
        json=update_payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == announcement_id
    assert data["title"] == "Updated Notice"
    assert data["content"] == "Updated content here."


@pytest.mark.asyncio()
async def test_delete_announcement_as_owner(
    teacher_client: AsyncClient,
    db_session: AsyncSession,
    mock_teacher,
):
    """The announcement's author can delete it; subsequent GET returns 404."""
    space = await _create_space(db_session, mock_teacher.id)

    create_resp = await teacher_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=_announcement_payload(str(space.id)),
    )
    assert create_resp.status_code == 200
    announcement_id = create_resp.json()["id"]

    delete_resp = await teacher_client.delete(
        f"{settings.API_V1_STR}/announcements/{announcement_id}"
    )
    assert delete_resp.status_code == 204

    get_resp = await teacher_client.get(
        f"{settings.API_V1_STR}/announcements/{announcement_id}"
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio()
async def test_student_cannot_create_announcement(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
    mock_student,
):
    """A student who is not the space owner and not a TA gets 403 on create."""
    # Space owned by superuser; student has no link
    space = await _create_space(db_session, mock_superuser.id)

    response = await student_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=_announcement_payload(str(space.id)),
    )
    assert response.status_code == 403


@pytest.mark.asyncio()
async def test_non_author_cannot_update_announcement(
    student_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """A user who is not the author and not admin gets 403 when trying to update."""
    space = await _create_space(db_session, mock_superuser.id)

    # Seed the announcement directly into the DB (avoid auth override conflict)
    from app.models.announcement import Announcement
    announcement = Announcement(
        title="Important Notice",
        content="Please read the updated syllabus.",
        space_id=space.id,
        author_id=mock_superuser.id,
    )
    db_session.add(announcement)
    await db_session.flush()
    await db_session.refresh(announcement)
    announcement_id = str(announcement.id)

    # Student tries to update — should be 403
    response = await student_client.put(
        f"{settings.API_V1_STR}/announcements/{announcement_id}",
        json={"title": "Hacked Title"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio()
async def test_announcement_requires_auth(client: AsyncClient):
    """Unauthenticated requests are rejected with 401."""
    response = await client.get(
        f"{settings.API_V1_STR}/announcements/",
        params={"space_id": "00000000-0000-0000-0000-000000000001"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio()
async def test_create_announcement_for_nonexistent_space(
    superuser_client: AsyncClient,
):
    """Creating an announcement for a space that doesn't exist returns 404."""
    payload = {
        "title": "Ghost Notice",
        "content": "This space doesn't exist.",
        "space_id": "00000000-0000-0000-0000-000000000099",
    }
    response = await superuser_client.post(
        f"{settings.API_V1_STR}/announcements/",
        json=payload,
    )
    assert response.status_code == 404


@pytest.mark.asyncio()
async def test_list_announcements_empty_for_space(
    superuser_client: AsyncClient,
    db_session: AsyncSession,
    mock_superuser,
):
    """A space with no announcements returns an empty list."""
    space = await _create_space(db_session, mock_superuser.id)

    response = await superuser_client.get(
        f"{settings.API_V1_STR}/announcements/",
        params={"space_id": str(space.id)},
    )
    assert response.status_code == 200
    assert response.json() == []
