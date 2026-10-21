from deta.knowledge import KnowledgeStore


def test_knowledge_store_add_search_and_deduplicate(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    page = {
        "title": "Python iterators",
        "url": "https://docs.example.org/python/iterators",
        "content": (
            "Python iterators provide a standard way to process sequences lazily. "
            "The iterator protocol uses iter and next to retrieve values one at a time. "
            "This method helps process large collections without loading everything into memory."
        ),
    }
    first = store.add(page["title"], page["url"], page["content"])
    second = store.add(page["title"], page["url"], page["content"])
    assert first["id"] == second["id"]
    assert store.count() == 1
    results = store.search("Python iterators process large collections", limit=3)
    assert results
    assert results[0]["title"] == "Python iterators"
    assert results[0]["url"] == page["url"]


def test_knowledge_store_persists_between_instances(tmp_path):
    path = tmp_path / "knowledge.json"
    first = KnowledgeStore(path)
    first.add(
        "Project safety",
        "https://docs.example.org/safety",
        "Run generated software with restricted permissions and isolate it from credentials and production systems.",
    )
    second = KnowledgeStore(path)
    assert second.count() == 1
    assert second.search("restricted permissions credentials")[0]["title"] == "Project safety"


def test_knowledge_store_rejects_non_https_sources(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    try:
        store.add("Bad", "http://example.org", "Enough text that would otherwise be long enough to index.")
        assert False, "Expected source URL validation to fail"
    except ValueError as exc:
        assert "HTTPS" in str(exc)


def test_knowledge_store_clear_is_explicit(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.json")
    store.add("A title", "https://example.org/a", "This content is long enough to be accepted into the local knowledge index.")
    assert store.clear() == 1
    assert store.count() == 0
