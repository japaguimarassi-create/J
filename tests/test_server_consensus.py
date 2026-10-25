import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import server


def review_payload():
    return {
        "scores": {
            "A": {"correcao": 5, "utilidade": 5, "viabilidade": 5},
            "B": {"correcao": 4, "utilidade": 4, "viabilidade": 4},
            "C": {"correcao": 3, "utilidade": 4, "viabilidade": 4},
        },
        "resumo": "Avaliacao técnica concluída"
    }


def vote(approve=True, score=5, risks=None):
    return json.dumps({"approve": approve, "score": score, "risks": risks or []})


class BrainstormTests(unittest.TestCase):
    def responses(self, final_votes):
        return [
            "Proposta técnica A",
            "Proposta visual B",
            "Proposta de revisão C",
            json.dumps(review_payload()),
            json.dumps(review_payload()),
            json.dumps(review_payload()),
            'Resumo consolidado\n\n~~~forge\nscene "Teste" fps=24 width=960 height=540\ncircle orb x=40 y=50 radius=12 color=#65e8d4\n~~~',
            *final_votes,
        ]

    def test_requires_unanimous_final_approval_and_logs_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(server, "DATA", Path(folder)), patch.object(server, "ollama_chat", side_effect=self.responses([vote(), vote(), vote()])):
                result = server.run_brainstorm("Crie um círculo 2D")
                self.assertTrue(result["approved_for_training"])
                self.assertEqual(sum(item["approve"] for item in result["final_votes"]), 3)
                self.assertIn("consenso unânime", result["vote_summary"])
                self.assertTrue((Path(folder) / "brainstorm-audit.jsonl").exists())

    def test_a_single_teacher_rejection_blocks_distillation(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(server, "DATA", Path(folder)), patch.object(server, "ollama_chat", side_effect=self.responses([vote(), vote(False, 5, ["sintaxe inválida"]), vote()])):
                result = server.run_brainstorm("Crie uma cena 3D")
                self.assertFalse(result["approved_for_training"])
                self.assertEqual(sum(item["approve"] for item in result["final_votes"]), 2)
                self.assertIn("NÃO aprovada para destilação", result["vote_summary"])

    def test_vote_below_four_is_not_approved(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(server, "DATA", Path(folder)), patch.object(server, "ollama_chat", side_effect=self.responses([vote(), vote(True, 3), vote()])):
                result = server.run_brainstorm("Explique keyframes")
                self.assertFalse(result["approved_for_training"])


    def test_reference_validator_accepts_only_small_jpeg_frames(self):
        image = base64.b64encode(bytes((255, 216, 255, 217))).decode("ascii")
        self.assertEqual(server.validate_reference_images([image]), [image])
        with self.assertRaises(ValueError):
            server.validate_reference_images(["not-base64"])
        with self.assertRaises(ValueError):
            server.validate_reference_images([base64.b64encode(b"PNG data").decode("ascii")])
        with self.assertRaises(ValueError):
            server.validate_reference_images([image] * 5)

    def test_visual_payload_is_attached_only_to_gemma(self):
        sample_image = base64.b64encode(bytes((255, 216, 255, 217))).decode("ascii")
        messages = [{"role": "system", "content": "System"}, {"role": "user", "content": "Look"}]
        with patch.object(server, "http_json", return_value={"message": {"content": "ok"}}) as request:
            server.ollama_chat("qwen3.6:27b", messages, images=[sample_image])
            payload = request.call_args.args[1]
            self.assertNotIn("images", payload["messages"][-1])
            server.ollama_chat("gemma4:12b", messages, images=[sample_image])
            payload = request.call_args.args[1]
            self.assertEqual(payload["messages"][-1]["images"], [sample_image])


if __name__ == "__main__":
    unittest.main()
