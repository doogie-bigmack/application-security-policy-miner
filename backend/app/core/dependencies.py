"""FastAPI dependencies for authentication and authorization."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    """Get the current authenticated user or None if not authenticated."""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    email: str | None = payload.get("sub")
    if email is None:
        return None

    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return None

    return user


async def require_auth(
    current_user: Annotated[User | None, Depends(get_current_user)],
) -> User:
    """Require authentication - raises 401 if not authenticated."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


async def get_tenant_id(
    current_user: Annotated[User | None, Depends(get_current_user)],
) -> str | None:
    """Get the current user's tenant_id or None if not authenticated."""
    if current_user is None:
        return None
    return current_user.tenant_id


async def get_current_user_email(
    current_user: Annotated[User | None, Depends(get_current_user)],
) -> str | None:
    """Get the current user's email or None if not authenticated."""
    if current_user is None:
        return None
    return current_user.email
