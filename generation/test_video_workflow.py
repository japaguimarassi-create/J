from __future__ import annotations

import unittest

from video_comfy import find_output_files, parse_assignment, set_node_input


class ComfyWorkflowTests(unittest.TestCase):
    def test_parse_json_assignment(self) -> None:
        node_id, input_name, value = parse_assignment('12.width=768')
        self.assertEqual((node_id, input_name, value), ("12", "width", 768))

    def test_parse_string_assignment(self) -> None:
        node_id, input_name, value = parse_assignment('6.text="A cinematic scene"')
        self.assertEqual((node_id, input_name, value), ("6", "text", "A cinematic scene"))

    def test_set_node_input_checks_node_and_field(self) -> None:
        workflow = {"6": {"inputs": {"text": "old"}}}
        set_node_input(workflow, "6", "text", "new")
        self.assertEqual(workflow["6"]["inputs"]["text"], "new")
        with self.assertRaises(KeyError):
            set_node_input(workflow, "7", "text", "new")
        with self.assertRaises(KeyError):
            set_node_input(workflow, "6", "missing", "new")

    def test_find_video_and_image_outputs(self) -> None:
        history = {
            "outputs": {
                "20": {
                    "videos": [{"filename": "clip.mp4", "subfolder": "motion", "type": "output"}],
                    "images": [{"filename": "frame.png"}],
                }
            }
        }
        results = find_output_files(history, set())
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["media_key"], "videos")
        self.assertEqual(results[1]["media_key"], "images")

    def test_output_node_filter(self) -> None:
        history = {
            "outputs": {
                "20": {"videos": [{"filename": "one.mp4"}]},
                "21": {"videos": [{"filename": "two.mp4"}]},
            }
        }
        results = find_output_files(history, {"21"})
        self.assertEqual([item["filename"] for item in results], ["two.mp4"])


if __name__ == "__main__":
    unittest.main()
