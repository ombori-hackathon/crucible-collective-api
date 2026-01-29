"""Pytest configuration and fixtures.

All tests use mocked external services by default to avoid real API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_gemini_service():
    """Auto-mock GeminiService for all tests to prevent real API calls.

    Patches both alchemist and critic modules where gemini_service is imported.
    """
    mock = MagicMock()
    mock.is_available = False  # Disable AI to use fallbacks
    mock.generate_text = AsyncMock(return_value=None)
    mock.generate_image = AsyncMock(return_value=None)

    with patch("app.personas.alchemist.gemini_service", mock), patch(
        "app.personas.critic.gemini_service", mock
    ):
        yield mock


@pytest.fixture
def mock_gemini_text_response(mock_gemini_service):
    """Fixture to set a specific text response from Gemini."""

    def _set_response(response: str):
        mock_gemini_service.is_available = True
        mock_gemini_service.generate_text = AsyncMock(return_value=response)

    return _set_response


@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch("app.db.get_db") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session
