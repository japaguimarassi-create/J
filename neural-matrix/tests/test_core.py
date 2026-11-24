import tempfile
import unittest
from pathlib import Path

from neural_matrix.config import MatrixConfig
from neural_matrix.experts import Expert, ExpertRouter
from neural_matrix.sparse import SparseGraph
from neural_matrix.training import CombinedTrainer
from neural_matrix.virtual import VirtualMatrix


class NeuralMatrixTests(unittest.TestCase):
    def test_config_keeps_logical_scale_separate_from_active_budget(self):
        config = MatrixConfig()
        config.validate()
        self.assertEqual(config.logical_units, 1_000_000_000)
        self.assertEqual(config.logical_connections, 2_000_000_000)
        self.assertLess(config.active_edges, config.logical_connections)

    def test_sparse_graph_respects_budget(self):
        graph = SparseGraph(4, 2, seed=1)
        graph.initialize(2)
        self.assertEqual(len(graph.edges), 2)
        with self.assertRaises(RuntimeError):
            graph.add_edge(0, 1, 0.2)

    def test_virtual_matrix_addressing(self):
        matrix = VirtualMatrix()
        self.assertEqual(matrix.logical_connections, 2_000_000_000_000_000_000)
        self.assertEqual(matrix.address_id(1, 0), 2_000_000_000)
        self.assertEqual(matrix.deterministic_weight(10, 20), matrix.deterministic_weight(10, 20))
        with self.assertRaises(IndexError):
            matrix.address_id(matrix.rows, 0)

    def test_expert_forward_and_training(self):
        expert = Expert(3, seed=2)
        inputs = [0.1, 0.2, 0.3]
        before = expert.forward(inputs)
        loss = expert.train_one(inputs, [0.0, 0.0, 0.0])
        self.assertEqual(len(before), 3)
        self.assertGreaterEqual(loss, 0.0)
        self.assertEqual(expert.steps, 1)

    def test_checkpoint_round_trip(self):
        experts = [Expert(2, 1), Expert(2, 2)]
        trainer = CombinedTrainer(experts, top_k=1)
        sample = ([0.2, -0.1], [0.0, 0.1])
        trainer.train_incremental(sample)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            trainer.save_checkpoint(path)
            restored = CombinedTrainer([Expert(2, 1), Expert(2, 2)], top_k=1)
            self.assertTrue(restored.load_checkpoint(path))
            self.assertEqual(restored.stats.samples, 1)
            self.assertEqual(restored.experts[0].weights, trainer.experts[0].weights)


if __name__ == "__main__":
    unittest.main()
