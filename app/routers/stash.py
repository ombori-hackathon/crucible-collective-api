"""Stash endpoint for viewing inventory."""

from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import get_logger
from app.models import Inventory, User
from app.models.item import ItemType, Rarity

logger = get_logger(__name__)

router = APIRouter(tags=["stash"])

# Rarity level for sorting (higher = more rare)
RARITY_LEVEL = {
    Rarity.Material: 0,
    Rarity.Common: 1,
    Rarity.Uncommon: 2,
    Rarity.Rare: 3,
    Rarity.Epic: 4,
    Rarity.Legendary: 5,
}


class SortBy(str, Enum):
    """Valid sort fields for stash."""

    rarity = "rarity"
    gold_value = "gold_value"
    date_acquired = "date_acquired"


class SortOrder(str, Enum):
    """Sort order direction."""

    asc = "asc"
    desc = "desc"


class StashItem(BaseModel):
    """Item with unique inventory ID for stash display."""

    inventory_id: int  # Unique ID from inventory table
    itemid: int
    name: str
    type: ItemType
    stat: Optional[str] = None
    stat_value: int = 0
    gold_value: int = 1
    description: Optional[str] = None
    rarity: Rarity = Rarity.Material
    base64: Optional[str] = None
    quantity: int = 1  # How many of this item the user has
    created_at: Optional[datetime] = None  # When item was acquired
    updated_at: Optional[datetime] = None  # Last update (quantity change)

    class Config:
        from_attributes = True


class StashResponse(BaseModel):
    """Response model for stash endpoint."""

    userid: int
    gold: int
    items: list[StashItem]


@router.get("/stash", response_model=StashResponse)
async def get_stash(
    userid: int = 1,
    sort_by: SortBy = Query(
        default=SortBy.rarity,
        description="Field to sort by: rarity, gold_value, or date_acquired",
    ),
    sort_order: SortOrder = Query(
        default=SortOrder.desc,
        description="Sort direction: asc or desc",
    ),
    db: Session = Depends(get_db),
) -> StashResponse:
    """Get a user's inventory and gold balance.

    Args:
        userid: The user's ID
        sort_by: Field to sort items by (rarity, gold_value, date_acquired)
        sort_order: Sort direction (asc, desc)
        db: Database session

    Returns:
        User's gold balance and inventory items, sorted as requested
    """
    logger.info(
        f"Stash request for userid={userid}, sort_by={sort_by.value}, "
        f"sort_order={sort_order.value}"
    )

    # Get user (create if doesn't exist)
    user = db.query(User).filter(User.userid == userid).first()
    if not user:
        logger.info(f"Creating new user with userid={userid}")
        user = User(userid=userid, gold=100)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get inventory items with item details, filtering out orphaned entries
    inventory_entries = db.query(Inventory).filter(Inventory.userid == userid).all()

    # Build items with inventory_id for unique identification
    items = []
    for entry in inventory_entries:
        if entry.item is not None:
            items.append(
                StashItem(
                    inventory_id=entry.id,
                    itemid=entry.item.itemid,
                    name=entry.item.name,
                    type=entry.item.type,
                    stat=entry.item.stat,
                    stat_value=entry.item.stat_value,
                    gold_value=entry.item.gold_value,
                    description=entry.item.description,
                    rarity=entry.item.rarity,
                    base64=entry.item.base64,
                    quantity=entry.quantity,
                    created_at=getattr(entry, "created_at", None),
                    updated_at=getattr(entry, "updated_at", None),
                )
            )

    # Sort items
    reverse = sort_order == SortOrder.desc
    if sort_by == SortBy.rarity:
        items.sort(key=lambda x: RARITY_LEVEL.get(x.rarity, 0), reverse=reverse)
    elif sort_by == SortBy.gold_value:
        items.sort(key=lambda x: x.gold_value, reverse=reverse)
    elif sort_by == SortBy.date_acquired:
        # Sort by created_at, with None values at the end
        items.sort(
            key=lambda x: (x.created_at is None, x.created_at or datetime.min),
            reverse=reverse,
        )

    orphaned = len(inventory_entries) - len(items)
    if orphaned > 0:
        logger.warning(f"User {userid} has {orphaned} orphaned inventory entries")
    logger.info(f"User {userid} has {user.gold} gold and {len(items)} items")

    return StashResponse(userid=userid, gold=user.gold, items=items)
