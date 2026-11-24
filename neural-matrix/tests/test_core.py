import tempfile
import unittest
from pathlib import Path

from neural_matrix.config import MatrixConfig
from neural_matrix.distributed import DistributedTrainer
from neural_matrix.experts import Expert, ExpertRouter
from neural_matrix.memory import MemoryBudget, MemoryBudgetExceeded, VirtualWeightCache
from neural_matrix.scaling import CapacityPlan, ProgressiveScaler
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

    def test_expert_rejects_overflowing_update_without_mutating_weights(self):
        expert = Expert(2, seed=3)
        weights_before = [row[:] for row in expert.weights]
        bias_before = expert.bias[:]
        with self.assertRaises(ValueError):
            expert.train_one([0.1, 0.2], [1e308, -1e308])
        self.assertEqual(expert.weights, weights_before)
        self.assertEqual(expert.bias, bias_before)
        self.assertEqual(expert.steps, 0)

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

    def test_memory_budget_evicts_oldest_cache_entry(self):
        budget = MemoryBudget(128)
        budget.put("a", 1.0, 64)
        budget.put("b", 2.0, 64)
        self.assertEqual(budget.get("a"), 1.0)
        budget.put("c", 3.0, 64)
        self.assertIsNone(budget.get("b"))
        self.assertEqual(budget.get("a"), 1.0)
        self.assertEqual(budget.snapshot()["used_bytes"], 128)
        with self.assertRaises(MemoryBudgetExceeded):
            budget.put("large", 0.0, 129)

    def test_memory_reservations_evict_cache_and_release(self):
        budget = MemoryBudget(128)
        budget.put("cached", 1.0, 64)
        with budget.reserve(96):
            self.assertEqual(budget.snapshot()["reserved_bytes"], 96)
            self.assertEqual(budget.cached_items, 0)
            with self.assertRaises(MemoryBudgetExceeded):
                budget.put("too-large-now", 2.0, 40)
        self.assertEqual(budget.used_bytes, 0)

    def test_virtual_weight_cache_uses_budget(self):
        budget = MemoryBudget(128)
        cache = VirtualWeightCache(VirtualMatrix(10, 10), budget)
        expected = cache.get(2, 3)
        self.assertEqual(cache.get(2, 3), expected)
        self.assertEqual(budget.cached_items, 1)

    def test_progressive_capacity_stays_inside_memory_limit(self):
        config = MatrixConfig()
        plan = CapacityPlan.from_config(config)
        self.assertGreater(len(plan.stages), 1)
        self.assertEqual(plan.stages[0].active_units, config.active_units)
        self.assertEqual(plan.stages[-1].active_units, config.max_active_units)
        self.assertEqual(plan.stages[-1].active_edges, config.max_active_edges)
        self.assertTrue(all(stage.estimated_bytes <= plan.memory_limit_bytes for stage in plan.stages))
        scaler = ProgressiveScaler(plan)
        self.assertTrue(scaler.has_next)
        self.assertEqual(scaler.advance(), plan.stages[1])

    def test_capacity_plan_rejects_growth_over_memory_limit(self):
        config = MatrixConfig(
            active_units=10_000,
            active_edges=0,
            max_active_units=20_000,
            max_active_edges=0,
            expert_count=1,
            expert_width=1,
            top_k_experts=1,
            memory_limit_mb=1,
        )
        with self.assertRaises(MemoryError):
            CapacityPlan.from_config(config)

    def test_distributed_training_updates_expert_shards(self):
        experts = [Expert(2, 11), Expert(2, 12)]
        trainer = DistributedTrainer(experts, workers=2)
        dataset = [
            ([0.2, -0.1], [0.0, 0.1]),
            ([0.1, 0.4], [0.2, -0.2]),
            ([-0.2, 0.3], [0.1, 0.0]),
        ]
        loss = trainer.train(dataset)
        self.assertGreaterEqual(loss, 0.0)
        self.assertEqual(trainer.stats.samples, 3)
        self.assertEqual(trainer.stats.updates, 3)
        self.assertEqual(sum(expert.steps for expert in experts), 3)

    def test_invalid_progressive_capacity_is_rejected(self):
        config = MatrixConfig(active_units=10, max_active_units=9)
        with self.assertRaises(ValueError):
            CapacityPlan.from_config(config)

    def test_cache_budget_cannot_exceed_total_memory_limit(self):
        config = MatrixConfig(memory_limit_mb=1, virtual_cache_mb=2)
        with self.assertRaises(ValueError):
            config.validate()


if __name__ == "__main__":
    unittest.main()
