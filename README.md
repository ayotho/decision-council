# Decision Council

Your own council for hard decisions, inside ChatGPT. You pick the people you learn from on YouTube, a free tool turns their videos into files ChatGPT can read, and every decision gets argued out by those mentors plus a few sharp thinking styles. A Chair scores the options by rule and gives you one recommendation and a first step.

**Start here: the setup page** walks you through it step by step and writes your personalised instructions. (Link from whoever shared this with you.)

```
 YOUR MENTORS (from YouTube)        THINKING SEATS
 Mentor A   Mentor B   ...          Contrarian   Executor
     │          │                        │          │
     └──────────┴──── blind openings ────┴──────────┘
                (each rates every option 1-5)
                          │
              Chair names the cruxes
                          │
              they argue by name, some move
                          │
     THE CHAIR scores by rule: median rating, RUIN caps at 2
     recommendation · what would flip it · first step (48h)
```

## What's in here

| Path | What it is |
|---|---|
| `tools/build_mentors.py` | Free YouTube-to-mentor-file tool. Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp), no API keys or accounts. Sets itself up on first run. |
| `PROMPT.md` | No-setup instructions with five thinking seats. Paste into a ChatGPT Project. |
| `council/` | The same council as a skill (Agent Skills format) for ChatGPT Business/Enterprise/Edu, Codex or Claude. Drop mentor files in `council/mentors/`. |
| `templates/` | The one source for the instructions. The setup page and `tools/render_prompt.py` both build from it. |
| `page/` | The setup page source. |

## Build mentor files yourself

You need Python 3 (Mac: type `python3` in Terminal and accept the developer tools install if asked. Windows: [python.org](https://www.python.org/downloads/windows/), tick "Add python.exe to PATH").

```bash
python3 tools/build_mentors.py --mentor "Alex Hormozi | @AlexHormozi | 25 | | Offers, pricing, sales" --mentor "Ali Abdaal | @aliabdaal | 20 | productivity"
```

Each `--mentor` is `Name | YouTube link(s) | how many videos | only titles with these words | what they're good for`. Only the name and a link are required. A link can be a channel (`@handle`), a playlist or single videos, comma separated.

| Option | Default | What it does |
|---|---|---|
| `--sort popular` / `recent` | popular | Most watched of the channel's latest 100+ uploads, or newest first |
| `--lang en` | en | Caption language |
| `--min-minutes 3` | 3 | Skips Shorts and clips |
| `--cookies-from-browser chrome` | off | Use if YouTube says "sign in to confirm you're not a bot" |
| `--config mentors.txt` | | One mentor per line instead of `--mentor` flags |

Output: `council-files/mentor-<name>.md`, one per mentor. Each video has its ID and link, and every paragraph starts with `[m:ss t=SECONDS]`, so the council can cite the exact moment as `https://youtu.be/ID?t=SECONDS`. Re-runs reuse videos already read (`.council-cache/`).

## Set up ChatGPT

1. Sidebar > **New project**.
2. **Add files**: everything in `council-files/` (Free: 5 files per project, Go/Plus: 25, Pro/Business/Edu: 40).
3. Paste your instructions (from the setup page, or `PROMPT.md`) into the project's **Instructions** and save. The limit is 8,000 characters; the setup page counts for you.
4. New chat in the project: `council this: ...`

Commands: `quick council` · `full council` · `go deeper` · `ask <name> ...` · `who's on my council` · `add <name>` / `drop <name>`.

## How the council keeps mentors honest

- A mentor speaks only from their own file, cites the video and timestamp, and quotes only words that are in the file.
- Every mentor take is tagged GROUNDED, PARTLY GROUNDED or LOW GROUNDING. Confidence can't be High when most takes are weakly grounded.
- The verdict is a rule, not a vibe: each option's score is the median seat rating, capped at 2 (WAIT) if any seat flags RUIN.

## Fine print

Mentors are simulations built from public videos, not the real people, and they don't endorse anything. Mentor files hold transcripts of other people's videos: keep them for your own use and don't republish them. One AI plays every seat, so treat this as a sharper way to think. You make the call, and for health, legal or big money decisions, check with a professional.

## Development

```bash
python3 -m unittest discover tests      # tool tests
python3 tools/render_prompt.py          # rebuild PROMPT.md
python3 tools/render_prompt.py --skill  # rebuild council/SKILL.md
python3 page/build_page.py              # rebuild the setup page
```

MIT licence. Based on the "LLM Council" idea from Andrej Karpathy, adapted into a one-chat council with grounded mentors.
