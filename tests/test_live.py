from dataclasses import replace

import pytest

from support_bot.config import load_settings
from support_bot.search import web_search
from support_bot.service import SupportService

settings = load_settings()
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(bool(settings.missing_keys()), reason="needs OPENAI_API_KEY and SERPAPI_API_KEY in .env"),
]


def test_search_provider_returns_compact_results():
    text = web_search("latest AI news", settings.serpapi_api_key, settings.search_provider)
    assert not text.startswith("SEARCH_ERROR"), text
    assert len(text) <= 2500


async def test_end_to_end_answer_then_memory_hit(tmp_path):
    service = SupportService(replace(settings, data_dir=tmp_path))
    first = await service.answer("live-test", "What is the latest model released by OpenAI?")
    assert first.source == "web", first.text
    assert first.agent == "ai_agent"
    second = await service.answer("live-test", "What is the latest model released by OpenAI?")
    assert second.source == "memory"
    assert second.prompt_tokens == 0
