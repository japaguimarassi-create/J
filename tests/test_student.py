import unittest

import torch

from ai.student import BLOCK_SIZE, EXPECTED_PARAMS, ForgeStudent, ByteBPETokenizer, VOCAB_SIZE
from ai.assistant import StudentAssistant, load_corpus, student_log_score
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StudentModelTests(unittest.TestCase):
    def test_exact_parameter_count(self):
        model = ForgeStudent()
        self.assertEqual(model.count_parameters(), EXPECTED_PARAMS)
        self.assertEqual(EXPECTED_PARAMS, 249984)

    def test_forward_shape_and_finite_logits(self):
        model = ForgeStudent()
        inputs = torch.randint(4, 260, (2, 16))
        logits = model(inputs)
        self.assertEqual(tuple(logits.shape), (2, 16, VOCAB_SIZE))
        self.assertTrue(torch.isfinite(logits).all().item())

    def test_context_is_limited_to_256_tokens(self):
        model = ForgeStudent()
        logits = model(torch.randint(4, 260, (1, BLOCK_SIZE + 8)))
        self.assertEqual(tuple(logits.shape), (1, BLOCK_SIZE, VOCAB_SIZE))

    def test_byte_bpe_round_trip(self):
        tokenizer = ByteBPETokenizer.train(["Olá animação FORGE", "Olá, cena 2D", "Animação FORGE 2D"])
        text = "Olá animação!"
        self.assertEqual(tokenizer.decode(tokenizer.encode(text)), text)
        self.assertEqual(len(tokenizer.token_bytes), VOCAB_SIZE)

    def test_corpus_has_valid_reviewable_examples(self):
        rows = load_corpus([ROOT / "data" / "seed.jsonl"])
        self.assertGreaterEqual(len(rows), 35)
        self.assertTrue(all(row["prompt"].strip() and row["response"].strip() for row in rows))

    def test_assistant_returns_known_example_and_abstains_out_of_scope(self):
        assistant = StudentAssistant([ROOT / "data" / "seed.jsonl"])
        match = assistant.answer("O que é a linguagem FORGE?")
        self.assertEqual(match["mode"], "retrieval")
        self.assertIn("FORGE", match["response"])
        unknown = assistant.answer("Explique a astrofísica das estrelas de nêutrons")
        self.assertIn("cobertura confiável", unknown["response"])
        self.assertEqual(unknown["mode"], "student")

    def test_student_scores_a_reviewed_answer(self):
        tokenizer = ByteBPETokenizer.train(["Usuário: oi\nAssistente: olá", "Usuário: cena\nAssistente: FORGE"])
        model = ForgeStudent()
        result = student_log_score(model, tokenizer, "oi", "", "Olá")
        self.assertTrue(torch.isfinite(torch.tensor(result)).item())


if __name__ == "__main__":
    unittest.main()
