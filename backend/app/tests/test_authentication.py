"""Authentication API tests backed by an isolated in-memory database."""

from datetime import UTC, datetime, timedelta
import logging
import secrets

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.auth import get_db
from app.core.config import settings
from app.core.database import Base
from app.main import app
from app.models.user import User


_PASSWORD = "correct horse battery staple"


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", SecretStr(secrets.token_urlsafe(48)))
    monkeypatch.setattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        with test_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, test_sessions
    app.dependency_overrides.clear()
    engine.dispose()


def _register(client, email="Person@example.com", password=_PASSWORD):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def test_registration_hashes_password_and_returns_only_public_user_fields(auth_client):
    client, sessions = auth_client
    response = _register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "person@example.com"
    assert set(body) == {"id", "email", "created_at", "updated_at"}
    with sessions() as db:
        user = db.scalar(select(User).where(User.email == "person@example.com"))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert user.password_hash != _PASSWORD
        assert _PASSWORD not in user.password_hash


@pytest.mark.parametrize(
    ("email", "password"),
    [("not-an-email", _PASSWORD), ("person@example.com", "short")],
)
def test_registration_rejects_invalid_input_without_echoing_password(auth_client, email, password):
    client, _sessions = auth_client
    response = _register(client, email, password)
    assert response.status_code == 422
    assert password not in response.text


def test_registration_rejects_duplicate_normalized_email(auth_client):
    client, _sessions = auth_client
    assert _register(client).status_code == 201
    duplicate = _register(client, "PERSON@EXAMPLE.COM")
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Unable to register an account with the supplied email"
    assert "password_hash" not in duplicate.text


def test_login_issues_short_lived_bearer_token_without_user_secrets(auth_client):
    client, _sessions = auth_client
    _register(client)
    response = client.post("/api/v1/auth/login", json={"email": "PERSON@example.com", "password": _PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert body["access_token"]
    assert "password" not in response.text
    assert "password_hash" not in response.text


def test_wrong_password_and_unknown_email_have_same_safe_failure(auth_client):
    client, _sessions = auth_client
    _register(client)
    wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "person@example.com", "password": "not the password"}
    )
    unknown_user = client.post(
        "/api/v1/auth/login", json={"email": "unknown@example.com", "password": "not the password"}
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"detail": "Invalid email or password"}


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bearer malformed-token"}, {"Authorization": "Basic abc"}],
)
def test_me_rejects_missing_or_malformed_authentication(auth_client, headers):
    client, _sessions = auth_client
    response = client.get("/api/v1/auth/me", headers=headers or {})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_resolves_authenticated_identity_without_password_hash(auth_client):
    client, _sessions = auth_client
    registered = _register(client).json()
    token = client.post(
        "/api/v1/auth/login", json={"email": registered["email"], "password": _PASSWORD}
    ).json()["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == registered["id"]
    assert response.json()["email"] == registered["email"]
    assert "password_hash" not in response.text


def test_me_rejects_expired_token(auth_client):
    client, _sessions = auth_client
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "token_type": "access",
        },
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_me_rejects_bad_signature_and_invalid_subject(auth_client):
    client, _sessions = auth_client
    now = datetime.now(UTC)
    claims = {
        "sub": "00000000-0000-0000-0000-000000000001",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "token_type": "access",
    }
    wrong_signature = jwt.encode(claims, secrets.token_urlsafe(48), algorithm="HS256")
    invalid_subject = jwt.encode(
        {**claims, "sub": "not-a-user-uuid"},
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm="HS256",
    )

    for token in (wrong_signature, invalid_subject):
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}


def test_auth_failures_do_not_log_passwords_or_tokens(auth_client, caplog):
    client, _sessions = auth_client
    secret_password = "this-password-must-not-be-logged"
    secret_token = "this-token-must-not-be-logged"
    with caplog.at_level(logging.DEBUG):
        login_response = client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": secret_password}
        )
        client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {secret_token}"})

    assert login_response.status_code == 401
    assert secret_password not in caplog.text
    assert secret_token not in caplog.text


def test_jwt_signing_secret_is_not_exposed_in_auth_responses_or_logs(auth_client, caplog):
    client, _sessions = auth_client
    signing_secret = settings.JWT_SECRET_KEY.get_secret_value()

    with caplog.at_level(logging.DEBUG):
        registration = _register(client)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "person@example.com", "password": _PASSWORD},
        )
        identity = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

    assert registration.status_code == 201
    assert login.status_code == identity.status_code == 200
    assert signing_secret not in registration.text
    assert signing_secret not in login.text
    assert signing_secret not in identity.text
    assert signing_secret not in caplog.text


def test_login_fails_clearly_when_jwt_secret_is_not_configured(auth_client, monkeypatch):
    client, _sessions = auth_client
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", None)
    response = client.post("/api/v1/auth/login", json={"email": "person@example.com", "password": _PASSWORD})
    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is unavailable because token signing is not configured"}


def test_authenticated_identity_fails_clearly_when_jwt_secret_is_not_configured(auth_client, monkeypatch):
    client, _sessions = auth_client
    _register(client)
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": _PASSWORD},
    ).json()["access_token"]
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", None)

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is unavailable because token signing is not configured"}
