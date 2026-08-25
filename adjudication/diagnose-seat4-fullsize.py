"""Reproduce the seat failure with a REAL full-size prompt.

diagnose-seats.py sends a 6-token prompt and every seat passed it. The live
run then lost a seat in four of five passes. The difference is prompt size and
generation length, so this sends the actual pass-1 prompt and reports whatever
comes back, verbatim.

One call per named seat. Prints the vendor's own error body.
"""
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from adjudication_orchestrator import (
    DEFAULT_PASSES,
    PANEL_OF_FIVE_EXTERNAL,
    build_blinded_prompt,
    load_panel,
)
from run_adjudication import load_env_file, load_profiles

SEATS = sys.argv[1:] or ["seat_4"]
print("env:", load_env_file(None))

with open("runs/20260825-074902-cost-estimate-decision/artifact.txt") as fh:
    artifact = fh.read()
prompt = build_blinded_prompt(DEFAULT_PASSES[0], "seat_x", artifact).render()
print(f"prompt: {len(prompt)} chars (~{len(prompt)//4} tokens) -- the real pass-1 prompt\n")

panel = {s.seat_id: s for s in load_panel(specs=PANEL_OF_FIVE_EXTERNAL)}
profiles = load_profiles("profiles.json")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: PLR0913, PLR0917
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused",
                                     headers, fp)


for sid in SEATS:
    seat, prof = panel[sid], profiles[sid]
    cap = prof.max_tokens or 4096
    body = json.dumps(prof.build_body(seat.model, prompt, cap, 0.0)).encode()
    headers = {"content-type": "application/json",
               prof.auth_header: prof.auth_template.format(key=seat.credential() or ""),
               **dict(prof.extra_headers)}
    print("=" * 68)
    print(f"{sid}  {prof.name}  model={seat.model}  max_tokens={cap}")
    req = urllib.request.Request(prof.endpoint, data=body, headers=headers,
                                 method="POST")
    import time
    t0 = time.time()
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=900) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:  # noqa: BLE001
        print(f"  TRANSPORT FAILURE after {time.time()-t0:.1f}s: "
              f"{type(e).__name__}: {e}")
        continue
    print(f"  HTTP {status} after {time.time()-t0:.1f}s")
    try:
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001
        print("  non-JSON:", raw[:300])
        continue
    if status >= 300:
        print("  VENDOR SAID:", json.dumps(payload)[:700])
        continue
    txt = prof.extract_text(payload)
    print(f"  text_path resolved: {'YES' if txt else 'NO'}  len={len(txt or '')}")
    u = payload.get("usage", {})
    print(f"  usage: {json.dumps(u)[:200]}")
    if not txt:
        print("  full response:", json.dumps(payload)[:800])
