"""Authentication dependencies for FastAPI endpoints."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token, get_user_by_id

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    token_data = decode_access_token(token)

    if token_data is None or token_data.user_id is None:
        logger.warning("Invalid token")
        raise credentials_exception

    user = get_user_by_id(db, user_id=token_data.user_id)
    if user is None:
        logger.warning("User not found", user_id=token_data.user_id)
        raise credentials_exception

    if not user.is_active:
        logger.warning("Inactive user", user_id=user.id)
        raise HTTPException(status_code=400, detail="Inactive user")

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get the current active user."""
    return current_user


def get_tenant_id(current_user: Annotated[User, Depends(get_current_user)]) -> str:
    """Get the current user's tenant ID."""
    return current_user.tenant_id
