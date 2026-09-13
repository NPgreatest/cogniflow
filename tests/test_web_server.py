import json
import threading
import unittest
import urllib.request
from unittest.mock import patch

from web_server import CogniflowServer


STORY = {
    "id": "hf-test", "title": "Evaluating AI agents", "url": "https://example.org/paper",
    "source": "Hugging Face Daily Papers", "published_at": "2026-09-13T00:00:00Z",
    "summary": "A paper proposes agent evaluation methods.", "evidence_level": "abstract",
}


class WebServerTests(unittest.TestCase):
    def setUp(self):
        self.server = CogniflowServer(("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_page_and_candidates(self):
        with urllib.request.urlopen(self.base) as response:
            self.assertIn(b"Cogniflow", response.read())
        with patch("web_server.fetch_hf_daily_papers", return_value=[STORY]):
            with urllib.request.urlopen(self.base + "/api/candidates?source=papers") as response:
                data = json.load(response)
        self.assertEqual(data["items"][0]["id"], STORY["id"])

    def test_generate_uses_cached_story_and_allowed_model(self):
        self.server.candidates = {STORY["id"]: STORY}
        expected = {"title": "Test briefing", "chapters": [{"url": STORY["url"]}]}
        body = json.dumps({"ids": [STORY["id"]], "model": "gpt-5.6-luna", "focus": "AI agents"}).encode()
        request = urllib.request.Request(self.base + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
        with patch("web_server.compose_with_openai", return_value=expected) as compose:
            with urllib.request.urlopen(request) as response:
                data = json.load(response)
        self.assertEqual(data["episode"], expected)
        self.assertEqual(compose.call_args.args[0][0]["url"], STORY["url"])


if __name__ == "__main__":
    unittest.main()
