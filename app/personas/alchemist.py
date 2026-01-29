"""Alchemist persona for crafting and fusion."""

import json
import random
from typing import Optional

from app.logging_config import get_logger
from app.models.item import Rarity
from app.services.gemini_service import gemini_service

logger = get_logger(__name__)

ALCHEMIST_SYSTEM_PROMPT = """You are Zephyrus the Alchemist, a wise and eccentric master of transmutation
in the world of The Crucible. You speak with enthusiasm about combining materials and creating
powerful items. You use alchemical terminology and occasionally reference ancient texts.

When given materials to fuse, you must:
1. Describe what you're creating with dramatic flair
2. Provide a creative name for the resulting item
3. Suggest what stats/abilities it might have
4. Keep responses concise but flavorful (2-3 sentences max)
"""

ALCHEMIST_GENERATION_PROMPT = """You are Zephyrus the Alchemist, master of transmutation in The Crucible.
Generate a {rarity} {item_type} from these materials: {materials}.

REQUIREMENTS:
1. Name must be EVOCATIVE and POETIC - NOT literal (bad: "Fire Sword", good: "Ember's Whisper")
2. Description: max 2 sentences of atmospheric lore
3. Visual prompt: detailed, artistic, include lighting/textures/mood (rim-lighting, ethereal glow, etc.)
4. Stats must match rarity tier power level

{previous_feedback}

RESPOND WITH ONLY THIS JSON (no markdown, no explanation):
{{"name": "...", "description": "...", "visual_prompt": "...", "stat": "strength|defense|magic|speed|luck", "stat_value": <number>}}
"""

# Stat value ranges by rarity (base range, will be adjusted)
STAT_RANGES = {
    Rarity.Common: (5, 15),
    Rarity.Uncommon: (15, 30),
    Rarity.Rare: (30, 50),
    Rarity.Epic: (50, 80),
    Rarity.Legendary: (80, 120),
}

STATS = ["strength", "defense", "magic", "speed", "luck"]


class AlchemistPersona:
    """Persona for the Alchemist character who handles fusion."""

    def __init__(self) -> None:
        self.name = "Zephyrus the Alchemist"
        logger.info(f"Initialized {self.name} persona")

    async def generate_item(
        self,
        material_names: list[str],
        item_type: str,
        rarity: Rarity,
        previous_feedback: Optional[str] = None,
    ) -> dict:
        """Generate a complete item with name, description, visual prompt, and stats.

        Args:
            material_names: Names of materials being fused
            item_type: Type of item (weapon, armor, consumable)
            rarity: Target rarity for the item
            previous_feedback: Optional feedback from critic for regeneration

        Returns:
            Dict with name, description, visual_prompt, stat, stat_value
        """
        feedback_text = ""
        if previous_feedback:
            feedback_text = f"\nPREVIOUS FEEDBACK FROM CRITIC (fix these issues):\n{previous_feedback}\n"

        prompt = ALCHEMIST_GENERATION_PROMPT.format(
            rarity=rarity.value,
            item_type=item_type,
            materials=", ".join(material_names),
            previous_feedback=feedback_text,
        )

        if not gemini_service.is_available:
            logger.warning("Gemini not available - using fallback generation")
            return self._generate_fallback(material_names, item_type, rarity)

        logger.info(
            f"Generating {rarity.value} {item_type} from {len(material_names)} materials"
        )
        response = await gemini_service.generate_text(
            prompt=prompt,
            system_instruction=ALCHEMIST_SYSTEM_PROMPT,
            temperature=0.9,
        )

        if not response:
            return self._generate_fallback(material_names, item_type, rarity)

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

            # Validate required fields
            required = ["name", "description", "visual_prompt", "stat", "stat_value"]
            if not all(k in result for k in required):
                logger.warning("Missing fields in alchemist response, using fallback")
                return self._generate_fallback(material_names, item_type, rarity)

            # Validate stat
            if result["stat"] not in STATS:
                result["stat"] = random.choice(STATS)

            # Ensure stat_value is in range for rarity
            min_stat, max_stat = STAT_RANGES.get(rarity, (10, 30))
            result["stat_value"] = max(
                min_stat, min(max_stat, int(result["stat_value"]))
            )

            logger.info(f"Generated item: {result['name']}")
            return result

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse alchemist response: {e}")
            return self._generate_fallback(material_names, item_type, rarity)

    def _generate_fallback(
        self,
        material_names: list[str],
        item_type: str,
        rarity: Rarity,
    ) -> dict:
        """Generate a fallback item when AI is unavailable."""
        prefixes = {
            Rarity.Common: ["Simple", "Basic", "Plain"],
            Rarity.Uncommon: ["Enhanced", "Refined", "Improved"],
            Rarity.Rare: ["Masterwork", "Exquisite", "Superior"],
            Rarity.Epic: ["Legendary", "Mythic", "Arcane"],
            Rarity.Legendary: ["Divine", "Celestial", "Primordial"],
        }
        prefix = random.choice(prefixes.get(rarity, ["Mysterious"]))
        name = f"{prefix} {item_type.title()} of {material_names[0].split()[0]}"

        min_stat, max_stat = STAT_RANGES.get(rarity, (10, 30))

        return {
            "name": name,
            "description": f"A {rarity.value.lower()} {item_type} forged from {', '.join(material_names)}.",
            "visual_prompt": f"A {rarity.value.lower()} fantasy {item_type}, glowing with magical energy, detailed illustration",
            "stat": random.choice(STATS),
            "stat_value": random.randint(min_stat, max_stat),
        }

    async def describe_fusion(
        self,
        material_names: list[str],
    ) -> Optional[str]:
        """Generate a description for fusing materials.

        DEPRECATED: Use generate_item() instead.

        Args:
            material_names: Names of materials being fused

        Returns:
            Alchemist's description of the fusion or None if unavailable
        """
        if not gemini_service.is_available:
            logger.warning("Gemini not available - using fallback description")
            return f"*mixes {', '.join(material_names)} in the crucible* Fascinating results!"

        prompt = f"I am fusing these materials: {', '.join(material_names)}. Describe the result."

        logger.info(
            f"Generating fusion description for {len(material_names)} materials"
        )
        return await gemini_service.generate_text(
            prompt=prompt,
            system_instruction=ALCHEMIST_SYSTEM_PROMPT,
            temperature=0.8,
        )

    async def suggest_item_name(
        self,
        material_names: list[str],
        item_type: str,
    ) -> Optional[str]:
        """Generate a name suggestion for a fused item.

        DEPRECATED: Use generate_item() instead.

        Args:
            material_names: Names of materials used
            item_type: Type of item being created

        Returns:
            Suggested name or None if unavailable
        """
        if not gemini_service.is_available:
            logger.warning("Gemini not available - using fallback name")
            return f"Mysterious {item_type.title()}"

        prompt = (
            f"Suggest a single creative fantasy name for a {item_type} "
            f"made from: {', '.join(material_names)}. "
            "Reply with ONLY the name, nothing else."
        )

        logger.info(f"Generating item name for {item_type}")
        return await gemini_service.generate_text(
            prompt=prompt,
            system_instruction=ALCHEMIST_SYSTEM_PROMPT,
            temperature=0.9,
        )
