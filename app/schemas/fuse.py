"""Pydantic schemas for fuse endpoint."""

from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.item import Item


class FuseRequest(BaseModel):
    """Request schema for fusing items."""

    userid: int = Field(description="The user's ID")
    itemids: list[int] = Field(
        description="List of item IDs to fuse (must be exactly 2)",
        min_length=2,
        max_length=2,
    )


class FuseResponse(BaseModel):
    """Response schema for fuse endpoint."""

    item: Item = Field(description="The newly created fused item")
    alchemist_says: str = Field(description="The alchemist's description of the fusion")
    critic_says: Optional[str] = Field(
        default=None, description="The critic's evaluation of the item"
    )
    critic_score: float = Field(
        description="The critic's score (0.0-1.0)", ge=0.0, le=1.0
    )
