"""
Field Notes Admin Server
========================
Lightweight local admin dashboard server.

Usage:
    .venv/bin/python admin_server.py
    .venv/bin/python admin_server.py --port 7657

Then open: http://localhost:7657/admin

Password: fieldnotes2026  (change ADMIN_PASSWORD below)
"""

import datetime
import glob
import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

ADMIN_PASSWORD = "fieldnotes2026"
PORT = 7657
BASE_DIR = Path(__file__).parent

NEWSLETTER_OUTPUT_DIR = BASE_DIR / "newsletter" / "output"
POSTS_FILE            = BASE_DIR / "social" / "data" / "scheduled_posts.json"
FIRST_COMMENTS_FILE   = BASE_DIR / "social" / "data" / "first_comments.json"
POST_PROMPT_FILE      = BASE_DIR / "social" / "data" / "post_prompt.txt"
ADMIN_HTML            = BASE_DIR / "web" / "admin.html"

# ── .env loader ───────────────────────────────────────────────────────────────

def _load_env():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # Prefer .env value over empty shell env vars
            if not os.environ.get(k):
                os.environ[k] = v

_load_env()

# ── Claude client ─────────────────────────────────────────────────────────────

_claude = None

def get_claude():
    global _claude
    if _claude is None:
        try:
            import anthropic  # noqa: PLC0415
            _claude = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        except ImportError:
            raise RuntimeError("anthropic package not installed — run: pip install anthropic")
    return _claude


def claude_ask(prompt: str, max_tokens: int = 1200) -> str:
    msg = get_claude().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# ── Section → source data mapping ────────────────────────────────────────────

SECTION_DATA_FILES = {
    "markets":           ["data/ahdb_grain.json"],
    "inputs":            ["data/ahdb_fertiliser.json", "data/ahdb_feed.json"],
    "weather":           ["data/met_office.json"],
    "schemes":           ["data/govuk_schemes.json"],
    "news":              ["data/local_news.json", "data/defra_blog.json"],
    "land":              ["data/land_listings.json"],
    "jobs":              ["data/jobs.json"],
    "machinery":         ["data/machinery_auctions.json"],
    "livestock":         ["data/ahdb_livestock.json", "data/norwich_livestock.json"],
    "regulatory":        ["data/defra_blog.json", "data/local_news.json"],
    "events":            ["data/events.json", "data/community_events.json"],
    "monday_newsletter": [],
}

ALL_DATA_FILES = [
    "data/ahdb_grain.json",
    "data/ahdb_livestock.json",
    "data/ahdb_fertiliser.json",
    "data/ahdb_feed.json",
    "data/met_office.json",
    "data/govuk_schemes.json",
    "data/local_news.json",
    "data/defra_blog.json",
    "data/events.json",
    "data/jobs.json",
    "data/land_listings.json",
    "data/machinery_auctions.json",
    "data/norwich_livestock.json",
]


def _load_data_files(file_list):
    result = {}
    for f in file_list:
        fp = BASE_DIR / f
        if fp.exists():
            try:
                result[Path(f).name] = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                pass
    return result


def _post_prompt_guidelines():
    if POST_PROMPT_FILE.exists():
        return POST_PROMPT_FILE.read_text(encoding="utf-8")[:2500]
    return (
        "Max 180 words. Direct, factual, no fluff. Specific numbers. "
        "Exactly 2 hashtags: #EastAnglia + one topic. No URL in body. "
        "End with: 'Full briefing — link in comments.'"
    )


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _json_response(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _error(handler, message, status=400):
    _json_response(handler, {"error": message}, status)


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# ── Newsletter helpers ────────────────────────────────────────────────────────

def _latest_newsletter():
    pattern = str(NEWSLETTER_OUTPUT_DIR / "field_notes_*.html")
    files = glob.glob(pattern)
    if not files:
        return None, None
    latest = max(files, key=os.path.getmtime)
    html = Path(latest).read_text(encoding="utf-8")
    return html, Path(latest).name


def _newsletter_meta(filename):
    mtime = os.path.getmtime(NEWSLETTER_OUTPUT_DIR / filename)
    return datetime.datetime.fromtimestamp(mtime).strftime("%d %b %Y, %H:%M")


# ── Posts helpers ─────────────────────────────────────────────────────────────

def _load_posts():
    if not POSTS_FILE.exists():
        return {"posts": []}
    return json.loads(POSTS_FILE.read_text(encoding="utf-8"))


def _save_posts(data):
    POSTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Request handler ───────────────────────────────────────────────────────────

class AdminHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):  # noqa: A002
        print(f"  {self.address_string()} {format % args}")

    def _check_auth(self):
        if self.headers.get("X-Admin-Password", "") != ADMIN_PASSWORD:
            _error(self, "Unauthorised", 401)
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-Admin-Password, Content-Type")
        self.end_headers()

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path in ("/admin", "/admin.html", ""):
            if ADMIN_HTML.exists():
                body = ADMIN_HTML.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                _error(self, "admin.html not found", 404)
            return

        if not self._check_auth():
            return

        if path == "/api/newsletter":
            html, filename = _latest_newsletter()
            if html is None:
                _json_response(self, {"html": None, "filename": None})
            else:
                _json_response(self, {"html": html, "filename": filename,
                                      "generated_at": _newsletter_meta(filename)})
            return

        if path == "/api/posts":
            _json_response(self, _load_posts())
            return

        if path == "/api/first-comments":
            if FIRST_COMMENTS_FILE.exists():
                _json_response(self, json.loads(FIRST_COMMENTS_FILE.read_text(encoding="utf-8")))
            else:
                _json_response(self, {"comments": []})
            return

        _error(self, "Not found", 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")

        if not self._check_auth():
            return

        # Newsletter endpoints
        if path == "/api/newsletter/chat":
            self._nl_chat()
            return
        if path == "/api/newsletter/regenerate":
            self._nl_regenerate()
            return

        if path == "/api/posts/regenerate":
            self._posts_regenerate()
            return

        # Posts endpoints: /api/posts/{idx}/{action}
        m = re.match(r"^/api/posts/(\d+)/(approve|unapprove|edit|investigate|alternative)$", path)
        if not m:
            _error(self, "Not found", 404)
            return

        idx = int(m.group(1))
        action = m.group(2)
        data = _load_posts()
        posts = data.get("posts", [])

        if not (0 <= idx < len(posts)):
            _error(self, f"Post index {idx} out of range", 400)
            return

        post = posts[idx]

        if action == "approve":
            if post.get("status") == "blocked":
                _error(self, "Cannot approve a blocked post — investigate or find an alternative first", 400)
                return
            post["approved"] = True
            posts[idx] = post
            data["posts"] = posts
            _save_posts(data)
            _json_response(self, {"ok": True, "post": post})

        elif action == "unapprove":
            post["approved"] = False
            posts[idx] = post
            data["posts"] = posts
            _save_posts(data)
            _json_response(self, {"ok": True, "post": post})

        elif action == "edit":
            body = _read_body(self)
            text = body.get("post_text")
            if text is None:
                _error(self, "Missing post_text", 400)
                return
            post["post_text"] = text
            if post.get("status") == "blocked":
                post["status"] = "edited"
            posts[idx] = post
            data["posts"] = posts
            _save_posts(data)
            _json_response(self, {"ok": True, "post": post})

        elif action == "investigate":
            self._post_investigate(post)

        elif action == "alternative":
            body = _read_body(self)
            self._post_alternative(idx, post, posts, data, body)

    # ── Newsletter: AI chat ───────────────────────────────────────────────────

    def _nl_chat(self):
        body = _read_body(self)
        action    = body.get("action", "ask")   # "ask" | "update"
        question  = body.get("question", "").strip()
        section_id   = body.get("section_id", "")
        section_text = body.get("section_text", "")  # plain text of selected section
        section_html = body.get("section_html", "")  # outerHTML (for update action)

        if not question:
            _error(self, "Missing question", 400)
            return

        section_ctx = ""
        if section_id:
            section_ctx = f"\n\nSelected section: **{section_id}**\n"
            if section_text:
                section_ctx += f"Current content:\n{section_text[:2500]}"

        if action == "ask":
            prompt = f"""You are helping review a section of the Field Notes East Anglia weekly farming newsletter.

This is a free weekly farming intelligence briefing for East Anglian (Norfolk, Suffolk, Cambridgeshire) farmers covering grain prices, fertiliser, margins, livestock, schemes, weather, land, jobs, machinery and events.
{section_ctx}

Editor's question: {question}

Be concise and specific. If commenting on copy quality, point to exact phrases."""

        elif action == "update":
            if not section_html:
                _error(self, "No section selected — click a section in the newsletter first", 400)
                return
            prompt = f"""You are editing a section of the Field Notes East Anglia farming newsletter.

The newsletter uses email HTML (tables, inline styles). Your job: rewrite the TEXT CONTENT of this section according to the editor's instruction, but preserve ALL HTML tags, attributes, and inline styles exactly.

Section: {section_id or "unknown"}

Editor instruction: {question}

Current HTML:
{section_html[:3500]}

Return ONLY the modified HTML. Do not add explanation. Keep the identical structure — only change text content inside the HTML elements."""

        else:
            prompt = f"You are helping edit the Field Notes East Anglia newsletter.\n{section_ctx}\n\n{question}"

        try:
            response = claude_ask(prompt)
            _json_response(self, {"response": response, "action": action})
        except Exception as e:
            _error(self, f"Claude error: {e}", 500)

    # ── Newsletter: regenerate ────────────────────────────────────────────────

    def _nl_regenerate(self):
        try:
            result = subprocess.run(
                [str(BASE_DIR / ".venv/bin/python"), str(BASE_DIR / "newsletter/generate.py")],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=str(BASE_DIR),
            )
            if result.returncode != 0:
                _error(self, f"generate.py failed:\n{result.stderr[-1200:]}", 500)
                return
            html, filename = _latest_newsletter()
            _json_response(self, {
                "ok": True,
                "html": html,
                "filename": filename,
                "generated_at": _newsletter_meta(filename),
                "log": result.stdout[-400:],
            })
        except subprocess.TimeoutExpired:
            _error(self, "Newsletter regeneration timed out after 180s", 500)
        except Exception as e:
            _error(self, str(e), 500)

    # ── Posts: regenerate all ────────────────────────────────────────────────

    def _posts_regenerate(self):
        try:
            result = subprocess.run(
                [str(BASE_DIR / ".venv/bin/python"), str(BASE_DIR / "social/generate_posts.py")],
                capture_output=True,
                text=True,
                timeout=360,
                cwd=str(BASE_DIR),
            )
            if result.returncode != 0:
                _error(self, f"generate_posts.py failed:\n{result.stderr[-1200:]}", 500)
                return
            posts_data = _load_posts()
            _json_response(self, {
                "ok": True,
                "posts": posts_data.get("posts", []),
                "count": len(posts_data.get("posts", [])),
                "generated_at": posts_data.get("generated_at", ""),
                "log": result.stdout[-600:],
            })
        except subprocess.TimeoutExpired:
            _error(self, "Post regeneration timed out after 360s", 500)
        except Exception as e:
            _error(self, str(e), 500)

    # ── Posts: investigate blocked post ──────────────────────────────────────

    def _post_investigate(self, post):
        section      = post.get("section", "")
        block_reason = post.get("block_reason", "")
        post_text    = post.get("post_text", "")
        verification = post.get("verification", {})

        source_data = _load_data_files(SECTION_DATA_FILES.get(section, []))

        prompt = f"""You are reviewing a blocked Facebook post for Field Notes East Anglia (weekly farming newsletter, East Anglia).

Post details:
- Section: {section}
- Day/date: {post.get('day')} {post.get('date')} at {post.get('time')}
- Block reason: {block_reason or "(not given)"}
- Gate 1 errors: {json.dumps(verification.get('gate1_errors', []))}
- Gate 2 notes: {json.dumps(verification.get('gate2_notes', []))}

{"Post text that was generated:" if post_text else "No post text was generated."}
{post_text[:800] if post_text else ""}

Source data available at the time of generation:
{json.dumps(source_data, indent=2, default=str)[:3500]}

Please:
1. **Why was this blocked?** Explain in plain English.
2. **Was the block justified?** Check the source data — was the required field actually missing or invalid?
3. **If the data was present** — what went wrong? What could the post have said?
4. **If the block was valid** — what data would need to exist to generate this post?
5. **Recommendation** — should the editor investigate the scraper, find an alternative topic, or write copy manually?

Be specific and practical."""

        try:
            response = claude_ask(prompt, max_tokens=1400)
            _json_response(self, {"response": response})
        except Exception as e:
            _error(self, f"Claude error: {e}", 500)

    # ── Posts: generate alternative ───────────────────────────────────────────

    def _post_alternative(self, idx, post, posts, data, body):
        section    = post.get("section", "")
        day        = post.get("day", "")
        topic_hint = body.get("topic", "").strip()

        all_data = _load_data_files(ALL_DATA_FILES)
        guidelines = _post_prompt_guidelines()

        avoid_note = f"Avoid covering '{section}' — find a DIFFERENT angle." if section else ""

        prompt = f"""You are generating a Facebook post for Field Notes East Anglia, a farming newsletter for Norfolk, Suffolk and Cambridgeshire farmers.

Day: {day} ({post.get('date', '')})
{f"Topic hint from editor: {topic_hint}" if topic_hint else "Find the single most newsworthy item from the data below."}
{avoid_note}

Brand voice rules:
{guidelines[:1800]}

Available data this week:
{json.dumps(all_data, indent=2, default=str)[:3500]}

Write ONE complete Facebook post. Return ONLY the post text — no preamble, no commentary, no "Here's the post:" prefix. Just the post."""

        try:
            response = claude_ask(prompt, max_tokens=450)

            # Strip any accidental preamble Claude might add
            lines = response.strip().split("\n")
            if lines and lines[0].lower().startswith(("here", "sure", "of course", "post:")):
                response = "\n".join(lines[1:]).strip()

            posts[idx]["post_text"] = response
            posts[idx]["status"] = "edited"
            posts[idx]["block_reason"] = ""
            data["posts"] = posts
            _save_posts(data)

            _json_response(self, {"response": response, "post": posts[idx]})
        except Exception as e:
            _error(self, f"Claude error: {e}", 500)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = PORT
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])
        elif arg == "--port" and i + 1 < len(args):
            port = int(args[i + 1])

    server = HTTPServer(("localhost", port), AdminHandler)
    print("Field Notes Admin Server")
    print(f"  http://localhost:{port}/admin")
    print(f"  Password: {ADMIN_PASSWORD}")
    print("  Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
