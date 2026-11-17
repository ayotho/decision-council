#!/usr/bin/env python3
"""Build mentor files for the Decision Council from YouTube.

Free, no API keys, no accounts. It uses yt-dlp (open source) to read the
captions of public videos and writes one tidy text file per mentor that you
upload to your ChatGPT Project.

Examples
  python3 build_mentors.py --mentor "Alex Hormozi | @AlexHormozi | 25"
  python3 build_mentors.py --mentor "Ali Abdaal | https://www.youtube.com/@aliabdaal | 20 | productivity, focus"
  python3 build_mentors.py --config mentors.txt

Mentor format (one per --mentor, or one per line in a config file):
  Name | YouTube links (comma separated) | how many videos | only titles with these words | what they're good for
Only the name and one link are required. A link can be a channel (@handle),
a playlist or single videos.

Personal use only: the files hold transcripts of other people's videos. Keep
them in your own ChatGPT Project and don't republish them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse

DEFAULT_MAX = 25
DEFAULT_OUT = "council-files"
HERE = pathlib.Path(__file__).resolve().parent


# ---------------------------------------------------------------- setup


def ensure_yt_dlp() -> None:
    """Import yt-dlp, or install it into a private folder next to this script and re-run."""
    try:
        import yt_dlp  # noqa: F401
        return
    except ImportError:
        pass
    if os.environ.get("COUNCIL_CHILD"):
        sys.exit("Could not load yt-dlp after installing it. Try: python3 -m pip install yt-dlp")
    import venv

    vdir = HERE / ".council-venv"
    py = vdir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        print("First run: setting up the free YouTube reader (yt-dlp). This takes about a minute...", flush=True)
        venv.create(vdir, with_pip=True)
    subprocess.check_call([str(py), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--upgrade", "yt-dlp"])
    env = dict(os.environ, COUNCIL_CHILD="1")
    sys.exit(subprocess.call([str(py), str(pathlib.Path(__file__).resolve()), *sys.argv[1:]], env=env))


# ---------------------------------------------------------------- parsing helpers


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "mentor"


_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def normalise_url(raw: str) -> tuple[str, str]:
    """Return ("list", url) for channels and playlists, ("video", url) for one video."""
    s = raw.strip()
    if s.startswith("@"):
        s = "https://www.youtube.com/" + s
    if not re.match(r"^https?://", s):
        s = "https://" + s
    u = urllib.parse.urlparse(s)
    host = u.netloc.lower().split(":")[0]
    if host.startswith("www.") or host.startswith("m."):
        host = host.split(".", 1)[1]
    q = urllib.parse.parse_qs(u.query)
    if host == "youtu.be":
        vid = u.path.strip("/").split("/")[0]
        if _VIDEO_ID.match(vid):
            return "video", f"https://www.youtube.com/watch?v={vid}"
        raise ValueError(f"Not a YouTube video link: {raw}")
    if host not in ("youtube.com", "music.youtube.com"):
        raise ValueError(f"Not a YouTube link: {raw}")
    parts = [p for p in u.path.split("/") if p]
    if parts[:1] == ["watch"] and q.get("v"):
        return "video", f"https://www.youtube.com/watch?v={q['v'][0]}"
    if parts[:1] in (["shorts"], ["live"], ["embed"]) and len(parts) > 1 and _VIDEO_ID.match(parts[1]):
        return "video", f"https://www.youtube.com/watch?v={parts[1]}"
    if parts[:1] == ["playlist"] and q.get("list"):
        return "list", f"https://www.youtube.com/playlist?list={q['list'][0]}"
    if parts and (parts[0].startswith("@") or parts[0] in ("channel", "c", "user")):
        base = parts[:1] if parts[0].startswith("@") else parts[:2]
        tab = parts[len(base)] if len(parts) > len(base) else "videos"
        if tab not in ("videos", "streams", "podcasts", "shorts", "playlists"):
            tab = "videos"
        return "list", "https://www.youtube.com/" + "/".join(base + [tab])
    raise ValueError(f"Couldn't read this YouTube link: {raw}")


def parse_mentor(spec: str) -> dict:
    parts = [p.strip() for p in spec.split("|")]
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f'Need at least "Name | YouTube link", got: {spec!r}')
    name = parts[0]
    sources = [normalise_url(x) for x in parts[1].split(",") if x.strip()]
    max_videos = DEFAULT_MAX
    if len(parts) > 2 and parts[2]:
        if not parts[2].isdigit():
            raise ValueError(f"The video count for {name} should be a number, got {parts[2]!r}")
        max_videos = max(1, min(200, int(parts[2])))
    keywords = [k.strip().lower() for k in parts[3].split(",") if k.strip()] if len(parts) > 3 else []
    lens = parts[4] if len(parts) > 4 else ""
    return {"name": name, "slug": slugify(name), "sources": sources, "max": max_videos, "keywords": keywords, "lens": lens}


_TIME = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d{3})\s+-->")


def _secs(m: re.Match) -> float:
    h = int(m.group(1) or 0)
    return h * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + int(m.group(4)) / 1000


def parse_vtt(text: str) -> list[tuple[float, str]]:
    """Caption cues as (start_seconds, line), with YouTube's rolling duplicates removed."""
    out: list[tuple[float, str]] = []
    recent: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    start = None
    for i, ln in enumerate(lines):
        m = _TIME.search(ln)
        if m:
            start = _secs(m)
            continue
        if start is None:
            continue  # header (WEBVTT, Kind, Language)
        if i + 1 < len(lines) and _TIME.search(lines[i + 1]):
            continue  # cue identifier such as "2"
        clean = html.unescape(re.sub(r"<[^>]+>", "", ln))
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean or clean in recent:
            continue
        out.append((start, clean))
        recent = (recent + [clean])[-3:]
    return out


def to_paragraphs(segs: list[tuple[float, str]], window: int = 60) -> list[tuple[int, str]]:
    paras: list[tuple[int, str]] = []
    start, buf = None, []
    for t, line in segs:
        if start is None:
            start = t
        elif t - start >= window:
            paras.append((int(start), " ".join(buf)))
            start, buf = t, []
        buf.append(line)
    if buf:
        paras.append((int(start), " ".join(buf)))
    return paras


def stamp(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pick_videos(entries: list[dict], max_videos: int, sort: str, keywords: list[str], min_seconds: int) -> list[dict]:
    keep = []
    for e in entries:
        if not e or not e.get("id"):
            continue
        d = e.get("duration")
        if d is not None and d < min_seconds:
            continue
        if keywords and not any(k in (e.get("title") or "").lower() for k in keywords):
            continue
        keep.append(e)
    if sort == "popular":
        keep.sort(key=lambda e: e.get("view_count") or -1, reverse=True)
    return keep[:max_videos]


# ---------------------------------------------------------------- YouTube


class YouTube:
    def __init__(self, lang: str, cookies_from: str | None, pause: float):
        import yt_dlp

        self.yt_dlp = yt_dlp
        self.lang = lang
        self.pause = pause
        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "retries": 3, "sleep_interval_requests": 0.5}
        if cookies_from:
            opts["cookiesfrombrowser"] = (cookies_from,)
        self.opts = opts

    def list_entries(self, url: str, limit: int) -> list[dict]:
        o = dict(self.opts, extract_flat="in_playlist", playlistend=limit)
        with self.yt_dlp.YoutubeDL(o) as y:
            info = y.extract_info(url, download=False)
        return [e for e in (info.get("entries") or []) if e]

    def video(self, url: str) -> tuple[dict, list[tuple[float, str]] | None]:
        with self.yt_dlp.YoutubeDL(self.opts) as y:
            info = y.extract_info(url, download=False)
            track = self._pick_track(info)
            if not track:
                return info, None
            raw = y.urlopen(track).read().decode("utf-8", "replace")
        return info, parse_vtt(raw)

    def _pick_track(self, info: dict) -> str | None:
        lang = self.lang
        manual = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}
        order = [(manual, lang), (manual, f"{lang}-orig")]
        order += [(manual, k) for k in manual if k.startswith(lang + "-")]
        order += [(auto, f"{lang}-orig"), (auto, lang)]
        for pool, key in order:
            for fmt in pool.get(key) or []:
                if fmt.get("ext") == "vtt" and fmt.get("url"):
                    return fmt["url"]
        return None


# ---------------------------------------------------------------- building


def fetch_video(yt: YouTube, vid: str, cache: pathlib.Path) -> dict | None:
    path = cache / f"{vid}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    url = f"https://www.youtube.com/watch?v={vid}"
    for attempt in (1, 2):
        try:
            info, segs = yt.video(url)
            break
        except Exception as e:  # network, 429, private video...
            msg = str(e).splitlines()[0][:160]
            if attempt == 1 and ("429" in msg or "Too Many" in msg):
                print("    YouTube asked us to slow down. Waiting 60 seconds...")
                time.sleep(60)
                continue
            print(f"    skipped ({msg})")
            return None
    if not segs:
        print("    skipped (no captions in this language)")
        return None
    rec = {
        "id": vid,
        "title": info.get("title") or vid,
        "upload_date": info.get("upload_date") or "",
        "duration": info.get("duration") or 0,
        "views": info.get("view_count") or 0,
        "channel": info.get("channel") or info.get("uploader") or "",
        "paragraphs": to_paragraphs(segs),
    }
    path.write_text(json.dumps(rec), encoding="utf-8")
    time.sleep(yt.pause)
    return rec


def human_views(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def human_date(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else "unknown"


def write_mentor_file(m: dict, videos: list[dict], out: pathlib.Path) -> pathlib.Path:
    words = sum(len(p[1].split()) for v in videos for p in v["paragraphs"])
    sources = ", ".join(u for _, u in m["sources"])
    lines = [
        f"# Mentor: {m['name']}",
        "",
        f"Mentor name: {m['name']}",
    ]
    if m["lens"]:
        lines.append(f"Good for: {m['lens']}")
    lines += [
        f"Source: YouTube ({sources})",
        f"Built: {dt.date.today().isoformat()} with build_mentors.py (Decision Council)",
        f"Videos: {len(videos)} | Words: {words:,}",
        "",
        "What this file is: automatic transcripts of this person's public videos. It is the ONLY",
        f"source the council may use for {m['name']}. Caption errors are possible.",
        "How to cite: video title plus a link made as https://youtu.be/VIDEO_ID?t=SECONDS, using the",
        "video ID in each video's header and the t= number in front of each paragraph.",
        "",
        "## Contents",
    ]
    for i, v in enumerate(videos, 1):
        lines.append(f"{i}. {v['title']} ({human_date(v['upload_date'])}, {stamp(v['duration'])}) https://youtu.be/{v['id']}")
    for i, v in enumerate(videos, 1):
        lines += [
            "",
            "---",
            "",
            f"## {m['name']} | Video {i}: {v['title']}",
            f"Video ID: {v['id']} | Link: https://youtu.be/{v['id']} | Published: {human_date(v['upload_date'])}"
            f" | Length: {stamp(v['duration'])} | Views: {human_views(v['views'])}",
            "",
        ]
        for t, text in v["paragraphs"]:
            lines.append(f"[{stamp(t)} t={t}] {text}")
    path = out / f"mentor-{m['slug']}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_mentor(yt: YouTube, m: dict, out: pathlib.Path, cache: pathlib.Path, args) -> tuple[pathlib.Path | None, int]:
    print(f"\n== {m['name']}")
    candidates: list[dict] = []
    for kind, url in m["sources"]:
        if kind == "video":
            candidates.append({"id": url.rsplit("=", 1)[1], "title": "", "duration": None, "view_count": None})
            continue
        limit = m["max"] if args.sort == "recent" and not m["keywords"] else min(400, max(100, m["max"] * 4))
        print(f"  Reading the video list: {url}")
        try:
            entries = yt.list_entries(url, limit)
        except Exception as e:
            print(f"  Couldn't read that list ({str(e).splitlines()[0][:160]})")
            continue
        candidates += pick_videos(entries, m["max"], args.sort, m["keywords"], args.min_minutes * 60)
    seen, picked = set(), []
    for c in candidates:
        if c["id"] not in seen:
            seen.add(c["id"])
            picked.append(c)
    picked = picked[: max(m["max"], sum(1 for k, _ in m["sources"] if k == "video"))]
    if not picked:
        print("  No videos matched. Check the link, or remove the title filter.")
        return None, 0
    videos, words = [], 0
    for i, c in enumerate(picked, 1):
        label = (c.get("title") or c["id"])[:70]
        print(f"  [{i}/{len(picked)}] {label}")
        rec = fetch_video(yt, c["id"], cache)
        if not rec:
            continue
        videos.append(rec)
        words += sum(len(p[1].split()) for p in rec["paragraphs"])
        if words >= args.max_words:
            print(f"  Reached the {args.max_words:,}-word cap for one file. Stopping here for {m['name']}.")
            break
    if not videos:
        print(f"  No captions found for {m['name']}.")
        return None, 0
    return write_mentor_file(m, videos, out), len(videos)


def read_config(path: str) -> list[str]:
    specs = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            specs.append(line)
    return specs


def open_folder(path: pathlib.Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Turn YouTube channels into mentor files for your Decision Council.")
    p.add_argument("--mentor", action="append", default=[], help='"Name | link(s) | count | title words | good for"')
    p.add_argument("--config", help="a text file with one mentor per line, same format")
    p.add_argument("--out", default=DEFAULT_OUT, help=f"output folder (default: {DEFAULT_OUT})")
    p.add_argument("--sort", choices=["popular", "recent"], default="popular",
                   help="popular = most viewed of the channel's latest 100+ uploads; recent = newest first (default: popular)")
    p.add_argument("--lang", default="en", help="caption language code (default: en)")
    p.add_argument("--min-minutes", type=float, default=3, help="skip videos shorter than this (default: 3, skips Shorts)")
    p.add_argument("--max-words", type=int, default=300_000, help="word cap per mentor file (default: 300000)")
    p.add_argument("--pause", type=float, default=1.5, help="seconds to wait between videos (default: 1.5)")
    p.add_argument("--cookies-from-browser", dest="cookies", help="chrome, edge, firefox or safari, if YouTube asks you to sign in")
    p.add_argument("--no-open", action="store_true", help="don't open the folder at the end")
    args = p.parse_args(argv)

    specs = list(args.mentor) + (read_config(args.config) if args.config else [])
    if not specs:
        p.print_help()
        return 2
    try:
        mentors = [parse_mentor(s) for s in specs]
    except ValueError as e:
        print(f"Problem with a mentor line: {e}")
        return 2

    ensure_yt_dlp()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cache = pathlib.Path(".council-cache") / args.lang
    cache.mkdir(parents=True, exist_ok=True)
    yt = YouTube(args.lang, args.cookies, args.pause)

    made = []
    for m in mentors:
        path, n = build_mentor(yt, m, out, cache, args)
        if path:
            made.append((m["name"], path, n))

    print("\n" + "=" * 60)
    if not made:
        print("No mentor files were made. See the messages above.")
        print("If YouTube said 'sign in to confirm you're not a bot', run again with")
        print("  --cookies-from-browser chrome   (or edge / firefox / safari)")
        return 1
    print(f"Done. {len(made)} mentor file(s) in: {out}\n")
    for name, path, n in made:
        kb = path.stat().st_size // 1024
        print(f"  {path.name:<40} {name}, {n} videos, {kb} KB")
    print("\nNext: upload every file in that folder to your ChatGPT Project (Add files).")
    print("Re-running is fast: videos already read are reused.")
    if not args.no_open:
        open_folder(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
