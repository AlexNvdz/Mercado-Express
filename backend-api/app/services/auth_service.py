"""Registration, login and token refresh business logic."""

import uuid

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.exceptions import AuthenticationError, ConflictError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair, UserRegister


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def register(self, data: UserRegister, *, role: UserRole = UserRole.CUSTOMER) -> User:
        existing = await self.users.get_by_email(data.email)
        if existing is not None:
            raise ConflictError(f"Email '{data.email}' is already registered.")

        user = await self.users.create(
            {
                "email": data.email.lower(),
                "hashed_password": hash_password(data.password),
                "full_name": data.full_name,
                "phone": data.phone,
                "role": role,
            }
        )
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password.")
        if not user.is_active:
            raise AuthenticationError("User account is disabled.")
        return user

    def issue_tokens(self, user: User) -> TokenPair:
        return TokenPair(
            access_token=create_access_token(str(user.id), user.role.value),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh_access_token(self, refresh_token: str) -> str:
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired refresh token.") from exc

        if payload.get("type") != TokenType.REFRESH.value:
            raise AuthenticationError("Token is not a refresh token.")

        user = await self.users.get(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("User no longer exists or is disabled.")

        return create_access_token(str(user.id), user.role.value)
