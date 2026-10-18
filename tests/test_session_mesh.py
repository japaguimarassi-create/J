import unittest

from ai.session_mesh import SessionMeshPlan


class SessionMeshTests(unittest.TestCase):
    def test_requested_plan_is_forty_billion_sessions(self):
        plan = SessionMeshPlan(100, 400_000_000)
        self.assertEqual(plan.total_sessions, 40_000_000_000)
        self.assertEqual(plan.progress(40_000_000_000), [400_000_000] * 100)

    def test_two_thousand_five_hundred_sessions_are_balanced(self):
        plan = SessionMeshPlan()
        self.assertEqual(plan.progress(2500), [25] * 100)

    def test_global_ids_are_disjoint_and_contiguous_across_ranks(self):
        plan = SessionMeshPlan(100, 400)
        generated = []
        for micro in range(2):
            for rank in range(4):
                generated.extend(plan.session_ids(0, micro, rank, 2, 2, 4))
        self.assertEqual(sorted(generated), list(range(16)))
        self.assertEqual(len(set(generated)), 16)

    def test_global_step_count_for_eight_gpu_default(self):
        plan = SessionMeshPlan()
        self.assertEqual(plan.steps_for_budget(plan.total_sessions, 1, 8, 8), 625_000_000)

    def test_rejects_partial_step_budget(self):
        plan = SessionMeshPlan(100, 400)
        with self.assertRaises(ValueError):
            plan.steps_for_budget(15, 1, 2, 4)

    def test_rejects_progress_outside_budget(self):
        with self.assertRaises(ValueError):
            SessionMeshPlan(100, 400).progress(40_001)


if __name__ == "__main__":
    unittest.main()
