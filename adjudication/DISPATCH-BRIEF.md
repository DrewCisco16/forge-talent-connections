# BRIEF FOR CLAUDE DISPATCH — set up Adjudication Five on this Mac

**Paste this whole file to Claude Dispatch and say: "Do everything in this brief."**

You are being asked to do every setup step on this Mac **except** the five API
key values. The operator will paste those in himself at the end. Your job is to
leave him a folder where the *only* thing still blank is five key lines.

---

## 0. Non-negotiable rules — read these before you touch anything

1. **Never ask the operator to paste an API key to you.** Not in chat, not in a
   file you read back, not "just to check it." If he offers one, refuse and
   point him at the `.env` file.
2. **Never print, echo, `cat`, log, or repeat the contents of `.env` or
   `profiles.json` once keys are in them.** You may check *whether* a line is
   blank. You may not display what is on it.
3. **Never `git add`, commit, or push `.env` or `profiles.json`.** Both are in
   `.gitignore`. Confirm that before you finish.
4. **Never push to `main`.** The only branch you may push to is
   `claude/adjudication-test-suite-w27c3h`. If you have nothing to push, push
   nothing.
5. **Do not invent an endpoint, a model ID, a request body, or a response
   path.** Every one of those comes from that vendor's own current API
   reference page, which you fetch. If you cannot reach a vendor's docs, leave
   that value as `FILL-IN` and say so in your report. A guessed endpoint that
   is one version stale returns a successful `200` with nothing usable, and the
   tool records it as *a seat that had nothing to say* rather than *a seat that
   was never reached*. Those are opposite facts, and the second one silently
   corrupts the statistics this whole tool exists to produce.
6. **Nothing you do may cost money.** No step in this brief calls a vendor API.
   The verification step is offline by design.

---

## 1. Find or create the folder

Run this first and report what you find:

```bash
ls -d ~/Downloads/EliminationProtocolFive 2>/dev/null
ls -d ~/forge-talent-connections/adjudication 2>/dev/null
```

**Decision rule — pick exactly one folder and use it for everything after this:**

- If `~/Downloads/EliminationProtocolFive/.env` exists **and** any
  `ADJ_SEAT_*_API_KEY=` line in it is non-blank → that folder is canonical. The
  operator has already started filling it in; do not make him do it twice.
- Otherwise → the git clone is canonical, because it can receive future fixes
  with `git pull`. Create it if it does not exist:

```bash
cd ~
git clone -b claude/adjudication-test-suite-w27c3h \
  https://github.com/DrewCisco16/forge-talent-connections.git
cd forge-talent-connections/adjudication
```

If it already exists, update it instead:

```bash
cd ~/forge-talent-connections
git fetch origin claude/adjudication-test-suite-w27c3h
git checkout claude/adjudication-test-suite-w27c3h
git pull origin claude/adjudication-test-suite-w27c3h
cd adjudication
```

Then say plainly, once: *"Your folder is `<path>`. If there is another copy in
`<other path>`, ignore it — editing the wrong copy is the single most common
way this goes wrong."* Do not delete the other copy without being asked.

---

## 2. Build the environment

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

If `python3` is missing, tell him to install it from python.org and stop. Do
not install a package manager on his machine on your own initiative.

---

## 3. Prove the machinery works before anything is configured

```bash
.venv/bin/python run_adjudication.py --demo
```

**Pass condition:** the output contains `SURVIVOR: c_true` and a `HOLES`
section. This uses fake seats, touches no network, and costs nothing. If it
fails, stop and report the error verbatim — everything after this depends on it.

---

## 4. Create the two files the operator owns

```bash
[ -f .env ] || cp .env.example .env
[ -f profiles.json ] || cp profiles.example.json profiles.json
```

**The `[ -f ]` guard matters.** If either file already exists it may already
hold his keys. Never overwrite either one. Never `cp` over them.

---

## 5. Fill in the model IDs — you do this, not him

Open `.env`. There are five `ADJ_SEAT_N_MODEL=` lines. Fill in each one with
the **exact model ID string** from that vendor's current model page, which you
fetch now. The marketing name on the box is never the ID the API wants.

| Seat | Vendor | Which model to look up |
|---|---|---|
| 1 | OpenAI | their current flagship reasoning model |
| 2 | Google | the **Pro** tier — explicitly **not** Flash |
| 3 | Mistral | their **reasoning** model (the Magistral line), not the general Large model |
| 4 | xAI | their current flagship Grok |
| 5 | Anthropic | their current flagship Opus |

Seat 2 is worth a sentence: Flash is the fast and cheap tier. A weak seat does
not merely contribute less — it contributes *misses*, and a miss from a weak
seat is indistinguishable in the output from something the whole panel missed.
That is the failure this tool is built to detect, so do not seed it deliberately.

**Report each model ID you wrote and the URL you took it from.** If the vendor
has renamed or retired one of these, use what their page actually lists today
and say what you changed and why. Their page wins over this table.

**Leave all five `ADJ_SEAT_N_API_KEY=` lines exactly as they are — blank.**

---

## 6. Fill in `profiles.json` — you do this too

`profiles.json` has five blocks: `seat_1` through `seat_5`. Every value marked
`FILL-IN` must be replaced from that vendor's current API reference. For each
seat you need four things:

- **`endpoint`** — the full HTTPS URL for a single chat/completion request.
- **`auth_header`** and **`auth_template`** — the header name that carries the
  credential, and its format. `{key}` is where the credential is substituted;
  the template must contain `{key}` exactly once. Some vendors want
  `authorization` + `Bearer {key}`; others want their own header name with a
  bare `{key}`. Use what the vendor documents.
- **`extra_headers`** — any additional required header, e.g. an API version
  header. **If a vendor requires none, delete the `extra_headers` entry
  entirely** rather than leaving a `FILL-IN` inside it.
- **`body`** — the request shape that vendor expects. Keep these placeholders
  where they belong: `{{prompt}}`, `{{model}}`, `{{max_tokens}}`,
  `{{temperature}}`. A value that is *exactly* one placeholder takes that
  placeholder's native type, so `"{{max_tokens}}"` sends the number `4096`, not
  the string `"4096"`. `{{prompt}}` must appear somewhere in the body or the
  seat is never actually asked anything.
- **`text_path`** — the path through the parsed JSON response to the reply
  text. Strings are object keys, integers are list indices. Read the vendor's
  documented *response* example and walk it. If this path does not land on a
  string, the seat fails loudly — which is correct, and is why getting it right
  matters more than it looks.

Keys starting with `_` are comments; the tool ignores them. Leave them or
remove them, your choice.

**Say which vendor doc URL you used for each seat.** If one is unreachable,
leave that seat's values as `FILL-IN`, finish the other four, and list the one
you could not do. Do not fill it from memory to make the report look complete.

---

## 7. Verify — offline, free, and it lists every problem at once

```bash
.venv/bin/python run_adjudication.py --check-profiles profiles.json
```

**Pass condition:** it prints `PROFILES OK`.

If it does not, it prints **every** problem in one go — that is deliberate, so
you fix them in one pass rather than discovering them one at a time. Fix them
all and re-run until it is clean. This never contacts a vendor and cannot cost
anything.

Note that `--check-profiles` validates the *settings*, not the keys. It will
say `PROFILES OK` while the key lines are still blank. That is the expected
state when you hand the folder back.

---

## 8. Confirm the two secret files cannot escape

```bash
git status --short
git check-ignore -v .env profiles.json
```

**Pass condition:** `.env` and `profiles.json` do **not** appear in
`git status`, and `check-ignore` names the rule that is blocking each. If
either one shows up as trackable, stop and fix `.gitignore` before doing
anything else with git.

---

## 9. Commit only what is safe

If you changed anything that belongs in the repository — nothing in this brief
requires that — commit it to `claude/adjudication-test-suite-w27c3h` and push
with `git push -u origin claude/adjudication-test-suite-w27c3h`. Otherwise push
nothing. `.env` and `profiles.json` are never part of this.

---

## 10. Report back in exactly this shape

```
FOLDER:        <the one canonical absolute path>
OTHER COPY:    <path, or "none">
PYTHON:        <version>
DEMO:          PASS / FAIL
MODELS WRITTEN:
  seat_1 OpenAI     <id>   source: <url>
  seat_2 Google     <id>   source: <url>
  seat_3 Mistral    <id>   source: <url>
  seat_4 xAI        <id>   source: <url>
  seat_5 Anthropic  <id>   source: <url>
PROFILES:      <5 of 5 filled, or which seats are still FILL-IN and why>
CHECK:         PROFILES OK / the exact problems remaining
GITIGNORE:     .env and profiles.json confirmed ignored
STILL BLANK:   the five ADJ_SEAT_N_API_KEY lines  <-- the operator's only job
```

Then give him these three lines and nothing else to do:

```bash
cd <FOLDER>
open -e .env
```

*"Paste each key onto its own `ADJ_SEAT_N_API_KEY=` line, save with ⌘S, close
the window. Nothing else in that file needs touching. Don't paste a key to me,
to ChatGPT, or to Gemini — that file is the only place it goes."*

---

## What is deliberately NOT in this brief

- **Running a live panel.** The first real run costs money and is a
  *measurement*, not a verdict: its job is to tell him whether his five AIs
  actually think differently or merely agree. He runs that himself, once the
  keys are in, with a file he chooses.
- **Anything involving RED material.** Do not put case or claim text into any
  AI tool, including yourself.
