"""Crucible orchestrator for game mechanics."""

import random
from typing import Optional, Tuple

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

# Deterministic fusion rules: (rarity1, rarity2) -> result_rarity
# Both orders are handled by sorting in can_fuse/calculate_deterministic_rarity
FUSION_RULES: dict[Tuple[Rarity, Rarity], Rarity] = {
    (Rarity.Material, Rarity.Material): Rarity.Common,
    (Rarity.Material, Rarity.Uncommon): Rarity.Common,  # Special combo
    (Rarity.Common, Rarity.Common): Rarity.Uncommon,
    (Rarity.Uncommon, Rarity.Uncommon): Rarity.Rare,
    (Rarity.Rare, Rarity.Rare): Rarity.Epic,
    (Rarity.Epic, Rarity.Epic): Rarity.Legendary,
    (Rarity.Legendary, Rarity.Legendary): Rarity.Legendary,  # Capped
}

# Rarity level for sorting (lower = less rare)
RARITY_LEVEL: dict[Rarity, int] = {
    Rarity.Material: 0,
    Rarity.Common: 1,
    Rarity.Uncommon: 2,
    Rarity.Rare: 3,
    Rarity.Epic: 4,
    Rarity.Legendary: 5,
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
    def can_fuse(rarity1: Rarity, rarity2: Rarity) -> bool:
        """Check if two rarities can be fused together.

        Valid combinations:
        - Material + Material → Common
        - Material + Uncommon → Common (special combo)
        - Same rarity + Same rarity (Common+, except Material handled above)

        Invalid combinations:
        - Common + Material (Common cannot fuse with Material)
        - Any cross-rarity fusion (e.g., Common + Rare, Uncommon + Epic)

        Args:
            rarity1: First item's rarity
            rarity2: Second item's rarity

        Returns:
            True if the combination is valid for fusion
        """
        # Sort by rarity level to normalize the pair
        sorted_pair = tuple(sorted([rarity1, rarity2], key=lambda r: RARITY_LEVEL[r]))
        return sorted_pair in FUSION_RULES

    @staticmethod
    def calculate_deterministic_rarity(
        rarity1: Rarity, rarity2: Rarity
    ) -> Optional[Rarity]:
        """Calculate the deterministic result rarity for a fusion.

        Args:
            rarity1: First item's rarity
            rarity2: Second item's rarity

        Returns:
            The resulting rarity tier, or None if invalid combination
        """
        # Sort by rarity level to normalize the pair
        sorted_pair = tuple(sorted([rarity1, rarity2], key=lambda r: RARITY_LEVEL[r]))

        result = FUSION_RULES.get(sorted_pair)
        if result:
            logger.info(
                f"Deterministic fusion: {rarity1.value} + {rarity2.value} "
                f"-> {result.value}"
            )
        else:
            logger.warning(f"Invalid fusion attempt: {rarity1.value} + {rarity2.value}")
        return result

    @staticmethod
    def get_fusable_rarities(rarity: Rarity) -> list[Rarity]:
        """Get list of rarities that can fuse with the given rarity.

        Args:
            rarity: The rarity to check fusability for

        Returns:
            List of rarities that can fuse with the input rarity
        """
        fusable = []
        for r in Rarity:
            sorted_pair = tuple(sorted([rarity, r], key=lambda x: RARITY_LEVEL[x]))
            if sorted_pair in FUSION_RULES:
                fusable.append(r)
        return fusable

    @staticmethod
    def calculate_fusion_rarity(
        input_rarities: list[Rarity],
        critic_score: float,
    ) -> Rarity:
        """Calculate the resulting rarity for a fusion.

        DEPRECATED: Use calculate_deterministic_rarity instead.
        Kept for backward compatibility.

        Args:
            input_rarities: Rarities of input materials
            critic_score: Score from the critic persona (0.0-1.0)

        Returns:
            The resulting rarity tier
        """
        logger.warning(
            "calculate_fusion_rarity is deprecated. "
            "Use calculate_deterministic_rarity instead."
        )

        if len(input_rarities) == 2:
            result = CrucibleOrchestrator.calculate_deterministic_rarity(
                input_rarities[0], input_rarities[1]
            )
            if result:
                return result

        # Fallback to old behavior if deterministic fails
        rarity_order = list(Rarity)
        avg_level = sum(rarity_order.index(r) for r in input_rarities) / len(
            input_rarities
        )
        bonus = int(critic_score * 2)
        final_level = min(int(avg_level) + bonus, len(rarity_order) - 1)

        result = rarity_order[final_level]
        logger.info(f"Fusion result rarity (legacy): {result.value}")
        return result
