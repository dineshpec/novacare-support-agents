from support_bot.agents import TeamOutcome
from support_bot.config import Settings
from support_bot.service import SupportService
from tests.test_memory import fake_embed


class FakeTeam:
    def __init__(self, outcome: TeamOutcome):
        self.outcome = outcome
        self.tasks: list[str] = []

    async def __call__(self, task: str, customer_id: str) -> TeamOutcome:
        self.tasks.append(task)
        return self.outcome


def make_service(tmp_path, outcome):
    settings = Settings(openai_api_key="k", serpapi_api_key="k", data_dir=tmp_path, similarity_threshold=0.9)
    team = FakeTeam(outcome)
    return SupportService(settings, embed_fn=fake_embed, run_team=team), team


ANSWER = TeamOutcome(text="GPT-5 was released.", agent="ai_agent", searched=True, prompt_tokens=100, completion_tokens=20)


async def test_first_question_is_answered_from_the_web_and_saved(tmp_path):
    service, team = make_service(tmp_path, ANSWER)
    reply = await service.answer("alice", "latest gpt llm release")
    assert reply.source == "web"
    assert reply.agent == "ai_agent"
    assert reply.prompt_tokens == 100
    assert len(team.tasks) == 1


async def test_repeat_question_is_answered_from_memory_without_running_agents(tmp_path):
    service, team = make_service(tmp_path, ANSWER)
    await service.answer("alice", "latest gpt llm release")
    reply = await service.answer("alice", "latest llm gpt release?")
    assert reply.source == "memory"
    assert reply.text == "GPT-5 was released."
    assert reply.prompt_tokens == 0
    assert len(team.tasks) == 1


async def test_force_web_bypasses_memory(tmp_path):
    service, team = make_service(tmp_path, ANSWER)
    await service.answer("alice", "latest gpt llm release")
    reply = await service.answer("alice", "latest gpt llm release", force_web=True)
    assert reply.source == "web"
    assert len(team.tasks) == 2


async def test_clarifying_questions_are_not_saved_to_memory(tmp_path):
    clarify = TeamOutcome(text="Which sport?", agent="triage_agent")
    service, team = make_service(tmp_path, clarify)
    first = await service.answer("alice", "latest score")
    second = await service.answer("alice", "latest score")
    assert first.source == second.source == "clarify"
    assert len(team.tasks) == 2


async def test_escalated_answers_are_flagged_and_not_saved(tmp_path):
    escalated = TeamOutcome(text="A human will contact you.", agent="job_agent", escalated=True)
    service, team = make_service(tmp_path, escalated)
    reply = await service.answer("alice", "python job refund")
    assert reply.source == "escalated"
    await service.answer("alice", "python job refund")
    assert len(team.tasks) == 2


async def test_answers_from_failed_searches_are_escalated_and_not_saved(tmp_path):
    failed = TeamOutcome(text="I can't access that.", agent="sports_agent", searched=True, search_failed=True)
    service, team = make_service(tmp_path, failed)
    reply = await service.answer("alice", "cricket score")
    assert reply.source == "escalated"
    await service.answer("alice", "cricket score")
    assert len(team.tasks) == 2
    assert "escalations.txt" in [p.name for p in tmp_path.iterdir()]


async def test_recent_history_is_included_in_task_for_follow_ups(tmp_path):
    service, team = make_service(tmp_path, ANSWER)
    history = [("user", "Who won the cricket world cup?"), ("assistant", "India won.")]
    await service.answer("alice", "Who was captain?", history=history)
    assert "Who won the cricket world cup?" in team.tasks[0]
    assert "India won." in team.tasks[0]
    assert "Who was captain?" in team.tasks[0]


async def test_agent_failure_returns_friendly_error(tmp_path):
    async def broken(task, customer_id):
        raise RuntimeError("boom")

    settings = Settings(openai_api_key="k", serpapi_api_key="k", data_dir=tmp_path)
    service = SupportService(settings, embed_fn=fake_embed, run_team=broken)
    reply = await service.answer("alice", "anything")
    assert reply.source == "error"


def test_human_escalation_ticket_is_written(tmp_path):
    service, _ = make_service(tmp_path, ANSWER)
    ticket = service.create_ticket("alice", "Customer asked for a human")
    content = (tmp_path / "escalations.txt").read_text(encoding="utf-8")
    assert ticket in content and "alice" in content
