"""
seat_profiles.py
================
Turns the last code-shaped step into a config-shaped one.

ProviderProfile carries two CALLABLES -- build_body and extract_text -- so
connecting a vendor meant writing Python. This module builds both from a JSON
file instead, so the remaining work is transcription: copy the endpoint, the
request shape, and the response path out of that vendor's API reference into
profiles.json. No code changes to connect a panel.

WHY DECLARATIVE IS THE SAFER SHAPE HERE, not merely the more convenient one.
A hand-written build_body can silently omit the prompt and still return a
well-formed dict; the seat then answers about nothing and its reply reads like
a considered opinion. A template is checked before a token is spent: every
placeholder must be known, and the prompt must appear somewhere in the body or
the profile is refused. That check cannot be written against a callable.

STILL NOT SHIPPED: any vendor's endpoint, request shape, or response path.
profiles.example.json names every field and leaves each value blank. Written
from memory they are the same unverified assertion this system exists to
catch; transcribed from the vendor's own reference they are a technical
manual, admissible under SOP 8.3.

PLACEHOLDERS, and how substitution types them:

    {{prompt}}       the blinded prompt text        -> str
    {{model}}        the seat's model id            -> str
    {{max_tokens}}   the cap HttpSeat was built with-> int
    {{temperature}}  0.0 unless overridden          -> float

A value that is EXACTLY one placeholder becomes that placeholder's native
type, so {"max_tokens": "{{max_tokens}}"} sends the number 4096, not the
string "4096" -- a vendor that type-checks would reject the string, and one
that does not might silently truncate. A placeholder inside a longer string
interpolates as text, which is how a system-prompt prefix is written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from seat_adapter import ProviderProfile

PROMPT = "{{prompt}}"
MODEL = "{{model}}"
MAX_TOKENS = "{{max_tokens}}"
TEMPERATURE = "{{temperature}}"
PLACEHOLDERS = (PROMPT, MODEL, MAX_TOKENS, TEMPERATURE)

REQUIRED_FIELDS = ("endpoint", "auth_header", "auth_template", "body", "text_path")

# JSON has no comments, and an operator transcribing five vendors needs to
# leave notes somewhere. A key starting with "_" is a comment: ignored by
# validation and by loading. Without this, the README block in
# profiles.example.json validates as a malformed seat, and the first thing the
# checker ever tells an operator is a false alarm about their own notes.
COMMENT_PREFIX = "_"

# profiles.example.json marks every value the operator must supply. A config
# still carrying one is a half-filled template, and the checker reporting it
# OK is the exact fail-open this whole module exists to prevent -- caught when
# the freshly written example validated clean.
UNFILLED_MARKER = "FILL-IN"


class ProfileConfigError(ValueError):
    """A profile cannot be built. Raised before any network call."""


# ---------------------------------------------------------------------------
# substitution
# ---------------------------------------------------------------------------

def _substitute(value: Any, model: str, prompt: str,
                max_tokens: int, temperature: float) -> Any:
    """Recursively fill placeholders, typing whole-value ones natively."""
    if isinstance(value, str):
        if value == PROMPT:
            return prompt
        if value == MODEL:
            return model
        if value == MAX_TOKENS:
            return max_tokens
        if value == TEMPERATURE:
            return temperature
        out = value
        for token, replacement in (
            (PROMPT, prompt), (MODEL, model),
            (MAX_TOKENS, str(max_tokens)), (TEMPERATURE, str(temperature)),
        ):
            out = out.replace(token, replacement)
        return out
    if isinstance(value, dict):
        return {k: _substitute(v, model, prompt, max_tokens, temperature)
                for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, model, prompt, max_tokens, temperature) for v in value]
    return value


def _unknown_placeholders(value: Any) -> set[str]:
    """Every {{...}} token in the template that is not one we substitute.

    A typo like {{promt}} would otherwise be sent to the vendor verbatim, and
    the seat would answer about the literal string rather than the artifact.
    """
    found: set[str] = set()
    if isinstance(value, str):
        rest = value
        while "{{" in rest:
            start = rest.index("{{")
            end = rest.find("}}", start)
            if end == -1:
                break
            token = rest[start:end + 2]
            if token not in PLACEHOLDERS:
                found.add(token)
            rest = rest[end + 2:]
    elif isinstance(value, dict):
        for v in value.values():
            found |= _unknown_placeholders(v)
    elif isinstance(value, list):
        for v in value:
            found |= _unknown_placeholders(v)
    return found


def _contains(value: Any, token: str) -> bool:
    if isinstance(value, str):
        return token in value
    if isinstance(value, dict):
        return any(_contains(v, token) for v in value.values())
    if isinstance(value, list):
        return any(_contains(v, token) for v in value)
    return False


def _walk(payload: Any, path: Sequence[Any]) -> Any:
    """Follow a response path. Returns None the moment it does not fit.

    None is the fail-closed answer: HttpSeat raises SeatError on it rather
    than handing the runner an empty string, which would read as a seat that
    examined the artifact and found nothing.

    Three kinds of step:
        "key"            an object key
        0                a list index
        {"type": "text"} SELECT the first list element whose fields all match

    WHY THE SELECTOR EXISTS. A fixed index assumes the reply text sits at the
    same position every time. On a thinking model it does not: Claude Opus 5
    returns content [{"type": "thinking", ...}, {"type": "text", ...}] when it
    thinks and [{"type": "text", ...}] when it does not, so ["content", 0,
    "text"] reads the thinking block and resolves to None on exactly the
    requests where the model worked hardest. Hard-coding index 1 trades one
    silent failure for another. The selector says what is actually wanted --
    the text block -- and keeps working whether or not thinking is present.
    """
    cur = payload
    for step in path:
        if isinstance(step, Mapping):
            if not isinstance(cur, list):
                return None
            for item in cur:
                if isinstance(item, dict) and all(
                    item.get(k) == v for k, v in step.items()
                ):
                    cur = item
                    break
            else:
                return None
        elif isinstance(step, int):
            if not isinstance(cur, list) or not -len(cur) <= step < len(cur):
                return None
            cur = cur[step]
        else:
            if not isinstance(cur, dict) or step not in cur:
                return None
            cur = cur[step]
    return cur


# ---------------------------------------------------------------------------
# validation, offline
# ---------------------------------------------------------------------------

def validate_config(raw: Any) -> list[str]:
    """
    Every problem this file has, without spending a token.

    Returns a list of human-readable problems, empty when the config is
    usable. It reports ALL of them rather than the first: an operator
    transcribing five vendors should get five reports, not five round trips.
    """
    problems: list[str] = []
    if not isinstance(raw, dict):
        return [f"expected a JSON object of {{seat_id: profile}}, "
                f"got {type(raw).__name__}"]
    entries = {k: v for k, v in raw.items() if not k.startswith("_")}
    if not entries:
        return ["no profiles defined; the file has no seat entries"]

    for seat_id, cfg in entries.items():
        where = f"seat {seat_id!r}"
        if not isinstance(cfg, dict):
            problems.append(f"{where}: profile is {type(cfg).__name__}, not an object")
            continue

        for field_name in REQUIRED_FIELDS:
            if field_name not in cfg:
                problems.append(f"{where}: missing required field {field_name!r}")

        endpoint = cfg.get("endpoint")
        if isinstance(endpoint, str) and endpoint and not endpoint.startswith("https://"):
            problems.append(
                f"{where}: endpoint must be https, got {endpoint!r} -- a credential "
                f"must never cross a plaintext connection"
            )
        if isinstance(endpoint, str) and "{{" in endpoint:
            problems.append(
                f"{where}: endpoint still contains a placeholder; fill it in from "
                f"the vendor's API reference"
            )

        auth = cfg.get("auth_template")
        if isinstance(auth, str) and "{key}" not in auth:
            problems.append(
                f"{where}: auth_template must contain a {{key}} placeholder, "
                f"got {auth!r}"
            )

        body = cfg.get("body")
        if body is not None:
            if not isinstance(body, dict):
                problems.append(f"{where}: body must be a JSON object")
            else:
                unknown = _unknown_placeholders(body)
                if unknown:
                    problems.append(
                        f"{where}: unknown placeholder(s) {', '.join(sorted(unknown))}; "
                        f"valid ones are {', '.join(PLACEHOLDERS)}"
                    )
                if not _contains(body, PROMPT):
                    problems.append(
                        f"{where}: body contains no {PROMPT} -- the seat would be "
                        f"asked to judge an artifact it was never sent, and would "
                        f"answer anyway"
                    )

        path = cfg.get("text_path")
        if path is not None:
            if not isinstance(path, list) or not path:
                problems.append(
                    f"{where}: text_path must be a non-empty list of keys and indices"
                )
            else:
                for step in path:
                    if isinstance(step, dict):
                        if not step:
                            problems.append(
                                f"{where}: text_path selector {{}} is empty; it would "
                                f"match the first element of any list"
                            )
                        continue
                    if not isinstance(step, (str, int)) or isinstance(step, bool):
                        problems.append(
                            f"{where}: text_path step {step!r} must be a string key, "
                            f"an integer index, or a selector object such as "
                            f'{{"type": "text"}}'
                        )

        if _contains(cfg, UNFILLED_MARKER):
            problems.append(
                f"{where}: still contains {UNFILLED_MARKER!r} -- this profile is an "
                f"unfilled template. Copy the endpoint, request shape, and response "
                f"path from the vendor's API reference."
            )

        cap = cfg.get("max_tokens")
        if cap is not None and (not isinstance(cap, int) or isinstance(cap, bool)
                                or cap < 1):
            problems.append(
                f"{where}: max_tokens must be a positive integer when present, "
                f"got {cap!r}"
            )

        headers = cfg.get("extra_headers", {})
        if not isinstance(headers, dict):
            problems.append(f"{where}: extra_headers must be an object")
        else:
            for k, v in headers.items():
                if not isinstance(v, str):
                    problems.append(
                        f"{where}: extra_headers[{k!r}] must be a string, "
                        f"got {type(v).__name__}"
                    )
    return problems


# ---------------------------------------------------------------------------
# building
# ---------------------------------------------------------------------------

def profile_from_config(seat_id: str, cfg: Mapping[str, Any]) -> ProviderProfile:
    """One validated profile. Raises ProfileConfigError before any network use."""
    problems = validate_config({seat_id: cfg})
    if problems:
        raise ProfileConfigError("; ".join(problems))

    body_template = cfg["body"]
    text_path = list(cfg["text_path"])

    def build_body(model: str, prompt: str, max_tokens: int,
                   temperature: float) -> dict[str, Any]:
        filled = _substitute(body_template, model, prompt, max_tokens, temperature)
        if not isinstance(filled, dict):
            # validate_config guarantees body is an object, so this is
            # unreachable through the public API. It is a guard rather than a
            # cast because the alternative is posting a JSON array or scalar
            # to the vendor and reading the resulting 400 as a seat failure.
            raise ProfileConfigError(
                f"{seat_id}: body must fill to a JSON object, "
                f"got {type(filled).__name__}"
            )
        return filled

    def extract_text(payload: Mapping[str, Any]) -> str | None:
        found = _walk(payload, text_path)
        return found if isinstance(found, str) else None

    return ProviderProfile(
        name=str(cfg.get("name", seat_id)),
        endpoint=cfg["endpoint"],
        auth_header=cfg["auth_header"],
        auth_template=cfg["auth_template"],
        build_body=build_body,
        extract_text=extract_text,
        extra_headers=dict(cfg.get("extra_headers", {})),
        max_tokens=cfg.get("max_tokens"),
    )


def profiles_from_config(raw: Any) -> dict[str, ProviderProfile]:
    """Every profile, or none. Reports all problems in one error."""
    problems = validate_config(raw)
    if problems:
        raise ProfileConfigError(
            f"{len(problems)} problem(s) in the profile config:\n  - "
            + "\n  - ".join(problems)
        )
    return {seat_id: profile_from_config(seat_id, cfg)
            for seat_id, cfg in raw.items() if not seat_id.startswith("_")}


def load_profiles(path: str) -> dict[str, ProviderProfile]:
    with open(path, encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ProfileConfigError(f"{path} is not valid JSON: {exc}") from exc
    return profiles_from_config(raw)


def describe(raw: Any) -> str:
    """A short readable report for the operator's --check-profiles run."""
    problems = validate_config(raw)
    if problems:
        lines = [f"PROFILES NOT USABLE -- {len(problems)} problem(s):"]
        lines += [f"  - {p}" for p in problems]
        return "\n".join(lines)
    seats = sorted(k for k in raw if not k.startswith("_"))
    lines = [f"PROFILES OK -- {len(seats)} seat(s) configured:"]
    for seat_id in seats:
        cfg = raw[seat_id]
        lines.append(
            f"  {seat_id:12} {cfg.get('name', seat_id):16} {cfg['endpoint']}"
        )
        lines.append(
            f"  {'':12} response text at: "
            + " -> ".join(str(s) for s in cfg["text_path"])
        )
    lines.append("")
    lines.append("Validated OFFLINE. This confirms the profiles are well-formed and")
    lines.append("that each body carries the prompt. It does NOT confirm the endpoint")
    lines.append("is correct, current, or reachable -- only a live call does that.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("usage: python seat_profiles.py <profiles.json>", file=sys.stderr)
        raise SystemExit(2)
    with open(sys.argv[1], encoding="utf-8") as fh:
        cfg = json.load(fh)
    print(describe(cfg))
    raise SystemExit(0 if not validate_config(cfg) else 1)
