import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ai.collect_knowledge import PageParser, allowed_url, parse_page, redact_secrets
from ai.knowledge_index import build_index, search_index, tokenize


class KnowledgeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "hosts": ["docs.example.org"],
            "path_prefixes": ["/docs/"],
        }

    def test_allowlist_requires_https_host_and_allowed_path(self):
        self.assertTrue(allowed_url("https://docs.example.org/docs/python.html", self.source))
        self.assertFalse(allowed_url("http://docs.example.org/docs/python.html", self.source))
        self.assertFalse(allowed_url("https://evil.example/docs/python.html", self.source))
        self.assertFalse(allowed_url("https://docs.example.org/private/page", self.source))
        self.assertFalse(allowed_url("https://docs.example.org/docs/%2e%2e/private", self.source))

    def test_html_extractor_ignores_navigation_and_scripts(self):
        parser = PageParser()
        parser.feed("<html><head><title>Python guide</title></head><body><nav>menu item</nav><main><h1>Python basics</h1><p>Use functions and classes.</p><script>API_KEY=do_not_keep_this</script></main></body></html>")
        text = parser.text()
        self.assertIn("Python basics", text)
        self.assertIn("functions and classes", text)
        self.assertNotIn("menu item", text)
        self.assertNotIn("do_not_keep_this", text)
        self.assertTrue(parser.title())

    def test_markdown_link_extraction_and_secret_redaction(self):
        title, text, links = parse_page("text/markdown", "# Python basics\n\nUse functions and classes. " * 20 + "\n[Guide](tutorial.html)\nAPI_KEY=abcdefghijklmnopqrstuv")
        self.assertIn("tutorial.html", links)
        self.assertIn("Python basics", text)
        self.assertNotIn("abcdefghijklmnopqrstuv", redact_secrets(text))

    def test_tokenizer_handles_programming_terms(self):
        tokens = tokenize("C++ C# .NET Node.js Python asyncio")
        self.assertTrue(tokens)
        self.assertIn("python", tokens)
        self.assertIn("asyncio", tokens)


class KnowledgeIndexTests(unittest.TestCase):
    def test_build_and_search_preserve_source_attribution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "documents.jsonl"
            body = ("In Python, functions define reusable behavior. " * 40).strip()
            doc = {
                "id": "doc-1",
                "source_id": "python-docs",
                "source_title": "Python documentation",
                "title": "Python functions",
                "url": "https://docs.example.org/docs/python.html",
                "license": "PSF-2.0",
                "license_url": "https://docs.example.org/license",
                "attribution": "Python Software Foundation",
                "category": ["programming", "python"],
                "retrieved_at": "2026-10-17T00:00:00+00:00",
                "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "content_chars": len(body),
                "text": body,
            }
            source.write_text(json.dumps(doc) + "\n", encoding="utf-8")
            database = root / "knowledge.sqlite3"
            result = build_index(source, database)
            self.assertEqual(result["documents"], 1)
            matches = search_index(database, "Python reusable functions", limit=3)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["url"], doc["url"])
            self.assertEqual(matches[0]["license"], "PSF-2.0")
            self.assertEqual(matches[0]["attribution"], "Python Software Foundation")
            self.assertIn("Python", matches[0]["snippet"])


if __name__ == "__main__":
    unittest.main()
