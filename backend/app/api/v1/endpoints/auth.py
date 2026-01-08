"""Authentication API endpoints."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.schemas.user import Token, User, UserCreate, UserLogin
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_tenant,
    create_user,
    get_tenant_by_id,
    get_user_by_email,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(
    user_create: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Register a new user."""
    # Check if user already exists
    existing_user = get_user_by_email(db, email=user_create.email)
    if existing_user:
        logger.warning("User already exists", email=user_create.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if tenant exists
    tenant = get_tenant_by_id(db, tenant_id=user_create.tenant_id)
    if not tenant:
        logger.warning("Tenant not found", tenant_id=user_create.tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Create user
    user = create_user(db, user_create=user_create)
    logger.info("User registered", user_id=user.id, email=user.email)
    return user


@router.post("/login", response_model=Token)
async def login(
    user_login: UserLogin,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Login and get access token."""
    user = authenticate_user(db, email=user_login.email, password=user_login.password)
    if not user:
        logger.warning("Invalid credentials", email=user_login.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Inactive user login attempt", user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "tenant_id": user.tenant_id}
    )

    logger.info("User logged in", user_id=user.id, email=user.email)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=User)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """Get current user info."""
    return current_user


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant_endpoint(
    name: str,
    description: str | None = None,
    db: Session = Depends(get_db),
):
    """Create a new tenant (for testing/demo purposes)."""
    tenant_id = str(uuid.uuid4())
    tenant = create_tenant(db, tenant_id=tenant_id, name=name, description=description)
    logger.info("Tenant created", tenant_id=tenant.id, name=tenant.name)
    return {
        "id": tenant.id,
        "name": tenant.name,
        "description": tenant.description,
        "is_active": tenant.is_active,
        "created_at": tenant.created_at.isoformat(),
    }
