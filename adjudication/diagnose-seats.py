"""Diagnostic: one tiny call per failing seat, to surface the vendor's error.

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
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from adjudication_orchestrator import PANEL_OF_FIVE_EXTERNAL, load_panel
from run_adjudication import load_env_file, load_profiles

SEATS = sys.argv[1:] or ["seat_1", "seat_2", "seat_5"]
PROMPT = "Reply with the single word: OK"

print("env:", load_env_file(None))
panel = {s.seat_id: s for s in load_panel(specs=PANEL_OF_FIVE_EXTERNAL)}
profiles = load_profiles("profiles.json")


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
    seat = panel[sid]
    prof = profiles[sid]

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
        print(f"  TRANSPORT FAILURE: {type(exc).__name__}: {exc}")
        continue

    print(f"HTTP {status}")
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001 - unparseable is a finding to show, not raise
        print("  non-JSON response:", raw[:300])
        continue

    if status >= 300:
        print("  VENDOR SAID:", json.dumps(payload)[:700])
        continue

    print("  top-level keys:", sorted(payload)[:10])
    got = prof.extract_text(payload)
    if got is None:
        print("  text_path resolved to None  <-- THE FAILURE IS HERE")
        print("  full response:", json.dumps(payload)[:900])
    else:
        print("  text_path resolved to:", repr(got)[:200])
