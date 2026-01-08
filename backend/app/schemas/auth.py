"""Authentication schemas."""
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    """Token response."""

    access_token: str
    token_type: str
    tenant_id: str


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class UserCreate(BaseModel):
    """User creation request."""

    email: EmailStr
    password: str
    full_name: str | None = None
    tenant_id: str


class UserResponse(BaseModel):
    """User response."""

    id: int
    email: str
    full_name: str | None
    tenant_id: str
    is_active: bool

    class Config:
        """Pydantic config."""

        from_attributes = True


class TenantCreate(BaseModel):
    """Tenant creation request."""

    tenant_id: str
    name: str
    description: str | None = None


class TenantResponse(BaseModel):
    """Tenant response."""

    id: int
    tenant_id: str
    name: str
    description: str | None
    is_active: bool

    class Config:
        """Pydantic config."""

        from_attributes = True
