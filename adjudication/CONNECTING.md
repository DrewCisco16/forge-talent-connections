# Connecting the panel

Everything else is built and tested. This is the only step left, and it is
transcription — no code changes.

## What you need

Four API keys, and each vendor's API reference open in a tab. Seat 5 is Claude
running in-process and needs no key.

## 1. Credentials

```
cd adjudication
cp .env.example .env
```

`.env` must sit **in the `adjudication/` folder**, right beside `.env.example`
— that is the only place the tool looks. Run
`python run_adjudication.py --env /some/other/path` to point somewhere else.

Every run prints which file it read (`env: loaded /path/to/.env`) so you never
have to guess whether your keys were picked up.

Fill in `ADJ_SEAT_1..4_API_KEY` and the five `ADJ_SEAT_*_MODEL` ids. `.env` is
gitignored. Never paste a key into a document, a screenshot, a chat window, or
source code.

`load_panel()` **fails closed** on a missing or blank credential. It will not
run a four-seat panel and call it five — seat count feeds effective seats, the
Chao1 estimate, and what the residual means, so a short panel misstates every
number downstream.

## 2. Profiles

```
cp profiles.example.json profiles.json
```

Fill every `FILL-IN` from that vendor's own API reference. Three fields decide
whether a seat works:

| Field | What it is | How it fails if wrong |
|---|---|---|
| `endpoint` | Full URL to POST to | A version-stale URL 404s, or worse, answers differently |
| `body` | The request shape | A body missing `{{prompt}}` still gets an answer — about nothing |
| `text_path` | Where the reply text sits in the response | Resolves to `None`, and the seat reads as having found nothing |

**Do not write these from memory or copy them from another project.** That is
the same unverified assertion this whole system exists to catch. The vendor's
API reference is a technical manual and admissible under SOP §8.3;
recollection is not.

### Placeholders

| Token | Becomes | Type |
|---|---|---|
| `{{prompt}}` | the blinded prompt | string |
| `{{model}}` | the seat's model id | string |
| `{{max_tokens}}` | the output cap | number |
| `{{temperature}}` | `0.0` unless overridden | number |

A value that is *exactly* one placeholder takes its native type, so
`"max_tokens": "{{max_tokens}}"` sends the number `4096`, not the string. A
placeholder inside a longer string interpolates as text, which is how you add a
system-prompt prefix.

### `text_path`

A list walking the parsed JSON response. Strings are object keys, integers are
list indices. For a response shaped
`{"choices": [{"message": {"content": "..."}}]}` the path is
`["choices", 0, "message", "content"]`.

Keys starting with `_` are comments — ignored by the checker and by loading.

### Start from run-001 rather than from scratch

A live five-vendor run already happened. `profiles.run001.json` in this
directory is the settings file reconstructed from it, and
`HANDOFF-run-001-failures.md` is what that run found.

```
cp profiles.run001.json profiles.json
```

It passes `--check-profiles` and the calibration preflight as shipped. What it
carries per seat:

| Seat | Vendor | run-001 |
|---|---|---|
| seat_1 | OpenAI | errored 5/5, cause unrecorded |
| seat_2 | Google | errored 5/5, cause unrecorded |
| seat_3 | Mistral | **answered** |
| seat_4 | xAI | **answered** |
| seat_5 | Anthropic | errored 5/5 on `temperature` — root-caused, fix applied here |

Everything in it is what that run actually sent, with one inference marked in
the file: the handoff records the Mistral and xAI hostnames and that both are
plain OpenAI-shaped chat completions, but not the URL path. Confirm both
against the vendor page; the vendor wins.

Seats 1 and 2 are the open question, and `diagnose-seats.py` settles them for
well under a cent — one call per seat, a six-token prompt, a 64-token cap. It
prints the HTTP status and the vendor's own error body, which is exactly what
run-001 discarded.

### A worked example: the Anthropic seat

One vendor's block, filled in, so you have something correct to pattern the
other four against. Paste it into whichever seat you give to Anthropic.

```json
{
  "name": "anthropic",
  "endpoint": "https://api.anthropic.com/v1/messages",
  "auth_header": "x-api-key",
  "auth_template": "{key}",
  "extra_headers": { "anthropic-version": "2023-06-01" },
  "body": {
    "model": "{{model}}",
    "max_tokens": "{{max_tokens}}",
    "messages": [{ "role": "user", "content": "{{prompt}}" }]
  },
  "text_path": ["content", 0, "text"]
}
```

Three things in it differ from the OpenAI-shaped default in
`profiles.example.json`, and each one fails in its own way if carried over:

- **`auth_template` is `{key}`, not `Bearer {key}`.** Anthropic authenticates
  on `x-api-key` with the bare key. A `Bearer ` prefix is a 401 on every call.
- **`anthropic-version` is required.** Without that header the request is
  rejected before the model sees it.
- **There is no `{{temperature}}`.** Current Claude models reject sampling
  parameters (`temperature`, `top_p`, `top_k`) with a 400. The preflight in §3
  refuses to start a run that would send one to an Anthropic endpoint, so this
  is caught before it costs anything — but only if you leave it out here.

`text_path` is `["content", 0, "text"]` because the reply is a list of content
blocks: `{"content": [{"type": "text", "text": "..."}], ...}`.

For your model id, Anthropic's current ids include `claude-opus-5`,
`claude-sonnet-5`, and `claude-haiku-4-5`. Copy the exact string from the
vendor's own model list; where it disagrees with this page, the vendor wins.

**This block is the only one written for you.** The other four vendors have to
come off their own API references, for the reason stated above — and because
the environment this repository is built in cannot reach vendor documentation
to verify them.

## 3. Check before you spend anything

```
python run_adjudication.py --check-profiles profiles.json
```

This validates **offline**. It confirms the file is well-formed, that every
placeholder is one the substituter knows, that no `FILL-IN` remains, that each
endpoint is `https`, and — the one that matters most — that **every body
actually carries the prompt**.

It reports *every* problem at once, not the first, so transcribing four vendors
costs one round trip rather than four.

It does **not** confirm the endpoint is correct, current, or reachable. Only a
live call does that.

## 4. Run

```
python run_adjudication.py ARTIFACT.txt \
    --profiles profiles.json \
    --candidates candidates.json \
    --audit run-001.jsonl
```

Exit code is `0` only when one candidate survives **and** no holes remain.

### Candidates

```json
[{"id": "c1",
  "content": "the answer this candidate asserts",
  "claims": [{"kind": "arithmetic",
              "text": "the total is 4",
              "warrant": "2 + 2 = 4"}]}]
```

A candidate's claims are what it stands on. Claim ids are content-addressed, so
a claim a seat proposes and a claim a candidate carries collide exactly when
they are the same proposition — which is what lets a failed gate eliminate the
candidate depending on it.

## 5. The first run is a calibration run

Run **five seats and all five passes** the first time. Its job is to produce ρ,
the measured error correlation. You cannot choose a seat count before you have
it, and no synthetic seat can substitute.

Then read SOP §6.7 and set `n` at the Kish knee. Every run after that is
cheaper, permanently.

## Two things that are not optional

**Seat 5 must be a separate session.** The orchestrator is code, not a model.
If the session running it is also seat 5, that seat can see gate verdicts, its
errors correlate with the adjudication itself, and the blinding is gone.

**Wire a real citation resolver before trusting any citation claim.** With none
configured, citation claims escalate to your queue and appear as a hole, which
is correct. The admissibility gate is *not* a substitute: it answers "is this
the right kind of source", never "does this source exist" — alone it accepts a
well-formed invented DOI. Route it conjoined with a resolver or not at all.

## When something fails

| Symptom | Cause | Fix |
|---|---|---|
| `credential missing` | Blank or absent env var | Fill `.env`; the panel will not run short |
| `profiles unusable` | Config problem | `--check-profiles` lists them all |
| `no ProviderProfile for seat(s)` | Key set, profile absent | Add that seat to `profiles.json` |
| Seat errors on every call | Endpoint, auth header, or auth template wrong | Re-read the vendor reference; check `auth_template` — some want `Bearer {key}`, some the raw key |
| Seat returns but the run says it errored | `text_path` does not resolve | Print one raw response and walk the path by hand |
| `401`/`403` | Bad key or wrong header | Not retried, deliberately — retrying an auth failure burns quota and hides the one thing to fix |
