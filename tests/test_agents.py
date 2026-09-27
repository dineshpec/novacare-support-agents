from autogen_core.models import CreateResult, RequestUsage
from autogen_core import FunctionCall
from autogen_ext.models.replay import ReplayChatCompletionClient

from support_bot.agents import SPECIALISTS, run_team

MODEL_INFO = {
    "vision": False,
    "function_calling": True,
    "json_output": False,
    "family": "gpt-4o",
    "structured_output": False,
}


def call(name: str, arguments: str = "{}") -> CreateResult:
    return CreateResult(
        finish_reason="function_calls",
        content=[FunctionCall(id=f"call-{name}", name=name, arguments=arguments)],
        usage=RequestUsage(prompt_tokens=10, completion_tokens=5),
        cached=False,
    )


def text(content: str) -> CreateResult:
    return CreateResult(
        finish_reason="stop", content=content, usage=RequestUsage(prompt_tokens=20, completion_tokens=8), cached=False
    )


def recording_tools():
    calls = {"search": [], "escalate": []}

    async def web_search(query: str) -> str:
        """Search the web."""
        calls["search"].append(query)
        return "1. GPT-5 launched: OpenAI released GPT-5 (http://x)"

    def escalate_to_human(reason: str) -> str:
        """Escalate to a human."""
        calls["escalate"].append(reason)
        return "ticket created"

    return web_search, escalate_to_human, calls


def test_there_is_one_specialist_per_supported_topic():
    assert set(SPECIALISTS) == {"ai_agent", "movie_agent", "sports_agent", "job_agent"}


async def test_triage_routes_to_specialist_which_searches_the_web_and_answers():
    web_search, escalate, calls = recording_tools()
    client = ReplayChatCompletionClient(
        [
            call("transfer_to_ai_agent"),
            call("web_search", '{"query": "latest GPT release"}'),
            text("GPT-5 is the latest release."),
        ],
        model_info=MODEL_INFO,
    )
    outcome = await run_team(client, web_search, escalate, "What is the latest GPT?")
    assert outcome.agent == "ai_agent"
    assert outcome.text == "GPT-5 is the latest release."
    assert calls["search"] == ["latest GPT release"]
    assert outcome.searched and not outcome.escalated
    assert outcome.prompt_tokens == 40 and outcome.completion_tokens == 18


async def test_triage_asks_a_clarifying_question_when_topic_is_unclear():
    web_search, escalate, calls = recording_tools()
    client = ReplayChatCompletionClient([text("Do you mean football or the movie?")], model_info=MODEL_INFO)
    outcome = await run_team(client, web_search, escalate, "Tell me about Goal")
    assert outcome.agent == "triage_agent"
    assert outcome.text == "Do you mean football or the movie?"
    assert calls["search"] == []


async def test_failed_search_is_reported_as_search_failure():
    async def web_search(query: str) -> str:
        """Search the web."""
        return "SEARCH_ERROR: Invalid API key"

    _, escalate, _ = recording_tools()
    client = ReplayChatCompletionClient(
        [call("transfer_to_sports_agent"), call("web_search", '{"query": "india schedule"}'), text("Unable to access.")],
        model_info=MODEL_INFO,
    )
    outcome = await run_team(client, web_search, escalate, "India match schedule?")
    assert outcome.searched and outcome.search_failed


async def test_specialist_escalation_is_reported():
    web_search, escalate, calls = recording_tools()
    client = ReplayChatCompletionClient(
        [
            call("transfer_to_job_agent"),
            call("escalate_to_human", '{"reason": "refund request"}'),
            text("I've passed this to a human colleague."),
        ],
        model_info=MODEL_INFO,
    )
    outcome = await run_team(client, web_search, escalate, "I want a refund for my job board subscription")
    assert outcome.agent == "job_agent"
    assert outcome.escalated
    assert calls["escalate"] == ["refund request"]
