import html
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any


USER_AGENT = "Deta-LocalResearch/0.3 (+public web retrieval; no AI API)"
MAX_PAGE_BYTES = 1_500_000
MAX_SEARCH_BYTES = 1_000_000
DEFAULT_TIMEOUT = 15
BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata",
}


class WebResearchError(RuntimeError):
    pass


def validate_public_url(url: str, resolve_dns: bool = True) -> str:
    value = (url or "").strip()
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() != "https":
        raise ValueError("Only HTTPS web pages are accepted.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("The URL must have a public hostname and no embedded credentials.")
    if parsed.port not in (None, 443):
        raise ValueError("Only the default HTTPS port is accepted.")
    host = parsed.hostname.rstrip(".").lower()
    if host in BLOCKED_HOSTS or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal hosts are not accepted.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise ValueError("Private, reserved, and non-routable IP addresses are not accepted.")
    elif resolve_dns:
        try:
            results = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise WebResearchError(f"Could not resolve public host '{host}': {exc}") from exc
        addresses = {item[4][0].split("%", 1)[0] for item in results}
        if not addresses:
            raise WebResearchError(f"No IP address was returned for '{host}'.")
        for result in addresses:
            try:
                parsed_address = ipaddress.ip_address(result)
            except ValueError as exc:
                raise WebResearchError(f"Invalid DNS address for '{host}'.") from exc
            if not parsed_address.is_global:
                raise ValueError(f"The host '{host}' resolves to a non-public address.")
    if not parsed.path:
        parsed = parsed._replace(path="/")
    return urllib.parse.urlunsplit(parsed)


def _safe_response_url(url: str) -> str:
    return validate_public_url(url, resolve_dns=True)


class _PageParser(HTMLParser):
    BLOCK_TAGS = {
        "article", "br", "dd", "div", "dl", "dt", "h1", "h2", "h3", "h4",
        "li", "main", "p", "pre", "section", "td", "th", "tr",
    }
    SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.stack: list[tuple[str, bool, bool]] = []
        self.title_depth: int | None = None
        self.skip_depth = 0
        self.characters = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        depth = len(self.stack) + 1
        is_title = tag.lower() == "title"
        is_skip = tag.lower() in self.SKIP_TAGS
        if is_title:
            self.title_depth = depth
        if is_skip:
            self.skip_depth += 1
        if tag.lower() in self.BLOCK_TAGS and not self.skip_depth:
            self.text_parts.append("\n")
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append((tag.lower(), is_title, is_skip))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        depth = len(self.stack)
        lowered = tag.lower()
        if self.title_depth == depth and lowered == "title":
            self.title_depth = None
        if lowered in self.BLOCK_TAGS and not self.skip_depth:
            self.text_parts.append("\n")
        match_index = next(
            (index for index in range(len(self.stack) - 1, -1, -1) if self.stack[index][0] == lowered),
            None,
        )
        if match_index is None:
            return
        removed = self.stack[match_index:]
        self.stack = self.stack[:match_index]
        self.skip_depth = max(0, self.skip_depth - sum(1 for item in removed if item[2]))

    def handle_data(self, data: str) -> None:
        if self.title_depth is not None:
            self.title_parts.append(data)
        if not self.skip_depth:
            clean = " ".join(data.split())
            if clean:
                self.text_parts.append(clean + " ")
                self.characters += len(clean) + 1

    def result(self) -> tuple[str, str]:
        title = re.sub(r"\s+", " ", html.unescape(" ".join(self.title_parts))).strip()
        body = re.sub(r"[ \t]+\n", "\n", "".join(self.text_parts))
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"[ \t]{2,}", " ", body)
        return title[:300], body.strip()


class _SearchParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.anchor_depth: int | None = None
        self.anchor: dict[str, Any] | None = None
        self.snippet_depth: int | None = None
        self.snippet_parts: list[str] = []
        self.titles: list[dict[str, str]] = []
        self.snippets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        depth = len(self.stack) + 1
        values = {key.lower(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag.lower() == "a" and classes.intersection({"result__a", "result-link"}):
            self.anchor_depth = depth
            self.anchor = {"url": values.get("href", ""), "parts": []}
        if classes.intersection({"result__snippet", "result-snippet"}):
            self.snippet_depth = depth
            self.snippet_parts = []
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(tag.lower())

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        depth = len(self.stack)
        lowered = tag.lower()
        if self.anchor is not None and self.anchor_depth == depth and lowered == "a":
            item = {
                "url": str(self.anchor["url"]),
                "title": re.sub(r"\s+", " ", "".join(self.anchor["parts"])).strip(),
            }
            if item["url"] and item["title"]:
                self.titles.append(item)
            self.anchor = None
            self.anchor_depth = None
        if self.snippet_depth == depth:
            snippet = re.sub(r"\s+", " ", "".join(self.snippet_parts)).strip()
            if snippet:
                self.snippets.append(snippet)
            self.snippet_depth = None
            self.snippet_parts = []
        match_index = next(
            (index for index in range(len(self.stack) - 1, -1, -1) if self.stack[index] == lowered),
            None,
        )
        if match_index is not None:
            self.stack = self.stack[:match_index]

    def handle_data(self, data: str) -> None:
        if self.anchor is not None:
            self.anchor["parts"].append(data)
        if self.snippet_depth is not None:
            self.snippet_parts.append(data)


def _decode_result_url(href: str) -> str:
    candidate = urllib.parse.urljoin("https://html.duckduckgo.com", html.unescape(href))
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
        values = urllib.parse.parse_qs(parsed.query)
        target = values.get("uddg", [None])[0]
        if target:
            candidate = urllib.parse.unquote(target)
    return candidate


def _http_get(url: str, max_bytes: int, timeout: int) -> tuple[str, str, bytes]:
    safe_url = validate_public_url(url)
    request = urllib.request.Request(
        safe_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html, text/plain, application/json;q=0.9, */*;q=0.5",
            "Accept-Language": "en-US,en;q=0.8,pt-BR;q=0.7,pt;q=0.6",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            final_url = _safe_response_url(response.geturl())
            content_type = response.headers.get_content_type().lower()
            if content_type not in {"text/html", "text/plain", "application/json", "application/xhtml+xml"}:
                raise WebResearchError(f"Unsupported content type: {content_type}")
            data = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        raise WebResearchError(f"Website returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise WebResearchError(f"Website connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise WebResearchError("Website connection timed out.") from exc
    if len(data) > max_bytes:
        raise WebResearchError(f"Page exceeds the {max_bytes}-byte download limit.")
    return final_url, content_type, data


def search_web(query: str, limit: int = 5, timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, str]]:
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10.")
    if not 1 <= timeout <= 60:
        raise ValueError("timeout must be between 1 and 60 seconds.")

    encoded = urllib.parse.urlencode({"q": query, "kl": "wt-wt"})
    search_urls = [
        "https://html.duckduckgo.com/html/?" + encoded,
        "https://lite.duckduckgo.com/lite/?" + encoded,
    ]
    last_error: Exception | None = None
    parser: _SearchParser | None = None
    for search_url in search_urls:
        try:
            _, _, payload = _http_get(search_url, MAX_SEARCH_BYTES, timeout)
            current = _SearchParser()
            current.feed(payload.decode("utf-8", "replace"))
            if current.titles:
                parser = current
                break
        except (WebResearchError, ValueError) as exc:
            last_error = exc

    if parser is None:
        detail = f" {last_error}" if last_error else ""
        raise WebResearchError("Web search returned no readable results." + detail)

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(parser.titles):
        url = _decode_result_url(item["url"])
        try:
            url = validate_public_url(url, resolve_dns=False)
        except ValueError:
            continue
        host = urllib.parse.urlsplit(url).hostname or ""
        if host.endswith("duckduckgo.com") or url in seen:
            continue
        seen.add(url)
        results.append({
            "title": item["title"][:300],
            "url": url,
            "snippet": parser.snippets[index][:1600] if index < len(parser.snippets) else "",
            "source": host,
        })
        if len(results) >= limit:
            break
    return results


def read_web_page(url: str, timeout: int = DEFAULT_TIMEOUT, max_chars: int = 20_000) -> dict[str, str]:
    if not 500 <= max_chars <= 50_000:
        raise ValueError("max_chars must be between 500 and 50000")
    final_url, content_type, payload = _http_get(url, MAX_PAGE_BYTES, timeout)
    decoded = payload.decode("utf-8", "replace")
    if content_type == "text/plain":
        title = urllib.parse.urlsplit(final_url).hostname or final_url
        body = re.sub(r"\n{3,}", "\n\n", decoded)
        body = body.strip()
    elif content_type == "application/json":
        title = urllib.parse.urlsplit(final_url).hostname or final_url
        body = decoded
    else:
        parser = _PageParser()
        parser.feed(decoded)
        title, body = parser.result()
        if not title:
            title = urllib.parse.urlsplit(final_url).hostname or final_url
    if not body:
        raise WebResearchError("The page contained no extractable text.")
    return {
        "title": title[:300],
        "url": final_url,
        "content": body[:max_chars],
        "content_type": content_type,
    }
