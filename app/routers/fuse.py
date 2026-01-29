"""Fuse endpoint for combining materials into items."""

from fastapi import APIRouter

from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["fuse"])


@router.post("/fuse")
async def fuse_items():
    """Fuse materials together to create a new item.

    Stub for future implementation.
    Will use:
    - AlchemistPersona to describe the fusion
    - CriticPersona to evaluate the result
    - CrucibleOrchestrator to calculate rarity/stats
    """
    logger.info("Fuse endpoint called (stub)")
    return {
        "message": "Fusion endpoint not yet implemented",
        "hint": "Coming soon: combine materials to create weapons, armor, and consumables!",
    }
