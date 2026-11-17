#!/usr/bin/env python3
"""Render templates/instructions.md into ChatGPT Project instructions.

The onboarding page does the same thing in the browser (keep the two in step).
This script writes PROMPT.md, the no-setup default with the five thinking seats,
and checks the result fits ChatGPT's 8,000-character limit for Project instructions.

  python3 tools/render_prompt.py                      # writes PROMPT.md
  python3 tools/render_prompt.py --mentor "Alex Hormozi|Offers and pricing" --seat contrarian --print
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

SKILL_HEAD = """---
name: council
description: Run a decision council on a real choice with stakes. Use when the user says "council this", "run the council", "/council", "should I X or Y", "I'm torn between", "pressure-test this decision" or "roast this decision". Mentors built from YouTube transcripts (files in mentors/) and thinking-style seats give blind openings with ratings, debate the cruxes, then a Chair scores the options by rule and gives one recommendation and a first step. Not for factual questions, writing tasks or summaries.
---

# Decision Council

Add your own mentors: run tools/build_mentors.py from the repo and copy the mentor-*.md files into the mentors/ folder next to this file, then zip the council folder and upload it as a skill. With no mentor files, the council runs on the five thinking seats.

"""

_OPTS = json.loads((ROOT / "templates/options.json").read_text(encoding="utf-8"))
LIMIT = _OPTS["limit"]
SEATS = {k: v["line"] for k, v in _OPTS["seats"].items()}
STYLES = _OPTS["styles"]
LENGTHS = _OPTS["lengths"]
MODES = _OPTS["modes"]


def render(name="My Council", about="", focus=(), mentors=(), seats=tuple(SEATS), style="direct",
           length="standard", mode="full", language="English") -> str:
    about_block = ""
    if about.strip() or focus:
        about_block = "\n## About me\n"
        if about.strip():
            about_block += about.strip() + "\n"
        if focus:
            about_block += "I'll mostly bring decisions about: " + ", ".join(focus) + ".\n"
    parts = []
    if mentors:
        parts.append("Mentors (each has a file in this project):")
        parts += [f"- {n}: {lens}" if lens else f"- {n}" for n, lens in mentors]
    if seats:
        parts.append("Thinking seats:")
        parts += ["- " + SEATS[s] for s in seats]
    if not parts:
        parts.append("Thinking seats:")
        parts += ["- " + SEATS[s] for s in SEATS]
    lang = "" if language.strip().lower() in ("", "english") else f"Reply in {language.strip()}."
    t = (ROOT / "templates/instructions.md").read_text(encoding="utf-8")
    for key, val in {
        "COUNCIL_NAME": name.strip() or "My Council",
        "ABOUT_BLOCK": about_block,
        "SEATS_BLOCK": "\n".join(parts),
        "LENGTH": LENGTHS[length],
        "STYLE_LINE": STYLES[style],
        "LANGUAGE_LINE": lang,
        "DEFAULT_MODE": MODES[mode],
    }.items():
        t = t.replace("{{" + key + "}}", val)
    return t.replace(" \n", "\n").strip() + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mentor", action="append", default=[], help='"Name|good for"')
    p.add_argument("--seat", action="append", choices=list(SEATS))
    p.add_argument("--print", action="store_true")
    p.add_argument("--skill", action="store_true", help="write council/SKILL.md instead of PROMPT.md")
    a = p.parse_args()
    mentors = [tuple((m.split("|", 1) + [""])[:2]) for m in a.mentor]
    text = render(mentors=[(n.strip(), l.strip()) for n, l in mentors], seats=tuple(a.seat or SEATS))
    if len(text) > LIMIT:
        print(f"Too long for ChatGPT Project instructions: {len(text)} > {LIMIT}", file=sys.stderr)
        return 1
    if a.print:
        print(text)
    elif a.skill:
        body = text.replace("their own file in this project (mentor-<name>.md)", "their own file in this skill's mentors/ folder (mentor-<name>.md)")
        body = body.replace("Mentors (each has a file in this project):", "Mentors (each has a file in mentors/):")
        body = body.replace("If a mentor listed above has no file you can find", "Seats: every mentor file in mentors/, plus the thinking seats listed. If a mentor has no file you can find")
        (ROOT / "council/SKILL.md").write_text(SKILL_HEAD + body.split("\n", 1)[1].lstrip(), encoding="utf-8")
    else:
        (ROOT / "PROMPT.md").write_text(
            "# Paste-in instructions (works on any ChatGPT plan)\n\n"
            "This is the no-setup version with five thinking seats. For your own mentors, use the setup page\n"
            "(link in the README), which writes a personalised version of this for you.\n\n"
            "Copy everything below the line into ChatGPT: Project > Project settings > Instructions.\n\n---\n\n" + text,
            encoding="utf-8")
    print(f"{len(text)} characters (limit {LIMIT})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
