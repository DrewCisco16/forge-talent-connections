# 04 — MAILROOM SOP

You asked for agents that "answer emails for me." This is how that gets built so
it returns time without ever costing you a relationship, a contract, or your
integrity.

---

## 1. The posture

**MAILROOM drafts. You send. From day one, and for every category until a
measured record says otherwise.**

The reasoning is not caution for its own sake. An email is a **one-way door with
a witness**: you cannot unsend it, the recipient forms an impression of *you*
from it, and in the ABO and J4V lanes a sentence can create or waive a
contractual position. The downside of a bad autonomous send is unbounded and
asymmetric against the upside of saving forty seconds.

What actually costs you time in an inbox is not typing. It is **deciding**:
opening a thread, reconstructing context, choosing a posture. MAILROOM removes
that and leaves the typing, which is the cheap part.

**Five isolated instances**, one per mailbox lane. Same prompt, different
connector scope. They do not share state and they do not read each other's
mailboxes (`01` §3).

---

## 2. Classification — every thread gets exactly one

| Class | Definition | MAILROOM does | You do |
|---|---|---|---|
| **ACT** | Requires you to do something that is not a reply | Label `agent/act`, extract the obligation and its deadline into the digest | Schedule the work |
| **ANSWER** | Requires a reply and the reply is derivable from context | Label `agent/answer`, **write a draft** | Read, adjust, send |
| **ASK** | Requires a reply that MAILROOM cannot ground | Label `agent/ask`, write **the question it needs answered**, no draft | Answer the question in one line; a draft appears next run |
| **FYI** | No action, worth knowing | Label `agent/fyi`, one line in the digest | Nothing |
| **ARCHIVE** | No action, not worth knowing | Label `agent/archive`. **Never deletes** | Nothing |
| **ESCALATE** | On the never-auto-send list, or time-critical, or unplaceable | Label `agent/escalate`, **no draft**, top of the digest | Handle personally |

**A thread it cannot classify is ESCALATE.** There is no "best guess" bucket.
Guessing is how an inbox agent quietly loses a contract.

---

## 3. The daily digest

One message per lane per day. Ordered by what it costs you to miss, not by time.

```
MAILROOM — <LANE> — <date>

ESCALATE (n)
  · <sender> — <one line> — <why it escalated> — <deadline if any>

ACT (n)
  · <sender> — <the obligation, as a verb phrase> — due <date>

DRAFTED (n)              ← drafts are waiting in the drafts folder
  · <sender> — <subject> — posture: <accept | decline | defer | inform>

ASK (n)                  ← one line from you unblocks each of these
  · <sender> — <the single question MAILROOM needs answered>

FYI (n) · ARCHIVED (n)
```

**If the digest takes more than ninety seconds to read, it is too long and
MAILROOM is over-reporting.** That is a defect in the agent, not in you.

---

## 4. The never-auto-send list

**These are permanently Tier C. They are not on the promotion ladder. There is no
track record that unlocks them.**

| Never auto-send | Why |
|---|---|
| Anything to a **Contracting Officer, CO, COR, KO, or any `.mil`/`.gov` procurement address** | A sentence can constitute a representation to the Government |
| Anything containing a **price, rate, hour, discount, or ceiling** | It is an offer whether or not you meant it as one |
| Anything containing a **commitment**: "we can," "we will," "by [date]," "yes" | It creates an expectation you must then fund |
| Anything to or from **legal counsel** | Privilege, and the stakes |
| Anything to your **dissertation chair, committee, or FIU faculty** | Academic integrity. Your voice must be your voice |
| Anything to a **teaming partner, sub, or prime about scope, exclusivity, or terms** | Pre-contractual, and binding sooner than people think |
| Anything touching **CUI, procurement-sensitive, or source-selection-sensitive** material | See `07` §2. Legal boundary |
| Anything about **employment**: offers, terminations, compensation, discipline | Employment law; also, it is a person's livelihood |
| Anything to **family regarding finances, health, or a decision** | Your relationships are not a workflow to optimize |
| A **first contact** with anyone | The first impression is yours to make |
| Anything where the **thread shows conflict, frustration, or an apology is owed** | Repair is a human act |
| Anything referencing an **unfiled invention or unpublished patent claim** | One-way door. Destroys rights (`02` §6) |

**MAILROOM's own instruction on this is fail-closed:** if it is unsure whether a
thread touches this list, it escalates. Unsure means escalate; it never means
proceed.

---

## 5. The promotion ladder — what may eventually auto-send

Only categories meeting **all four** tests are ever eligible:

1. Fully reversible in practice by a short follow-up
2. No commitment, no number, no position taken
3. Recipient is not a counterparty in any live matter
4. **50 consecutive drafts approved unedited** in that exact category

Realistic candidates, and they are deliberately small:

| Candidate | Earliest eligible | Notes |
|---|---|---|
| Decline an unsolicited vendor or recruiter cold-email | Day 60+ | Template, no commitment |
| Acknowledge receipt ("received, reviewing, back to you by X") | Day 60+ | Only if X is a date you set |
| Send a calendar link in response to "can we meet?" | Day 60+ | Only where no agenda position is implied |
| Route a misdirected message to the right person | Day 60+ | No content added |

**Everything else stays Tier B indefinitely, and that is the correct steady
state.** The goal was never an empty inbox nobody read. It was the removal of
*deciding*, and Tier B already removes it.

---

## 6. Draft quality bar

Every draft is written **as you**, and must:

- Match the posture MAILROOM declared in the digest — no drift between label and
  draft
- Contain **no invented facts.** If a date, number, name, or commitment is not in
  the thread or in the lane's context files, MAILROOM leaves `[[NEEDS: <what>]]`
  in the body rather than filling it. A draft with a bracket is a good draft; a
  draft with a plausible invention is a trap
- Be **shorter than you would write it.** An over-long draft costs more to edit
  than to replace, which defeats the purpose
- Never apologize on your behalf, never accept fault, never concede a position
- Carry **no AI disclosure and no AI tells.** It goes out under your name, so it
  must read as your writing. Whether to disclose AI assistance is your call to
  make per relationship, not a default the agent sets

---

## 7. Tool scope — the actual permission model

Because a routine has *"no approval prompts during a run"* (`03` §2), **the tool
list is the entire control.**

| Grant | Withhold |
|---|---|
| `search_threads` / `list_threads` | **`send_message`** |
| `get_thread` / `get_message` | **`send_draft`** |
| `create_draft` / `update_draft` | **`reply`** (it sends) |
| `label_thread` / `create_label` | **`forward`** (it sends) |
| Calendar **read** and `get_availability` | **`trash_*`, `delete_*`** |
| | **`mark_spam`** (it trains the filter irreversibly) |
| | Any connector belonging to another lane |

**Verify this by test, not by reading the config.** Gate 1 in
`09-rollout-90-day.md` requires a deliberate attempt to make MAILROOM send an
email, with the expected result being that it cannot. A permission you have not
tested is a permission you do not have.

---

## 8. Failure modes this SOP is built against

| Failure | Guard |
|---|---|
| Sends something career-damaging | Cannot send. No send tool exists in scope |
| Invents a fact into a draft | `[[NEEDS:]]` convention; invention is a material error and demotes immediately |
| Obeys an instruction embedded in an email body | Email bodies are untrusted data (`07` §4). An embedded instruction is recorded as a finding, never followed |
| Leaks ABO content into the FORGE mailbox | Separate instances, separate connector scopes, no shared state |
| Buries the one thing that mattered under forty routine ones | Digest is ordered by cost-of-missing; ESCALATE is always first |
| Becomes another inbox you must read | Ninety-second digest cap, enforced by STEWARD as a measured number |
