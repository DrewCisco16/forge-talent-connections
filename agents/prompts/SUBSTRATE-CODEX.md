# SUBSTRATE — OPENAI CODEX  ·  **FILL-IN REQUIRED**

**Status: UNVERIFIED. Do not build a load-bearing agent on this substrate until
this file is complete.**

## Why this file is empty

An attempt to retrieve OpenAI's Codex documentation during the session that built
this system returned:

```
{"error_type":"EGRESS_BLOCKED","domain":"developers.openai.com",
 "message":"Access to developers.openai.com is blocked by the network egress proxy."}
```

Rather than describe the product from recollection, the design routes around it
with an adapter. Fill this in from OpenAI's current documentation and the Codex
half of the system becomes usable. Until then it is deferred, not assumed.

**Specifically unresolved:** you asked about a **"GPT-5.6 Codex"** option. **I
could not verify that a model by that name exists** and I am not repeating it back
as fact. Confirm the actual current model identifiers at the source.

---

## The four properties the design actually depends on

Answer these four and the adapter is done. Everything else is detail.

```yaml
# 1. ISOLATION — does each task run in its own isolated environment?
isolation:            FILL-IN
isolation_docs_url:   FILL-IN
retrieved:            FILL-IN

# 2. NETWORK — can egress be restricted, and how?
network_policy_configurable: FILL-IN
default_network_posture:     FILL-IN
how_to_restrict:             FILL-IN

# 3. REPOSITORY SCOPE — how is repo access granted, and can it be scoped to one repo?
repo_access_mechanism:  FILL-IN
scopable_to_one_repo:   FILL-IN
write_access_default:   FILL-IN
can_it_push_to_main:    FILL-IN   # if yes, protect main — this is a one-way door

# 4. TRIGGERING — can a task be started on a schedule or by an event?
schedule_trigger:  FILL-IN   # if NO: invoke from a Claude Code routine or a
                             #        GitHub Action instead of abandoning the
                             #        second-vendor track
event_trigger:     FILL-IN
api_trigger:       FILL-IN
```

## Also confirm before any lane-restricted data touches it

```yaml
data_retention:        FILL-IN   # what is retained, for how long
training_on_input:     FILL-IN   # CRITICAL — determines whether an unfiled
                                 # invention disclosure may ever go near it
enterprise_terms:      FILL-IN
model_identifiers:     FILL-IN   # the actual current names
config_file_convention: FILL-IN  # what file, if any, configures per-repo behavior
```

## Where Codex earns its cost in this design

**BUILDER and REVIEWER only.** Two vendors implementing or reviewing the same
change is genuine independence, and independence is the scarce good in an agent
system. Everywhere else in the roster, a second vendor is a second thing to
maintain for no gain.

Two configurations worth trying once Gate 2 is stable:

| Configuration | What it buys |
|---|---|
| Codex builds → Claude reviews | Cross-vendor review. The reviewer shares no training or prompt lineage with the builder |
| Both build the same issue → you compare | Reveals where the specification was ambiguous. **Where two competent implementations diverge, the issue was underspecified** — and that is worth knowing |

**Do not run both vendors on everything.** That doubles cost and review load to
buy independence you only need where being wrong is expensive.
