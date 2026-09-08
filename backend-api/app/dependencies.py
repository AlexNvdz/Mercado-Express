"""Shared FastAPI dependencies: DB session re-export, current user resolution,
role-based authorization, and pagination params."""

import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenType, decode_token
from app.db.session import get_db
from app.exceptions import AuthenticationError, AuthorizationError
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Could not validate credentials.") from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise AuthenticationError("Token is not an access token.")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject claim.")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User no longer exists.")
    if not user.is_active:
        raise AuthenticationError("User account is disabled.")
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory: raises AuthorizationError unless current user has
    one of `roles`. Adding a new role later only means passing it here."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise AuthorizationError(
                f"Role '{current_user.role}' is not permitted to perform this action."
            )
        return current_user

    return _check


require_admin = require_roles(UserRole.ADMIN)
require_staff = require_roles(UserRole.ADMIN, UserRole.EMPLOYEE)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
