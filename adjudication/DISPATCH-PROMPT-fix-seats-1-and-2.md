# Dispatch prompt — diagnose why the OpenAI and Google API seats fail

Copy everything below the line into Claude Dispatch. It contains no secrets.

---

## Your task

Two API credentials are failing for a tool I run locally. I need you to open the
vendor consoles in a browser, find out **why**, and report back. Three other
vendors (Mistral, xAI, Anthropic) work fine with the same tool, so the tool's
code is not in question — this is an account, key, or billing problem on the
OpenAI and Google side.

Open browser windows/tabs for the consoles listed below. If you cannot open a
browser or are not signed in to an account, say so immediately and tell me what
to do rather than guessing.

## HARD RULES — these override anything else

1. **Never ask me for an API key, and never type, paste, echo, screenshot, or
   read aloud a full API key.** If a console displays a full key, do not
   reproduce it anywhere. Last-4 characters only, which every console shows by
   design.
2. **Never create, rotate, revoke, or delete an API key.** Tell me to do it. Keys
   are displayed once and I must be the one who copies them.
3. **Never enter payment details, card numbers, or billing information.** If a
   fix requires adding a payment method or upgrading a plan, STOP and tell me
   exactly which page and which button — I will do it myself.
4. **Never accept terms, change account settings, or click an irreversible
   control** (upgrade, purchase, confirm, delete) without asking me first.
5. **Do not make API calls to any vendor.** This is console inspection only.
   Nothing you do should cost money.
6. **Do not guess.** If a page does not show what I asked for, say "not visible"
   and describe what the page does show.

## Background: what is failing

A five-vendor evaluation panel sends the same prompt to five LLMs and measures
whether their errors are correlated. Each vendor is one "seat." Three seats work.
Two fail on every call, deterministically.

### Seat 1 — OpenAI, model `gpt-5.6-sol`

Request sent:

```
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer <key>
{"model": "gpt-5.6-sol", "max_completion_tokens": 64,
 "messages": [{"role": "user", "content": "..."}]}
```

Exact response:

```
HTTP 401
{"error": {"message": "Incorrect API key provided: sk-proj-****...****IvQA.
 You can find your API key at https://platform.openai.com/account/api-keys.",
 "type": "invalid_request_error", "code": "invalid_api_key"}, "status": 401}
```

Two facts worth checking:
- The key **ends in `IvQA`** (OpenAI echoed that in the error). The console shows
  the last few characters of each key — use that to identify which key this is.
- The stored key is **325 characters long**, which seems long for an OpenAI
  project key. Please find out what length a current `sk-proj-` key actually is.
  If the real one is shorter, my copy is probably truncated or padded and I need
  to re-copy it.

### Seat 2 — Google Gemini, model `gemini-3.1-pro-preview`

Request sent:

```
POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
Authorization: Bearer <key>
{"model": "gemini-3.1-pro-preview", "messages": [{"role": "user", "content": "..."}]}
```

Exact response:

```
HTTP 429
{"error": {"code": 429, "message": "You exceeded your current quota...
 * Quota exceeded for metric:
   generativelanguage.googleapis.com/generate_content_free_tier_requests,
   limit: 0, model: gemini-3.1-pro
 * Quota exceeded for metric:
   generativelanguage.googleapis.com/generate_content_free_tier_input_token_count,
   limit: 0, model: gemini-3.1-pro"}}
```

Note this is a **429, not a 401** — the key authenticated successfully. The
free-tier quota for Gemini 3.1 Pro appears to be **zero**, i.e. the Pro tier is
not available without billing. I need that confirmed, not assumed.

---

## Investigation 1 — OpenAI

Open these and report what each shows:

1. **https://platform.openai.com/api-keys**
   - List every key: its name, last-4 characters, created date, last-used date,
     project, and whether it is enabled or revoked.
   - **Is there a key ending in `IvQA`?** If yes: is it active? Which project is
     it in? Has it ever been used?
   - If no key ends in `IvQA`, that is the answer — my stored key was revoked or
     belongs to a deleted project, and I need to make a new one.
   - Note any per-key restrictions (some project keys are scoped to specific
     models or endpoints — if this key is restricted, say which restrictions).

2. **https://platform.openai.com/settings/organization/billing/overview**
   - Is a payment method on file?
   - What is the current credit balance / is it zero?
   - Is the account in good standing, or is there a past-due or suspended notice?
   - **Important:** a ChatGPT Plus or Pro subscription is billed separately and
     grants **no API credit**. Tell me explicitly whether this organization has
     API billing set up, separate from any ChatGPT subscription.

3. **https://platform.openai.com/settings/organization/limits**
   - Which usage tier is this organization on?
   - Is `gpt-5.6-sol` available at that tier, or does it require a higher one?

4. **Organization verification** — some OpenAI orgs must complete identity
   verification before the newest models unlock. Check whether this org shows a
   verification prompt or a "verify organization" banner anywhere in settings,
   and report it.

5. **Which organization/project am I signed in as?** If the account has more than
   one org or project, the key may belong to one and the billing to another.
   Report every org and project you can see.

## Investigation 2 — Google Gemini

Open these and report what each shows:

1. **https://aistudio.google.com/apikey**
   - List every API key: its last-4 characters, and critically **which Google
     Cloud project each key belongs to**.
   - Does the key show as a "Standard" key or one of the newer "auth" keys?
   - Report the exact project name/ID the key is attached to — the next steps all
     depend on that specific project, not on any other project in the account.

2. **https://console.cloud.google.com/billing** (for the project from step 1)
   - Is a billing account **linked to that specific project**? Having billing set
     up somewhere in the account is not the same as it being linked to this one.
   - Is the billing account active, or closed/suspended?

3. **https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com**
   - Is the **Generative Language API** enabled on that project?

4. **Quotas** — for that project, find the quota page for the Generative Language
   API and report the limits for `generate_content_free_tier_requests` and the
   paid-tier equivalent. I want to know whether the limit is 0 because there is
   no billing, or 0 for some other reason.

5. **Model availability** — find out whether `gemini-3.1-pro-preview` is available
   on the paid tier at all, or whether preview models require separate access
   (allowlist, waitlist, or a specific tier). Check Google's own current docs, not
   forum posts. If the exact model ID has changed or been superseded, tell me the
   current one.

## What I need back

For each of the two vendors, report in this shape:

```
VENDOR:
  ROOT CAUSE:        one sentence, based on what you actually saw
  EVIDENCE:          which page, what it showed
  MY FIX:            exact steps I must take myself (keys, payment, upgrades)
  YOUR FIX:          anything safe you can do without touching keys or payment
                     — ask me before doing it
  UNKNOWN:           anything you could not determine, and why
```

Then one line: **is `gpt-5.6-sol` reachable on my account at all, yes or no**, and
the same for **`gemini-3.1-pro-preview`**. If either answer is no, tell me the best
available substitute of comparable capability from that vendor — for Google it must
be a **Pro-tier** model, not Flash, because a weaker seat degrades the measurement
this tool exists to produce.

## After you report

Do not change anything. I will fix the keys and billing myself, then re-run the
tool's own offline check. If a fix is safe, reversible, and touches no credential
or payment method, propose it and wait for my go-ahead.
