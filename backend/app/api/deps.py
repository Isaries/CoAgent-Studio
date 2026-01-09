from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.db import get_session
from app.models.user import User


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        # Priority: Cookie > Header
        authorization: str = request.cookies.get("access_token")
        if not authorization:
             authorization = request.headers.get("Authorization")
             if authorization:
                 scheme, param = get_authorization_scheme_param(authorization) # type: ignore
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

from fastapi.security.utils import get_authorization_scheme_param

reusable_oauth2 = OAuth2PasswordBearerWithCookie(
    tokenUrl=f"{settings.API_V1_STR}/login/refresh"
)

async def get_current_user(
    session: AsyncSession = Depends(get_session),
    token: str = Depends(reusable_oauth2),
) -> User:
    try:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            token_data = payload.get("sub")
            if token_data is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Could not validate credentials",
                )
        except (jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )

        # In SQLModel for async, we use exec/one_or_none
        from uuid import UUID

        from sqlmodel import select
        try:
            user_id = UUID(token_data)
        except ValueError:
             raise HTTPException(status_code=403, detail="Invalid token subject")

        query = select(User).where(User.id == user_id)
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Auth Error: {e!s}")

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_current_active_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges (Super Admin required)"
        )
    return current_user
