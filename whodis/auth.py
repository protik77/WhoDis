"""Authentication utilities."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from whodis.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    ALGORITHM,
    SECRET_KEY,
)
from whodis.models import APIKey, SessionLocal, User, get_db

security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(UTC).replace(tzinfo=None) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return str(encoded_jwt)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return cast(dict | None, payload)
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a new secure API key."""
    return "whodis_" + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    return hash_api_key(key) == key_hash


def get_current_user_from_session(request: Request, db: Session) -> User | None:
    """Get current user from session cookie."""
    token = request.cookies.get("session")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = db.query(User).filter(User.username == username).first()
    return user


def get_current_user_from_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """Get current user from API key header."""
    if not credentials:
        return None

    key = credentials.credentials
    key_hash = hash_api_key(key)

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
        .first()
    )

    if not api_key:
        return None

    # Update last used
    api_key.last_used_at = datetime.now(UTC).replace(tzinfo=None)  # type: ignore[assignment]
    db.commit()

    return cast(User | None, api_key.created_by_user)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    api_user: User | None = Depends(get_current_user_from_api_key),
) -> User | None:
    """Get current user from either session or API key."""
    if api_user:
        return api_user
    return get_current_user_from_session(request, db)


def require_auth(
    request: Request, user: User | None = Depends(get_current_user)
) -> User:
    """Dependency to require authentication."""
    if not user:
        # Check if it's a browser request
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            from fastapi.responses import RedirectResponse

            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/login"},
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """Dependency to require admin access."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_api_key(
    user: User | None = Depends(get_current_user_from_api_key),
) -> User:
    """Dependency to require API key authentication."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def create_default_admin() -> None:
    """Create default admin user if no users exist."""
    db = SessionLocal()
    try:
        # Check if any users exist
        user_count = db.query(User).count()
        if user_count == 0:
            # Create default admin
            admin = User(
                username=ADMIN_USERNAME,
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print(f"Created default admin user: {ADMIN_USERNAME}")
    finally:
        db.close()
