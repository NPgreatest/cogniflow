"""Small, source-grounded Cogniflow episode generator (Python standard library)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = ROOT / "examples" / "profile.json"
DEFAULT_STORIES = ROOT / "examples" / "stories.json"
USER_AGENT = "Cogniflow-MVP/0.1 (personal research prototype)"
OPENAI_API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6-luna"
PODCAST_PROMPT = ROOT / "prompts" / "podcast_v1.txt"
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


def load_env_file(path: Path = ROOT / ".env") -> None:
    """Load simple KEY=VALUE entries without printing or overriding shell variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"\'')


def compose_with_openai(selected: list[dict], profile: dict, model: str) -> dict:
    """One grounded, structured LLM call; it does not itself browse the web."""
    if not selected:
        raise ValueError("No relevant stories found. Try different topics or more candidates.")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing; add it to the ignored .env file.")
    source_cards = [
        {
            "id": story["id"],
            "title": clean_for_speech(story["title"])[:240],
            "source": story["source"],
            "published_at": story.get("published_at", ""),
            "summary": clean_for_speech(story.get("summary", ""))[:1400],
            "evidence_level": story.get("evidence_level", "headline_only"),
        }
        for story in selected
    ]
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "opening": {"type": "string"},
            "segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"story_id": {"type": "string"}, "narration": {"type": "string"}},
                    "required": ["story_id", "narration"],
                    "additionalProperties": False,
                },
            },
            "closing": {"type": "string"},
        },
        "required": ["title", "opening", "segments", "closing"],
        "additionalProperties": False,
    }
    instructions = PODCAST_PROMPT.read_text(encoding="utf-8")
    payload = {
        "model": model,
        "instructions": instructions,
        "input": json.dumps({"profile": profile, "source_cards": source_cards}, ensure_ascii=False),
        "text": {"format": {"type": "json_schema", "name": "cogniflow_episode", "strict": True, "schema": schema}},
        "max_output_tokens": 2400,
        "store": False,
    }
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenAI request failed (HTTP {exc.code}); check key, model access, and billing.") from None
    content = [
        part.get("text", "")
        for item in result.get("output", []) if item.get("type") == "message"
        for part in item.get("content", []) if part.get("type") == "output_text"
    ]
    if not content:
        raise RuntimeError("OpenAI returned no text; try again or increase the output token limit.")
    draft = json.loads("".join(content))
    expected = [story["id"] for story in selected]
    actual = [segment["story_id"] for segment in draft["segments"]]
    if len(actual) != len(expected) or set(actual) != set(expected):
        raise ValueError("Model output did not preserve all selected source IDs exactly once.")
    stories_by_id = {story["id"]: story for story in selected}
    chapters = [
        {
            "title": story["title"], "source": story["source"], "url": story["url"],
            "published_at": story.get("published_at", ""),
            "evidence_level": story.get("evidence_level", "headline_only"),
            "selection_reason": story["selection_reason"],
            "narration": clean_for_speech(segment["narration"]),
        }
        for segment in draft["segments"]
        for story in [stories_by_id[segment["story_id"]]]
    ]
    script = "\n\n".join([clean_for_speech(draft["opening"]),
                           *[chapter["narration"] for chapter in chapters],
                           clean_for_speech(draft["closing"])])
    return {
        "title": clean_for_speech(draft["title"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile, "chapters": chapters, "script": script,
        "model": model, "usage": result.get("usage", {}),
        "note": "AI-generated from source metadata. Review facts against linked sources before sharing.",
    }


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


def synthesize_macos_mp3(script: str, output: Path, voice: str | None = None) -> Path:
    """Generate speech with macOS say, then encode a phone-friendly MP3."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("MP3 export requires ffmpeg and ffprobe. Install them before generating audio.")
    output.mkdir(parents=True, exist_ok=True)
    mp3 = output / "episode.mp3"
    with tempfile.TemporaryDirectory(prefix="cogniflow-tts-") as temp_dir:
        aiff = synthesize_macos(script, Path(temp_dir), voice)
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(aiff),
             "-codec:a", "libmp3lame", "-qscale:a", "3", str(mp3)],
            check=True, capture_output=True,
        )
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)],
        capture_output=True, text=True,
    )
    try:
        duration = float(probe.stdout.strip()) if probe.returncode == 0 else 0
    except ValueError:
        duration = 0
    if duration < 0.5:
        mp3.unlink(missing_ok=True)
        raise RuntimeError("macOS produced an empty audio file. Retry with local speech permission enabled.")
    return mp3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a source-linked Cogniflow briefing")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--stories", type=Path, default=DEFAULT_STORIES)
    parser.add_argument("--out", type=Path, default=Path("episode-output"))
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--live-hn", action="store_true", help="Add fresh HN candidates")
    parser.add_argument("--live-papers", action="store_true", help="Add HF Daily Papers candidates")
    parser.add_argument("--live-only", action="store_true", help="Exclude sample stories from this run")
    parser.add_argument("--ai", action="store_true", help="Use OpenAI to write a source-grounded script")
    parser.add_argument("--model", default=None, help="OpenAI model (default: gpt-5.6-luna)")
    parser.add_argument("--tts", action="store_true", help="Generate audio with macOS say")
    parser.add_argument("--voice", help="Optional installed macOS voice name")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    stories = [] if args.live_only else json.loads(args.stories.read_text(encoding="utf-8"))
    if args.live_only and not (args.live_hn or args.live_papers):
        parser.error("--live-only requires --live-hn and/or --live-papers")
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
    selected = select_stories(stories, profile, args.limit)
    if args.ai:
        load_env_file()
        episode = compose_with_openai(selected, profile, args.model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL))
    else:
        episode = create_episode(selected, profile)
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
