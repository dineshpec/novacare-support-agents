import requests

SERPAPI_URL = "https://serpapi.com/search.json"
SERPER_URL = "https://google.serper.dev/search"
FAILURE_PREFIXES = ("SEARCH_ERROR", "NO_RESULTS")


def search_failed(text: str) -> bool:
    return str(text).startswith(FAILURE_PREFIXES)


def detect_provider(api_key: str, provider: str = "auto") -> str:
    """SerpAPI keys are 64 characters; Serper.dev keys are 40."""
    if provider in ("serpapi", "serper"):
        return provider
    return "serpapi" if len(api_key) >= 64 else "serper"


def from_serper(data: dict) -> dict:
    """Map a Serper.dev response onto the SerpAPI field names used by compact_results."""
    return {
        "error": data.get("message") if "organic" not in data and data.get("message") else None,
        "answer_box": data.get("answerBox"),
        "knowledge_graph": data.get("knowledgeGraph"),
        "top_stories": data.get("topStories"),
        "organic_results": data.get("organic"),
    }


def _clip(text, limit: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def compact_results(data: dict, max_results: int = 5, max_chars: int = 2500) -> str:
    """Reduce a SerpAPI response to the few lines an LLM needs, to keep prompts small."""
    if data.get("error"):
        return f"SEARCH_ERROR: {data['error']}"

    lines: list[str] = []
    box = data.get("answer_box") or {}
    box_text = box.get("answer") or box.get("snippet") or box.get("result")
    if box_text:
        lines.append(f"Answer box: {_clip(box_text, 300)}")

    sports = data.get("sports_results") or {}
    if sports:
        game = sports.get("game_spotlight") or {}
        teams = ", ".join(f"{t.get('name', '')} {t.get('score', '')}".strip() for t in game.get("teams") or [])
        parts = [sports.get("title"), game.get("league"), game.get("date"), game.get("status"), teams]
        summary = " | ".join(p for p in parts if p)
        if summary:
            lines.append(f"Sports: {_clip(summary, 300)}")

    graph = data.get("knowledge_graph") or {}
    if graph.get("description"):
        lines.append(f"Knowledge: {_clip(graph.get('title'), 60)} - {_clip(graph['description'], 250)}")

    for story in (data.get("top_stories") or [])[:3]:
        lines.append(
            f"News: {_clip(story.get('title'), 120)} ({story.get('source', '')}, {story.get('date', '')}) "
            f"{story.get('link', '')}"
        )

    for i, item in enumerate((data.get("organic_results") or [])[:max_results], 1):
        date = f" [{item['date']}]" if item.get("date") else ""
        lines.append(
            f"{i}. {_clip(item.get('title'), 120)}{date}: {_clip(item.get('snippet'), 280)} ({item.get('link', '')})"
        )

    if not lines:
        return "NO_RESULTS: the search returned nothing useful."
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def serpapi_search(query: str, api_key: str, max_results: int = 5, timeout: float = 20) -> str:
    """Run a Google search through SerpAPI. Returns text and never raises, so agents can recover."""
    try:
        response = requests.get(
            SERPAPI_URL,
            params={"engine": "google", "q": query, "api_key": api_key, "num": max_results, "hl": "en"},
            timeout=timeout,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        return f"SEARCH_ERROR: {type(exc).__name__}"
    if response.status_code != 200 and not data.get("error"):
        return f"SEARCH_ERROR: HTTP {response.status_code}"
    return compact_results(data, max_results=max_results)


def serper_search(query: str, api_key: str, max_results: int = 5, timeout: float = 20) -> str:
    """Run a Google search through Serper.dev. Returns text and never raises."""
    try:
        response = requests.post(
            SERPER_URL,
            json={"q": query, "num": max_results, "hl": "en"},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        return f"SEARCH_ERROR: {type(exc).__name__}"
    if response.status_code != 200:
        return f"SEARCH_ERROR: HTTP {response.status_code} {data.get('message', '')}".strip()
    return compact_results(from_serper(data), max_results=max_results)


def web_search(query: str, api_key: str, provider: str = "auto") -> str:
    if detect_provider(api_key, provider) == "serper":
        return serper_search(query, api_key)
    return serpapi_search(query, api_key)
