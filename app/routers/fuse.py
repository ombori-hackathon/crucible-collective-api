"""Fuse endpoint for combining materials into items."""

import random
from typing import Optional

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

# Maximum attempts for critic-alchemist loop
MAX_GENERATION_ATTEMPTS = 3


async def generate_with_critic_loop(
    alchemist: AlchemistPersona,
    critic: CriticPersona,
    material_names: list[str],
    item_type: str,
    rarity: Rarity,
) -> tuple[dict, int, Optional[str]]:
    """Generate an item with critic quality control loop.

    The alchemist generates an item, the critic evaluates it.
    If rejected, the alchemist regenerates with feedback.
    Repeats up to MAX_GENERATION_ATTEMPTS times.

    Args:
        alchemist: AlchemistPersona instance
        critic: CriticPersona instance
        material_names: Names of materials being fused
        item_type: Type of item to generate
        rarity: Target rarity tier

    Returns:
        Tuple of (item_data dict, attempts count, final critic feedback)
    """
    previous_feedback: Optional[str] = None
    final_feedback: Optional[str] = None

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        logger.info(f"Generation attempt {attempt}/{MAX_GENERATION_ATTEMPTS}")

        # Alchemist generates item
        item_data = await alchemist.generate_item(
            material_names=material_names,
            item_type=item_type,
            rarity=rarity,
            previous_feedback=previous_feedback,
        )

        # Critic evaluates
        evaluation = await critic.evaluate_quality(
            name=item_data["name"],
            description=item_data["description"],
            visual_prompt=item_data["visual_prompt"],
            stat=item_data["stat"],
            stat_value=item_data["stat_value"],
            rarity=rarity,
            item_type=item_type,
        )

        if evaluation["status"] == "APPROVED":
            logger.info(f"Critic approved on attempt {attempt}")
            final_feedback = "APPROVED"
            return item_data, attempt, final_feedback

        # Rejected - prepare for next attempt
        previous_feedback = evaluation.get("feedback", "Quality not sufficient")
        final_feedback = previous_feedback
        logger.info(f"Critic rejected: {previous_feedback}")

    # Max attempts reached, use last generated item
    logger.warning(f"Max attempts ({MAX_GENERATION_ATTEMPTS}) reached, using last item")
    return item_data, MAX_GENERATION_ATTEMPTS, final_feedback


@router.post("/fuse", response_model=FuseResponse)
async def fuse_items(
    request: FuseRequest,
    db: Session = Depends(get_db),
) -> FuseResponse:
    """Fuse 2 items together to create a new item.

    Uses deterministic rarity calculation based on input rarities.
    Valid fusion combinations:
    - Material + Material → Common
    - Material + Uncommon → Common (special combo)
    - Common + Common → Uncommon
    - Uncommon + Uncommon → Rare
    - Rare + Rare → Epic
    - Epic + Epic → Legendary
    - Legendary + Legendary → Legendary (capped)

    Invalid combinations return 400 error:
    - Common + Material (Common cannot fuse with Material)
    - Any cross-rarity fusion (e.g., Common + Rare)

    Uses agentic critic-alchemist loop for quality control (max 3 attempts).

    Args:
        request: FuseRequest with userid and itemids
        db: Database session

    Returns:
        FuseResponse with the new item and persona commentary

    Raises:
        HTTPException: 404 if user not found, 400 for validation/fusability errors
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

    # Validate fusability
    rarity1, rarity2 = input_rarities[0], input_rarities[1]
    if not CrucibleOrchestrator.can_fuse(rarity1, rarity2):
        fusable = CrucibleOrchestrator.get_fusable_rarities(rarity1)
        fusable_names = [r.value for r in fusable]
        logger.warning(
            f"Invalid fusion: {rarity1.value} + {rarity2.value} "
            f"(valid for {rarity1.value}: {fusable_names})"
        )
        raise HTTPException(
            status_code=400,
            detail=f"Cannot fuse {rarity1.value} with {rarity2.value}. "
            f"{rarity1.value} can only fuse with: {', '.join(fusable_names)}",
        )

    # Calculate deterministic result rarity
    result_rarity = CrucibleOrchestrator.calculate_deterministic_rarity(
        rarity1, rarity2
    )
    if not result_rarity:
        # This shouldn't happen if can_fuse passed, but handle it
        raise HTTPException(status_code=400, detail="Invalid fusion combination")
    logger.info(f"Deterministic result rarity: {result_rarity.value}")

    # Initialize personas
    alchemist = AlchemistPersona()
    critic = CriticPersona()

    # Roll item type
    item_types = list(ITEM_TYPE_WEIGHTS.keys())
    weights = list(ITEM_TYPE_WEIGHTS.values())
    result_type = random.choices(item_types, weights=weights, k=1)[0]
    logger.info(f"Rolled item type: {result_type.value}")

    # Generate item with critic-alchemist loop
    item_data, attempts, critic_feedback = await generate_with_critic_loop(
        alchemist=alchemist,
        critic=critic,
        material_names=material_names,
        item_type=result_type.value,
        rarity=result_rarity,
    )

    item_name = item_data["name"].strip().strip('"')
    alchemist_description = item_data["description"]
    result_stat = item_data["stat"]
    result_stat_value = item_data["stat_value"]

    logger.info(f"Generated item: {item_name} after {attempts} attempt(s)")

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
        critic_says=critic_feedback,
        critic_score=0.0,  # Deprecated, kept for backward compatibility
        attempts=attempts,
        critic_feedback=critic_feedback,
    )
