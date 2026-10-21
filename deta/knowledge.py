import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from deta.data import valid_source_url


MAX_DOCUMENTS = 1500
MAX_DOCUMENT_CHARS = 20_000
MAX_DATABASE_BYTES = 32 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"[^\W_]+(?:[_'-][^\W_]+)*", re.UNICODE)
STOP_WORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "dela", "dele",
    "do", "dos", "e", "em", "entre", "essa", "esse", "esta", "este", "eu",
    "foi", "for", "from", "how", "is", "it", "na", "nas", "no", "nos", "o",
    "of", "os", "ou", "para", "por", "que", "qual", "quais", "quando", "se",
    "sobre", "the", "to", "um", "uma", "what", "when", "where", "which", "who",
    "why", "with",
}


def default_knowledge_path() -> Path:
    custom = os.getenv("DETA_HOME")
    base = Path(custom).expanduser() if custom else Path.home() / ".local" / "share" / "deta"
    return base / "knowledge.json"


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text or "")
        if len(token) > 1 and token.lower() not in STOP_WORDS
    ]


def _clean_content(value: str) -> str:
    value = re.sub(r"\r\n?", "\n", value or "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()[:MAX_DOCUMENT_CHARS]


class KnowledgeStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_knowledge_path()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise ValueError(f"Knowledge database is unreadable: {self.path}")
        if not isinstance(payload, list):
            raise ValueError("Knowledge database must contain a JSON list.")
        documents = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if not isinstance(item.get("url"), str) or not valid_source_url(item["url"]):
                continue
            if not isinstance(item.get("content"), str) or not item["content"].strip():
                continue
            documents.append(item)
        return documents[-MAX_DOCUMENTS:]

    def _save(self, documents: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        kept = documents[-MAX_DOCUMENTS:]
        while kept:
            serialized = json.dumps(kept, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if len(serialized) <= MAX_DATABASE_BYTES:
                break
            kept.pop(0)
        file_descriptor, temporary_path = tempfile.mkstemp(
            dir=self.path.parent,
            prefix=self.path.name + ".",
            suffix=".tmp",
        )
        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as stream:
                json.dump(kept, stream, ensure_ascii=False, separators=(",", ":"))
            os.replace(temporary_path, self.path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    def add(
        self,
        title: str,
        url: str,
        content: str,
        source_type: str = "web",
    ) -> dict[str, Any]:
        if not valid_source_url(url):
            raise ValueError("Knowledge records require an HTTPS source URL.")
        cleaned = _clean_content(content)
        if len(cleaned) < 40:
            raise ValueError("Document text is too short to store.")
        digest = hashlib.sha256((url + "\0" + cleaned).encode("utf-8")).hexdigest()
        document = {
            "id": digest,
            "title": (title or urlsplit(url).hostname or "Untitled source")[:300],
            "url": url,
            "content": cleaned,
            "source_type": (source_type or "web")[:40],
            "sha256": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
        }
        records = self._load()
        existing = next((index for index, row in enumerate(records) if row.get("id") == digest), None)
        if existing is not None:
            records[existing] = document
        else:
            records.append(document)
        self._save(records)
        return {"id": digest, "title": document["title"], "url": url, "characters": len(cleaned)}

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query_tokens = list(dict.fromkeys(_tokens(query)))
        if not query_tokens:
            return []
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        documents = self._load()
        if not documents:
            return []
        corpus_tokens = [_tokens(item["title"] + " " + item["content"]) for item in documents]
        document_frequency = {
            token: sum(1 for tokens in corpus_tokens if token in set(tokens))
            for token in query_tokens
        }
        scored = []
        for document, tokens in zip(documents, corpus_tokens):
            if not tokens:
                continue
            term_counts: dict[str, int] = {}
            for token in tokens:
                term_counts[token] = term_counts.get(token, 0) + 1
            score = 0.0
            title_tokens = set(_tokens(document["title"]))
            for token in query_tokens:
                frequency = term_counts.get(token, 0)
                if frequency == 0:
                    continue
                idf = 1.0 + (len(documents) / (1 + document_frequency[token]))
                normalized_frequency = frequency / (frequency + 1.2)
                score += idf * normalized_frequency * (3.0 if token in title_tokens else 1.0)
            if score <= 0:
                continue
            query_set = set(query_tokens)
            content = document["content"]
            sentences = re.split(r"(?<=[.!?])\s+|\n+", content)
            sentence_scores = []
            for sentence in sentences:
                sentence_tokens = set(_tokens(sentence))
                overlap = len(query_set.intersection(sentence_tokens))
                if overlap:
                    sentence_scores.append((overlap / max(1, len(query_set)), sentence.strip()))
            sentence_scores.sort(key=lambda item: item[0], reverse=True)
            snippet = sentence_scores[0][1] if sentence_scores else content[:360]
            if len(snippet) > 520:
                snippet = snippet[:517].rsplit(" ", 1)[0] + "..."
            scored.append({
                "title": document["title"],
                "url": document["url"],
                "score": round(score, 4),
                "snippet": snippet,
                "content": content,
                "source_type": document.get("source_type", "web"),
                "sha256": document.get("sha256", ""),
            })
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    def count(self) -> int:
        return len(self._load())

    def clear(self) -> int:
        current_count = len(self._load())
        self._save([])
        return current_count
