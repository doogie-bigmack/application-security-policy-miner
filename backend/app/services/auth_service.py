"""Authentication service for user login and JWT token management."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import Tenant, User
from app.schemas.user import TokenData, UserCreate

logger = logging.getLogger(__name__)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData | None:
    """Decode and verify a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        tenant_id: str | None = payload.get("tenant_id")
        if user_id is None:
            return None
        return TokenData(user_id=user_id, tenant_id=tenant_id)
    except JWTError:
        logger.warning("JWT decode error", exc_info=True)
        return None


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_create.password)
    db_user = User(
        id=str(uuid.uuid4()),
        email=user_create.email,
        hashed_password=hashed_password,
        full_name=user_create.full_name,
        is_active=user_create.is_active,
        tenant_id=user_create.tenant_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info("User created", user_id=db_user.id, email=db_user.email)
    return db_user


def create_tenant(db: Session, tenant_id: str, name: str, description: str | None = None) -> Tenant:
    """Create a new tenant."""
    db_tenant = Tenant(
        id=tenant_id,
        name=name,
        description=description,
    )
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    logger.info("Tenant created", tenant_id=db_tenant.id, name=db_tenant.name)
    return db_tenant


def get_user_by_id(db: Session, user_id: str) -> User | None:
    """Get a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def get_tenant_by_id(db: Session, tenant_id: str) -> Tenant | None:
    """Get a tenant by ID."""
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()
