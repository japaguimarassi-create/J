import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

USER_AGENT = "KoworkKnowledgeCollector/0.1 (+https://github.com/japaguimarassi-create/Z-do-Black-)"
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form", "svg", "noscript", "button", "template"}
BLOCK_TAGS = {"p", "div", "article", "main", "section", "br", "li", "pre", "code", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "td", "th", "dt", "dd"}
SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/-]{12,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|client[_-]?secret|password|private[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{12,}"),
]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
RST_LINK = re.compile(r"\s*<([^>]+)>_")


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.hidden_stack = []
        self.parts = []
        self.links = []
        self.title_depth = 0
        self.title_parts = []
        self.h1_depth = 0
        self.h1_parts = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        hidden = tag in SKIP_TAGS or attr.get("aria-hidden") == "true"
        self.hidden_stack.append(hidden)
        if hidden:
            self.hidden_depth += 1
        if tag == "title":
            self.title_depth += 1
        if tag == "h1":
            self.h1_depth += 1
        if tag == "a" and attr.get("href"):
            self.links.append(attr["href"])

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.hidden_stack:
            if self.hidden_stack.pop():
                self.hidden_depth = max(0, self.hidden_depth - 1)
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        if tag == "h1" and self.h1_depth:
            self.h1_depth -= 1
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.hidden_depth:
            return
        if self.title_depth:
            self.title_parts.append(data)
        if self.h1_depth:
            self.h1_parts.append(data)
        text = data.strip()
        if text:
            self.parts.extend((text, " "))

    def text(self):
        return clean_text("".join(self.parts))

    def title(self):
        return clean_text(" ".join(self.title_parts) or " ".join(self.h1_parts))


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts):
        super().__init__()
        self.allowed_hosts = set(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise urllib.error.URLError("Redirect blocked outside the source HTTPS host allowlist")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def clean_text(value):
    value = html.unescape(value).replace("\x00", " ")
    value = re.sub(r"\r", "\n", value)
    value = re.sub(r"[ \t\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    lines, seen = [], set()
    for raw in value.splitlines():
        line = raw.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        key = re.sub(r"\s+", " ", line).casefold()
        if key not in seen:
            seen.add(key)
            lines.append(line)
    return "\n".join(lines).strip()


def redact_secrets(value):
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


def canonical_url(url):
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))


def allowed_url(url, source):
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return False
        if parsed.hostname not in source["hosts"]:
            return False
        path = urllib.parse.unquote(parsed.path or "/")
        if any(part in {".", ".."} for part in path.split("/")):
            return False
        if any(path.startswith(prefix) for prefix in source.get("exclude_path_prefixes", [])):
            return False
        return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in source["path_prefixes"])
    except (KeyError, TypeError, ValueError):
        return False


def robots_policy(host, cache, opener):
    if host in cache:
        return cache[host]
    parser = urllib.robotparser.RobotFileParser()
    url = "https://" + host + "/robots.txt"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=8) as response:
            data = response.read(512 * 1024 + 1)
            if len(data) > 512 * 1024:
                cache[host] = None
                return None
            parser.parse(data.decode("utf-8", "replace").splitlines())
            cache[host] = parser
            return parser
    except urllib.error.HTTPError as error:
        if error.code == 404:
            parser.parse([])
            cache[host] = parser
            return parser
        if error.code in {401, 403}:
            parser.parse(["User-agent: *", "Disallow: /"])
            cache[host] = parser
            return parser
        cache[host] = None
        return None
    except (OSError, TimeoutError, urllib.error.URLError):
        cache[host] = None
        return None


def fetch_url(url, source, robots_cache, max_bytes, timeout):
    if not allowed_url(url, source):
        raise ValueError("URL outside source allowlist")
    opener = urllib.request.build_opener(SafeRedirectHandler(source["hosts"]))
    policy = robots_policy(urllib.parse.urlsplit(url).hostname, robots_cache, opener)
    if policy is None:
        raise PermissionError("robots.txt could not be verified; source skipped")
    if not policy.can_fetch(USER_AGENT, url):
        raise PermissionError("robots.txt disallows this path")
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,text/plain,text/markdown,application/xhtml+xml;q=0.9,*/*;q=0.1",
        "Accept-Encoding": "identity",
    })
    with opener.open(request, timeout=timeout) as response:
        final_url = canonical_url(response.geturl())
        if not allowed_url(final_url, source):
            raise ValueError("Final URL outside source allowlist")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Page exceeded its byte limit")
        content_type = response.headers.get_content_type()
        charset = response.headers.get_content_charset() or "utf-8"
    try:
        body = data.decode(charset, "replace")
    except LookupError:
        body = data.decode("utf-8", "replace")
    return final_url, content_type, body, len(data)


def parse_page(content_type, body):
    if "html" in content_type or body.lstrip().lower().startswith(("<!doctype html", "<html")):
        parser = PageParser()
        parser.feed(body)
        return parser.title(), parser.text(), parser.links
    links = MARKDOWN_LINK.findall(body) + RST_LINK.findall(body)
    body = re.sub(r"<script\b[^>]*>.*?</script>", " ", body, flags=re.I | re.S)
    body = re.sub(r"<style\b[^>]*>.*?</style>", " ", body, flags=re.I | re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return "", clean_text(body), links


def extract_title(text, fallback):
    for line in text.splitlines():
        candidate = re.sub(r"^#{1,6}\s+", "", line).strip().strip("#").strip()
        if 4 <= len(candidate) <= 180 and not candidate.startswith(("http://", "https://")):
            return candidate
    return fallback


def document_id(source_id, url):
    return hashlib.sha256((source_id + "\0" + url).encode("utf-8")).hexdigest()[:20]


def collect_source(source, args, shared):
    queue = deque((canonical_url(url), 0) for url in source["seed_urls"])
    queued, seen, documents = {canonical_url(url) for url in source["seed_urls"]}, set(), []
    source_bytes = 0
    limit = min(int(source.get("max_pages", args.max_pages_per_source)), args.max_pages_per_source)
    while queue and len(documents) < limit:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        if not allowed_url(url, source):
            continue
        remaining = args.max_total_mib * 1024 * 1024 - shared["total_bytes"]
        if remaining <= 0:
            shared["events"].append({"source": source["id"], "status": "budget_exhausted"})
            break
        page_limit = min(int(source.get("max_page_bytes", 2_000_000)), args.max_page_mib * 1024 * 1024, remaining)
        try:
            final_url, content_type, body, size = fetch_url(url, source, shared["robots"], page_limit, args.timeout)
        except Exception as error:
            shared["events"].append({"source": source["id"], "url": url, "status": "skipped", "reason": str(error)[:240]})
            continue
        source_bytes += size
        shared["total_bytes"] += size
        title, text, links = parse_page(content_type, body)
        text = redact_secrets(clean_text(text))
        if len(text) >= args.min_chars:
            title = title or extract_title(text, final_url)
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            documents.append({
                "id": document_id(source["id"], final_url),
                "source_id": source["id"],
                "source_title": source["title"],
                "title": title[:240],
                "url": final_url,
                "license": source["license"],
                "license_url": source["license_url"],
                "attribution": source["attribution"],
                "category": source["category"],
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "content_sha256": digest,
                "content_chars": len(text),
                "text": text,
            })
            shared["events"].append({"source": source["id"], "url": final_url, "status": "collected", "chars": len(text), "bytes": size})
        else:
            shared["events"].append({"source": source["id"], "url": final_url, "status": "short_or_empty", "chars": len(text)})
        if depth < args.max_depth:
            for href in links:
                next_url = canonical_url(urllib.parse.urljoin(final_url, href))
                if next_url not in queued and allowed_url(next_url, source):
                    queued.add(next_url)
                    queue.append((next_url, depth + 1))
        time.sleep(args.delay)
        if shared["total_bytes"] >= args.max_total_mib * 1024 * 1024:
            break
    return documents, {"pages": len(documents), "bytes": source_bytes}


def write_results(documents, output, report):
    docs_dir = output / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    with (output / "documents.jsonl").open("w", encoding="utf-8") as metadata, (output / "corpus.txt").open("w", encoding="utf-8") as corpus:
        for doc in documents:
            metadata.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
            document_text = (
                "# " + doc["title"] + "\nSource: " + doc["url"] + "\nLicense: "
                + doc["license"] + " (" + doc["license_url"] + ")\nAttribution: "
                + doc["attribution"] + "\n\n" + doc["text"] + "\n"
            )
            (docs_dir / (doc["id"] + ".md")).write_text(document_text, encoding="utf-8")
            corpus.write(document_text + "\n\n")
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Collect a bounded, license-attributed public documentation corpus for Kowork.")
    parser.add_argument("--manifest", default="ai/knowledge_sources.json")
    parser.add_argument("--output-dir", default="data/knowledge")
    parser.add_argument("--max-pages-per-source", type=int, default=40)
    parser.add_argument("--max-total-mib", type=int, default=64)
    parser.add_argument("--max-page-mib", type=int, default=3)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--min-chars", type=int, default=400)
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--include-disabled", action="store_true")
    args = parser.parse_args()
    if min(args.max_pages_per_source, args.max_total_mib, args.max_page_mib, args.min_chars) < 1:
        parser.error("page, corpus and character limits must be positive")
    if args.max_depth < 0 or args.timeout <= 0 or args.delay < 0:
        parser.error("invalid depth, timeout or delay")
    manifest_path, output = Path(args.manifest), Path(args.output_dir)
    if not manifest_path.is_file():
        raise SystemExit("Source manifest not found: " + str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise SystemExit("Unsupported knowledge source manifest schema")
    sources = [source for source in manifest.get("sources", []) if source.get("enabled") or args.include_disabled]
    if not sources:
        raise SystemExit("No enabled sources are configured")
    for source in sources:
        required = {"id", "title", "category", "license", "license_url", "attribution", "hosts", "path_prefixes", "seed_urls"}
        if not required.issubset(source) or not source["hosts"] or not source["path_prefixes"] or not source["seed_urls"]:
            raise SystemExit("Invalid source allowlist: " + str(source.get("id", "unknown")))
        if not all(urllib.parse.urlsplit(url).scheme == "https" and allowed_url(url, source) for url in source["seed_urls"]):
            raise SystemExit("A seed URL is outside its declared HTTPS allowlist: " + source["id"])
    shared = {"robots": {}, "events": [], "total_bytes": 0}
    documents, source_reports = [], []
    for source in sources:
        before = len(documents)
        collected, metrics = collect_source(source, args, shared)
        documents.extend(collected)
        source_reports.append({
            "id": source["id"], "title": source["title"], "license": source["license"],
            "license_url": source["license_url"], "pages_collected": len(documents) - before,
            "bytes_collected": metrics["bytes"]
        })
    unique = {}
    for doc in documents:
        unique.setdefault(doc["content_sha256"], doc)
    documents = list(unique.values())
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(manifest_path),
        "source_count_enabled": len(sources),
        "documents_collected": len(documents),
        "total_download_bytes": shared["total_bytes"],
        "total_characters": sum(doc["content_chars"] for doc in documents),
        "license_attribution_required": True,
        "internet_access": "Direct HTTPS fetch of allowlisted public documentation; no external AI inference API",
        "robots_policy": manifest["policy"]["robots_txt"],
        "sources": source_reports,
        "events": shared["events"]
    }
    write_results(documents, output, report)
    print(json.dumps({key: report[key] for key in ("documents_collected", "total_download_bytes", "total_characters", "sources")}, indent=2, ensure_ascii=False))
    if not documents:
        raise SystemExit("No documents were collected. Inspect robots/access restrictions; the collector never fabricates training data.")


if __name__ == "__main__":
    main()
