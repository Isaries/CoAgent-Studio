from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import structlog
from cryptography.fernet import Fernet, InvalidToken
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = settings.ALGORITHM


def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# Encryption for API Keys

try:
    cipher_suite = Fernet(settings.ENCRYPTION_KEY)
except Exception as _e:
    logger.error("fernet_key_invalid", error=str(_e),
                 hint="ENCRYPTION_KEY must be a valid 32-byte base64-encoded Fernet key. "
                      "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
    raise SystemExit("Invalid ENCRYPTION_KEY – cannot start application.") from _e


def encrypt_api_key(api_key: str) -> Optional[str]:
    if not api_key:
        return None
    return cipher_suite.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    if not encrypted_key:
        return None
    try:
        return cipher_suite.decrypt(encrypted_key.encode()).decode()
    except (InvalidToken, Exception) as e:
        logger.warning("decrypt_api_key_failed", error=str(e),
                       hint="Key may be legacy plaintext or encrypted with a different key.")
        return None


def mask_api_key(encrypted_key: str) -> Optional[str]:
    """
    Returns masked key: sk******89 or sk****** (if short)
    """
    if not encrypted_key:
        return None

    # Decrypt first
    plain = decrypt_api_key(encrypted_key)
    if not plain:
        return "****"

    if len(plain) <= 4:
        return "****"

    prefix = plain[:2]
    suffix = plain[-2:]
    return f"{prefix}******{suffix}"
