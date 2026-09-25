"""Diagnostic: one tiny call per failing seat, to surface the vendor's error.

IT SPENDS MONEY, SO IT COUNTS WHAT IT SPENDS. This called the transport
directly with no ledger and no ceiling, which made it the one paid path in the
tool with nothing bounding it -- reachable from the console's "ping all five"
action. The calls are tiny, but "tiny" is not a control: a misconfigured
endpoint, a retry loop, or a seat that returns a huge body costs whatever it
costs. Every call is now booked against a ledger with a small hard ceiling,
and the run stops if it is reached.

This is the project's own seat machinery (load_panel + profiles.json), run
once per seat with a ~6-token prompt and a 64-token cap, so it costs a
fraction of a cent rather than the 25 calls a full run makes.

It prints the HTTP status and the response body, because that is where each
vendor puts the message explaining what it rejected. It never prints request
headers, since those carry the credential.

Usage:  .venv/bin/python diagnose-seats.py            # seats 1, 2, 5
        .venv/bin/python diagnose-seats.py seat_2     # just one
"""
import json
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from adjudication_orchestrator import PANEL_OF_FIVE_EXTERNAL, load_panel
from run_adjudication import load_env_file, load_profiles


def _safe(text: str, key: str | None) -> str:
    """Never print a credential, whatever the vendor or the exception says.

    These scripts exist to be run against a LIVE panel and their output is
    pasted into chats and issue trackers. A vendor error body can echo the
    request, and urllib puts a malformed Authorization value straight into its
    exception text, so the raw string is the one thing that must not be
    printed unfiltered.
    """
    out = text or ""
    if key and len(key) >= 8:
        out = out.replace(key, "[redacted credential]")
    return re.sub(r"\b(sk|pk|gh[pousr]|xox[baprs])[-_][A-Za-z0-9_\-]{8,}\b",
                  "[redacted]", out)


SEATS = sys.argv[1:] or ["seat_1", "seat_2", "seat_5"]
PROMPT = "Reply with the single word: OK"

MAX_TOTAL = 0.05
"""Hard ceiling for the whole diagnostic, in dollars.

Five calls of about seventy tokens each cost a small fraction of a cent. This
is two orders of magnitude above that, which is enough headroom that an
honest run never reaches it and low enough that a misconfigured seat cannot
spend meaningfully before it stops.
"""

print("env:", load_env_file(None))
panel = {s.seat_id: s for s in load_panel(specs=PANEL_OF_FIVE_EXTERNAL)}
profiles = load_profiles("profiles.json")

ledger = None
per_call = 0.0
try:
    from cost_ledger import CeilingReached, CostLedger, rates_from_config
    with open("rates.json", encoding="utf-8") as _fh:
        _rates = rates_from_config(json.load(_fh))
    ledger = CostLedger(rates=_rates, per_run=MAX_TOTAL)
    # Every call is priced at its worst case up front, because the reply's
    # own usage block is exactly what a broken seat may not return.
    per_call = max(
        (r.cost(64, 64) for r in _rates.values()), default=0.0)
    print(f"ceiling: ${MAX_TOTAL:.2f} for the whole run "
          f"(about ${per_call:.6f} per call at the worst seat's price)")
except Exception as exc:  # noqa: BLE001
    # A diagnostic that cannot price itself must not spend at all: the reason
    # to run it is usually that something is already misconfigured.
    print(f"refusing to run: could not build a spend ledger ({exc}). "
          f"This makes real calls, and a paid path with nothing counting is "
          f"the one thing that must not exist here.")
    sys.exit(2)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse 3xx on a credentialed request.

    Same leak the main transport had: urllib follows redirects and carries
    the Authorization / x-api-key headers to the new origin, possibly over
    plaintext. These requests carry a credential, so they must not follow.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code,
            f"refusing a {code} redirect to {newurl!r} on a credentialed request",
            headers, fp,
        )


for sid in SEATS:
    if ledger is not None:
        try:
            ledger.check_before_call(sid, 64, 64)
        except CeilingReached as exc:
            print(f"\nstopping: {exc}")
            break
    seat = panel[sid]
    prof = profiles[sid]

    # Bound once so every print below can scrub it out.
    key = seat.credential() or ""
    sent = prof.build_body(seat.model, PROMPT, 64, 0.0)
    headers = {
        "content-type": "application/json",
        prof.auth_header: prof.auth_template.format(key=seat.credential() or ""),
        **dict(prof.extra_headers),
    }

    print("\n" + "=" * 68)
    print(f"{sid}  {prof.name}  model={seat.model}")
    print(f"POST {prof.endpoint}")
    print("request body:", json.dumps(prof.build_body(seat.model, "<prompt>", 64, 0.0)))

    req = urllib.request.Request(
        prof.endpoint, data=json.dumps(sent).encode("utf-8"),
        headers=headers, method="POST",
    )
    try:
        # Endpoint comes from profiles.json, which validate_config refuses
        # unless it is https. Reason off the nosec line by convention.
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=60) as resp:  # nosec B310
            status, raw = resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001 - fail-closed: a diagnostic that
        # dies on the first bad seat cannot diagnose the others, which is the
        # whole reason it exists.
        print(f"  TRANSPORT FAILURE: {type(exc).__name__}: "
              f"{_safe(str(exc), key)}")
        continue

    if ledger is not None:
        # Booked against the same ledger every other paid path uses, so a
        # misconfigured seat cannot run away here either.
        ledger.record(sid, None, None, estimated_dollars=per_call,
                      authorised=per_call)
    print(f"HTTP {status}")
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001 - unparseable is a finding to show, not raise
        print("  non-JSON response:",
              _safe(raw[:300].decode("utf-8", "replace"), key))
        continue

    if status >= 300:
        print("  VENDOR SAID:", _safe(json.dumps(payload)[:700], key))
        continue

    print("  top-level keys:", sorted(payload)[:10])
    got = prof.extract_text(payload)
    if got is None:
        print("  text_path resolved to None  <-- THE FAILURE IS HERE")
        print("  full response:", json.dumps(payload)[:900])
    else:
        print("  text_path resolved to:", repr(got)[:200])
