"""Pydantic schemas for inventory."""

from pydantic import BaseModel


class InventoryBase(BaseModel):
    """Base inventory schema."""

    userid: int
    itemid: int


class InventoryCreate(InventoryBase):
    """Schema for creating an inventory entry."""

    pass


class Inventory(InventoryBase):
    """Schema for inventory response."""

    id: int

    class Config:
        from_attributes = True
