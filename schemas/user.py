from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    display_name: str
    email: EmailStr
    username: str
    password: str
    confirm_password: str

    @field_validator("display_name")
    @classmethod
    def display_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name is required.")
        if len(v) > 100:
            raise ValueError("Display name must be 100 characters or fewer.")
        return v

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Email is required.")
        return v

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Username is required.")
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(v) > 50:
            raise ValueError("Username must be 50 characters or fewer.")
        if not v.isalnum() and not all(c.isalnum() or c in ("_", "-") for c in v):
            raise ValueError("Username may only contain letters, numbers, underscores, and hyphens.")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("Password must be 128 characters or fewer.")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        password = info.data.get("password")
        if password is not None and v != password:
            raise ValueError("Passwords do not match.")
        return v


class UserLogin(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Username is required.")
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required.")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str
    role: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserProfile(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("display_name")
    @classmethod
    def display_name_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Display name cannot be empty.")
        if len(v) > 100:
            raise ValueError("Display name must be 100 characters or fewer.")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            raise ValueError("Email cannot be empty.")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("current_password")
    @classmethod
    def current_password_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Current password is required.")
        return v

    @field_validator("new_password")
    @classmethod
    def new_password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters.")
        if len(v) > 128:
            raise ValueError("New password must be 128 characters or fewer.")
        return v

    @field_validator("confirm_new_password")
    @classmethod
    def new_passwords_match(cls, v: str, info) -> str:
        new_password = info.data.get("new_password")
        if new_password is not None and v != new_password:
            raise ValueError("New passwords do not match.")
        return v