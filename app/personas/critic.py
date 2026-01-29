"""Critic persona for evaluating fused items."""

import json
import random
from typing import Optional

from app.logging_config import get_logger
from app.models.item import Rarity
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

CRITIC_QUALITY_PROMPT = """You are Mordecai the Critic, Senior Quality Auditor for The Crucible.

Evaluate this {rarity} {item_type}:
- Name: {name}
- Description: {description}
- Visual prompt: {visual_prompt}
- Stat: {stat} = {stat_value}

REJECT (REDO) if ANY of these apply:
1. Name is LITERAL or LAZY (e.g., "Fire Sword", "Water Potion", "Iron Shield")
   - Names should be EVOCATIVE (e.g., "Ember's Whisper", "Tidecaller's Lament")
2. Stats not scaled for {rarity} tier (must feel appropriately powerful)
3. Description exceeds 2 sentences or is generic/boring
4. Visual prompt lacks descriptors (needs: rim-lighting, particle effects, ethereal textures, mood)

RESPOND WITH ONLY THIS JSON (no markdown, no explanation):
{{"status": "APPROVED"}}
OR
{{"status": "REDO", "feedback": "Specific reason the alchemist must fix"}}
"""


class CriticPersona:
    """Persona for the Critic character who evaluates items."""

    def __init__(self) -> None:
        self.name = "Mordecai the Critic"
        logger.info(f"Initialized {self.name} persona")

    async def evaluate_quality(
        self,
        name: str,
        description: str,
        visual_prompt: str,
        stat: str,
        stat_value: int,
        rarity: Rarity,
        item_type: str,
    ) -> dict:
        """Evaluate an alchemist's item output for quality.

        Args:
            name: Item name
            description: Item description/lore
            visual_prompt: Visual generation prompt
            stat: Item stat type
            stat_value: Item stat value
            rarity: Target rarity tier
            item_type: Item type (weapon, armor, consumable)

        Returns:
            Dict with status ("APPROVED" or "REDO") and optional feedback
        """
        prompt = CRITIC_QUALITY_PROMPT.format(
            rarity=rarity.value,
            item_type=item_type,
            name=name,
            description=description,
            visual_prompt=visual_prompt,
            stat=stat,
            stat_value=stat_value,
        )

        if not gemini_service.is_available:
            logger.warning("Gemini not available - auto-approving")
            return {"status": "APPROVED"}

        logger.info(f"Critic evaluating: {name}")
        response = await gemini_service.generate_text(
            prompt=prompt,
            system_instruction=CRITIC_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for more consistent judgment
        )

        if not response:
            logger.warning("No response from critic - auto-approving")
            return {"status": "APPROVED"}

        # Parse JSON response
        try:
            # Clean up response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)

            if "status" not in result:
                logger.warning("Invalid critic response - auto-approving")
                return {"status": "APPROVED"}

            status = result["status"].upper()
            if status not in ["APPROVED", "REDO"]:
                logger.warning(f"Unknown status '{status}' - treating as APPROVED")
                return {"status": "APPROVED"}

            logger.info(f"Critic verdict: {status}")
            return {
                "status": status,
                "feedback": result.get("feedback") if status == "REDO" else None,
            }

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse critic response: {e} - auto-approving")
            return {"status": "APPROVED"}

    async def evaluate_item(
        self,
        item_name: str,
        item_description: str,
        material_names: list[str],
    ) -> tuple[float, Optional[str]]:
        """Evaluate a fused item and provide a score.

        DEPRECATED: Use evaluate_quality() instead.

        Args:
            item_name: Name of the item
            item_description: Description of the item
            material_names: Materials used to create it

        Returns:
            Tuple of (score 0.0-1.0, critique text or None)
        """
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
