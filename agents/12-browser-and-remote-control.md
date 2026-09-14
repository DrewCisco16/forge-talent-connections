# 12 — BROWSER AND REMOTE CONTROL

How the loops actually touch the world: Claude driving local Chrome, and ChatGPT
running remotely in its own cloud browser.

**All facts Docs-Verified from vendor sources, retrieved 2026-09-14.**

---

## 1. Claude Code driving your local Chrome

**Source:** `code.claude.com/docs/en/chrome` and `claude.com/claude-in-chrome`.

### How it works

> "Claude Code integrates with the Claude in Chrome browser extension to give you
> browser automation capabilities from the CLI."

> "Claude opens new tabs for browser tasks and **shares your browser's login
> state, so it can access any site you're already signed into.** Browser actions
> run in a visible Chrome window in real time. When Claude encounters a login page
> or CAPTCHA, it pauses and asks you to handle it manually."

> "The extension collects the tabs Claude opens into a Chrome tab group tied to
> your session."

Claude in Chrome is **generally available on every paid Claude plan**, supports
multi-tab work via a designated tab group, and can now *"take actions
autonomously in the browser, instead of needing approval for every one,"* with
*"a safety classifier [that] validates each action before it's performed."*

### Setup

```bash
claude --chrome          # start with Chrome integration
/chrome                  # status, permissions, reconnect, choose browser
```

`/chrome` → "Enabled by default" removes the flag. **Note the documented
trade-off:** *"Enabling Chrome by default in the CLI increases context usage since
browser tools are always loaded."*

### Requirements — four of them, and each one can stop you

| Requirement | Detail |
|---|---|
| Chromium browser | Chrome, Edge, Brave, Arc, Vivaldi, Opera |
| Extension | Claude in Chrome **v1.0.36 or higher** |
| Plan | **A direct Anthropic plan** (Pro, Max, Team, Enterprise). Not available through Bedrock, Google Cloud Agent Platform, or Microsoft Foundry |
| Auth | **Must sign in with `/login`.** *"If you authenticate with an API key or a long-lived token... Claude Code keeps Chrome integration off, even when you pass `--chrome`"* |

### Four constraints that shape the loop design

**1. WSL cannot do this.** *"Chrome integration isn't supported in Windows
Subsystem for Linux (WSL)."* Your HP Envy's WSL2 Ubuntu is excellent for bash-heavy
loop work and **cannot drive Chrome**. Run browser loops from Windows-side Claude
Code on that machine.

**2. It is interactive and local — a cloud routine cannot drive your Chrome.**
This is the real architectural consequence and it cuts against `01` §6. A
browser-driving loop needs: that machine awake, Chrome running, a signed-in
session live. **Browser loops are local and machine-awake. API loops are cloud and
laptop-closed.** Choose per workload; do not assume one substrate does both.

**3. The service worker goes idle on long runs.** *"The Chrome extension's service
worker can go idle during extended sessions, which breaks the connection."* Fix is
`/chrome` → "Reconnect extension". **An overnight browser loop needs a
reconnect-and-resume step, or it dies quietly at 2am and shows you nothing.**

**4. Windows named-pipe conflicts.** *"if another process is using the same named
pipe, restart Claude Code. Close any other Claude Code sessions that might be
using Chrome."* Relevant directly: **do not run two browser loops on one Windows
machine.** One lane per machine is not only a compliance choice, it is an
operational one.

---

## 2. ChatGPT running remotely

**Source:** OpenAI Help Center and OpenAI's own announcements, reached via search.
`developers.openai.com` remains blocked from this session, so this section is
**thinner and more cautious than the Claude section by design.**

What the vendor's own material states:

- ChatGPT agent *"uses screenshots of its virtual browser window to 'see' and
  interact with web pages"* and runs in a **cloud virtual machine**, not your
  local browser.
- It *"requests permission before taking actions of consequence,"* and you can
  *"interrupt, take over the browser, or stop tasks at any point."*
- On login: *"ChatGPT agent will pause and prompt you to take control of the
  virtual browser. While you control the browser, screenshots are not captured."*

**Inference, and it is the useful one:** because ChatGPT agent browses in **its
own remote environment** while Claude drives **your local Chrome with your logged-in
sessions**, the two have fundamentally different exposure profiles. That is not a
nuisance — **use it as an architectural asset:**

| Surface | Sees | Therefore use it for |
|---|---|---|
| **ChatGPT, remote** | Only what it can reach from its own cloud VM. **Not your logged-in sessions** | Public-web research: solicitations, literature discovery, market and competitive scanning |
| **Claude, local Chrome** | Your authenticated sessions | Work that genuinely requires your logins — and **only** in a locked-down profile (§3) |

**Unverified / confirm yourself before relying on it:** current model names,
whether a local-browser mode has shipped (a "use cloud browser" toggle was
reported as a *leak*, which is not a fact), data retention, and whether inputs may
be used for training. That last one gates whether any lane-restricted material may
go near it at all. → `10-open-questions.md` A5.

---

## 3. The risk you have not priced yet — read this before enabling anything

The single most consequential sentence in this entire document set:

> **"shares your browser's login state, so it can access any site you're already
> signed into."**

That is the feature working correctly. It is also the whole risk.

**If you enable Claude in Chrome on your everyday Chrome profile, a browser agent
has reach into every session that profile holds** — your banking, your brokerage,
your SAM.gov and contract systems, every mailbox, your FIU portal, your family's
accounts. All four lanes at once, through one profile. **That collapses every
boundary in `07` §5 in a single step.**

Combine it with `07` §4: a web page or an email body is untrusted content written
by someone else. An agent with browser control that encounters a crafted page is
operating with your session cookies in hand. The safety classifier is real and
helps; **it is not a substitute for not being logged in.**

### The rule: a dedicated Chrome profile per lane, per machine

**Non-negotiable, and it takes fifteen minutes to set up.**

| Lane | Machine | Chrome profile holds | Never logged into |
|---|---|---|---|
| **DBA** | HP Envy 17 (Windows side) | FIU library, scholarly indexes, Crossref/PubMed | Banking · brokerage · mail · SAM.gov · contract systems |
| **FORGE** | ASUS ProArt 16 | GitHub, the product's own staging environment | Banking · brokerage · personal mail · anything ABO |
| **ABO** | Surface Pro 8 | **Only what counsel permits.** Presume nothing until A1 is answered | Banking · brokerage · personal · FORGE · J4V |
| **HOME** | MacBook Air 15 M4 | **Nothing. Browser control OFF for this lane** | Everything |

**Four hard rules:**

1. **Never enable browser control on a profile logged into a bank, brokerage,
   payment, or payroll system.** Money movement is a one-way door (`07` §6) and no
   safety classifier is your last line of defense on it.
2. **Never enable browser control on your everyday personal profile.** Create a
   new profile for the lane, sign it into only what the loop needs, and use only
   that one.
3. **Site permissions are inherited from the extension** — Docs-Verified:
   *"Manage permissions in the Chrome extension settings to control which sites
   Claude can browse, click, and type on."* **Set an allowlist there. Do not rely
   on the agent's prompt to remember the boundary.**
4. **The GovCon lane gets browser control only after counsel answers A1.** A
   browser agent inside a profile authenticated to Government systems is a much
   larger question than an agent reading a public notice.

### Recording and screenshots

Docs-Verified: *"The recording captures everything visible in the browser,
including account details on logged-in pages, so review it before sharing it
outside your team."* GIFs and screenshots from a loop are artifacts that can leak
a session. Treat them as sensitive by default and keep them out of any public
repository.

---

## 4. The dispatch pattern — how a loop actually drives a browser

You described "Claude dispatch" controlling Chrome windows and tabs. Here is the
shape, using only verified mechanics.

```
┌─────────────────────────────────────────────────────────────┐
│  LANE MACHINE  (awake, Chrome running, claude --chrome)      │
│                                                               │
│   Claude Code session  ── the DISPATCHER                      │
│     │                                                         │
│     │  reads loops/<lane>/program.md                          │
│     │  proposes a change                                      │
│     │                                                         │
│     ├──▶ Chrome tab group (session-scoped, per docs)          │
│     │      tab 1 · source A        tab 3 · source C           │
│     │      tab 2 · source B        tab 4 · scratch            │
│     │                                                         │
│     ├──▶ subagents in isolated context windows                │
│     │      (adversarial-reviewer, citation-verifier, ...)     │
│     │                                                         │
│     └──▶ METRIC SCRIPT  ── code, no model judgment            │
│               │                                               │
│               ├── improved → git commit                       │
│               └── not     → git reset --hard                  │
└─────────────────────────────────────────────────────────────┘
           │
           └──▶ ChatGPT agent, remote cloud browser, public-web
                research only, no access to local sessions
```

**Three things this pattern gets right:**

1. **The dispatcher never scores.** Scoring is the metric script. This is G1 of the
   Measurability Gate and it is what makes the run unattendable.
2. **Tabs are scoped to a session tab group**, per the extension's documented
   behavior — not scattered across your working browser.
3. **Verification runs in an isolated context window** (`code.claude.com/docs/en/sub-agents`:
   *"Each subagent starts with a fresh, isolated context window"*), so the checker
   is not anchored on the proposer's reasoning.

---

## 5. Terms of service — check this yourself, once

Driving another vendor's **consumer chat UI** through browser automation is a
different act from calling that vendor's **API**, and their terms may treat it
differently. I do not have verified current terms for every vendor you might put
in a window, so I am not going to tell you it is fine.

**Prefer, in this order:**

1. **Official API** — your `adjudication/` engine already does this, which is why
   it is the soundest thing you own.
2. **Official browser-control product** — Claude in Chrome, ChatGPT agent. Using a
   vendor's own supported agent feature is squarely within the intended use.
3. **Scripted UI automation of a chat window** — **check that vendor's terms
   first.** Your Night Agent skill drives multiple chat windows; that is an
   established practice of yours, and it is worth a one-time read of each
   vendor's terms rather than an assumption.

**Professional verification required** if any of it touches contract work.

---

## 6. Setup order

```
1. Create the per-lane Chrome profile. Sign it into ONLY the lane's sources.
2. Install Claude in Chrome (v1.0.36+) in THAT profile only.
3. Set the extension's site permissions to an allowlist.
4. claude --chrome  →  /chrome  →  confirm "Status: Enabled"
5. Test the boundary: ask it to open a site NOT on the allowlist. Confirm refusal.
6. Test the reconnect: leave it idle, then /chrome → "Reconnect extension".
7. Only then point a loop at it.
```

**Step 5 is the one people skip.** A permission you have not tested is a
permission you do not have (`07` §1).
