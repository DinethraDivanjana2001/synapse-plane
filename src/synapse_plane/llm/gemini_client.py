"""Gemini via its OpenAI-compatible endpoint — lets IntentPlanner,
LLMMemoryExtractor, and the search-backed adapters reuse the same
OpenAI-SDK-shaped client (chat.completions.create, JSON mode) unchanged."""

from openai import AsyncOpenAI

from synapse_plane.config import Settings

GEMINI_OPENAI_COMPAT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def make_gemini_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key, base_url=GEMINI_OPENAI_COMPAT_BASE_URL)
