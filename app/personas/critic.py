"""Critic persona for evaluating fused items."""

from typing import Optional

from app.logging_config import get_logger
from app.services.gemini_service import gemini_service

logger = get_logger(__name__)

CRITIC_SYSTEM_PROMPT = """You are Mordecai the Critic, a discerning appraiser of magical items
in the world of The Crucible. You are somewhat cynical but fair, with high standards for quality.
You speak in a refined, slightly condescending tone.

When evaluating items, you must:
1. Comment on the craftsmanship and quality
2. Provide a score from 0.0 to 1.0 (be discerning - high scores are rare)
3. Keep responses brief and pointed (1-2 sentences max)
"""


class CriticPersona:
    """Persona for the Critic character who evaluates items."""

    def __init__(self) -> None:
        self.name = "Mordecai the Critic"
        logger.info(f"Initialized {self.name} persona")

    async def evaluate_item(
        self,
        item_name: str,
        item_description: str,
        material_names: list[str],
    ) -> tuple[float, Optional[str]]:
        """Evaluate a fused item and provide a score.

        Stub for future /fuse endpoint.

        Args:
            item_name: Name of the item
            item_description: Description of the item
            material_names: Materials used to create it

        Returns:
            Tuple of (score 0.0-1.0, critique text or None)
        """
        import random

        if not gemini_service.is_available:
            logger.warning("Gemini not available - using random score")
            score = random.uniform(0.3, 0.8)
            return score, f"*adjusts monocle* A passable {item_name}, I suppose."

        prompt = (
            f"Evaluate this item:\n"
            f"Name: {item_name}\n"
            f"Description: {item_description}\n"
            f"Made from: {', '.join(material_names)}\n\n"
            f"Provide a brief critique and end with 'SCORE: X.X' where X.X is 0.0-1.0"
        )

        logger.info(f"Evaluating item: {item_name}")
        response = await gemini_service.generate_text(
            prompt=prompt,
            system_instruction=CRITIC_SYSTEM_PROMPT,
            temperature=0.7,
        )

        if not response:
            score = random.uniform(0.3, 0.8)
            return score, None

        # Parse score from response
        score = 0.5  # Default
        try:
            if "SCORE:" in response.upper():
                score_str = response.upper().split("SCORE:")[-1].strip()
                score = float(score_str.split()[0])
                score = max(0.0, min(1.0, score))  # Clamp to valid range
        except (ValueError, IndexError):
            logger.warning("Failed to parse critic score, using default")

        # Remove score from critique text
        critique = response
        if "SCORE:" in response.upper():
            idx = response.upper().index("SCORE:")
            critique = response[:idx].strip()

        logger.info(f"Critic score: {score}")
        return score, critique
