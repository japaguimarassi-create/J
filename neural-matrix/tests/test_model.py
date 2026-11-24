import json
import tempfile
import unittest
from pathlib import Path

from neural_matrix.config import MatrixConfig
from neural_matrix.experts import Expert, ExpertRouter
from neural_matrix.model import NeuralMatrixModel
from neural_matrix.training import CombinedTrainer


def small_config(top_k=1):
    return MatrixConfig(
        logical_units=100,
        logical_connections=200,
        active_units=8,
        active_edges=16,
        expert_count=2,
        expert_width=2,
        top_k_experts=top_k,
        max_active_units=16,
        max_active_edges=32,
        memory_limit_mb=4,
        virtual_cache_mb=1,
        max_workers=2,
    )


class ModelTests(unittest.TestCase):
    def test_router_uses_expert_specific_input_projection(self):
        first = Expert(2, seed=1)
        second = Expert(2, seed=2)
        first.weights[0] = [1.0, 0.0]
        second.weights[0] = [-1.0, 0.0]
        router = ExpertRouter([first, second], top_k=1)
        self.assertEqual(router.route([1.0, 0.0]), [0])
        first.weights[0] = [-1.0, 0.0]
        second.weights[0] = [1.0, 0.0]
        self.assertEqual(router.route([1.0, 0.0]), [1])

    def test_prediction_is_deterministic_for_equal_seeds(self):
        first = NeuralMatrixModel(small_config())
        second = NeuralMatrixModel(small_config())
        self.assertEqual(first.predict([0.25, -0.5]), second.predict([0.25, -0.5]))

    def test_prediction_rejects_wrong_input_width(self):
        model = NeuralMatrixModel(small_config())
        with self.assertRaises(ValueError):
            model.predict([0.1])

    def test_model_encodes_inputs_through_virtual_sparse_graph(self):
        model = NeuralMatrixModel(small_config())
        encoded = model.encode_inputs([0.25, -0.5])
        self.assertEqual(len(encoded), 2)
        self.assertNotEqual(encoded, [0.25, -0.5])
        self.assertGreater(model.memory_budget.cached_items, 0)

    def test_training_updates_selected_experts(self):
        model = NeuralMatrixModel(small_config())
        before = sum(expert.steps for expert in model.experts)
        loss = model.train_sample(([0.2, -0.1], [0.0, 0.1]))
        self.assertGreaterEqual(loss, 0.0)
        self.assertGreater(sum(expert.steps for expert in model.experts), before)

    def test_batch_validation_prevents_partial_training(self):
        model = NeuralMatrixModel(small_config())
        before = [expert.steps for expert in model.experts]
        with self.assertRaises(ValueError):
            model.train_batch([
                ([0.2, -0.1], [0.0, 0.1]),
                ([0.1, 0.3], [0.2]),
            ], mode="incremental")
        self.assertEqual([expert.steps for expert in model.experts], before)

    def test_distributed_batch_updates_each_selected_expert(self):
        model = NeuralMatrixModel(small_config(top_k=2))
        samples = [
            ([0.2, -0.1], [0.0, 0.1]),
            ([0.1, 0.4], [0.2, -0.2]),
        ]
        model.train_batch(samples, mode="distributed", workers=2)
        self.assertEqual(model.stats.samples, 2)
        self.assertEqual(model.stats.updates, 4)
        self.assertEqual(sum(expert.steps for expert in model.experts), 4)

    def test_model_checkpoint_round_trip_preserves_predictions(self):
        model = NeuralMatrixModel(small_config())
        model.train_sample(([0.2, -0.1], [0.0, 0.1]))
        expected = model.predict([0.3, 0.4])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "model.json"
            model.save(path)
            restored = NeuralMatrixModel.from_checkpoint(path)
            self.assertEqual(restored.config, model.config)
            self.assertEqual(restored.predict([0.3, 0.4]), expected)

    def test_bad_checkpoint_does_not_partially_mutate_model(self):
        model = NeuralMatrixModel(small_config())
        before = [[row[:] for row in expert.weights] for expert in model.experts]
        payload = {
            "format_version": 2,
            "format": "neural-matrix",
            "architecture": "expert-mlp-tanh-v1",
            "config": small_config().__dict__,
            "expert_width": 2,
            "stats": {"samples": 0, "updates": 0, "mean_loss": 0.0},
            "experts": [
                {"weights": [[0.0, 0.0], [0.0, 0.0]], "bias": [0.0, 0.0], "steps": 1},
                {"weights": [[0.0]], "bias": [0.0, 0.0], "steps": 1},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                model.load(path)
        self.assertEqual([expert.weights for expert in model.experts], before)

    def test_legacy_trainer_checkpoint_remains_loadable(self):
        experts = [Expert(2, 1), Expert(2, 2)]
        trainer = CombinedTrainer(experts, top_k=1)
        trainer.train_incremental(([0.2, -0.1], [0.0, 0.1]))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.json"
            trainer.save_checkpoint(path)
            model = NeuralMatrixModel(small_config())
            model.load(path)
            self.assertEqual(model.trainer.stats.samples, 1)

    def test_model_rejects_checkpoint_with_different_architecture(self):
        model = NeuralMatrixModel(small_config())
        incompatible = small_config().__dict__.copy()
        incompatible["expert_width"] = 3
        payload = {
            "format_version": 2,
            "format": "neural-matrix",
            "architecture": "expert-mlp-tanh-v1",
            "config": incompatible,
            "expert_width": 3,
            "stats": {"samples": 0, "updates": 0, "mean_loss": 0.0},
            "experts": [],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "different.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                model.load(path)


if __name__ == "__main__":
    unittest.main()
