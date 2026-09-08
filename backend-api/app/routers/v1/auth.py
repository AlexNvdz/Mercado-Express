from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessToken,
    RefreshRequest,
    TokenPair,
    UserOut,
    UserRegister,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new customer account. Staff/admin accounts are provisioned
    separately (not self-service)."""
    service = AuthService(db)
    return await service.register(data)


@router.post("/login", response_model=TokenPair)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """OAuth2-compatible login. `username` field carries the email address."""
    service = AuthService(db)
    user = await service.authenticate(form_data.username, form_data.password)
    return service.issue_tokens(user)


@router.post("/refresh", response_model=AccessToken)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessToken:
    service = AuthService(db)
    access_token = await service.refresh_access_token(data.refresh_token)
    return AccessToken(access_token=access_token)


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
