import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    serpapi_api_key: str
    model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    similarity_threshold: float = 0.88
    data_dir: Path = PROJECT_ROOT / "data"
    history_turns: int = 3
    max_completion_tokens: int = 600
    search_provider: str = "auto"

    @property
    def memory_dir(self) -> Path:
        return self.data_dir / "memory"

    @property
    def escalations_file(self) -> Path:
        return self.data_dir / "escalations.txt"

    def missing_keys(self) -> list[str]:
        missing = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.serpapi_api_key:
            missing.append("SERPAPI_API_KEY")
        return missing


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        serpapi_api_key=(os.getenv("SERPAPI_API_KEY") or os.getenv("SERPER_API_KEY") or "").strip(),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        similarity_threshold=float(os.getenv("MEMORY_SIMILARITY_THRESHOLD", "0.88")),
        data_dir=Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))),
        history_turns=int(os.getenv("HISTORY_TURNS", "3")),
        max_completion_tokens=int(os.getenv("MAX_COMPLETION_TOKENS", "600")),
        search_provider=os.getenv("SEARCH_PROVIDER", "auto").strip().lower(),
    )
