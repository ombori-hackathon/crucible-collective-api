"""Pydantic schemas for items."""

from typing import Optional

from pydantic import BaseModel

from app.models.item import ItemType, Rarity


class ItemBase(BaseModel):
    """Base item schema with common fields."""

    name: str
    type: ItemType = ItemType.material
    stat: Optional[str] = None
    stat_value: int = 0
    gold_value: int = 1
    description: Optional[str] = None
    rarity: Rarity = Rarity.Material


class ItemCreate(ItemBase):
    """Schema for creating an item."""

    pass


class Item(ItemBase):
    """Schema for item response."""

    itemid: int
    base64: Optional[str] = None

    class Config:
        from_attributes = True
