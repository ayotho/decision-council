# Decision Council

A ChatGPT skill that runs your hard decisions past five advisors who think differently, makes them argue, then gives you one straight recommendation and a first step.

```
            YOUR DECISION
                 │
   ┌──────┬──────┼──────┬──────┐
   ▼      ▼      ▼      ▼      ▼
Contrarian  First    Expansionist  Outsider  Executor
 what      Principles  hidden       fresh     what do you
 breaks?   real goal?  upside?      eyes      do Monday?
   └──────┴──────┼──────┴──────┘
                 ▼
         CROSS-EXAMINATION
     (anonymous: who's strongest,
       where's the hole?)
                 ▼
            THE CHAIR
  agree · clash · recommendation ·
  what would flip it · first step
```

Based on Andrej Karpathy's "LLM Council" idea, simplified to run inside one chat.

## Use it for

- "Should I take the job offer or stay?"
- "Launch at $49 or $199?"
- "Go full-time on my side project now or in six months?"

Not for facts, writing or summaries. It's for choices where being wrong costs you.

## Set it up (pick one)

### Option 1: Paste-in (any plan, 1 minute)

1. Open [`PROMPT.md`](PROMPT.md) and copy everything below the line.
2. In ChatGPT, create a **Project** (sidebar > New project), call it "Council".
3. Open the project's settings, paste into **Instructions**, save.
4. Start any chat inside that project and type your decision.

No project? Paste it as the first message of a chat, then your decision.

### Option 2: Install as a skill

ChatGPT skills on the web are for Business, Enterprise, Edu and Healthcare workspaces. On Free, Go, Plus or Pro, use the ChatGPT desktop app or Codex. Menus move, so if these names differ, look for "Skills".

1. Download `council.zip` from the [latest release](../../releases/latest).
2. In ChatGPT open **Plugins** > **Skills** > **Create** > **Upload from your computer**, and pick the zip.
3. Use it by typing `@council` or saying "council this: ...".

The skill follows the open Agent Skills format (`council/SKILL.md`), so it also works in Codex and Claude.

## How to ask

> council this: I've been offered a marketing job at $72k. I currently freelance and make about $60k but it's up and down. I care most about stability for the next year and still having time for my own projects. I need to answer by Friday.

The more you give it (options, what matters, deadline), the better the verdict. If you leave things out it asks once, with its best guesses.

**Shortcuts:** `quick council` (short version) · `go deeper` (another round of arguing) · `ask the Contrarian about...` (one advisor only)

## The fine print

It's one AI playing five thinking styles, not five separate minds. It helps you see a decision from angles you'd skip. You still make the call, and for health, legal or big money decisions, check with a professional.

MIT licence.
