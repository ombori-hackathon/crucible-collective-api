"""Sell endpoint for converting items to gold."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.logging_config import get_logger
from app.models import Inventory, User

logger = get_logger(__name__)

router = APIRouter(tags=["sell"])


class SellRequest(BaseModel):
    """Request model for sell endpoint."""

    userid: int
    inventory_id: int  # Unique inventory entry ID
    quantity: int = 1  # How many to sell (default 1 for backwards compatibility)


class SellResponse(BaseModel):
    """Response model for sell endpoint."""

    gold_earned: int
    new_balance: int
    remaining_quantity: int  # How many remain after sale (0 if item removed)


@router.post("/sell", response_model=SellResponse)
async def sell_item(
    request: SellRequest, db: Session = Depends(get_db)
) -> SellResponse:
    """Sell an item from inventory for gold.

    Args:
        request: Sell request with userid and inventory_id
        db: Database session

    Returns:
        Gold earned and new balance

    Raises:
        HTTPException: If user or inventory entry not found
    """
    logger.info(
        f"Sell request: user={request.userid}, inventory_id={request.inventory_id}"
    )

    # Validate user exists
    user = db.query(User).filter(User.userid == request.userid).first()
    if not user:
        logger.error(f"User {request.userid} not found")
        raise HTTPException(status_code=404, detail="User not found")

    # Find inventory entry by ID and verify it belongs to this user
    inventory_entry = (
        db.query(Inventory)
        .filter(
            Inventory.id == request.inventory_id, Inventory.userid == request.userid
        )
        .first()
    )
    if not inventory_entry:
        logger.error(
            f"Inventory entry {request.inventory_id} not found for user {request.userid}"
        )
        raise HTTPException(status_code=404, detail="Item not in inventory")

    # Get item's gold value
    item = inventory_entry.item
    if item is None:
        logger.error(f"Orphaned inventory entry {request.inventory_id}")
        db.delete(inventory_entry)
        db.commit()
        raise HTTPException(status_code=404, detail="Item no longer exists")

    # Validate requested quantity
    if request.quantity < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    if request.quantity > inventory_entry.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot sell {request.quantity}, only have {inventory_entry.quantity}",
        )

    # Calculate gold earned
    gold_earned = item.gold_value * request.quantity
    logger.info(f"Selling {request.quantity}x {item.name} for {gold_earned} gold")

    # Decrement quantity or delete entry if selling all
    remaining_quantity = inventory_entry.quantity - request.quantity
    if remaining_quantity == 0:
        db.delete(inventory_entry)
        logger.debug(f"Removed inventory entry {request.inventory_id} (sold all)")
    else:
        inventory_entry.quantity = remaining_quantity
        logger.debug(f"Decremented quantity to {remaining_quantity}")

    # Add gold to user
    user.gold += gold_earned
    db.commit()

    logger.info(
        f"User {request.userid} sold {request.quantity}x {item.name}, new balance: {user.gold}"
    )

    return SellResponse(
        gold_earned=gold_earned,
        new_balance=user.gold,
        remaining_quantity=remaining_quantity,
    )
