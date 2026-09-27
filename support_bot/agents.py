from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMessageTermination
from autogen_agentchat.messages import TextMessage, ToolCallExecutionEvent, ToolCallRequestEvent
from autogen_agentchat.teams import Swarm
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_core.models import ChatCompletionClient

from .search import search_failed

SPECIALISTS: dict[str, dict[str, str]] = {
    "ai_agent": {
        "label": "AI Expert",
        "icon": "🤖",
        "focus": "artificial intelligence, machine learning, LLMs, AI companies, AI tools and research",
    },
    "movie_agent": {
        "label": "Movie Buff",
        "icon": "🎬",
        "focus": "movies, releases, box office, reviews, actors, OTT/streaming and awards",
    },
    "sports_agent": {
        "label": "Sports Desk",
        "icon": "🏆",
        "focus": "sports scores, fixtures, players, teams, tournaments and results",
    },
    "job_agent": {
        "label": "Career Coach",
        "icon": "💼",
        "focus": "jobs, hiring trends, openings, salaries, skills, interviews and careers",
    },
}

TRIAGE = "triage_agent"

TRIAGE_PROMPT = (
    "You route customer questions for a support desk. Topics: "
    + "; ".join(f"{name} = {spec['focus']}" for name, spec in SPECIALISTS.items())
    + ". Use the conversation to resolve follow-ups. If the question clearly fits a topic, "
    "call the matching transfer tool immediately without writing text. If it could fit several topics "
    "or is too vague, ask ONE short clarifying question. If it fits none, politely say you can help "
    "with AI, movies, sports and jobs. Never answer topic questions yourself."
)

SPECIALIST_PROMPT = (
    "You are the {label} of a friendly customer support desk, covering {focus}. Today is {today}. "
    "ALWAYS call web_search once with a precise query (include the year for recent info) before answering. "
    "Answer only from the search results: be concise (under 150 words), conversational, use bullet points "
    "when listing, and cite 1-3 source links. If results are missing, errors, or do not answer the question, "
    "or the customer asks for a human, refunds, complaints or account issues, call escalate_to_human with a "
    "short reason and tell the customer a human colleague will follow up."
)


@dataclass
class TeamOutcome:
    text: str
    agent: str
    searched: bool = False
    escalated: bool = False
    search_failed: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0


def build_team(model_client: ChatCompletionClient, web_search: Callable, escalate_to_human: Callable) -> Swarm:
    def context():
        # Only the last few messages are sent to the model, keeping prompts small.
        return BufferedChatCompletionContext(buffer_size=6)

    triage = AssistantAgent(
        TRIAGE,
        model_client=model_client,
        handoffs=list(SPECIALISTS),
        system_message=TRIAGE_PROMPT,
        model_context=context(),
        description="Routes the customer to the right specialist.",
    )
    today = date.today().strftime("%d %B %Y")
    specialists = [
        AssistantAgent(
            name,
            model_client=model_client,
            tools=[web_search, escalate_to_human],
            system_message=SPECIALIST_PROMPT.format(label=spec["label"], focus=spec["focus"], today=today),
            model_context=context(),
            reflect_on_tool_use=True,
            max_tool_iterations=1,
            description=f"Answers questions about {spec['focus']}.",
        )
        for name, spec in SPECIALISTS.items()
    ]
    # Stop at the first text reply from any agent (the task itself is a user TextMessage).
    termination = MaxMessageTermination(10)
    for agent in [TRIAGE, *SPECIALISTS]:
        termination = termination | TextMessageTermination(source=agent)
    return Swarm([triage, *specialists], termination_condition=termination)


def _add_usage(totals: list[int], message: Any) -> None:
    usage = getattr(message, "models_usage", None)
    if usage:
        totals[0] += usage.prompt_tokens
        totals[1] += usage.completion_tokens


async def run_team(
    model_client: ChatCompletionClient, web_search: Callable, escalate_to_human: Callable, task: str
) -> TeamOutcome:
    team = build_team(model_client, web_search, escalate_to_human)
    result = await team.run(task=task)
    totals = [0, 0]
    tool_names: set[str] = set()
    search_ids: set[str] = set()
    search_outputs: list[str] = []
    final: TextMessage | None = None
    for message in result.messages:
        _add_usage(totals, message)
        if isinstance(message, ToolCallRequestEvent):
            tool_names.update(call.name for call in message.content)
            search_ids.update(call.id for call in message.content if call.name == "web_search")
        if isinstance(message, ToolCallExecutionEvent):
            search_outputs += [
                "SEARCH_ERROR: tool error" if r.is_error else r.content for r in message.content if r.call_id in search_ids
            ]
        if isinstance(message, TextMessage) and message.source != "user":
            final = message
    if final is None:
        text, agent = "Sorry, I couldn't finish that request. Could you rephrase it?", TRIAGE
    else:
        text, agent = final.content, final.source
    return TeamOutcome(
        text=text,
        agent=agent,
        searched="web_search" in tool_names,
        escalated="escalate_to_human" in tool_names,
        search_failed=bool(search_outputs) and all(search_failed(o) for o in search_outputs),
        prompt_tokens=totals[0],
        completion_tokens=totals[1],
    )
