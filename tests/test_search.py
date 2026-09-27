from support_bot.search import compact_results, detect_provider, from_serper, search_failed


def test_serper_response_is_normalized_and_compacted():
    serper = {
        "answerBox": {"answer": "Sept 30"},
        "knowledgeGraph": {"title": "India", "description": "Cricket team"},
        "topStories": [{"title": "India squad named", "source": "ESPN", "date": "2h ago", "link": "http://s"}],
        "organic": [{"title": "Schedule", "snippet": "India vs Aus", "link": "http://o", "date": "Sep 1"}],
    }
    text = compact_results(from_serper(serper))
    assert "Answer box: Sept 30" in text
    assert "India squad named" in text
    assert "Schedule [Sep 1]: India vs Aus" in text


def test_provider_is_detected_from_key_format():
    assert detect_provider("a" * 64, "auto") == "serpapi"
    assert detect_provider("a" * 40, "auto") == "serper"
    assert detect_provider("a" * 40, "serpapi") == "serpapi"


def test_failed_searches_are_recognized():
    assert search_failed("SEARCH_ERROR: Invalid API key")
    assert search_failed("NO_RESULTS: nothing")
    assert not search_failed("1. Title: snippet")


def test_compacts_organic_results_to_the_requested_count():
    data = {"organic_results": [{"title": f"T{i}", "snippet": f"S{i}", "link": f"http://x/{i}"} for i in range(10)]}
    text = compact_results(data, max_results=3)
    assert "T0" in text and "T2" in text
    assert "T3" not in text


def test_includes_answer_box_and_top_stories_highlights():
    data = {
        "answer_box": {"answer": "42"},
        "top_stories": [{"title": "Big news", "source": "BBC", "date": "1 hour ago", "link": "http://n"}],
    }
    text = compact_results(data)
    assert "Answer box: 42" in text
    assert "Big news" in text and "BBC" in text


def test_output_is_capped_to_max_chars():
    data = {"organic_results": [{"title": "t" * 200, "snippet": "s" * 1000, "link": "l"} for _ in range(5)]}
    assert len(compact_results(data, max_chars=500)) <= 500


def test_reports_no_results_when_response_is_empty():
    assert compact_results({}).startswith("NO_RESULTS")


def test_reports_api_error_message():
    assert compact_results({"error": "Invalid API key"}) == "SEARCH_ERROR: Invalid API key"
