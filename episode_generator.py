"""Small, source-grounded Cogniflow episode generator (Python standard library)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = ROOT / "examples" / "profile.json"
DEFAULT_STORIES = ROOT / "examples" / "stories.json"
USER_AGENT = "Cogniflow-MVP/0.1 (personal research prototype)"
TOPIC_TERMS = {
    "ai": ("ai", "llm", "model", "agent", "inference", "transformer"),
    "mle": ("machine learning", "training", "inference", "evaluation", "serving", "mlops"),
    "agents": ("agent", "tool use", "workflow", "reasoning"),
    "tts": ("speech", "voice", "tts", "audio"),
}


def fetch_json(url: str) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def fetch_hacker_news(limit: int = 30) -> list[dict]:
    """Fetch recent HN candidates. A title is not treated as article evidence."""
    ids = fetch_json("https://hacker-news.firebaseio.com/v0/newstories.json")
    stories = []
    for item_id in ids[:limit]:
        item = fetch_json(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
        if not isinstance(item, dict) or item.get("type") != "story" or not item.get("title"):
            continue
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        stories.append({
            "id": f"hn-{item_id}", "title": item["title"], "url": url,
            "source": "Hacker News", "published_at": datetime.fromtimestamp(
                item.get("time", 0), timezone.utc
            ).isoformat(), "summary": "", "evidence_level": "headline_only",
        })
    return stories


def fetch_hf_daily_papers(limit: int = 30) -> list[dict]:
    """Use HF's public daily-papers metadata endpoint; no paper PDFs are copied."""
    data = fetch_json(f"https://huggingface.co/api/daily_papers?limit={limit}")
    stories = []
    for entry in data if isinstance(data, list) else []:
        paper = entry.get("paper", {})
        if not paper.get("title") or not paper.get("id"):
            continue
        stories.append({
            "id": f"hf-{paper['id']}", "title": paper["title"],
            "url": f"https://huggingface.co/papers/{paper['id']}",
            "source": "Hugging Face Daily Papers",
            "published_at": entry.get("publishedAt", ""),
            "summary": paper.get("summary", ""),
            "evidence_level": "abstract" if paper.get("summary") else "headline_only",
        })
    return stories


def valid_story(story: dict) -> bool:
    if not all(story.get(k) for k in ("id", "title", "url", "source")):
        return False
    return urlparse(story["url"]).scheme == "https"


def dedupe(stories: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for story in stories:
        if not valid_story(story):
            continue
        key = re.sub(r"\W+", " ", story["title"].casefold()).strip()
        if key in seen:
            continue
        seen.add(key)
        result.append(story)
    return result


def score_story(story: dict, topics: list[str]) -> tuple[int, str]:
    text = f"{story['title']} {story.get('summary', '')}".casefold()
    matches = [topic for topic in topics if any(term in text for term in TOPIC_TERMS.get(topic, (topic,)))]
    score = len(matches) * 3 + (2 if story.get("summary") else 0)
    return score, ", ".join(matches) if matches else "general interest"


def select_stories(stories: list[dict], profile: dict, count: int) -> list[dict]:
    topics = [str(topic).casefold() for topic in profile.get("topics", ["ai"])]
    scored = []
    for story in dedupe(stories):
        score, reason = score_story(story, topics)
        scored.append((score, {**story, "selection_reason": reason}))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [story for score, story in scored if score > 0][:count]


def clean_for_speech(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def create_episode(selected: list[dict], profile: dict) -> dict:
    if not selected:
        raise ValueError("No relevant stories found. Try different topics or more candidates.")
    name = clean_for_speech(profile.get("name", "listener"))
    chapters = []
    script_parts = [
        f"Hello {name}. This is Cogniflow, your brief tour of selected AI and machine learning ideas.",
        "This early version reports only what is supported by the linked headlines or summaries. Follow the sources for full details.",
    ]
    for index, story in enumerate(selected, 1):
        title = clean_for_speech(story["title"])
        summary = clean_for_speech(story.get("summary", ""))
        source = clean_for_speech(story["source"])
        if summary:
            narration = f"Story {index}. {source} highlights: {title}. Its published summary says: {summary}"
        else:
            narration = f"Story {index}. A headline on {source} reads: {title}. We have not verified the full article, so this is a pointer for further reading, not a detailed report."
        chapters.append({
            "title": title, "source": source, "url": story["url"],
            "published_at": story.get("published_at", ""),
            "evidence_level": story.get("evidence_level", "headline_only"),
            "selection_reason": story["selection_reason"], "narration": narration,
        })
        script_parts.append(narration)
    script_parts.append("That is today's Cogniflow. The source links are in your episode notes.")
    return {
        "title": "Cogniflow — AI and MLE briefing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile, "chapters": chapters,
        "script": "\n\n".join(script_parts),
        "note": "Source-grounded prototype. This is not a full-article summary or fact-checked analysis.",
    }


def synthesize_macos(script: str, output: Path, voice: str | None) -> Path:
    if not shutil.which("say"):
        raise RuntimeError("macOS 'say' is unavailable. Run without --tts to get script only.")
    output = output / "episode.aiff"
    command = ["say", "-o", str(output)]
    if voice:
        command.extend(["-v", voice])
    subprocess.run(command + [script], check=True)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a source-linked Cogniflow briefing")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--stories", type=Path, default=DEFAULT_STORIES)
    parser.add_argument("--out", type=Path, default=Path("episode-output"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--live-hn", action="store_true", help="Add fresh HN candidates")
    parser.add_argument("--live-papers", action="store_true", help="Add HF Daily Papers candidates")
    parser.add_argument("--tts", action="store_true", help="Generate audio with macOS say")
    parser.add_argument("--voice", help="Optional installed macOS voice name")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    stories = json.loads(args.stories.read_text(encoding="utf-8"))
    for name, enabled, fetcher in (
        ("Hacker News", args.live_hn, fetch_hacker_news),
        ("Hugging Face Daily Papers", args.live_papers, fetch_hf_daily_papers),
    ):
        if enabled:
            try:
                live = fetcher()
                print(f"Fetched {len(live)} {name} candidates", file=sys.stderr)
                stories.extend(live)
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                print(f"Warning: {name} unavailable: {exc}", file=sys.stderr)
    episode = create_episode(select_stories(stories, profile, args.limit), profile)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "episode.json").write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "episode.txt").write_text(episode["script"] + "\n", encoding="utf-8")
    if args.tts:
        audio = synthesize_macos(episode["script"], args.out, args.voice)
        print(f"Audio: {audio}")
    print(f"Episode: {args.out / 'episode.json'} ({len(episode['chapters'])} stories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
