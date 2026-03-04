"""
Unit tests for app.core.security — JWT tokens and password hashing.

All tests are pure-unit: no database, no network, no fixtures needed.
"""

from datetime import timedelta

import pytest
from jose import jwt, JWTError

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)

ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------


def test_create_access_token_returns_string():
    token = create_access_token(subject="user-123")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_contains_subject():
    subject = "test-user-abc"
    token = create_access_token(subject=subject)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == subject


def test_create_access_token_with_custom_expiry():
    """Token created with a custom timedelta should encode the expected expiry."""
    delta = timedelta(minutes=30)
    token = create_access_token(subject="exp-test", expires_delta=delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_create_access_token_default_expiry_exists():
    """Token without explicit expires_delta still carries an 'exp' claim."""
    token = create_access_token(subject="default-exp")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_create_access_token_expired_raises():
    """A token with a negative delta is already expired and should be rejected on decode."""
    token = create_access_token(subject="expired-user", expires_delta=timedelta(seconds=-1))
    with pytest.raises(JWTError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def test_create_access_token_wrong_key_raises():
    """Decoding with an incorrect secret must raise JWTError."""
    token = create_access_token(subject="wrong-key-user")
    with pytest.raises(JWTError):
        jwt.decode(token, "completely-wrong-secret", algorithms=[ALGORITHM])


def test_create_access_token_invalid_token_string_raises():
    """An arbitrary string is not a valid JWT and must raise JWTError."""
    with pytest.raises(JWTError):
        jwt.decode("not.a.valid.jwt", SECRET_KEY, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# create_refresh_token
# ---------------------------------------------------------------------------


def test_create_refresh_token_returns_string():
    token = create_refresh_token(subject="user-456")
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token_contains_type_refresh():
    token = create_refresh_token(subject="refresh-subject")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload.get("type") == "refresh"


def test_create_refresh_token_contains_subject():
    subject = "refresh-abc"
    token = create_refresh_token(subject=subject)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == subject


def test_create_refresh_token_with_custom_expiry():
    delta = timedelta(days=1)
    token = create_refresh_token(subject="refresh-exp", expires_delta=delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


# ---------------------------------------------------------------------------
# get_password_hash
# ---------------------------------------------------------------------------


def test_get_password_hash_returns_string():
    hashed = get_password_hash("my-password")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_get_password_hash_is_bcrypt():
    """bcrypt hashes always start with '$2b$' (or '$2a$')."""
    hashed = get_password_hash("bcrypt-check")
    assert hashed.startswith("$2")


def test_get_password_hash_different_each_time():
    """Bcrypt salts each hash — same password produces different hashes."""
    pw = "same-password"
    hash1 = get_password_hash(pw)
    hash2 = get_password_hash(pw)
    assert hash1 != hash2


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------


def test_verify_password_correct():
    password = "correct-horse-battery-staple"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_verify_password_wrong():
    hashed = get_password_hash("right-password")
    assert verify_password("wrong-password", hashed) is False


def test_verify_password_empty_string_fails():
    hashed = get_password_hash("non-empty")
    assert verify_password("", hashed) is False


def test_verify_password_case_sensitive():
    password = "CaseSensitive"
    hashed = get_password_hash(password)
    assert verify_password("casesensitive", hashed) is False
    assert verify_password("CaseSensitive", hashed) is True
