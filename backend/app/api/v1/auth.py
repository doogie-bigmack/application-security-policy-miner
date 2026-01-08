"""Authentication endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TenantCreate,
    TenantResponse,
    Token,
    UserCreate,
    UserResponse,
)

router = APIRouter()


@router.post("/login", response_model=Token)
def login(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    """Authenticate user and return JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()

    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    access_token = create_access_token(data={"sub": user.email, "tenant_id": user.tenant_id})

    return Token(
        access_token=access_token,
        token_type="bearer",
        tenant_id=user.tenant_id,
    )


@router.post("/tenants/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant: TenantCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Tenant:
    """Create a new tenant."""
    # Check if tenant_id already exists
    existing_tenant = db.query(Tenant).filter(Tenant.tenant_id == tenant.tenant_id).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant ID already exists",
        )

    db_tenant = Tenant(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        description=tenant.description,
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Create a new user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if tenant exists
    tenant = db.query(Tenant).filter(Tenant.tenant_id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not found",
        )

    db_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        tenant_id=user.tenant_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/tenants/", response_model=list[TenantResponse])
def list_tenants(
    db: Annotated[Session, Depends(get_db)],
) -> list[Tenant]:
    """List all tenants."""
    return db.query(Tenant).all()
