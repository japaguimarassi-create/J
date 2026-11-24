import unittest

from neural_matrix.evaluation import evaluate
from neural_matrix.metrics import RegressionMetrics


class StubModel:
    def predict(self, inputs):
        return [1.0, 2.0]


class EvaluationTests(unittest.TestCase):
    def test_metrics_calculate_hand_checked_mse_and_mae(self):
        metrics = RegressionMetrics()
        metrics.update([1.0, 2.0], [0.0, 0.0])
        result = metrics.to_dict()
        self.assertEqual(result["samples"], 1)
        self.assertEqual(result["values"], 2)
        self.assertEqual(result["mse"], 2.5)
        self.assertEqual(result["mae"], 1.5)

    def test_metrics_accumulate_multiple_samples(self):
        metrics = RegressionMetrics()
        metrics.update([1.0], [0.0])
        metrics.update([3.0], [1.0])
        self.assertEqual(metrics.to_dict()["mse"], 2.5)
        self.assertEqual(metrics.to_dict()["mae"], 1.5)

    def test_metrics_reject_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            RegressionMetrics().update([1.0], [1.0, 2.0])

    def test_evaluation_streams_and_counts_samples(self):
        samples = [
            ([0.0, 0.0], [0.0, 0.0]),
            ([0.5, 0.5], [0.0, 0.0]),
        ]
        result = evaluate(StubModel(), iter(samples))
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["mse"], 2.5)
        self.assertEqual(result["mae"], 1.5)

    def test_evaluation_rejects_empty_dataset(self):
        with self.assertRaises(ValueError):
            evaluate(StubModel(), iter(()))


if __name__ == "__main__":
    unittest.main()
