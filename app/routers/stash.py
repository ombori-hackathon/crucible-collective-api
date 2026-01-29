"""Stash endpoint for viewing inventory."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import get_logger
from app.models import Inventory, User
from app.models.item import ItemType, Rarity

logger = get_logger(__name__)

router = APIRouter(tags=["stash"])


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

    class Config:
        from_attributes = True


class StashResponse(BaseModel):
    """Response model for stash endpoint."""

    userid: int
    gold: int
    items: list[StashItem]


@router.get("/stash", response_model=StashResponse)
async def get_stash(userid: int = 1, db: Session = Depends(get_db)) -> StashResponse:
    """Get a user's inventory and gold balance.

    Args:
        userid: The user's ID
        db: Database session

    Returns:
        User's gold balance and inventory items
    """
    logger.info(f"Stash request for userid={userid}")

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
                )
            )

    orphaned = len(inventory_entries) - len(items)
    if orphaned > 0:
        logger.warning(f"User {userid} has {orphaned} orphaned inventory entries")
    logger.info(f"User {userid} has {user.gold} gold and {len(items)} items")

    return StashResponse(userid=userid, gold=user.gold, items=items)
