import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)


class WebLearningTests(unittest.TestCase):
    def test_learning_panel_has_multimodal_inputs_and_resource_guides(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        for expected in ("learnPanel", "referenceFiles", "referenceNote", "animationIdea", "useReferencesForAI", "planWithReferences"):
            self.assertIn('id="' + expected + '"', html)
        self.assertIn("Grease Pencil Fundamentals", html)
        self.assertIn("Do storyboard", html)
        self.assertIn("Estudo de personagem 3D", html)

    def test_static_ids_are_unique_and_app_selectors_exist(self):
        parser = IdCollector()
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        parser.feed(html)
        duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        self.assertEqual(duplicates, [])
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        selectors = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', js))
        self.assertEqual(sorted(selectors - set(parser.ids)), [])

    def test_reference_media_stays_in_browser_and_frames_are_limited(self):
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("indexedDB.open(REFERENCE_DB_NAME,1)", js)
        self.assertIn("images.length>=4", js)
        self.assertIn('canvas.toBlob(function(output)', js)
        self.assertNotIn('fetch(\"https://', js)


if __name__ == "__main__":
    unittest.main()
