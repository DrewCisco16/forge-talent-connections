# START HERE — Elimination Protocol Five

Everything you need, in order. Nothing here assumes you know Python.

---

## Step 1 — Get everything onto your Mac

There are **two routes**. Pick ONE. They produce the same thing in different
places, and doing both just leaves you with two copies to confuse yourself with.

### Route A — the zip (easiest, no Terminal needed)

If you have `EliminationProtocolFive.zip` in your Downloads:

1. Double-click the zip. You get a folder called `EliminationProtocolFive`.
2. Open that folder.
3. **Double-click `SETUP.command`.**

That script does everything: checks Python, builds the environment, installs
the libraries, creates your two editable files, and runs a demo to prove the
machinery works. Then it opens the folder and prints where everything is.

⚠️ The first time, macOS will say *"cannot be opened because it is from an
unidentified developer."* **Right-click `SETUP.command` → Open → Open.** Once
only. This is the step where people give up; it is not a problem with the file.

Your folder is then:
```
/Users/YOUR-NAME/Downloads/EliminationProtocolFive/
```

**Skip to Step 3.** Step 2 already ran inside the script.

### Route B — from GitHub (keeps up to date)

Better if you want to pull future changes with `git pull`. Open **Terminal**
(⌘+Space, type `Terminal`, Enter) and paste this whole block:

```bash
cd ~
git clone -b claude/adjudication-test-suite-w27c3h \
  https://github.com/DrewCisco16/forge-talent-connections.git
cd forge-talent-connections/adjudication
./SETUP.command
```

Your folder is then:
```
/Users/YOUR-NAME/forge-talent-connections/adjudication/
```

To open either folder in Finder, paste the matching line into Terminal:

```bash
open ~/Downloads/EliminationProtocolFive              # Route A
open ~/forge-talent-connections/adjudication          # Route B
```

**Everything below is inside whichever folder you chose.** Where this guide
says "the folder", it means that one.

## Step 2 — Check it works (skip if SETUP.command already ran)

`SETUP.command` does this for you. Only run it by hand if you set things up
some other way:

```bash
cd "the folder"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_adjudication.py --demo
```

✅ **You'll know it worked:** you see a report ending in
`SURVIVOR: c_true` and a `HOLES` section.

That was a pretend run with fake AI seats. It proves the machinery works
before you spend a cent.

---

## Step 3 — The two files YOU fill in

These are the only two files that need you. Both are already in the folder.

### 3a. `.env` — your five API keys

```bash
cd "the folder you chose in Step 1"
cp .env.example .env
open -e .env
```

That opens it in TextEdit. You'll see five blocks. Fill in the key and the
model ID for each. **Nothing else in the file needs changing.**

| Seat | Company | Model to use | Why |
|---|---|---|---|
| 1 | OpenAI | **GPT-5.6 Sol** | their flagship — your pick, and correct |
| 2 | Google | **the Pro tier — NOT Flash** | Flash is the fast/cheap tier; a weak seat contributes *misses* |
| 3 | Mistral | **Magistral Medium** | their *reasoning* model — thinks stepwise, which is the job |
| 4 | xAI | **Grok 4.3** | flagship, reasoning on by default |
| 5 | Anthropic | **Claude Opus 5** | reasoning flagship; reported id `claude-opus-5` |

⚠️ **The model ID is not the marketing name.** "Gemini Pro" is the name;
the API wants an exact code string from their model page. Copy it exactly.

⚠️ If a name above disagrees with what's on the vendor's site, **their site
is right.** These came from web search — the vendor doc sites were blocked
from the machine that built this.

### 3b. `profiles.json` — how to talk to each company

```bash
cp profiles.example.json profiles.json
open -e profiles.json
```

Each of the five blocks needs three things copied from that vendor's API
documentation, wherever it says `FILL-IN`:

- **`endpoint`** — the web address to send to
- **`body`** — how that company wants the request laid out
- **`text_path`** — where the answer sits in what comes back

Keys starting with `_` are just notes — the tool ignores them.

---

## Step 4 — Check your work (free, no internet, no cost)

```bash
.venv/bin/python run_adjudication.py --check-profiles profiles.json
```

✅ **Worked:** prints `PROFILES OK`
❌ **Not yet:** it lists **every** problem at once, so you only go round once.

This never contacts any company. It cannot cost you money.

---

## Step 5 — The real run

```bash
.venv/bin/python run_adjudication.py YOUR-FILE.txt \
  --profiles profiles.json \
  --candidates candidates.json \
  --audit run-001.jsonl
```

Every run tells you which key file it read:
`env: loaded /Users/.../adjudication/.env`

**Your first run is a measurement, not a verdict.** Its job is to tell you
whether your five AIs actually think differently. Treat its answer as
provisional until you've seen that number.

---

## 🛑 The safety rules — these have no exceptions

1. **Never paste a key into a chat window.** Not to me, not to ChatGPT, not
   to Gemini.
2. **Never send `.env` or `profiles.json` to anyone.** Those two hold your
   keys. Every *other* file is safe to share.
3. Both files are already blocked from being uploaded to GitHub — that's
   automatic, you don't have to do anything.

---

## Where the code is, for copy-pasting to Codex and Gemini

Ready-made bundles are generated into a `review/` folder:

```bash
cd "the folder you chose in Step 1"
python3 make_review_bundles.py
open review
```

That gives you four text files. **Paste `REVIEW-BRIEF.md` first**, then one
bundle:

| File | What's in it | Ask them |
|---|---|---|
| `bundle-1-math.txt` | the statistics | are the formulas and the scoring right? |
| `bundle-2-orchestrator.txt` | gates, blinding, passes | where does this fail open? |
| `bundle-3-io.txt` | network, settings, audit log | where can a key leak? |
| `bundle-4-tests.txt` | the tests | which test would still pass if you deleted what it checks? |

**Ask each AI separately. Never show one what the other said.** That's the
same rule this tool enforces on its own five seats, for the same reason: two
reviewers who've seen each other stop being two reviewers.

The bundles have been machine-checked to contain no keys. The generator
refuses to write one that does.

---

## Every file in the folder, and what it's for

**You edit these two:**
| File | What it is |
|---|---|
| `.env` | your five API keys and model IDs |
| `profiles.json` | how to reach each company |

**You read these:**
| File | What it is |
|---|---|
| `START-HERE.md` | this file |
| `CONNECTING.md` | longer setup guide + troubleshooting table |
| `Get-Your-5-AI-Keys.pdf` | tap-the-boxes walkthrough for getting keys |
| `REVIEW-BRIEF.md` | paste this to Codex/Gemini before any code |
| `SOP_v1.2.html` | the full operating manual |

**The program itself — you don't edit these:**
| File | What it does |
|---|---|
| `run_adjudication.py` | the command you run |
| `adjudication_orchestrator.py` | the five passes, the gates, the blinding |
| `seat_independence.py` | the statistics |
| `correctness_matrix.py` | turns a run into the eliminative-vs-collapse verdict |
| `seat_adapter.py` / `seat_profiles.py` | talking to the five companies |
| `audit_log.py` | tamper-evident record of every run |
| `validation_harness.py` | self-test with known planted defects |
| `test_suite.py` / `test_properties.py` | 503 tests |

---

## If something goes wrong

| It says | It means | Do this |
|---|---|---|
| `no .env found at ...` | wrong folder, or not created | `cp .env.example .env` in the adjudication folder |
| `credential missing` | a key line is still blank | fill it in, save the file |
| `profiles unusable` | settings problem | run `--check-profiles`, it lists them all |
| `still contains FILL-IN` | a placeholder is left | copy the real value from the vendor's docs |
| `no ProviderProfile for seat(s)` | key set, settings block missing | add that seat to `profiles.json` |
| `401` or `403` | wrong key, or wrong header | re-check that vendor's auth format |

---

## What's genuinely left

1. Your five keys and five model IDs → `.env`
2. Five endpoints and response paths → `profiles.json`
3. One live run, to measure whether your panel is real

Everything else is built, tested, and green.
