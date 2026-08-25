# Connecting GitHub so Codex can see this repo

Run these yourself. Nothing here should be pasted to me or to any assistant —
a token or a private key in a chat window is a token you have to rotate.

---

## 0. What is true right now

```
identity     Andrew Francisco <afran295@fiu.edu>      already set
remote       https://github.com/DrewCisco16/forge-talent-connections.git
branch       claude/adjudication-test-suite-w27c3h
unpushed     14 commits
credentials  osxkeychain configured, nothing stored in it
gh CLI       not installed
SSH keys     none on this machine
```

**Cloud Codex reads GitHub, not your Mac.** Until you push, everything built in
this session is invisible to it. That is the whole reason to do this.

---

## 1. Pick how git authenticates

### Option A — SSH key (recommended)

No expiry, nothing to paste into a terminal, and the private half never leaves
the machine.

```bash
ssh-keygen -t ed25519 -C "andrew-macbook-air" -f ~/.ssh/id_ed25519
```

Press Return for the passphrase prompts, or set one — either works. Then:

```bash
eval "$(ssh-agent -s)" && ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

Copy the PUBLIC key. It is safe to share; that is what it is for:

```bash
pbcopy < ~/.ssh/id_ed25519.pub && echo "public key copied"
```

Paste it at **github.com/settings/ssh/new**, title it "Andrew MacBook Air",
key type Authentication. Then point the remote at SSH and test:

```bash
cd ~/forge-talent-connections && git remote set-url origin git@github.com:DrewCisco16/forge-talent-connections.git
```

```bash
ssh -T git@github.com
```

A reply reading `Hi DrewCisco16! You've successfully authenticated` is
success, even though it also says shell access is not provided.

### Option B — personal access token over HTTPS

Use this if SSH is blocked on your network. Create a **fine-grained** token at
**github.com/settings/personal-access-tokens/new**:

- Repository access: only `DrewCisco16/forge-talent-connections`
- Permissions: Contents **Read and write**, Metadata **Read-only**
- Expiration: 90 days

Then push once. Git will prompt for a username and password:

- Username: `DrewCisco16`
- Password: **paste the token**, not your GitHub password

`osxkeychain` is already configured, so it stores the token and will not ask
again. **Do not paste that token anywhere else** — not into a chat, not into a
file, not into a config you might commit.

---

## 2. Push

```bash
cd ~/forge-talent-connections && git push origin claude/adjudication-test-suite-w27c3h
```

That branch name is easy to mistype. Safer:

```bash
cd ~/forge-talent-connections && git push origin HEAD
```

Confirm it landed:

```bash
cd ~/forge-talent-connections && git log --oneline origin/claude/adjudication-test-suite-w27c3h..HEAD | wc -l
```

`0` means everything is on GitHub. Anything else means commits are still local.

**Never push to `main`.** `git push origin HEAD` pushes the branch you are on,
which is the safe form.

---

## 3. Check what actually went up

Two files must NOT be on GitHub. Confirm rather than assume:

```bash
cd ~/forge-talent-connections && git ls-files | grep -E "\.env$|profiles\.json$|approved-commands|canaries" || echo "clean: no secrets or local policy tracked"
```

Expect `clean`. If anything is listed, stop and say so before going further —
a key that reached a remote is a key to rotate, not to delete.

---

## 4. Connect Codex

### Cloud Codex (chatgpt.com)

1. Settings → Connectors → GitHub → Connect, and authorise as **DrewCisco16**.
2. Grant access to `DrewCisco16/forge-talent-connections` specifically rather
   than all repositories.
3. Point it at branch `claude/adjudication-test-suite-w27c3h`, **not** `main`.
   Everything from this work is on the branch; `main` does not have it.

### Codex CLI (local)

It uses the git config above, so once `ssh -T git@github.com` succeeds there is
nothing further to configure. Run it from the repo root, not from
`adjudication/`, so it can see the whole tree.

---

## 5. What to tell Codex once connected

```
Repo:    DrewCisco16/forge-talent-connections
Branch:  claude/adjudication-test-suite-w27c3h
Path:    adjudication/
Python:  3.13 in adjudication/.venv

Verify before reviewing:
  cd adjudication
  .venv/bin/ruff check .
  .venv/bin/mypy
  .venv/bin/bandit -q -r . -x ./.venv,./test_suite.py,./test_properties.py
  .venv/bin/python -m pytest test_suite.py test_properties.py

All four are currently clean: ruff passes, mypy strict passes on its eight
configured files, bandit reports zero issues, 503 tests pass.

Read adjudication/REVIEW-BRIEF.md first. It lists the design rules and the
things that look wrong but are deliberate, so a review does not spend itself
re-reporting intentional behaviour.

Two things worth its attention more than style:

1. mypy strict covers 8 of 21 modules -- the original author's list. The newer
   ones (quote_gate, citation_gate, night_loop, watcher, test_runner,
   recency_canary) are clean where mypy looks but are not in files=. Adding
   them is worth doing.

2. No new module has a dedicated test. All 503 tests are the original suite.
   quote_gate, citation_gate, test_runner, recency_canary, and watcher were
   verified by hand, not by anything that runs on every commit. That is the
   most valuable thing to add.
```

---

## 6. If you would rather not push yet

The paste-based path needs no GitHub at all:

```bash
cd ~/forge-talent-connections/adjudication && .venv/bin/python make_review_bundles.py && open review
```

Seven bundles, each with a specific attack to attempt. Paste `REVIEW-BRIEF.md`
first, then one bundle. **Ask each AI separately and never show one what
another said** -- the same rule the tool enforces on its own five seats, for
the same reason.

---

## A note on the commit email

Commits are attributed to `afran295@fiu.edu`. If that address is not verified
on the `DrewCisco16` GitHub account, they will show as unlinked rather than as
yours. Check at **github.com/settings/emails**, and if you would rather they
carry the business address:

```bash
cd ~/forge-talent-connections && git config user.email "andrew@forgetalentconnections.com"
```

That affects future commits only. The 14 already made keep the FIU address
unless they are rewritten, which is not worth doing on a branch you are about
to have reviewed.
