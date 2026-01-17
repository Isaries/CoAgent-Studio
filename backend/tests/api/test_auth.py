import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole


# Use the base 'client' fixture which has DB session override but NO Auth override
@pytest.mark.asyncio()
async def test_login_access_token(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a real user in the test DB
    password = "testpassword123"
    hashed = get_password_hash(password)
    user = User(
        email="auth_test@example.com",
        username="authtester",
        hashed_password=hashed,
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 2. Try to login
    login_data = {"username": "auth_test@example.com", "password": password}

    # Note: OAuth2PasswordRequestForm expects form data, not JSON
    response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    # 3. Verify
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio()
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a real user
    password = "correctpassword"
    user = User(
        email="wrong_pass@example.com",
        username="wrongpass",
        hashed_password=get_password_hash(password),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    # 2. Try to login with wrong password
    login_data = {"username": "wrong_pass@example.com", "password": "wrongpassword"}

    response = await client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)

    # 3. Verify
    assert response.status_code == 400
