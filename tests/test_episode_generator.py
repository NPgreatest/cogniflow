import unittest

from episode_generator import create_episode, dedupe, select_stories


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


if __name__ == "__main__":
    unittest.main()
