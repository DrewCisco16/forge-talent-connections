"""Reproduce the seat failure with a REAL full-size prompt.

diagnose-seats.py sends a 6-token prompt and every seat passed it. The live
run then lost a seat in four of five passes. The difference is prompt size and
generation length, so this sends the actual pass-1 prompt and reports whatever
comes back, verbatim.

One call per named seat. Prints the vendor's own error body.
"""
import json
import re
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
    # Bound once so every print below can scrub it out.
    key = seat.credential() or ""
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
        print("  non-JSON:", _safe(raw[:300].decode("utf-8", "replace"), key))
        continue
    if status >= 300:
        print("  VENDOR SAID:", _safe(json.dumps(payload)[:700], key))
        continue
    txt = prof.extract_text(payload)
    print(f"  text_path resolved: {'YES' if txt else 'NO'}  len={len(txt or '')}")
    u = payload.get("usage", {})
    print(f"  usage: {json.dumps(u)[:200]}")
    if not txt:
        print("  full response:", json.dumps(payload)[:800])
