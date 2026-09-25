"""Password hashing and signed access-token helpers."""

import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jwt import InvalidTokenError
from pydantic import SecretStr

from app.core.config import Settings, settings


_PASSWORD_HASHER = PasswordHasher()
_JWT_ALGORITHM = "HS256"


class AuthenticationConfigurationError(RuntimeError):
    """Raised when required signing configuration is absent or unsafe."""


class InvalidAccessToken(ValueError):
    """Raised when a bearer token is invalid, expired, or has invalid claims."""


def hash_password(password: str) -> str:
    """Return an Argon2id password hash."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing details about malformed stored hashes."""
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    """Create a process-local dummy hash to keep unknown-user logins costly."""
    return hash_password(secrets.token_urlsafe(32))


def perform_dummy_password_verification(password: str) -> None:
    """Perform equivalent password-hash work for an unknown identity."""
    verify_password(password, _dummy_password_hash())


def get_jwt_signing_key(configuration: Settings = settings) -> str:
    configured_key: SecretStr | None = configuration.JWT_SECRET_KEY
    if configured_key is None:
        raise AuthenticationConfigurationError("JWT_SECRET_KEY is not configured")
    key = configured_key.get_secret_value()
    if len(key.encode("utf-8")) < 32:
        raise AuthenticationConfigurationError("JWT_SECRET_KEY must contain at least 32 bytes")
    return key


def create_access_token(user_id: UUID, configuration: Settings = settings) -> str:
    key = get_jwt_signing_key(configuration)
    now = datetime.now(UTC)
    expires_in = configuration.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "token_type": "access",
        },
        key,
        algorithm=_JWT_ALGORITHM,
    )


def decode_access_token(token: str, configuration: Settings = settings) -> UUID:
    key = get_jwt_signing_key(configuration)
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["sub", "iat", "exp", "token_type"]},
        )
        if payload.get("token_type") != "access":
            raise InvalidAccessToken
        return UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken from exc
