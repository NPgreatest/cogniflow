import unittest
import io
import json
from unittest.mock import patch

from episode_generator import compose_with_openai, create_episode, dedupe, select_stories


class EpisodeTests(unittest.TestCase):
    def setUp(self):
        self.story = {
            "id": "one", "title": "New AI agent evaluation",
            "url": "https://example.org/story", "source": "Example",
            "summary": "An evaluation method is proposed.",
        }

    def test_dedupe_and_reject_insecure_urls(self):
        result = dedupe([self.story, {**self.story, "id": "two"}, {**self.story, "id": "three", "url": "http://example.org"}])
        self.assertEqual(len(result), 1)

    def test_selection_and_citation(self):
        selected = select_stories([self.story], {"topics": ["agents"]}, 3)
        episode = create_episode(selected, {"topics": ["agents"]})
        self.assertEqual(episode["chapters"][0]["url"], self.story["url"])
        self.assertIn("evaluation method is proposed", episode["script"])

    def test_headline_only_is_labeled(self):
        selected = select_stories([{**self.story, "summary": ""}], {"topics": ["agents"]}, 3)
        episode = create_episode(selected, {"topics": ["agents"]})
        self.assertIn("not verified the full article", episode["script"])

    def test_ai_output_preserves_source_link(self):
        selected = select_stories([self.story], {"topics": ["agents"]}, 1)
        draft = {"title": "AI evaluation", "opening": "Welcome.",
                 "segments": [{"story_id": "one", "narration": "Example describes an evaluation method."}],
                 "closing": "Source links are in the notes."}
        response = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(draft)}]}], "usage": {"input_tokens": 1}}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())):
            episode = compose_with_openai(selected, {"topics": ["agents"]}, "test-model")
        self.assertEqual(episode["chapters"][0]["url"], self.story["url"])
        self.assertEqual(episode["model"], "test-model")

    def test_podcast_can_reorder_sources_without_losing_citations(self):
        second = {**self.story, "id": "two", "title": "Voice AI evaluation",
                  "url": "https://example.org/voice"}
        selected = select_stories([self.story, second], {"topics": ["agents", "tts"]}, 2)
        draft = {"title": "A thought for the commute", "opening": "What makes an agent useful?",
                 "segments": [
                     {"story_id": "two", "narration": "Voice systems offer one perspective."},
                     {"story_id": "one", "narration": "Evaluation offers another."}],
                 "closing": "The useful question is what we can measure."}
        response = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(draft)}]}]}
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())):
            episode = compose_with_openai(selected, {"topics": ["agents"]}, "test-model")
        self.assertEqual([chapter["url"] for chapter in episode["chapters"]],
                         ["https://example.org/voice", "https://example.org/story"])
        self.assertNotIn("Voice AI evaluation", episode["script"])


if __name__ == "__main__":
    unittest.main()
