"""Stash endpoint for viewing inventory."""

from fastapi import APIRouter

from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["stash"])


@router.get("/stash")
async def get_stash(userid: int = 1):
    """Get a user's inventory.

    Stub for future implementation.
    """
    logger.info(f"Stash request for userid={userid} (stub)")
    return {
        "message": "Stash endpoint not yet implemented",
        "hint": "Coming soon: view all your collected materials and crafted items!",
    }
