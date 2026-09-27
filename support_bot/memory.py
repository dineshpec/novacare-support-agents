import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

EmbedFn = Callable[[str], list[float]]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def safe_customer_id(customer_id: str) -> str:
    raw = customer_id.strip() or "guest"
    readable = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_")[:40] or "guest"
    # The hash keeps IDs that sanitize to the same text (e.g. "a/1" and "a_1") in separate files.
    return f"{readable}-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


@dataclass
class MemoryMatch:
    question: str
    answer: str
    agent: str
    timestamp: str
    similarity: float


class MemoryStore:
    """Per-customer memory: a readable .txt transcript plus a .jsonl index of answered questions."""

    def __init__(self, customer_id: str, base_dir: Path, embed_fn: EmbedFn):
        self.customer_id = safe_customer_id(customer_id)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.embed_fn = embed_fn
        self.transcript_path = self.base_dir / f"{self.customer_id}.txt"
        self.index_path = self.base_dir / f"{self.customer_id}.jsonl"

    def _entries(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        entries = []
        for line in self.index_path.read_text(encoding="utf-8").splitlines():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def count(self) -> int:
        return len(self._entries())

    def find_similar(self, question: str, threshold: float, embedding: list[float] | None = None) -> MemoryMatch | None:
        entries = self._entries()
        if not entries:
            return None
        vector = embedding if embedding is not None else self.embed_fn(question)
        best, best_score = None, -1.0
        for entry in entries:
            score = cosine(vector, entry["embedding"])
            if score >= best_score:  # ">=" so the newest entry wins ties (e.g. after a web refresh)
                best, best_score = entry, score
        if best is None or best_score < threshold:
            return None
        return MemoryMatch(best["question"], best["answer"], best["agent"], best["timestamp"], best_score)

    def save(self, question: str, answer: str, agent: str, embedding: list[float] | None = None) -> None:
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": question,
            "answer": answer,
            "agent": agent,
            "embedding": embedding if embedding is not None else self.embed_fn(question),
        }
        with self.index_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def log_turn(self, question: str, answer: str, agent: str, source: str) -> None:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.transcript_path.open("a", encoding="utf-8") as f:
            f.write(f"[{stamp}] Customer: {question}\n")
            f.write(f"[{stamp}] {agent} ({source}): {answer}\n\n")
