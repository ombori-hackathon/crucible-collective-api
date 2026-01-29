"""Fuse endpoint for combining materials into items."""

import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import get_logger
from app.models import Inventory, Item, ItemType, Rarity, User
from app.orchestrator.crucible import CrucibleOrchestrator
from app.personas.alchemist import AlchemistPersona
from app.personas.critic import CriticPersona
from app.schemas import FuseRequest, FuseResponse
from app.schemas import Item as ItemSchema

logger = get_logger(__name__)

router = APIRouter(tags=["fuse"])

# Item type weights for random selection
ITEM_TYPE_WEIGHTS = {
    ItemType.weapon: 40,
    ItemType.armor: 40,
    ItemType.consumable: 20,
}

# Stats for items
ITEM_STATS = ["strength", "defense", "magic", "speed", "luck"]


@router.post("/fuse", response_model=FuseResponse)
async def fuse_items(
    request: FuseRequest,
    db: Session = Depends(get_db),
) -> FuseResponse:
    """Fuse 2 items together to create a new item.

    Uses:
    - AlchemistPersona to describe the fusion and suggest a name
    - CriticPersona to evaluate the result
    - CrucibleOrchestrator to calculate rarity/stats

    Args:
        request: FuseRequest with userid and itemids
        db: Database session

    Returns:
        FuseResponse with the new item and persona commentary

    Raises:
        HTTPException: 404 if user not found, 400 for validation errors
    """
    logger.info(f"Fuse request for userid={request.userid}, itemids={request.itemids}")

    # Validate user exists
    user = db.query(User).filter(User.userid == request.userid).first()
    if not user:
        logger.warning(f"User {request.userid} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Find inventory entries for the items belonging to this user
    inventory_entries: list[Inventory] = []
    items: list[Item] = []

    for itemid in request.itemids:
        # Find inventory entry for this user and item
        inventory_entry = (
            db.query(Inventory)
            .filter(Inventory.userid == request.userid, Inventory.itemid == itemid)
            .first()
        )
        if not inventory_entry:
            logger.warning(f"Item {itemid} not in inventory for user {request.userid}")
            raise HTTPException(
                status_code=400,
                detail=f"Item {itemid} not found in user's inventory",
            )

        # Get the item
        item = db.query(Item).filter(Item.itemid == itemid).first()
        if not item:
            logger.error(f"Item {itemid} exists in inventory but not in items table")
            raise HTTPException(status_code=400, detail=f"Item {itemid} not found")

        inventory_entries.append(inventory_entry)
        items.append(item)

    material_names = [item.name for item in items]
    input_rarities = [item.rarity for item in items]
    logger.info(f"Fusing materials: {material_names}")

    # Initialize personas
    alchemist = AlchemistPersona()
    critic = CriticPersona()

    # Roll item type
    item_types = list(ITEM_TYPE_WEIGHTS.keys())
    weights = list(ITEM_TYPE_WEIGHTS.values())
    result_type = random.choices(item_types, weights=weights, k=1)[0]
    logger.info(f"Rolled item type: {result_type.value}")

    # Generate item name with Alchemist
    item_name = await alchemist.suggest_item_name(material_names, result_type.value)
    if not item_name:
        item_name = f"Mysterious {result_type.value.title()}"
    item_name = item_name.strip().strip('"')
    logger.info(f"Generated item name: {item_name}")

    # Generate fusion description with Alchemist
    alchemist_description = await alchemist.describe_fusion(material_names)
    if not alchemist_description:
        alchemist_description = (
            f"*mixes {', '.join(material_names)} in the crucible* Fascinating results!"
        )
    logger.info(f"Alchemist says: {alchemist_description[:50]}...")

    # Evaluate with Critic
    critic_score, critic_says = await critic.evaluate_item(
        item_name, alchemist_description, material_names
    )
    logger.info(f"Critic score: {critic_score}, says: {critic_says}")

    # Calculate rarity based on input rarities and critic score
    result_rarity = CrucibleOrchestrator.calculate_fusion_rarity(
        input_rarities, critic_score
    )
    logger.info(f"Result rarity: {result_rarity.value}")

    # Roll stat
    result_stat = random.choice(ITEM_STATS)

    # Calculate stat value based on input items + rarity bonus
    base_stat = sum(item.stat_value for item in items)
    rarity_bonus = list(Rarity).index(result_rarity) * 3
    result_stat_value = base_stat + random.randint(5, 15) + rarity_bonus

    # Calculate gold value
    result_gold_value = CrucibleOrchestrator.calculate_gold_value(result_rarity)

    # Create new item in database
    new_item = Item(
        name=item_name,
        type=result_type,
        stat=result_stat,
        stat_value=result_stat_value,
        gold_value=result_gold_value,
        description=alchemist_description,
        rarity=result_rarity,
        base64=None,
    )

    # Handle potential name collision by appending a suffix
    existing = db.query(Item).filter(Item.name == item_name).first()
    if existing:
        suffix = random.randint(1, 999)
        new_item.name = f"{item_name} #{suffix}"
        logger.info(f"Name collision, renamed to: {new_item.name}")

    db.add(new_item)
    db.flush()  # Get the new item's ID
    logger.info(f"Created new item with itemid={new_item.itemid}")

    # Decrement quantity of consumed items (delete if quantity becomes 0)
    for inventory_entry in inventory_entries:
        if inventory_entry.quantity > 1:
            inventory_entry.quantity -= 1
            logger.debug(
                f"Decremented inventory entry {inventory_entry.id} to quantity {inventory_entry.quantity}"
            )
        else:
            logger.debug(
                f"Removing inventory entry {inventory_entry.id} (quantity was 1)"
            )
            db.delete(inventory_entry)

    # Add new item to user's inventory (upsert pattern)
    existing_inventory = (
        db.query(Inventory)
        .filter(Inventory.userid == request.userid, Inventory.itemid == new_item.itemid)
        .first()
    )

    if existing_inventory:
        existing_inventory.quantity += 1
        logger.debug(
            f"Incremented existing inventory entry to {existing_inventory.quantity}"
        )
    else:
        new_inventory_entry = Inventory(
            userid=request.userid, itemid=new_item.itemid, quantity=1
        )
        db.add(new_inventory_entry)

    db.commit()
    db.refresh(new_item)
    logger.info(f"Fuse complete: created {new_item.name} ({new_item.rarity.value})")

    return FuseResponse(
        item=ItemSchema.model_validate(new_item),
        alchemist_says=alchemist_description,
        critic_says=critic_says,
        critic_score=critic_score,
    )
