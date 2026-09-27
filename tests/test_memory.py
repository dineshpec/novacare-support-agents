import math

from support_bot.memory import MemoryStore, cosine


def fake_embed(text: str) -> list[float]:
    """Deterministic bag-of-words embedding over a tiny vocabulary."""
    vocab = ["llm", "gpt", "movie", "oscar", "cricket", "score", "python", "job", "latest", "release"]
    words = text.lower().replace("?", "").split()
    return [float(words.count(v)) for v in vocab]


def test_cosine_of_identical_vectors_is_one():
    assert math.isclose(cosine([1, 2, 3], [1, 2, 3]), 1.0)


def test_cosine_with_zero_vector_is_zero():
    assert cosine([0, 0], [1, 1]) == 0.0


def test_finds_saved_answer_for_similar_question(tmp_path):
    store = MemoryStore("alice", tmp_path, fake_embed)
    store.save("latest gpt llm release", "GPT-5 was released.", "ai_agent")
    match = store.find_similar("latest llm gpt release?", threshold=0.9)
    assert match is not None
    assert match.answer == "GPT-5 was released."
    assert match.agent == "ai_agent"
    assert match.similarity >= 0.9


def test_returns_none_when_no_question_is_similar_enough(tmp_path):
    store = MemoryStore("alice", tmp_path, fake_embed)
    store.save("latest gpt llm release", "GPT-5 was released.", "ai_agent")
    assert store.find_similar("cricket score", threshold=0.88) is None


def test_newest_answer_wins_for_the_same_question(tmp_path):
    store = MemoryStore("alice", tmp_path, fake_embed)
    store.save("latest gpt release", "old answer", "ai_agent")
    store.save("latest gpt release", "fresh answer", "ai_agent")
    assert store.find_similar("latest gpt release", 0.9).answer == "fresh answer"


def test_memory_is_isolated_per_customer(tmp_path):
    MemoryStore("alice", tmp_path, fake_embed).save("movie oscar", "Oppenheimer", "movie_agent")
    assert MemoryStore("bob", tmp_path, fake_embed).find_similar("movie oscar", 0.5) is None


def test_saved_answers_persist_across_store_instances(tmp_path):
    MemoryStore("alice", tmp_path, fake_embed).save("python job", "Many openings.", "job_agent")
    assert MemoryStore("alice", tmp_path, fake_embed).find_similar("python job", 0.9) is not None


def test_transcript_is_written_as_readable_text(tmp_path):
    store = MemoryStore("alice", tmp_path, fake_embed)
    store.log_turn("What is new in AI?", "Lots of things.", "ai_agent", "web")
    content = store.transcript_path.read_text(encoding="utf-8")
    assert "Customer: What is new in AI?" in content
    assert "Lots of things." in content
    assert store.transcript_path.suffix == ".txt"


def test_customer_id_is_sanitized_for_file_names(tmp_path):
    store = MemoryStore("../evil/ id", tmp_path, fake_embed)
    assert store.transcript_path.parent == tmp_path
    assert ".." not in store.transcript_path.name and "/" not in store.transcript_path.name


def test_ids_that_sanitize_alike_do_not_share_memory(tmp_path):
    MemoryStore("alice/1", tmp_path, fake_embed).save("movie oscar", "Oppenheimer", "movie_agent")
    assert MemoryStore("alice_1", tmp_path, fake_embed).find_similar("movie oscar", 0.5) is None
    long_a, long_b = "x" * 100 + "a", "x" * 100 + "b"
    MemoryStore(long_a, tmp_path, fake_embed).save("movie oscar", "Oppenheimer", "movie_agent")
    assert MemoryStore(long_b, tmp_path, fake_embed).find_similar("movie oscar", 0.5) is None
