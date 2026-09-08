"""Unit test for the Gemini client factory — construction only, no network."""

from synapse_plane.config import Settings
from synapse_plane.llm.gemini_client import GEMINI_OPENAI_COMPAT_BASE_URL, make_gemini_client


def test_make_gemini_client_points_at_gemini_endpoint() -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", openai_api_key="fake-key-for-test"
    )

    client = make_gemini_client(settings)

    assert str(client.base_url) == GEMINI_OPENAI_COMPAT_BASE_URL
