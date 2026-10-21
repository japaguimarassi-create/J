import re
import urllib.parse
from typing import Any

from deta.knowledge import KnowledgeStore, _tokens
from deta.web import WebResearchError, read_web_page, search_web


class DetaAssistant:
    """Retrieval assistant using public web pages and a local knowledge index, without an AI API."""

    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store or KnowledgeStore()

    def ask(
        self,
        question: str,
        web: bool = True,
        max_results: int = 5,
        pages_to_read: int = 3,
    ) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            raise ValueError("Question cannot be empty.")
        if not 1 <= max_results <= 10:
            raise ValueError("max_results must be between 1 and 10.")
        if not 0 <= pages_to_read <= 5:
            raise ValueError("pages_to_read must be between 0 and 5.")

        sources: list[dict[str, str]] = []
        errors: list[str] = []
        local_results = self.store.search(question, limit=5)
        if web:
            if _looks_like_url(question):
                try:
                    page = read_web_page(question)
                    self.store.add(page["title"], page["url"], page["content"], "web-page")
                    sources.append({
                        "title": page["title"],
                        "url": page["url"],
                        "snippet": page["content"][:1200],
                    })
                except (ValueError, WebResearchError) as exc:
                    errors.append(str(exc))
            else:
                try:
                    results = search_web(question, limit=max_results)
                    for result in results[:pages_to_read]:
                        try:
                            page = read_web_page(result["url"], max_chars=16_000)
                            self.store.add(page["title"], page["url"], page["content"], "web-page")
                            sources.append({
                                "title": page["title"],
                                "url": page["url"],
                                "snippet": page["content"][:1200],
                            })
                        except (ValueError, WebResearchError) as exc:
                            errors.append(f"{result['url']}: {exc}")
                            if result.get("snippet"):
                                sources.append({
                                    "title": result["title"],
                                    "url": result["url"],
                                    "snippet": result["snippet"],
                                })
                    if not sources:
                        sources = [
                            {
                                "title": item["title"],
                                "url": item["url"],
                                "snippet": item["snippet"],
                            }
                            for item in results
                        ]
                except (ValueError, WebResearchError) as exc:
                    errors.append(str(exc))

        indexed = self.store.search(question, limit=8)
        if not indexed:
            indexed = local_results
        summary = _extractive_summary(question, indexed, sources)
        if not summary:
            if errors:
                summary = (
                    "Não consegui obter fontes utilizáveis para responder. "
                    "Confira a conexão ou tente uma consulta mais específica.\n\n"
                    + "\n".join(f"- {item}" for item in errors[:3])
                )
            else:
                summary = (
                    "Ainda não encontrei conteúdo suficiente para responder com segurança. "
                    "Tente uma pergunta mais específica ou informe um site público para consultar."
                )
        return {
            "question": question,
            "answer": summary,
            "web_enabled": web,
            "sources": _deduplicate_sources(sources, indexed),
            "errors": errors[:5],
            "knowledge_documents": self.store.count(),
            "mode": "web retrieval + local indexed knowledge; no AI API",
        }


def _looks_like_url(value: str) -> bool:
    parsed = urllib.parse.urlsplit(value)
    return parsed.scheme == "https" and bool(parsed.hostname)


def _extractive_summary(
    question: str,
    indexed: list[dict[str, Any]],
    fresh_sources: list[dict[str, str]],
) -> str:
    query_tokens = set(_tokens(question))
    candidates: list[tuple[float, str, str]] = []
    source_lookup: dict[str, str] = {}

    for source in fresh_sources:
        url = source.get("url", "")
        source_lookup[url] = source.get("title", url)
        snippet = source.get("snippet", "")
        for sentence in re.split(r"(?<=[.!?])\\s+|\\n+", snippet):
            sentence = sentence.strip()
            if len(sentence) < 40:
                continue
            score = _sentence_score(sentence, query_tokens)
            if score > 0:
                candidates.append((score + 0.25, sentence, url))

    for document in indexed:
        url = document.get("url", "")
        source_lookup[url] = document.get("title", url)
        content = document.get("content", "")
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", content):
            sentence = sentence.strip()
            if len(sentence) < 45:
                continue
            score = _sentence_score(sentence, query_tokens)
            if score > 0:
                candidates.append((score, sentence, url))

    best_by_text: dict[str, tuple[float, str, str]] = {}
    for score, sentence, url in candidates:
        normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
        if len(normalized) < 35:
            continue
        current = best_by_text.get(normalized)
        if current is None or score > current[0]:
            best_by_text[normalized] = (score, sentence, url)
    ranked = sorted(best_by_text.values(), key=lambda item: item[0], reverse=True)
    selected = []
    seen_sources = set()
    for score, sentence, url in ranked:
        normalized = re.sub(r"\W+", " ", sentence.lower()).strip()
        if any(_text_similarity(normalized, re.sub(r"\W+", " ", item[1].lower()).strip()) > 0.86 for item in selected):
            continue
        if len(sentence) > 520:
            sentence = sentence[:517].rsplit(" ", 1)[0] + "..."
        selected.append((score, sentence, url))
        seen_sources.add(url)
        if len(selected) >= 6:
            break

    if not selected and fresh_sources:
        for source in fresh_sources:
            url = source.get("url", "")
            source_lookup[url] = source.get("title", url)
            for sentence in re.split(r"(?<=[.!?])\\s+|\\n+", source.get("snippet", "")):
                sentence = sentence.strip()
                if len(sentence) >= 45:
                    selected.append((0.0, sentence[:517].rsplit(" ", 1)[0] + ("..." if len(sentence) > 520 else ""), url))
                    if len(selected) >= 3:
                        break
            if selected:
                break
    if not selected:
        return ""
    response = ["Encontrei estas informações nas fontes consultadas:"]
    for _, sentence, url in selected:
        if url:
            response.append(f"- {sentence} [Fonte: {source_lookup.get(url, url)} — {url}]")
        else:
            response.append(f"- {sentence}")
    return "\n\n".join(response)


def _sentence_score(sentence: str, query_tokens: set[str]) -> float:
    words = _tokens(sentence)
    if not words or not query_tokens:
        return 0.0
    overlap = set(words).intersection(query_tokens)
    if not overlap:
        return 0.0
    return len(overlap) / max(1, len(query_tokens)) + 0.05 * len(overlap)


def _text_similarity(left: str, right: str) -> float:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _deduplicate_sources(
    fresh_sources: list[dict[str, str]],
    indexed: list[dict[str, Any]],
) -> list[dict[str, str]]:
    output = []
    seen = set()
    for item in fresh_sources + [
        {"title": str(doc.get("title", "")), "url": str(doc.get("url", "")), "snippet": str(doc.get("snippet", ""))}
        for doc in indexed
    ]:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            output.append({"title": item.get("title", url), "url": url, "snippet": item.get("snippet", "")[:700]})
        if len(output) >= 8:
            break
    return output
