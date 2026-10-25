import base64
import json
import unittest
from unittest.mock import patch

import cloud_backend


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class CloudBackendTests(unittest.TestCase):
    def test_prompt_contains_request_and_editing_contract(self):
        system, prompt = cloud_backend.make_prompt(
            {"prompt": "Monte um trailer", "source": "video1.mp4", "reference_notes": "estilo sombrio"},
            [],
        )
        self.assertIn("Forge AI", system)
        self.assertIn("Monte um trailer", prompt)
        self.assertIn("video1.mp4", prompt)
        self.assertIn("PLANO JSON", prompt)

    def test_image_validation_accepts_jpeg_base64(self):
        image = base64.b64encode(b"\xff\xd8fake-jpeg").decode("ascii")
        self.assertEqual(cloud_backend.validate_images([image]), [image])

    def test_image_validation_rejects_non_jpeg(self):
        image = base64.b64encode(b"not-a-jpeg").decode("ascii")
        with self.assertRaises(cloud_backend.BackendError) as result:
            cloud_backend.validate_images([image])
        self.assertEqual(result.exception.status, 400)

    def test_model_request_uses_github_models_chat_endpoint(self):
        fake = FakeResponse({"choices": [{"message": {"content": "Plano pronto"}}]})
        with patch("cloud_backend.urllib.request.urlopen", return_value=fake) as send:
            answer = cloud_backend.request_model("openai/gpt-4o", "system", "pedido", [])
        self.assertEqual(answer, "Plano pronto")
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, cloud_backend.API_URL)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "openai/gpt-4o")
        self.assertEqual(body["messages"][1]["content"][0]["text"], "pedido")

    def test_empty_prompt_is_rejected(self):
        with self.assertRaises(cloud_backend.BackendError) as result:
            cloud_backend.make_prompt({"prompt": "   "}, [])
        self.assertEqual(result.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
