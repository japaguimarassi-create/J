import argparse
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


TOKEN_PATTERN = re.compile(r"C\+\+|C#|\.NET|[^\W_]+(?:[_+#.-][^\W_+#.-]+)*", re.IGNORECASE | re.UNICODE)
SCHEMA_VERSION = 1


def tokenize(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return [match.group(0) for match in TOKEN_PATTERN.finditer(normalized) if len(match.group(0)) <= 80]


def build_index(documents_jsonl, output_db):
    source = Path(documents_jsonl)
    target = Path(output_db)
    if not source.is_file():
        raise SystemExit("Knowledge metadata file not found: " + str(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    if temp.exists():
        temp.unlink()
    connection = sqlite3.connect(temp)
    try:
        connection.executescript("""
            PRAGMA journal_mode=DELETE;
            PRAGMA synchronous=FULL;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                source_title TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                license TEXT NOT NULL,
                license_url TEXT NOT NULL,
                attribution TEXT NOT NULL,
                category_json TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL
            );
            CREATE TABLE postings (
                term TEXT NOT NULL,
                document_id TEXT NOT NULL,
                frequency INTEGER NOT NULL,
                PRIMARY KEY (term, document_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE INDEX postings_by_document ON postings(document_id);
            CREATE INDEX documents_by_source ON documents(source_id);
        """)
        connection.execute("PRAGMA foreign_keys=ON")
        document_count = 0
        token_count = 0
        with source.open("r", encoding="utf-8") as input_file:
            for line_number, line in enumerate(input_file, 1):
                if not line.strip():
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError("Invalid JSON on line " + str(line_number)) from error
                required = ("id", "source_id", "source_title", "title", "url", "license", "license_url", "attribution", "category", "retrieved_at", "content_sha256", "text")
                if any(not doc.get(key) for key in required):
                    raise ValueError("Missing required provenance fields on line " + str(line_number))
                if not str(doc["url"]).startswith("https://") or not str(doc["license_url"]).startswith("https://"):
                    raise ValueError("Only HTTPS source and license URLs are accepted")
                body = str(doc["text"]).strip()
                tokens = tokenize(str(doc["title"]) + "\n" + body)
                if len(tokens) < 40:
                    continue
                if hashlib.sha256(body.encode("utf-8")).hexdigest() != doc["content_sha256"]:
                    raise ValueError("Content hash mismatch for " + str(doc["id"]))
                counts = Counter(tokens)
                connection.execute(
                    "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        doc["id"], doc["source_id"], doc["source_title"], doc["title"], doc["url"],
                        doc["license"], doc["license_url"], doc["attribution"],
                        json.dumps(doc["category"], ensure_ascii=False),
                        doc["retrieved_at"], doc["content_sha256"], body, len(tokens)
                    )
                )
                connection.executemany(
                    "INSERT INTO postings(term, document_id, frequency) VALUES (?, ?, ?)",
                    [(term, doc["id"], frequency) for term, frequency in counts.items()]
                )
                document_count += 1
                token_count += len(tokens)
        if document_count == 0:
            raise ValueError("No valid documents found for the local search index")
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES (?,?)",
            [
                ("schema_version", str(SCHEMA_VERSION)),
                ("document_count", str(document_count)),
                ("token_count", str(token_count)),
                ("source_manifest", "ai/knowledge_sources.json"),
                ("index_type", "local BM25 lexical retrieval with source attribution")
            ]
        )
        connection.commit()
        connection.execute("PRAGMA optimize")
    finally:
        connection.close()
    temp.replace(target)
    return {"index": str(target), "documents": document_count, "tokens": token_count}


def make_snippet(text, terms, max_chars=420):
    lowered = text.casefold()
    hits = [lowered.find(term.casefold()) for term in terms]
    hits = [position for position in hits if position >= 0]
    center = min(hits) if hits else 0
    start = max(0, center - max_chars // 3)
    end = min(len(text), start + max_chars)
    excerpt = text[start:end].strip()
    if start:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt += "…"
    return excerpt


def search_index(index_path, query, limit=5):
    query_tokens = list(dict.fromkeys(tokenize(query)))
    if not query_tokens:
        return []
    limit = max(1, min(int(limit), 20))
    connection = sqlite3.connect(str(index_path))
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT value FROM metadata WHERE key='document_count'").fetchone()
        if not row:
            raise ValueError("Knowledge index has no metadata")
        total_docs = int(row["value"])
        placeholders = ",".join("?" for _ in query_tokens)
        df_rows = connection.execute(
            "SELECT term, COUNT(*) AS df FROM postings WHERE term IN (" + placeholders + ") GROUP BY term",
            query_tokens
        ).fetchall()
        document_frequency = {item["term"]: item["df"] for item in df_rows}
        if not document_frequency:
            return []
        avg_length = connection.execute("SELECT AVG(token_count) AS avg FROM documents").fetchone()["avg"] or 1.0
        posting_rows = connection.execute(
            "SELECT p.term,p.document_id,p.frequency,d.token_count FROM postings p JOIN documents d ON d.id=p.document_id WHERE p.term IN (" + placeholders + ")",
            query_tokens
        ).fetchall()
        scores = defaultdict(float)
        hit_terms = defaultdict(set)
        k1, b = 1.5, 0.75
        for posting in posting_rows:
            term = posting["term"]
            frequency = posting["frequency"]
            df = document_frequency[term]
            idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
            length_ratio = posting["token_count"] / avg_length
            denom = frequency + k1 * (1.0 - b + b * length_ratio)
            scores[posting["document_id"]] += idf * (frequency * (k1 + 1.0) / denom)
            hit_terms[posting["document_id"]].add(term)
        ranked_ids = [doc_id for doc_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]]
        output = []
        for doc_id in ranked_ids:
            doc = connection.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            categories = json.loads(doc["category_json"])
            terms = sorted(hit_terms[doc_id], key=len, reverse=True)
            output.append({
                "id": doc["id"],
                "title": doc["title"],
                "source": doc["source_title"],
                "url": doc["url"],
                "license": doc["license"],
                "license_url": doc["license_url"],
                "attribution": doc["attribution"],
                "category": categories,
                "score": round(scores[doc_id], 5),
                "matched_terms": terms,
                "snippet": make_snippet(doc["text"], terms),
                "content_sha256": doc["content_sha256"]
            })
        return output
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Build or query Kowork's local, provenance-preserving documentation index.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--documents", default="data/knowledge/documents.jsonl")
    build.add_argument("--output", default="data/knowledge/knowledge.sqlite3")
    query = sub.add_parser("search")
    query.add_argument("--index", default="data/knowledge/knowledge.sqlite3")
    query.add_argument("--query", required=True)
    query.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build_index(args.documents, args.output), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(search_index(args.index, args.query, args.limit), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
