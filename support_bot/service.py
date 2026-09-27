import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Awaitable, Callable, Sequence

from .agents import TRIAGE, TeamOutcome, run_team
from .config import Settings
from .memory import EmbedFn, MemoryStore, safe_customer_id
from .search import web_search as run_web_search

RunTeamFn = Callable[[str, str], Awaitable[TeamOutcome]]


@dataclass
class BotReply:
    text: str
    agent: str
    source: str  # memory | web | clarify | escalated | error
    prompt_tokens: int = 0
    completion_tokens: int = 0
    embedding_tokens: int = 0
    similarity: float | None = None
    remembered_at: str | None = None


class OpenAIEmbedder:
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self.last_tokens = 0

    def __call__(self, text: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model, input=text[:2000])
        self.last_tokens = response.usage.total_tokens
        return response.data[0].embedding


def _clip(text: str, limit: int = 300) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


class SupportService:
    def __init__(self, settings: Settings, embed_fn: EmbedFn | None = None, run_team: RunTeamFn | None = None):
        self.settings = settings
        self.embed_fn = embed_fn or OpenAIEmbedder(settings.openai_api_key, settings.embedding_model)
        self.run_team = run_team or self._run_autogen_team

    def memory(self, customer_id: str) -> MemoryStore:
        return MemoryStore(customer_id, self.settings.memory_dir, self.embed_fn)

    def build_task(self, question: str, history: Sequence[tuple[str, str]]) -> str:
        recent = list(history)[-2 * self.settings.history_turns :]
        lines = [f"Today: {date.today().isoformat()}"]
        if recent:
            lines.append("Recent conversation:")
            lines += [f"{'Customer' if role == 'user' else 'Support'}: {_clip(text)}" for role, text in recent]
        lines.append(f"Customer question: {question}")
        return "\n".join(lines)

    async def answer(
        self, customer_id: str, question: str, history: Sequence[tuple[str, str]] = (), force_web: bool = False
    ) -> BotReply:
        store = self.memory(customer_id)
        try:
            embedding = self.embed_fn(question)
        except Exception:
            embedding = None
        embedding_tokens = getattr(self.embed_fn, "last_tokens", 0)

        if embedding is not None and not force_web:
            match = store.find_similar(question, self.settings.similarity_threshold, embedding=embedding)
            if match:
                reply = BotReply(
                    match.answer, match.agent, "memory", embedding_tokens=embedding_tokens,
                    similarity=match.similarity, remembered_at=match.timestamp,
                )
                store.log_turn(question, reply.text, reply.agent, reply.source)
                return reply

        try:
            outcome = await self.run_team(self.build_task(question, history), store.customer_id)
        except Exception as exc:
            return BotReply(
                f"Sorry, something went wrong while contacting our assistants ({type(exc).__name__}). "
                "Please try again, or use **Talk to a human**.",
                TRIAGE, "error", embedding_tokens=embedding_tokens,
            )

        if outcome.agent == TRIAGE:
            source = "clarify"
        elif outcome.search_failed and not outcome.escalated:
            # The model sometimes apologises instead of escalating; the service escalates for it.
            source = "escalated"
            ticket = self.create_ticket(customer_id, f"Web search failed for: {_clip(question, 150)}")
            outcome.text += f"\n\n🙋 I couldn't reach live sources, so I've created ticket **{ticket}** for a human colleague."
        elif outcome.escalated:
            source = "escalated"
        else:
            source = "web"
            if embedding is not None:
                store.save(question, outcome.text, outcome.agent, embedding=embedding)
        store.log_turn(question, outcome.text, outcome.agent, source)
        return BotReply(
            outcome.text, outcome.agent, source, outcome.prompt_tokens, outcome.completion_tokens, embedding_tokens
        )

    def create_ticket(self, customer_id: str, reason: str) -> str:
        ticket = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        path = self.settings.escalations_file
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().isoformat(timespec="seconds")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {ticket} customer={safe_customer_id(customer_id)} reason={reason}\n")
        return ticket

    async def _run_autogen_team(self, task: str, customer_id: str) -> TeamOutcome:
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        settings = self.settings

        async def web_search(query: str) -> str:
            """Search Google for up-to-date information. Returns compact results with links."""
            import asyncio

            return await asyncio.to_thread(
                run_web_search, query, settings.serpapi_api_key, settings.search_provider
            )

        def escalate_to_human(reason: str) -> str:
            """Hand the conversation to a human support agent when you cannot answer confidently."""
            return f"Ticket {self.create_ticket(customer_id, reason)} created; a human will follow up."

        client = OpenAIChatCompletionClient(
            model=settings.model, api_key=settings.openai_api_key,
            max_tokens=settings.max_completion_tokens, temperature=0.3,
        )
        try:
            return await run_team(client, web_search, escalate_to_human, task)
        finally:
            await client.close()
