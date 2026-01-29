"""Singleton service for Gemini AI integration."""

import asyncio
from typing import Optional

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Retry configuration for rate limiting
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


class GeminiService:
    """Singleton service for interacting with Google's Gemini AI models."""

    _instance: Optional["GeminiService"] = None
    _initialized: bool = False

    def __new__(cls) -> "GeminiService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._client = None
        self._imagen_client = None

        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not set - AI features disabled")
        else:
            try:
                from google import genai

                self._client = genai.Client(api_key=settings.gemini_api_key)
                logger.info("Gemini client initialized successfully")
            except ImportError:
                logger.error("google-genai package not installed")
            except Exception as e:
                logger.error(
                    f"Failed to initialize Gemini client: {type(e).__name__}: {e}"
                )

        self._initialized = True

    @property
    def is_available(self) -> bool:
        """Check if Gemini service is available."""
        return self._client is not None

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Generate text using Gemini 2.0 Flash.

        Args:
            prompt: The user prompt to send
            system_instruction: Optional system instruction
            temperature: Sampling temperature (0.0-1.0)

        Returns:
            Generated text or None if unavailable
        """
        if not self.is_available:
            logger.warning("Gemini not available - returning None")
            return None

        config = {"temperature": temperature}
        if system_instruction:
            config["system_instruction"] = system_instruction

        backoff = INITIAL_BACKOFF_SECONDS
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Generating text with prompt length: {len(prompt)}")
                logger.debug(f"Prompt: {prompt[:100]}...")

                response = self._client.models.generate_content(
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=config,
                )

                result = response.text
                logger.info(f"Generated text length: {len(result)}")
                return result

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            f"Rate limited (attempt {attempt}/{MAX_RETRIES}), "
                            f"retrying in {backoff:.1f}s..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        continue
                    else:
                        logger.warning(
                            f"Rate limited after {MAX_RETRIES} attempts - "
                            "using fallback generation"
                        )
                        return None
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"Text generation failed: {type(e).__name__}: {e}")
                    return None

        logger.warning(f"All {MAX_RETRIES} attempts failed: {last_error}")
        return None

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
    ) -> Optional[str]:
        """Generate an image using Imagen 3.

        Args:
            prompt: Description of the image to generate
            aspect_ratio: Image aspect ratio (e.g., "1:1", "16:9")

        Returns:
            Base64 encoded image data or None if unavailable
        """
        if not self.is_available:
            logger.warning("Gemini not available - returning None")
            return None

        backoff = INITIAL_BACKOFF_SECONDS
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(f"Generating image with prompt: {prompt[:50]}...")

                response = self._client.models.generate_images(
                    model="imagen-3.0-generate-002",
                    prompt=prompt,
                    config={
                        "number_of_images": 1,
                        "aspect_ratio": aspect_ratio,
                    },
                )

                if response.generated_images:
                    # Get the base64 encoded image
                    image = response.generated_images[0]
                    import base64

                    image_data = base64.b64encode(image.image.image_bytes).decode(
                        "utf-8"
                    )
                    logger.info("Image generated successfully")
                    return image_data

                logger.warning("No image generated")
                return None

            except Exception as e:
                last_error = e
                error_str = str(e)

                # Check if it's a rate limit error (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            f"Rate limited (attempt {attempt}/{MAX_RETRIES}), "
                            f"retrying in {backoff:.1f}s..."
                        )
                        await asyncio.sleep(backoff)
                        backoff *= 2  # Exponential backoff
                        continue
                    else:
                        logger.warning(
                            f"Rate limited after {MAX_RETRIES} attempts - "
                            "image generation unavailable"
                        )
                        return None
                else:
                    # Non-rate-limit error, don't retry
                    logger.error(f"Image generation failed: {type(e).__name__}: {e}")
                    return None

        logger.warning(f"All {MAX_RETRIES} attempts failed: {last_error}")
        return None


# Singleton instance
gemini_service = GeminiService()
