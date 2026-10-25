import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from teacher_brainstorm import TEACHERS, run_brainstorm, tally_approvals


def good_reviews():
    return {"scores": {key: {"technical": 5, "useful": 5, "learnable": 5, "testable": 5} for key in TEACHERS}, "risks": []}


class TeacherTests(unittest.TestCase):
    def test_requires_unanimous_score_at_least_four(self):
        reviews = {key: {"approve": True, "score": 4, "risks": []} for key in TEACHERS}
        flags, approved = tally_approvals(reviews)
        self.assertTrue(approved)
        reviews["gemma"] = {"approve": False, "score": 5, "risks": ["erro"]}
        self.assertFalse(tally_approvals(reviews)[1])

    def test_writes_training_record_only_after_three_approvals(self):
        outputs = ["proposal qwen", "proposal gemma", "proposal gpt", json.dumps(good_reviews()), json.dumps(good_reviews()), json.dumps(good_reviews()), "Final FORGE example.", json.dumps({"approve": True, "score": 5, "risks": []}), json.dumps({"approve": True, "score": 4, "risks": []}), json.dumps({"approve": True, "score": 5, "risks": []})]
        with tempfile.TemporaryDirectory() as folder, patch("teacher_brainstorm.ask", side_effect=outputs):
            result = run_brainstorm("Crie uma animação 2D", Path(folder))
            self.assertTrue(result["approved_for_training"])
            generated = (Path(folder) / "teacher_generated.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(generated), 1)
            self.assertEqual(json.loads(generated[0])["source"], "three_teacher_consensus")

    def test_rejected_synthesis_is_not_training_data(self):
        outputs = ["p1", "p2", "p3", json.dumps(good_reviews()), json.dumps(good_reviews()), json.dumps(good_reviews()), "Síntese inválida.", json.dumps({"approve": True, "score": 5, "risks": []}), json.dumps({"approve": False, "score": 2, "risks": ["erro de sintaxe"]}), json.dumps({"approve": True, "score": 4, "risks": []})]
        with tempfile.TemporaryDirectory() as folder, patch("teacher_brainstorm.ask", side_effect=outputs):
            result = run_brainstorm("Crie uma animação 3D", Path(folder))
            self.assertFalse(result["approved_for_training"])
            self.assertFalse((Path(folder) / "teacher_generated.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
