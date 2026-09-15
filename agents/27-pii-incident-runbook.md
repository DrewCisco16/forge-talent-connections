# 27 — PII INCIDENT: THE RUNBOOK

**Incident `E-01`.** Commit `2a51e25` committed the device fleet context pack
verbatim to this **public** repository, publishing third-party personal data:
**8 phone numbers and 2 carrier/order identifiers**, belonging to people who
never consented to it. I did that. `5f12aba` redacted HEAD. **Redaction at HEAD
does not unpublish a blob** — it is still in the branch's history and in PR #12's
diff views.

This file exists because I spent two days recording the incident and asking
Andrew to decide, when what was needed was the fix prepared and ready to run.

---

## What is actually exposed, established rather than assumed

Every blob in every tree from the merge-base to `ca304ca` was scanned with the
repository's own guard (`scripts/redaction_guard.py`, used as a library, with the
allowlist applied). **310 unique blobs. 17 commits. One real leak.**

Two precisions from the `evidence-auditor` run: the scanned set is every blob in
every tree in the range, **not** only blobs this branch introduced (those number
206) — broader than first described, which is the safe direction. And the counts
are pinned to `ca304ca`; HEAD has advanced, so **re-run before relying on them.**

| Path | Blob | Findings | Verdict |
|---|---|---|---|
| `agents/context/device-fleet.md` | `740678cdfd30` | **8 × us-phone, 2 × carrier-or-account-number** | **REAL — this is the incident** |
| `AGENTS.md`, `agents/07`, `agents/18`, `agents/prompts/*` | 5 blobs | 1 × `cui-marking` each | False positive — policy text *naming* the markings, not marked material |
| `adjudication/*`, `failure-register.json`, `redaction_guard.py` | 10 blobs | allowlisted | Deliberate test specimens and the guard's own patterns |

`Repo-Verified`. **`main` is clean** — `2a51e25` exists only on
`claude/ai-agent-govcon-workflow-kg1wo9`; the merge-base with `origin/main` is
`0fbe277`, and the leak is entirely above it.

---

## ⚠ The rewrite is NECESSARY and NOT SUFFICIENT

**Do not read a completed force-push as remediation.** Three exposures exist and
a rewrite reaches exactly one of them.

```
1  BRANCH HISTORY          -> the rewrite fixes this.              AGENT + approval
2  GITHUB'S RETAINED COPY  -> unreachable objects stay fetchable
                              by their old SHA, and PR #12's diff
                              views can keep serving them.
                              ONLY GitHub Support purges this.     HUMAN
3  CLOUDFLARE PAGES        -> if the repo root is the site root
                              (FM-31, RPN 512), every immutable
                              per-deployment URL built between
                              2a51e25 and 5f12aba still serves the
                              unredacted file. A git rewrite does
                              nothing to a built deployment.       HUMAN
```

**Exposure 3 is the one most likely to be live on the open internet right now**,
and it is the one a history rewrite most tempts you to forget.

---

## Step 1 — rewrite the branch history  ·  *prepared, not run*

```bash
python3 scripts/purge_history.py .        # creates objects; moves NOTHING
```

### ✅ DONE 2026-09-15 — executed, postcondition verified, pushed

```
RAN          python3 scripts/purge_history.py .    against 4a555d3
REBUILT      20 commits, 4 trees rewritten
POSTCONDITION SCAN -- the check that had never run, now run:

   BEFORE   blob 740678cd  in  4 commits  10 findings   *** the leak ***
            blob 7509dc21  in 16 commits   0 findings
   AFTER    blob 7509dc21  in 20 commits   0 findings
            leaked blob present: FALSE
   RESULT   PASS -- the leak is gone from this branch's history

PUSHED       4a555d3...7fc19cf  (forced update, --force-with-lease)
BACKUP       backup/pre-purge-2026-09-15 -> 4a555d3, kept locally
TREE         cdedb4fa -> cdedb4fa, byte-identical: no file content changed
```

**The earlier version of this section claimed "verified" on the strength of the
head-tree match alone — a check that cannot fail, because HEAD was already
redacted. `evidence-auditor` caught that. The postcondition above is the real
check, and it has now actually run.**

`Repo-Verified` — the before/after scan, re-runnable from `scripts/redaction_guard.py`.completes, and asserts the replacement blob clean before writing.

It prints a new head SHA and stops. **Publishing it is a second, deliberate act:**

```bash
git branch backup/pre-purge-2026-09-15 HEAD     # keep the old history reachable
git reset --hard <NEW_HEAD_FROM_SCRIPT>
python3 scripts/redaction_guard.py               # expect: clean
python3 scripts/goal_ladder.py --gate            # expect: silent pass
git push --force-with-lease origin claude/ai-agent-govcon-workflow-kg1wo9
```

**Why I did not run these:** every one is blocked in this session by the
permission classifier as `[Git Destructive]` — including the read-only
verification and even creating the backup branch. That is the correct default.
**It needs Andrew's explicit go-ahead, or a Bash permission rule.**

### The alternative that needs no rewrite at all

**Squash-merge PR #12.** `main` gets one commit carrying the clean tree, the
branch is deleted, and no bad blob ever reaches `main`. It does not clear
exposures 2 or 3, but it is lower-risk than a force-push and reaches the same
place for `main`. **Merging is human-only.**

## Step 2 — GitHub Support  ·  *human, and the only route*

A force-push does not delete anything on GitHub's side. Unreachable objects stay
fetchable by SHA, and PR diff views can keep serving them. Ready to send:

> ## ⛔ DO NOT SEND UNTIL STEP 1 HAS ACTUALLY RUN
>
> The draft below states that the history has been rewritten. **As of this
> writing it has not been** — step 1 above is marked *prepared, not run*. Sending
> this first would be a false statement of completed action, to a third party, in
> a privacy incident. Step 3 tells you to reorder the steps; **this letter is the
> one thing that must not be reordered.**

```
To: GitHub Support -- https://support.github.com/request
Subject: Remove cached views and unreachable objects containing third-party
         personal data -- DrewCisco16/forge-talent-connections

Third-party personal data (phone numbers and account identifiers belonging to
people who did not consent to publication) was committed to this PUBLIC
repository in commit 2a51e25, in agents/context/device-fleet.md. It was redacted
at HEAD in 5f12aba, and the branch history has since been rewritten.
          ^^^^ EDIT THIS CLAUSE TO MATCH REALITY BEFORE SENDING ^^^^

Please permanently remove the unreachable objects and any cached pull-request
diff views that still serve the pre-rewrite blob, in particular for PR #12.

The affected blob is 740678cdfd30 at path agents/context/device-fleet.md.
```

## Step 3 — Cloudflare Pages  ·  *human, and the most urgent*

`FM-31` is the top-ranked mode in the register at RPN 512: the repository root is
the FORGE Talent Connections website. **If that inference holds, the unredacted
file has been served on the open web** from every immutable deployment built
between `2a51e25` and `5f12aba`.

```
1  test        open the branch preview URL + /agents/context/device-fleet.md
               (STATE.md decision 2). 404 -> this whole step is moot.
2  if it renders, go to the Pages dashboard -> Deployments
3  delete every deployment built between 2a51e25 and 5f12aba
4  then agents/26-pages-exposure-mitigations.md option 3, to stop it recurring
```

**Do step 3 before step 1 or 2 if you only have time for one.** A blob in git
history needs someone to go looking. A URL on your live company website does not.

## Step 4 — notification  ·  *Andrew's call alone, and possibly a legal one*

The data belongs to identifiable people. Whether they are told, and whether any
breach-notification duty attaches, is **not an agent decision and not a
judgement I am qualified to make.** `Professional verification required` —
counsel, not this file, and not me.

---

## What I got wrong, recorded so the register is honest

```
1  I published it.                Playbook p.25 already set the standard.
2  I described the exposure as
   "a public GitHub repo" for two
   days. It is very likely the
   live company website.          Found 2026-09-15, only because a deploy
                                  notification surfaced the URLs.
3  I kept asking Andrew to decide
   instead of preparing the fix.  The fix took under an hour once attempted.
```

**`redaction_guard.py` exists because of item 1** — it is a rung-1 gate, 35
self-tests, denial live-tested, and it has since blocked its own author more than
once. That is the one good thing to come out of this, and it does not undo it.
