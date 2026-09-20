from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Alphanumeric username")
    email: Optional[str] = Field(None, max_length=255, description="User email address")
    role: UserRole = Field(default=UserRole.VIEWER, description="Role-based access level")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128, description="User password")


class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRole(BaseModel):
    role: UserRole


class UserUpdatePassword(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    role: str
    exp: int
    iat: int
    jti: Optional[str] = None
