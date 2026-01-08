"""Pydantic schemas for User and Tenant."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class TenantBase(BaseModel):
    """Base schema for Tenant."""

    name: str
    description: str | None = None


class TenantCreate(TenantBase):
    """Schema for creating a Tenant."""

    id: str


class Tenant(TenantBase):
    """Schema for Tenant response."""

    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base schema for User."""

    email: EmailStr
    full_name: str | None = None
    is_active: bool = True


class UserCreate(UserBase):
    """Schema for creating a User."""

    password: str
    tenant_id: str


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class User(UserBase):
    """Schema for User response."""

    id: str
    tenant_id: str
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for JWT token payload."""

    user_id: str | None = None
    tenant_id: str | None = None
