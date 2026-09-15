# 26 — PAGES EXPOSURE: THE OPTIONS, PREPARED AND NOT ACTIVATED

> ## ⛔ NOTHING IN THIS FILE IS ACTIVE
>
> **No option below has been applied.** Every one of them changes what a live
> website serves, and deployment is human-only in `AGENTS.md`: *do not purchase,
> publish, deploy, delete, modify permissions, merge, send, submit or make any
> external commitment without exact human approval.* This file is a menu with
> the work already done. **Andrew picks; the picking is the approval.**

**The finding it answers** (`STATE.md` decision 2, `FM-31`, RPN 512): the
repository root is the FORGE Talent Connections website, and there is no build
configuration in the repo — so the Pages output directory is very likely the repo
root, which would serve every `.md` file in this project at its repo path.
`Evidence-Based Inference`, not verified.

---

## ⚠ Read this before choosing: what NONE of these options fixes

```
IMMUTABLE PAST DEPLOYMENTS.  Every prior Pages deployment keeps its own
permanent URL and its own copy of the files as they were at that commit.
A change pushed today does not alter a deployment built in September.
```

**If the unredacted `device-fleet.md` was ever served, it is still served from
those URLs no matter which option below is chosen.** The only remedy for that is
deleting those deployments in the Cloudflare dashboard — human-only, and not
something any option here reaches. Do not let a fix applied going forward read as
an all-clear for what is already out.

---

## Option 0 — verify before changing anything  ·  *recommended first*

30 seconds, no risk, no deploy: the two-step test in `STATE.md` decision 2. **If
step 1 returns 404, `FM-31` closes and every option below is unnecessary.**
Changing a live site to fix a problem that may not exist is its own risk.

## Option 1 — `_headers` with `X-Robots-Tag: noindex`

Reduces **discovery**. Does **not** reduce access.

```
# proposed content -- NOT written to _headers
/agents/*
  X-Robots-Tag: noindex
/*.md
  X-Robots-Tag: noindex
```

**Be clear about what this buys:** it asks search engines not to index the paths.
Anyone with the URL still gets the file, and a crawler that ignores the header
still gets the file. **It is not privacy.** If the concern is "a competitor
googles this," it helps. If the concern is "this should not be publicly
readable," it does nothing.

`Assumption` — that Cloudflare Pages honours `_headers` with this syntax. Pages
documentation is egress-blocked from this session and I have not verified it.

## Option 2 — `_redirects` returning 404 for non-site paths

Blocks **access** at the edge, not just indexing.

```
# proposed content -- NOT written to _redirects
/agents/*   /404.html   404
/scripts/*  /404.html   404
```

`Assumption`, and a weaker one than Option 1 — I believe Pages `_redirects`
supports an explicit status code, but **I have not verified the syntax, the
wildcard behaviour, or whether a 404 target must exist**, and the docs are
blocked. **Do not apply this one without checking it against current Cloudflare
documentation**, or it may silently do nothing while appearing to be a fix — the
worst of both outcomes.

## Option 3 — move the site into its own directory  ·  *the structural fix*

Move `index.html`, `styles.css` and `assets/` into `site/`, and set the Pages
output directory to `site/`. Then **nothing outside `site/` is servable at all** —
not by oversight, but by construction. A new document added later is safe by
default, which is the property the other options lack.

```
repo work    move 3 paths, fix relative links in index.html    (agent can do)
dashboard    set output directory to site/                     (HUMAN ONLY)
```

**The two halves must land together.** Moving the files without changing the
setting takes the website down; changing the setting without moving the files
does the same. **Sequence: set the dashboard first, verify, then move the files.**

## Option 4 — split the repositories  ·  *the cleanest, and the most work*

The website and the agent system are different things with different audiences
and different disclosure rules; they are in one repository by history, not by
design. Move the agent system to a **private** repository and this class of
failure ends permanently — along with `FM-04` (unfiled invention disclosure
committed to a public repo) and the reason the redaction guard has to exist at
all.

`AGENTS.md` already points here: *"put disclosures in a PRIVATE repo first."*
That advice was written for the IP lane and applies to the whole project.

---

## Recommendation

```
1  Option 0 today.        30 seconds. It may close FM-31 outright.
2  If step 1 renders:     Option 3, in the stated sequence. It is the only
                          in-repo option that is safe by construction.
3  Separately, always:    the dashboard deployment list, for the immutable
                          past deployments. Nothing else reaches them.
4  When there is time:    Option 4. It removes the failure class.
```

**Options 1 and 2 are listed for completeness and are not recommended.** Option 1
does not restrict access, and Option 2 rests on a syntax I could not verify — a
mitigation that might not work, reported as done, is exactly the false-clean this
project's gates exist to prevent.

`Confidence: Medium` on the shape of the problem — the repo evidence is solid and
the inference is short. `Confidence: Low` on Cloudflare specifics in Options 1 and
2. `Unknown` throughout: the dashboard settings, which only Andrew can read.
