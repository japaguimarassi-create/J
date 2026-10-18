import json
import unittest
from pathlib import Path


class ContractTests(unittest.TestCase):
    def test_registry_declares_non_modal_overlay_and_tool_allowlist(self):
        contract = json.loads(Path("ai/assistant_tools.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["schema_version"], 1)
        overlay = contract["host_contract"]
        self.assertTrue(overlay["non_modal"])
        self.assertTrue(overlay["pass_through_outside_window"])
        self.assertTrue(overlay["draggable"])
        self.assertTrue(overlay["minimize_to_bubble"])
        self.assertTrue(overlay["dismissible"])
        self.assertTrue(overlay["stop_button"])
        self.assertGreaterEqual(len(contract["tools"]), 50)
        self.assertEqual(len(contract["tools"]), len(set(contract["tools"])))


if __name__ == "__main__":
    unittest.main()
