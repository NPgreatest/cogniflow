"""Local-only Cogniflow web MVP. Run: python3 web_server.py"""

from __future__ import annotations

import json
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from episode_generator import (
    ROOT, compose_with_openai, dedupe, fetch_hacker_news,
    fetch_hf_daily_papers, load_env_file, score_story,
)

FILES = {
    "/": (ROOT / "web_mvp.html", "text/html; charset=utf-8"),
    "/web_mvp.css": (ROOT / "web_mvp.css", "text/css; charset=utf-8"),
    "/web_mvp.js": (ROOT / "web_mvp.js", "text/javascript; charset=utf-8"),
}
MODELS = {"gpt-5.6-luna", "gpt-5.6-terra"}
SOURCES = {"hn", "papers"}


class CogniflowServer(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, CogniflowHandler)
        self.candidates: dict[str, dict] = {}


class CogniflowHandler(BaseHTTPRequestHandler):
    server: CogniflowServer

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path in FILES:
            path, content_type = FILES[parsed.path]
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path != "/api/candidates":
            self.send_json(404, {"error": "Not found"})
            return
        requested = set(parse_qs(parsed.query).get("source", ["hn", "papers"])) & SOURCES
        if not requested:
            self.send_json(400, {"error": "Select at least one source."})
            return
        items, warnings = [], []
        for source, fetcher in (("hn", fetch_hacker_news), ("papers", fetch_hf_daily_papers)):
            if source not in requested:
                continue
            try:
                items.extend(fetcher(20))
            except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                warnings.append(f"{source} is unavailable: {type(exc).__name__}")
        items = dedupe(items)
        items.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        items = items[:40]
        self.server.candidates = {item["id"]: item for item in items}
        self.send_json(200 if items else 503, {"items": items, "warnings": warnings})

    def do_POST(self) -> None:
        if self.path != "/api/generate":
            self.send_json(404, {"error": "Not found"})
            return
        origin = self.headers.get("Origin", "")
        if origin and origin != f"http://127.0.0.1:{self.server.server_port}":
            self.send_json(403, {"error": "This demo accepts requests only from its local page."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("Invalid request size.")
            request = json.loads(self.rfile.read(length))
            ids, model = request.get("ids"), request.get("model")
            focus = str(request.get("focus", "AI and machine learning")).strip()[:120]
            if not isinstance(ids, list) or not 1 <= len(ids) <= 5 or len(set(ids)) != len(ids):
                raise ValueError("Choose 1–5 distinct items.")
            if model not in MODELS:
                raise ValueError("Unsupported model.")
            if not focus:
                raise ValueError("Enter a topic or learning goal.")
            if any(item_id not in self.server.candidates for item_id in ids):
                raise ValueError("Refresh the feed and choose items again.")
            profile = {"name": "listener", "topics": [focus], "knowledge_level": "intermediate"}
            selected = []
            for item_id in ids:
                story = self.server.candidates[item_id]
                _, reason = score_story(story, [focus.casefold()])
                selected.append({**story, "selection_reason": reason})
            load_env_file()
            episode = compose_with_openai(selected, profile, model)
            self.send_json(200, {"episode": episode})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(502, {"error": str(exc)})
        except urllib.error.URLError:
            self.send_json(502, {"error": "The model service is unavailable. Try again shortly."})


def main() -> None:
    address = ("127.0.0.1", 8765)
    server = CogniflowServer(address)
    print(f"Cogniflow web MVP: http://{address[0]}:{address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
