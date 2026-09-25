# Handoff: 3 of 5 seats failed on run-001

**Contains no API keys.** Safe to paste anywhere.

## What this system is

`run_adjudication.py` sends the same blinded prompt to five different vendors' LLMs
("seats"), five times (five analysis passes), and measures whether the seats' errors
are correlated. The output that matters is **ρ (rho)** — the measured error
correlation. If the seats all fail the same way, the panel is a collapse, not five
independent reviewers. Candidates are eliminated by mechanical gates (arithmetic,
schema, etc.), not by vote.

Each seat is configured declaratively in `profiles.json`: an `endpoint`, an
`auth_header` + `auth_template`, an optional `extra_headers`, a `body` template with
`{{prompt}} {{model}} {{max_tokens}} {{temperature}}` placeholders, and a `text_path`
(a list walking the JSON response to the reply text). Keys live only in `.env`.

The adapter (`seat_adapter.py`) calls each seat with **`max_tokens=4096`,
`temperature=0.0`, `timeout=120s`** by default. It fails closed: any non-2xx, or a
`text_path` that doesn't resolve to a string, raises `SeatError` and the seat is
recorded as errored for that pass.

## What ran

```
.venv/bin/python run_adjudication.py calibration.txt \
  --profiles profiles.json --candidates candidates.json --audit run-001.jsonl
```

Artifact: a 131-byte note asserting "3 units + 1 unit = 5 units".
Candidates: `c_total_4` (correct) and `c_total_5` (the planted error).

## Result

The **answer was right** — `c_total_4` survived, `c_total_5` eliminated by the
arithmetic gate recomputing `3 + 1 = 4`. That gate is mechanical and needed no seats.

But **ρ was NOT MEASURABLE**, which was the whole point of the run:

```
coverage: 0 item(s) x 5 seat(s); 0 from gates; 24 excluded
          (pass had a seat error: p1, p2, p3, p4, p5)
NOT MEASURABLE: no claim in this run has mechanical ground truth:
          0 escalated without adjudication, 24 dropped from passes with a seat error
```

Every pass reported:

```
SEAT ERROR: seat_1, seat_2, seat_5
```

Failing **5 passes out of 5, identically**, means a deterministic config or
credential fault — not a rate limit or a network blip, which would fail some
passes and not others.

### Seats that worked

| Seat | Vendor | Model | Body shape |
|---|---|---|---|
| seat_3 | Mistral | `mistral-medium-latest` | `model, max_tokens, temperature, messages` |
| seat_4 | xAI | `grok-4.6` | `model, max_completion_tokens, temperature, messages` |

Both are plain OpenAI-shaped chat completions, reply text at
`choices[0].message.content`.

### Seats that failed

| Seat | Vendor | Model | Endpoint | Body sent |
|---|---|---|---|---|
| seat_1 | OpenAI | `gpt-5.6-sol` | `https://api.openai.com/v1/chat/completions` | `model, max_completion_tokens, messages` (no `temperature`) |
| seat_2 | Google | `gemini-3.1-pro-preview` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | `model, messages` only |
| seat_5 | Anthropic | `claude-opus-5` | `https://api.anthropic.com/v1/messages` | `model, max_tokens, temperature, messages` |

Auth: seats 1, 2 `Authorization: Bearer {key}`; seat 5 `x-api-key: {key}` plus
`anthropic-version: 2023-06-01`.
`text_path`: seats 1, 2 → `["choices",0,"message","content"]`; seat 5 → `["content",0,"text"]`.

---

## seat_5 — ROOT CAUSE CONFIRMED, ALREADY FIXED

Anthropic's thinking documentation
(`platform.claude.com/docs/en/build-with-claude/thinking`) states:

> On Claude Fable 5, Claude Mythos 5, Claude Mythos Preview, **Claude Opus 5**,
> Claude Opus 4.8, Claude Opus 4.7, and Claude Sonnet 5, non-default `temperature`,
> `top_p`, or `top_k` values return a **400 error on every request**, regardless of
> whether thinking is used.

The profile sent `temperature: 0.0` — a non-default value — to `claude-opus-5`.
That is a guaranteed 400 on every call, which matches the 5-of-5 failure exactly.

**Fix applied:** `temperature` removed from the `seat_5` body. It is now
`{model, max_tokens, messages}`. `--check-profiles` still returns `PROFILES OK`.

**Still open on seat_5:** the same doc says thinking tokens count toward `max_tokens`.
The adapter's cap is 4096 and Opus 5 has adaptive thinking on, so thinking and the
reply share that budget. This will not error, but it could truncate. There is no CLI
flag to raise the cap; it is `max_tokens: int = 4096` in `seat_adapter.py`.

---

## seat_1 and seat_2 — CAUSE UNKNOWN, NEED THE RESPONSE BODY

The report prints only seat IDs and discards the `SeatError` message
(`run_adjudication.py:471`), and the audit log does not record it either. So the
actual HTTP status and vendor message from run-001 are unrecoverable.

### seat_1 (OpenAI `gpt-5.6-sol`) — competing hypotheses

1. **Reasoning tokens exhaust the cap.** On reasoning models, thinking tokens count
   against `max_completion_tokens`. If reasoning consumes all 4096, `content` comes
   back empty, `text_path` fails, and the adapter raises `SeatError`. Would present
   as HTTP 200 with an empty/missing `content`.
   Possible fix: send `reasoning_effort` (Chat Completions form; `gpt-5.6-sol`
   documents levels `none, low, medium, high, xhigh, max`), or raise the cap.
2. **Wrong parameter.** `max_completion_tokens` was chosen because OpenAI documents
   that reasoning models take it rather than `max_tokens`, but this was never
   confirmed on the `gpt-5.6-sol` page specifically. Would present as HTTP 400.
3. **Credential/account problem.** Would present as HTTP 401/403. Note the stored key
   is 325 characters, which is longer than typical.

### seat_2 (Google `gemini-3.1-pro-preview`) — competing hypotheses

1. **Key format.** Google is migrating from Standard `AIza` keys to new "auth keys";
   their docs say the Gemini API will reject Standard keys from September 2026, and
   new AI Studio keys are issued as auth keys. Auth keys are widely reported to fail
   against the OpenAI-compatibility endpoint with
   `401 ACCESS_TOKEN_TYPE_UNSUPPORTED`. The stored key is 53 characters; an `AIza`
   key is 39.
2. **Model not available.** `gemini-3.1-pro-preview` is preview-tier and may not be
   enabled on this project. Would present as HTTP 404 or 400.
3. **Endpoint choice.** The OpenAI-compatibility endpoint was used deliberately
   because Gemini's native endpoint embeds the model ID in the URL
   (`.../models/MODEL:generateContent`), and `seat_profiles.py` rejects an endpoint
   containing a placeholder — so the native URL would hard-code one model while
   `.env` supplies another. If the compat layer is the problem, this constraint has
   to be solved another way.

### How to distinguish them

`diagnose-seats.py` is already written in the repo. One call per seat, ~6-token
prompt, 64-token cap, well under a cent:

```
.venv/bin/python diagnose-seats.py
```

It prints the HTTP status, the vendor's error body, the exact request body sent
(no credential), and whether `text_path` resolved. That single output decides
between every hypothesis above.

---

## Questions for whoever picks this up

1. For `gpt-5.6-sol` on `v1/chat/completions`: is the output cap `max_tokens` or
   `max_completion_tokens`? Is `temperature` accepted or rejected? Is
   `reasoning_effort` required, and does `"none"` meaningfully reduce token burn?
2. For Gemini auth keys (`AQ.` prefix): do they work against
   `/v1beta/openai/chat/completions`, or only the native endpoint? If only native,
   how should a model-in-URL endpoint be expressed in a config that forbids
   placeholders in `endpoint`?
3. Is dropping `temperature` from a seat acceptable epistemically? The tool wants
   `temperature: 0.0` for determinism; three of five seats may not accept it. A panel
   where seats run at different effective temperatures is still a valid panel, but
   ρ then measures something slightly different.

## Separately worth fixing

`run_adjudication.py:471` prints `SEAT ERROR: seat_1, seat_2, seat_5` and throws away
the exception message. Every one of these questions would have been answered by
run-001 if the message were printed. One-line change; would have saved this entire
round trip.
