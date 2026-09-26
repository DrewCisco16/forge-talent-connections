"""The only writer of the run folder (SCHEMA files; DISPATCH 6).

Write-once for every file except status.json; append-only jsonl records; every write is
logged with its sha256 so na_check.py LOG-ALL and WO-1 hold. Bytes are UTF-8 with \\n
newlines on every platform so the logged hash equals the file on disk.
"""
import hashlib
import json
import os
import re
import time


class WriteOnceViolation(Exception):
    pass


def sha_text(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


class Clock:
    def __init__(self, fixed: str | None = None):
        self.fixed = fixed
        self.tick = 0

    def now(self) -> float:
        return time.time()

    def iso(self) -> str:
        if self.fixed:
            self.tick += 1
            return f"{self.fixed[:17]}{self.tick % 60:02d}"
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    def hhmm(self) -> str:
        if self.fixed:
            return self.fixed[11:16]
        return time.strftime("%H:%M", time.localtime())


class RunFolder:
    APPEND_ONLY = ("log.jsonl", "metrics.jsonl", "experiments/log.jsonl", "dispatch.jsonl", "capture.jsonl", "executions.jsonl")

    def __init__(self, run_dir: str, run_id: str, clock: Clock | None = None):
        self.root = os.path.abspath(run_dir)
        self.run_id = run_id
        self.clock = clock or Clock()
        os.makedirs(self.root, exist_ok=True)

    # ---- paths
    def path(self, rel: str) -> str:
        p = os.path.abspath(os.path.join(self.root, rel))
        if not p.startswith(self.root + os.sep) and p != self.root:
            raise ValueError(f"path escapes the run folder: {rel}")
        return p

    def exists(self, rel: str) -> bool:
        return os.path.exists(self.path(rel))

    def read(self, rel: str) -> str:
        with open(self.path(rel), "rb") as f:
            return f.read().decode("utf-8")

    def read_json(self, rel: str, default=None):
        try:
            return json.loads(self.read(rel))
        except (OSError, ValueError):
            return default

    def read_jsonl(self, rel: str) -> list:
        if not self.exists(rel):
            return []
        return [json.loads(l) for l in self.read(rel).splitlines() if l.strip()]

    def listdir(self, rel: str = "") -> list:
        p = self.path(rel) if rel else self.root
        return sorted(os.listdir(p)) if os.path.isdir(p) else []

    def stages(self) -> list:
        return sorted(d for d in self.listdir() if re.match(r"stage-\d\d-", d))

    # ---- writes
    def _write_bytes(self, rel: str, text: str):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(text.encode("utf-8"))

    def write_once(self, rel: str, text: str, *, seat: str = "DISPATCH", action: str = "write", stage: str | None = None) -> str:
        if rel == "status.json" or rel in self.APPEND_ONLY:
            raise ValueError(f"{rel} is not a write-once file")
        if self.exists(rel):
            raise WriteOnceViolation(rel)
        self._write_bytes(rel, text)
        sha = sha_text(text)
        self.log(seat, action, file=rel, stage=stage, sha=sha)
        return sha

    def append_jsonl(self, rel: str, obj: dict):
        if rel not in self.APPEND_ONLY:
            raise ValueError(f"{rel} is not an append-only file")
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "ab") as f:
            f.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))

    def log(self, seat: str, action: str, result: str = "OK", file: str | None = None, stage: str | None = None,
            sha: str | None = None, **extra):
        rec = {"t": self.clock.iso(), "seat": seat, "action": action, "result": result}
        if file:
            rec["file"] = file
        if stage:
            rec["stage"] = stage
        if sha:
            rec["sha256"] = sha
        rec.update(extra)
        self.append_jsonl("log.jsonl", rec)

    def status(self, **updates) -> dict:
        cur = self.read_json("status.json", {}) or {}
        cur.setdefault("run", self.run_id)
        cur.setdefault("flags", [])
        cur.setdefault("sends_used", 0)
        cur.setdefault("sends_reserved_for_tail", 0)
        cur.setdefault("experiments_used", 0)
        cur.setdefault("caps_known", {})
        cur.setdefault("stop_reason", None)
        if "last_complete" in updates and updates["last_complete"] and not self.exists(updates["last_complete"]):
            raise ValueError(f"last_complete must exist on disk: {updates['last_complete']}")
        cur.update(updates)
        self._write_bytes("status.json", json.dumps(cur, indent=1))
        return cur

    def add_flag(self, flag: str):
        st = self.read_json("status.json", {}) or {}
        flags = list(st.get("flags", []))
        if flag not in flags:
            flags.append(flag)
            self.status(flags=flags)
            self.log("DISPATCH", "flag", result=flag)

    def flags(self) -> list:
        return list((self.read_json("status.json", {}) or {}).get("flags", []))


def next_run_id(root: str) -> str:
    runs = os.path.join(root, "runs")
    n = 0
    if os.path.isdir(runs):
        for d in os.listdir(runs):
            m = re.match(r"na-(\d{3})$", d)
            if m:
                n = max(n, int(m.group(1)))
    return f"na-{n + 1:03d}"
