"""Loot endpoint for acquiring random materials."""

import json
import random
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import get_logger
from app.models import Inventory, Item, ItemType, Rarity, User
from app.schemas import Item as ItemSchema

logger = get_logger(__name__)

router = APIRouter(tags=["loot"])

# Load base materials at module level
_materials_cache: list[dict[str, Any]] | None = None


def _load_materials() -> list[dict[str, Any]]:
    """Load materials from JSON file with caching."""
    global _materials_cache
    if _materials_cache is not None:
        return _materials_cache

    data_path = Path(__file__).parent.parent / "data" / "base_materials.json"
    logger.info(f"Loading base materials from {data_path}")

    with open(data_path, "r") as f:
        data = json.load(f)
        _materials_cache = data["materials"]
        logger.info(f"Loaded {len(_materials_cache)} base materials")

    return _materials_cache


def _get_or_create_user(db: Session, userid: int) -> User:
    """Get existing user or create new one."""
    user = db.query(User).filter(User.userid == userid).first()
    if not user:
        logger.info(f"Creating new user with userid={userid}")
        user = User(userid=userid, gold=100)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _get_or_create_item(db: Session, material: dict[str, Any]) -> Item:
    """Get existing item or create from material definition."""
    item = db.query(Item).filter(Item.name == material["name"]).first()
    if not item:
        logger.info(f"Creating new item: {material['name']}")
        item = Item(
            name=material["name"],
            description=material["description"],
            type=ItemType.material,
            rarity=Rarity.Material,
            gold_value=random.randint(1, 2),  # Materials are worth 1-2 gold
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@router.get("/loot", response_model=list[ItemSchema])
async def get_loot(userid: int = 1, db: Session = Depends(get_db)) -> list[Item]:
    """Get 4 random materials for a user.

    Creates the user if they don't exist.
    Creates items in DB if they don't exist.
    Adds items to user's inventory.

    Args:
        userid: The user's ID (creates user if not exists)
        db: Database session

    Returns:
        List of 4 random material items
    """
    logger.info(f"Loot request for userid={userid}")

    # Ensure user exists
    user = _get_or_create_user(db, userid)
    logger.debug(f"User {userid} has {user.gold} gold")

    # Load and select random materials
    materials = _load_materials()
    selected = random.sample(materials, min(4, len(materials)))
    logger.info(f"Selected materials: {[m['name'] for m in selected]}")

    # Get or create items and add to inventory (upsert pattern)
    items: list[Item] = []
    for material in selected:
        item = _get_or_create_item(db, material)
        items.append(item)

        # Upsert to inventory: increment quantity if exists, else create with quantity=1
        existing = (
            db.query(Inventory)
            .filter(Inventory.userid == user.userid, Inventory.itemid == item.itemid)
            .first()
        )

        if existing:
            existing.quantity += 1
            logger.debug(
                f"Incremented {item.name} quantity to {existing.quantity} for user {userid}"
            )
        else:
            inventory_entry = Inventory(
                userid=user.userid, itemid=item.itemid, quantity=1
            )
            db.add(inventory_entry)
            logger.debug(f"Added {item.name} to inventory for user {userid}")

    db.commit()
    logger.info(f"Loot complete: {len(items)} items added to user {userid} inventory")

    return items
