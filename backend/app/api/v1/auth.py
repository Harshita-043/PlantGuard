"""Registration, bearer-token login, and authenticated identity endpoint."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    AuthenticationConfigurationError,
    InvalidAccessToken,
    create_access_token,
    decode_access_token,
    get_jwt_signing_key,
    perform_dummy_password_verification,
    verify_password,
    hash_password,
)
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse


router = APIRouter(prefix="/auth")
_bearer_scheme = HTTPBearer(auto_error=False)
_INVALID_CREDENTIALS = "Invalid email or password"


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve a user from a valid, unexpired bearer access token."""
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable because token signing is not configured",
        ) from exc
    except InvalidAccessToken:
        raise _unauthorized() from None

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> User:
    """Create an account with a normalized email and Argon2id password hash."""
    if not 12 <= len(request.password.get_secret_value()) <= 128:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be between 12 and 128 characters",
        )
    email = str(request.email)
    existing = db.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to register an account with the supplied email",
        )

    user = User(email=email, password_hash=hash_password(request.password.get_secret_value()))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to register an account with the supplied email",
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Verify credentials and issue a short-lived signed bearer token."""
    if not 1 <= len(request.password.get_secret_value()) <= 128:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Password must be between 1 and 128 characters",
        )
    try:
        get_jwt_signing_key(settings)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is unavailable because token signing is not configured",
        ) from exc

    email = str(request.email)
    user = db.scalar(select(User).where(User.email == email))
    password = request.password.get_secret_value()
    if user is None:
        perform_dummy_password_verification(password)
        raise _unauthorized()
    if not verify_password(password, user.password_hash):
        raise _unauthorized()

    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
def current_identity(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Return the current authenticated account without exposing its password hash."""
    return user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS,
        headers={"WWW-Authenticate": "Bearer"},
    )
