"""Pydantic schemas for users."""

from pydantic import BaseModel


class UserBase(BaseModel):
    """Base user schema."""

    gold: int = 100


class UserCreate(UserBase):
    """Schema for creating a user."""

    pass


class User(UserBase):
    """Schema for user response."""

    userid: int

    class Config:
        from_attributes = True
