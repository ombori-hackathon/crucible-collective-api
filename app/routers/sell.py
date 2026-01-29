"""Sell endpoint for converting items to gold."""

from fastapi import APIRouter

from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["sell"])


@router.post("/sell")
async def sell_item(itemid: int, userid: int = 1):
    """Sell an item from inventory for gold.

    Stub for future implementation.
    """
    logger.info(f"Sell request: user={userid}, item={itemid} (stub)")
    return {
        "message": "Sell endpoint not yet implemented",
        "hint": "Coming soon: trade your items for gold!",
    }
