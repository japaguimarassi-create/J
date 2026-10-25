import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from assistant import LocalAssistant, normalize
from model import ForgeStudent


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.assistant = LocalAssistant(ROOT / "data" / "seed_examples.jsonl")

    def test_accent_normalization(self):
        self.assertEqual(normalize("Animação 3D"), normalize("animacao 3d"))

    def test_exact_prompt_uses_curated_answer(self):
        result = self.assistant.answer("Como começo um projeto 2D?")
        self.assertEqual(result["method"], "curated_retrieval")
        self.assertIn("scene", result["answer"])
        self.assertGreaterEqual(result["confidence"], 0.22)

    def test_unknown_prompt_abstains(self):
        result = self.assistant.answer("Explique astrofísica de estrelas de nêutrons")
        self.assertEqual(result["method"], "low_confidence_fallback")
        self.assertIn("cobertura confiável", result["answer"])

    def test_student_reranks_curated_answer(self):
        result = self.assistant.answer("Como começo um projeto 2D?", model=ForgeStudent())
        self.assertEqual(result["method"], "student_reranked_retrieval")
        self.assertEqual(result["matched_prompt"], "Como começo um projeto 2D?")
        self.assertIsInstance(result["student_score"], float)


if __name__ == "__main__":
    unittest.main()
