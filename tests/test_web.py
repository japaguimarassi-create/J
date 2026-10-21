import pytest

from deta import web


def test_url_validation_rejects_http_private_ip_and_credentials():
    with pytest.raises(ValueError, match="HTTPS"):
        web.validate_public_url("http://example.com", resolve_dns=False)
    with pytest.raises(ValueError, match="non-routable"):
        web.validate_public_url("https://127.0.0.1/path", resolve_dns=False)
    with pytest.raises(ValueError, match="credentials"):
        web.validate_public_url("https://user:pass@example.com", resolve_dns=False)
    with pytest.raises(ValueError, match="internal"):
        web.validate_public_url("https://host.local", resolve_dns=False)


def test_page_parser_keeps_article_text_and_skips_script_navigation():
    parser = web._PageParser()
    parser.feed(
        '<html><head><meta charset="utf-8"><title>Test page</title></head>'
        '<body><header>menu should not appear</header>'
        '<main><h1>Useful heading</h1><p>Important public information.</p>'
        '<script>secret script text</script></main></body></html>'
    )
    title, body = parser.result()
    assert title == "Test page"
    assert "Useful heading" in body
    assert "Important public information." in body
    assert "menu should not appear" not in body
    assert "secret script text" not in body


def test_search_parser_extracts_titles_links_and_snippets():
    parser = web._SearchParser()
    parser.feed(
        '<div class="result"><a class="result__a" href="https://example.org/page">'
        'A useful &amp; public page</a><a class="result__snippet">Summary of this page.</a></div>'
    )
    assert parser.titles == [{"url": "https://example.org/page", "title": "A useful & public page"}]
    assert parser.snippets == ["Summary of this page."]


def test_read_web_page_returns_extracted_text(monkeypatch):
    monkeypatch.setattr(
        web,
        "_http_get",
        lambda url, max_bytes, timeout: (
            "https://example.org/page",
            "text/html",
            b"<html><head><title>Example</title></head><body><main><p>This article has enough useful content to be extracted.</p></main></body></html>",
        ),
    )
    page = web.read_web_page("https://example.org/page")
    assert page["title"] == "Example"
    assert "useful content" in page["content"]
    assert page["url"] == "https://example.org/page"


def test_search_web_uses_direct_html_without_api_key(monkeypatch):
    monkeypatch.setattr(
        web,
        "_http_get",
        lambda url, max_bytes, timeout: (
            url,
            "text/html",
            b'<div class="result"><a class="result__a" href="https://example.org/guide">Guide</a>'
            b'<a class="result__snippet">A useful learning guide.</a></div>',
        ),
    )
    results = web.search_web("learn something", limit=1)
    assert len(results) == 1
    assert results[0]["title"] == "Guide"
    assert results[0]["url"] == "https://example.org/guide"
    assert results[0]["snippet"] == "A useful learning guide."


@pytest.mark.parametrize("limit", [0, 11])
def test_search_web_rejects_invalid_result_count(limit):
    with pytest.raises(ValueError, match="limit"):
        web.search_web("hello", limit=limit)

def test_redirect_handler_rejects_private_targets_before_following():
    import urllib.request

    handler = web._SafeRedirectHandler()
    request = urllib.request.Request("https://public.example.org/page")
    with pytest.raises(ValueError, match="HTTPS"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "http://127.0.0.1/admin",
        )
    with pytest.raises(ValueError, match="non-routable"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://127.0.0.1/admin",
        )

