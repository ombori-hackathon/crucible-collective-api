"""Crucible orchestrator for game mechanics."""

import random
from typing import Tuple

from app.logging_config import get_logger
from app.models.item import Rarity

logger = get_logger(__name__)

# Gold value ranges for each rarity tier
GOLD_RANGES: dict[Rarity, Tuple[int, int]] = {
    Rarity.Material: (1, 2),
    Rarity.Common: (5, 10),
    Rarity.Uncommon: (10, 20),
    Rarity.Rare: (20, 50),
    Rarity.Epic: (50, 150),
    Rarity.Legendary: (150, 300),
}

# Rarity weights for random selection (higher = more common)
RARITY_WEIGHTS: dict[Rarity, int] = {
    Rarity.Common: 50,
    Rarity.Uncommon: 30,
    Rarity.Rare: 15,
    Rarity.Epic: 4,
    Rarity.Legendary: 1,
}


class CrucibleOrchestrator:
    """Orchestrator for The Crucible game mechanics."""

    @staticmethod
    def calculate_gold_value(rarity: Rarity) -> int:
        """Calculate gold value based on rarity.

        Args:
            rarity: The item's rarity tier

        Returns:
            Random gold value within the rarity's range
        """
        min_gold, max_gold = GOLD_RANGES.get(rarity, (1, 2))
        value = random.randint(min_gold, max_gold)
        logger.debug(f"Calculated gold value {value} for rarity {rarity.value}")
        return value

    @staticmethod
    def roll_rarity() -> Rarity:
        """Roll for a random rarity based on weights.

        Returns:
            A randomly selected rarity tier
        """
        rarities = list(RARITY_WEIGHTS.keys())
        weights = list(RARITY_WEIGHTS.values())
        selected = random.choices(rarities, weights=weights, k=1)[0]
        logger.debug(f"Rolled rarity: {selected.value}")
        return selected

    @staticmethod
    def calculate_fusion_rarity(
        input_rarities: list[Rarity],
        critic_score: float,
    ) -> Rarity:
        """Calculate the resulting rarity for a fusion.

        Stub for future /fuse endpoint.

        Args:
            input_rarities: Rarities of input materials
            critic_score: Score from the critic persona (0.0-1.0)

        Returns:
            The resulting rarity tier
        """
        # Placeholder implementation
        logger.info(
            f"Calculating fusion rarity from {len(input_rarities)} inputs, "
            f"critic score: {critic_score}"
        )

        # Average input rarity level + critic bonus
        rarity_order = list(Rarity)
        avg_level = sum(rarity_order.index(r) for r in input_rarities) / len(
            input_rarities
        )
        bonus = int(critic_score * 2)  # Up to +2 rarity levels
        final_level = min(int(avg_level) + bonus, len(rarity_order) - 1)

        result = rarity_order[final_level]
        logger.info(f"Fusion result rarity: {result.value}")
        return result
