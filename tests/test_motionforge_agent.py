import os
import unittest
from unittest.mock import patch

import motionforge_agent


class MotionForgeAgentTests(unittest.TestCase):
    def test_model_list_requires_three_distinct_models(self):
        with patch.dict(os.environ, {"MOTIONFORGE_TEACHERS": "alpha,beta,gamma"}):
            self.assertEqual(motionforge_agent.model_list(), ["alpha", "beta", "gamma"])
        with patch.dict(os.environ, {"MOTIONFORGE_TEACHERS": "alpha,beta"}):
            with self.assertRaises(ValueError):
                motionforge_agent.model_list()
        with patch.dict(os.environ, {"MOTIONFORGE_TEACHERS": "alpha,beta,alpha"}):
            with self.assertRaises(ValueError):
                motionforge_agent.model_list()

    def test_endpoint_parts_parses_local_ollama(self):
        scheme, hostname, cli_host, port = motionforge_agent.endpoint_parts(
            "http://127.0.0.1:11434/"
        )
        self.assertEqual(scheme, "http")
        self.assertEqual(hostname, "127.0.0.1")
        self.assertEqual(cli_host, "127.0.0.1:11434")
        self.assertEqual(port, 11434)

    def test_endpoint_parts_rejects_bad_url(self):
        with self.assertRaises(ValueError):
            motionforge_agent.endpoint_parts("not-an-url")

    def test_model_present_requires_exact_tag(self):
        self.assertTrue(motionforge_agent.model_present("gemma4:12b", ["gemma4:12b"]))
        self.assertFalse(motionforge_agent.model_present("gemma4:12b", ["gemma4:e4b"]))

    def test_storage_estimate_is_only_for_missing_models(self):
        self.assertEqual(motionforge_agent.required_free_gb(["gemma4:12b"]), 12)
        self.assertEqual(motionforge_agent.required_free_gb([]), 0)


if __name__ == "__main__":
    unittest.main()
