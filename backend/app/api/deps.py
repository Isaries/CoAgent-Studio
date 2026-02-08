from typing import Any, Callable, Optional

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param  # Moved up
from jose import jwt
from jose.exceptions import JWTError  # explicit import
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security  # Moved up
from app.core.config import settings  # Moved up
from app.core.db import get_session  # Moved up
from app.models.user import User, UserRole  # Moved up

logger = structlog.get_logger()
# Imports removed from here


def require_role(allowed_roles: list[str]) -> Callable[[User], Any]:
    """
    Dependency to ensure the user has one of the allowed roles.
    Super Admin is always allowed.
    """

    async def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return current_user

    return _checker


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        # try:
        #     with open("deps_trace.log", "a") as f:
        #         f.write("OAuth2PasswordBearerWithCookie called\n")
        # except:
        #      pass
        # Priority: Cookie > Header
        authorization: Optional[str] = request.cookies.get("access_token")
        if not authorization:
            authorization = request.headers.get("Authorization")
            if authorization:
                scheme, param = get_authorization_scheme_param(authorization)  # type: ignore
                if scheme.lower() == "bearer":
                    authorization = param

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return authorization


reusable_oauth2 = OAuth2PasswordBearerWithCookie(tokenUrl=f"{settings.API_V1_STR}/login/refresh")
reusable_oauth2_optional = OAuth2PasswordBearerWithCookie(
    tokenUrl=f"{settings.API_V1_STR}/login/refresh", auto_error=False
)


async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(reusable_oauth2),
) -> User:
    # try:
    #     with open("deps_trace.log", "a") as f:
    #         f.write("get_current_user called\n")
    # except:
    #     pass
    try:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
            token_data = payload.get("sub")
            if token_data is None:
                logger.warning("auth_failed", reason="missing_sub_in_token")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Could not validate credentials",
                )
        except (JWTError, ValidationError) as e:
            logger.warning("auth_failed", reason="jwt_validation_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            ) from None

        # In SQLModel for async, we use exec/one_or_none
        from uuid import UUID

        from sqlmodel import select

        try:
            user_id = UUID(token_data)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid token subject") from None

        query: Any = select(User).where(User.id == user_id)
        result = await session.exec(query)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Internal Auth Error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Internal Auth Error: {e!r}") from e


async def get_current_user_optional(
    session: AsyncSession = Depends(get_session),
    token: Optional[str] = Depends(reusable_oauth2_optional),
) -> Optional[User]:
    """
    Return the current user if token is valid.
    Return None if no token is present.
    Raise HTTPException if token is present but invalid (to trigger refresh logic if needed).
    """
    if not token:
        return None
    return await get_current_user(session=session, token=token)


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="The user doesn't have enough privileges")
    return current_user


async def get_current_active_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges (Super Admin required)"
        )
    return current_user
