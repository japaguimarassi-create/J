import html
import re
import urllib.parse
import urllib.request

SEARCH_URL = "https://html.duckduckgo.com/html/?q="


def search_web(query, max_results=5, timeout=12):
    query = str(query).strip()
    if not query or len(query) > 240:
        raise ValueError("query deve conter de 1 a 240 caracteres")
    maximum = max(1, min(int(max_results), 8))
    request = urllib.request.Request(SEARCH_URL + urllib.parse.quote_plus(query), headers={"User-Agent": "MotionForgeResearch/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        page = response.read(1_500_000).decode("utf-8", errors="replace")
    results = []
    matches = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.I | re.S)
    for raw_url, raw_title in matches:
        title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
        decoded = html.unescape(raw_url)
        parsed = urllib.parse.urlparse(decoded)
        actual_url = urllib.parse.parse_qs(parsed.query).get("uddg", [decoded])[0]
        actual = urllib.parse.urlparse(actual_url)
        if actual.scheme not in {"http", "https"} or not actual.netloc:
            continue
        pos = page.find(raw_title)
        snippet = ""
        if pos >= 0:
            part = page[pos:pos + 3000]
            found = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', part, flags=re.I | re.S)
            if found:
                snippet = html.unescape(re.sub(r"<[^>]+>", "", found[0])).strip()
        if title and actual_url not in {row["url"] for row in results}:
            results.append({"title": title[:300], "url": actual_url, "snippet": snippet[:800]})
        if len(results) >= maximum:
            break
    return results
