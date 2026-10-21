from deta.assistant import DetaAssistant
from deta.knowledge import KnowledgeStore


def test_assistant_answers_from_local_index_without_network(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    store.add(
        "Safer code execution",
        "https://docs.example.org/security",
        "Generated code should run in a disposable sandbox without API keys, personal tokens, production credentials, or unrestricted filesystem access.",
    )
    result = DetaAssistant(store).ask("How do I sandbox generated code?", web=False)
    assert "sandbox" in result["answer"].lower()
    assert result["web_enabled"] is False
    assert result["sources"]
    assert result["sources"][0]["url"] == "https://docs.example.org/security"


def test_assistant_reports_no_sources_instead_of_inventing(tmp_path):
    result = DetaAssistant(KnowledgeStore(tmp_path / "empty.json")).ask("unrelated unknown topic", web=False)
    assert "não encontrei" in result["answer"].lower() or "ainda não encontrei" in result["answer"].lower()
    assert result["sources"] == []


def test_assistant_can_read_direct_public_url_without_api(monkeypatch, tmp_path):
    from deta import assistant

    monkeypatch.setattr(
        assistant,
        "read_web_page",
        lambda url, max_chars=20000: {
            "title": "Example paper",
            "url": "https://example.org/paper",
            "content": "A practical paper explains local retrieval, searchable notes, and source citations for factual answers without a paid AI API.",
            "content_type": "text/html",
        },
    )
    result = DetaAssistant(KnowledgeStore(tmp_path / "kb.json")).ask("https://example.org/paper", web=True)
    assert result["sources"]
    assert "example paper" in result["sources"][0]["title"].lower()
