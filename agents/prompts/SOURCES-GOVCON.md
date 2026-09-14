# SOURCES — GOVCON  ·  **FILL-IN REQUIRED**

**Status: INCOMPLETE. SCOUT and CAPTURE must refuse to run while any value below
reads `FILL-IN`.**

Every value here comes from that provider's own published API documentation. Do
not write one from memory, from another project, or from a model's recollection.
This convention is copied deliberately from `adjudication/profiles.example.json`,
which states the reason (Repo-Verified):

> "a stale endpoint or a response path that shifted one version ago returns None
> on a successful 200, and the run records a seat that had nothing to say rather
> than a seat that was never asked."

The same failure here produces a night with no opportunities that looks exactly
like a night with no opportunities in it.

**Why this file is a stub and not filled in:** `open.gsa.gov` returned
`EGRESS_BLOCKED` from the session that built this system. The values were not
available to verify, and writing them from memory would have been the exact
error this file exists to prevent.

---

## Verification checklist — per source

```
[ ] Base URL read from the provider's current documentation, not from memory
[ ] Retrieval date recorded
[ ] Authentication: key required? where does it go — header or query?
[ ] Rate limits: requests per hour/day, and behavior on exceeding them
[ ] Required parameters, with exact formats
[ ] Date-range parameter format AND maximum span per request
[ ] Pagination shape
[ ] Response path to the fields SCOUT needs
[ ] One live call made and its response shape confirmed against the docs
[ ] Host added to the routine environment's Custom allowed-domains list
```

---

## SAM.gov — Get Opportunities

```yaml
base_url:        FILL-IN
docs_url:        FILL-IN
retrieved:       FILL-IN   # date you read the docs
api_key_required: FILL-IN  # yes/no; if yes, where does it go?
key_storage:     FILL-IN   # environment API credential — never a repo, never a doc
rate_limit:      FILL-IN
date_param:      FILL-IN   # exact parameter name(s)
date_format:     FILL-IN   # exact format
max_span:        FILL-IN   # maximum range per request
pagination:      FILL-IN
fields_needed:   [ solicitation_number, title, agency, naics, set_aside,
                   response_deadline, posted_date, notice_type, url ]
response_paths:  FILL-IN   # path to each field above
```

## SAM.gov — Entity Management

```yaml
base_url:        FILL-IN
docs_url:        FILL-IN
retrieved:       FILL-IN
sensitive_data_requires_separate_role: FILL-IN   # confirm before requesting it
purpose:         confirm registration status, socio-economic status, size standard
```

## FPDS — award history / incumbency

```yaml
base_url:        FILL-IN
docs_url:        FILL-IN
retrieved:       FILL-IN
response_format: FILL-IN
```

## USASpending — award values, subawards

```yaml
base_url:        FILL-IN
docs_url:        FILL-IN
retrieved:       FILL-IN
```

## Acquisition.gov — FAR / DFARS clause lookup

```yaml
base_url:        FILL-IN
docs_url:        FILL-IN
retrieved:       FILL-IN
```

## Agency forecasts

```yaml
target_agencies: FILL-IN   # Andrew must name these first. Unknown today
forecast_urls:   FILL-IN   # varies by agency; many are not APIs
```

---

## Andrew's own parameters — **SCOUT's gates are wrong without these**

```yaml
naics_codes:              FILL-IN
psc_codes:                FILL-IN
size_standard:            FILL-IN
socioeconomic_status:     FILL-IN   # confirm against the SAM registration, not memory
uei:                      FILL-IN
cage:                     FILL-IN
active_registration:      FILL-IN   # yes/no + expiry date
clearances_held:          FILL-IN   # personnel and facility, separately
citable_past_performance: FILL-IN   # contract, agency, value, period, POC
geographic_limits:        FILL-IN
bid_cost_threshold:       FILL-IN   # below this margin, gate 6 says NO
```

**Note on `socioeconomic_status`:** your fleet pack references SDVOSB GovCon work
at standing desk B (Stated). Whether any specific certification is currently held
and active is **Unknown to this system** and must come from the SAM registration.
Eligibility determinations are counsel's. **Professional verification required.**
