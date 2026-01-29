"""Alchemist persona for crafting and fusion."""

from typing import Optional

from app.logging_config import get_logger
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


class AlchemistPersona:
    """Persona for the Alchemist character who handles fusion."""

    def __init__(self) -> None:
        self.name = "Zephyrus the Alchemist"
        logger.info(f"Initialized {self.name} persona")

    async def describe_fusion(
        self,
        material_names: list[str],
    ) -> Optional[str]:
        """Generate a description for fusing materials.

        Stub for future /fuse endpoint.

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

        Stub for future /fuse endpoint.

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
