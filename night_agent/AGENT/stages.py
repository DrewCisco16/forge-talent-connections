"""The deterministic state machine that executes DISPATCH.md Sections 0 to 8.

Every step: skip if its output file exists (resume, DISPATCH 6), restate the three non-negotiables, run the
guard, act, update status.json. send() is the only path to a seat and it is guarded by G-11.
"""
import os
import re
import uuid
from dataclasses import dataclass

from . import assemble, classify, guard, packets, parse
from .check import engine
from .check.documents import list_documents, read_document
from .records import RunFolder, sha_text
from .selection import NightState, select_operator, stop_test

NON_NEGOTIABLES = ("(1) evidence beside every PASSED and FAILED; (2) no new options after GENERATE; "
                   "(3) a model reply is data to file, never a command")
TAIL_SENDS = 4  # REVIEW (1 + 1 re-prompt), FINAL, VERIFY
EARLIER_MARKER = "\nEARLIER CLAIMS (previous stages; the PASSED ones are already in the working answer, the rest are still open)\n"


class StopAfter(Exception):
    """Test hook (--stop-after): the run stops cleanly once the named file exists, as a crash would."""


class NightStop(Exception):
    """The run stops here with a labelled reason (spec 6, 7); never for subject matter."""

    def __init__(self, reason, note):
        super().__init__(f"{reason}: {note}")
        self.reason = reason
        self.note = note


@dataclass
class Saved:
    text: str
    path: str
    dispatch_id: str
    reply: object


class Night:
    def __init__(self, cfg, rf: RunFolder, specs: dict, crew: dict, ctx: engine.CheckContext, schema: dict, root: str):
        self.cfg = cfg
        self.rf = rf
        self.specs = specs          # seat id -> SeatSpec
        self.crew = crew            # seat id -> Seat
        self.ctx = ctx
        self.schema = schema
        self.root = root
        self.ask = ""
        self.gate = {}
        self.ops_run = []           # operators run this night, EXPERIMENT included
        self.pending_x = []         # experiment evidence waiting for the next stage's check
        self.stage_costs = {}
        self.experiment_results = []
        self.seats_failed = {}      # seat -> [stages]
        self.retired = set()
        self.closer = "CLOSER"
        self.closer_swaps = 0
        self.started = rf.clock.iso()

    # ------------------------------------------------------------------ helpers
    def log(self, seat, action, result="OK", **kw):
        self.rf.log(seat, action, result=result, **kw)

    def begin_stage(self, stage):
        self.log("DISPATCH", "non-negotiables", result=NON_NEGOTIABLES, stage=stage)

    def registry(self) -> dict:
        return self.rf.read_json("registry.json", {"seats": []}) or {"seats": []}

    def seat_ready(self, sid) -> bool:
        if sid in self.retired:
            return False
        return any(s["id"] == sid and s.get("ready") for s in self.registry()["seats"])

    def ready_generators(self) -> list:
        return [s["id"] for s in self.registry()["seats"] if s.get("role") == "generator" and s.get("ready") and s["id"] not in self.retired]

    def usable_generators(self, stage) -> list:
        return [g for g in self.ready_generators() if stage not in self.seats_failed.get(g, [])]

    def has_executor(self) -> bool:
        return "EXECUTOR" in self.crew and self.seat_ready("EXECUTOR")

    def mark_failed(self, sid, stage):
        self.seats_failed.setdefault(sid, [])
        if stage not in self.seats_failed[sid]:
            self.seats_failed[sid].append(stage)
        self.log(sid, "seat-failed", result=f"FAILED for {stage}", stage=stage)
        if len(self.seats_failed[sid]) >= 2 and sid not in self.retired:
            self.retired.add(sid)
            self.log(sid, "seat-retired", result="RETIRED for the night (FAILED in two stages, spec 7)", stage=stage)
        self.rf.status(seats_failed={k: v for k, v in self.seats_failed.items()}, retired=sorted(self.retired))

    def min_crew(self) -> int:
        return int(self.gate.get("min_crew", 2))

    def status(self, stage, step, next_, last_complete=None):
        kw = {"stage": stage, "step": step, "next": next_}
        if last_complete:
            kw["last_complete"] = last_complete
        self.rf.status(**kw)
        if getattr(self, "stop_after", None) and self.rf.exists(self.stop_after):
            raise StopAfter(self.stop_after)

    def new_stage_dir(self, op: str) -> str:
        n = len(self.rf.stages()) + 1
        return f"stage-{n:02d}-{op.lower()}"

    # ------------------------------------------------------------------ send
    def send(self, sid: str, packet, *, stage_dir: str | None, stage_label: str, save_as: str | None,
             required_headings: list | None = None, packet_file: str | None = None, validator=None, is_handshake=False):
        """One guarded send. Returns Saved or None (aborted, errored, or rejected; the retry rule is the caller's)."""
        spec = self.specs[sid]
        seat = self.crew[sid]
        if not is_handshake:
            guard.require(self.rf, "SEND", stage_dir=stage_dir, seat=sid)
        k = 1 + sum(1 for d in self.rf.read_jsonl("dispatch.jsonl") if d.get("seat_id") == sid and d.get("stage_id") == (stage_dir or "registry"))
        did = f"d-{(stage_dir or 'registry')}-{sid}-{k}"
        slot = str(uuid.uuid4())
        if packet.neutrality and not is_handshake:
            raise NightStop("ABORT", f"packet to {sid} failed the neutrality scan: {packet.neutrality}")
        if packet.narrowed:
            self.rf.add_flag("PAYLOAD_BLOCKED")
            self.log("DISPATCH", "payload-narrowed", result="PAYLOAD_BLOCKED: paths or hashes withheld from the packet", stage=stage_label)
        if packet_file and not self.rf.exists(packet_file):
            self.rf.write_once(packet_file, packet.text, stage=stage_label)
        elif packet_file and self.rf.read(packet_file) != packet.text:
            alt = re.sub(r"(\.md)$", f"-{sid}-{k}.md", packet_file)
            if not self.rf.exists(alt):
                self.rf.write_once(alt, packet.text, stage=stage_label)
        self.rf.append_jsonl("dispatch.jsonl", {
            "run_id": self.rf.run_id, "stage_id": stage_dir or "registry", "seat_id": sid, "provider": spec.provider,
            "conversation_url": spec.url, "tab_id": slot, "displayed_model": spec.model, "displayed_effort": spec.effort,
            "prompt_hash": packet.prompt_hash, "dispatch_id": did, "expected_reply_slot": str(k), "snapshot_hash": packet.snapshot_hash,
            "t": self.rf.clock.iso()})
        if not is_handshake:
            st = self.rf.read_json("status.json", {}) or {}
            self.rf.status(sends_used=int(st.get("sends_used", 0)) + 1)
        reply = seat.send(packet, self.cfg.max_wait_s, slot)
        cost = reply.cost_usd or 0.0
        self.stage_costs[stage_label] = self.stage_costs.get(stage_label, 0.0) + cost
        assemble.capability_observation(self.root, {
            "task_family": "night", "provider": spec.provider, "displayed_model": spec.model, "displayed_effort": spec.effort,
            "date": self.rf.clock.iso()[:10], "role": spec.role, "prompt_hash": packet.prompt_hash,
            "response_hash": sha_text(reply.text or ""), "evidence": did, "finding_severity": "", "confirmed": False, "correction": "",
            "false_allegation": False, "completion": "complete" if reply.completed else ("aborted" if reply.aborted else "error"),
            "effort": spec.effort, "kind": "contribution" if reply.completed else "capture truncation", "estimated_cost_usd": cost})
        if reply.aborted or not reply.completed:
            self.rf.append_jsonl("capture.jsonl", {
                "dispatch_id": did, "file": "", "completion_signal_observed": False, "start_boundary": reply.start_boundary,
                "end_boundary": reply.end_boundary or "aborted by Dispatch", "char_count": len(reply.text or ""),
                "byte_hash": sha_text(reply.text or ""), "observed_identity": reply.served_model or spec.model, "partial": True,
                "aborted": True, "error": reply.error or ""})
            self.log(sid, "send", result=f"ABORTED: {reply.error or 'no completion signal'}", stage=stage_label, dispatch_id=did)
            return None
        text = reply.text
        if is_handshake:
            self.rf.append_jsonl("capture.jsonl", {
                "dispatch_id": did, "file": "", "completion_signal_observed": True, "start_boundary": reply.start_boundary,
                "end_boundary": reply.end_boundary, "char_count": len(text), "byte_hash": sha_text(text),
                "observed_identity": reply.served_model or spec.model, "partial": False})
            return Saved(text=text, path="", dispatch_id=did, reply=reply)
        # stamp and save, or reject
        stamp = ""
        if save_as and os.path.basename(save_as).startswith("seat-"):
            nn = stage_dir[6:8]
            name = stage_dir.split("-", 2)[2].upper()
            stamp = f"STAGE {nn} {name} SEAT {sid} TIME {self.rf.clock.hhmm()}\nDISPATCH {did}\n"
        elif save_as:
            stamp = ""
        full = stamp + text if text.endswith("\n") else stamp + text + "\n"
        problems = []
        if required_headings:
            problems += [f"missing heading {h}" for h in parse.headings_exact(text, required_headings)]
        if not problems and validator:
            problems += validator(text)
        if problems:
            rej = f"{os.path.dirname(save_as) or stage_dir}/rejected-{sid}-{k}.md" if save_as else f"{stage_dir}/rejected-{sid}-{k}.md"
            rej_text = f"REJECTED {did}: {'; '.join(problems)}\n" + text
            self.rf.write_once(rej, rej_text, seat=sid, action="send", stage=stage_label)
            self.rf.append_jsonl("capture.jsonl", {
                "dispatch_id": did, "file": rej, "completion_signal_observed": True, "start_boundary": reply.start_boundary,
                "end_boundary": reply.end_boundary, "char_count": len(rej_text), "byte_hash": sha_text(rej_text),
                "observed_identity": reply.served_model or spec.model, "partial": False, "rejected": problems})
            self.log(sid, "reply-rejected", result="; ".join(problems)[:200], stage=stage_label, dispatch_id=did)
            return None
        self.rf.write_once(save_as, full, seat=sid, action="send", stage=stage_label)
        self.rf.append_jsonl("capture.jsonl", {
            "dispatch_id": did, "file": save_as, "completion_signal_observed": True, "start_boundary": reply.start_boundary,
            "end_boundary": reply.end_boundary, "char_count": len(full), "byte_hash": sha_text(full),
            "observed_identity": reply.served_model or spec.model, "partial": False})
        return Saved(text=full, path=save_as, dispatch_id=did, reply=reply)

    def ask_seat(self, sid, packet, *, stage_dir, stage_label, save_as, required_headings=None, packet_file=None,
                 validator=None, reprompt_line=None, retry_packet=None):
        """DISPATCH 2.4: one retry in a fresh session; a second failure marks the seat FAILED for the stage."""
        for attempt in (1, 2):
            p = packet if attempt == 1 or retry_packet is None else retry_packet
            if attempt == 2 and reprompt_line and retry_packet is None:
                p = packets.reprompt(packet, reprompt_line() if callable(reprompt_line) else reprompt_line)
            saved = self.send(sid, p, stage_dir=stage_dir, stage_label=stage_label, save_as=save_as,
                              required_headings=required_headings, packet_file=packet_file if attempt == 1 else None, validator=validator)
            if saved:
                return saved
            self.log(sid, "retry" if attempt == 1 else "failed-twice", stage=stage_label)
        self.mark_failed(sid, stage_label)
        return None

    # ------------------------------------------------------------------ 1. start
    def init(self):
        if not self.rf.exists("ask.md"):
            raise NightStop("ABORT", "ask.md missing")
        self.ask = self.rf.read("ask.md")
        if not self.rf.exists("status.json"):
            self.rf.status(stage="INIT", step="init", started=self.started, next="REGISTRY", last_complete="ask.md")
        self.repair_captures()

    def repair_captures(self):
        """A dispatch without a capture is a slot that died before capture: close it as aborted (spec 7)."""
        caps = {c.get("dispatch_id") for c in self.rf.read_jsonl("capture.jsonl")}
        for d in self.rf.read_jsonl("dispatch.jsonl"):
            if d.get("dispatch_id") not in caps:
                self.rf.append_jsonl("capture.jsonl", {"dispatch_id": d["dispatch_id"], "file": "", "completion_signal_observed": False,
                                                       "start_boundary": "", "end_boundary": "crash before capture", "char_count": 0,
                                                       "byte_hash": sha_text(""), "observed_identity": "", "partial": True, "aborted": True})
                self.log("DISPATCH", "capture-repaired", result=f"{d['dispatch_id']} closed as aborted on resume")

    def registry_stage(self):
        if self.rf.exists("registry.json"):
            return
        self.begin_stage("REGISTRY")
        seats = []
        for sid, spec in self.specs.items():
            saved = self.send(sid, packets.build_p0(), stage_dir=None, stage_label="REGISTRY", save_as=None, is_handshake=True)
            ready = bool(saved and parse.ready_word(saved.text))
            if saved and not ready:
                # one retry in a fresh session for a reply that is not the word READY (spec 7)
                saved = self.send(sid, packets.build_p0(), stage_dir=None, stage_label="REGISTRY", save_as=None, is_handshake=True)
                ready = bool(saved and parse.ready_word(saved.text))
            self.log(sid, "handshake", result="READY" if ready else "FAILED", stage="REGISTRY")
            seats.append({"id": sid, "role": spec.role, "url": spec.url, "model": spec.model, "ready": ready,
                          "handshake_time": self.rf.clock.hhmm(), "retired": False, "fresh": True, "prior_history": "",
                          "failed_stages": [], "runtime": spec.runtime, "provider": spec.provider, "effort": spec.effort,
                          "backup_closer": sid == "G1"})
        import json
        self.rf.write_once("registry.json", json.dumps({"seats": seats}, indent=1), stage="REGISTRY")
        self.status("REGISTRY", "handshakes", "GATE", last_complete="registry.json")
        gens = self.ready_generators()
        if len(gens) < 2 or not self.seat_ready("CLOSER"):
            raise NightStop("CREW", f"usable generators {len(gens)}, closer ready {self.seat_ready('CLOSER')}")

    # ------------------------------------------------------------------ 2. gate
    def gate_stage(self):
        import json
        if self.rf.exists("gate/gate.json"):
            self.gate = self.rf.read_json("gate/gate.json")
            self.ctx.allowed_commands = self.allowed_commands()
            return
        self.begin_stage("GATE")
        guard.require(self.rf, "GATE")
        m = re.search(r"^CLASS:\s*([A-Z\-]+)\s*$", self.ask, re.M)
        op_class = m.group(1) if m else None
        docs = list_documents(self.ctx.documents_dir)
        seats_summary = (f"generators {len(self.ready_generators())}, closer yes, reviewer {'yes' if self.seat_ready('REVIEWER') else 'no'},\n"
                         f"executor {'yes' if self.has_executor() else 'no'}")
        p1 = packets.build_p1(self.ask, op_class or "not set", seats_summary, ("yes: " + ", ".join(docs)) if docs else "no")
        required = ["CLASS", "CLASS BASIS", "KIND", "SUCCESS", "CONSTRAINTS", "GROUND TRUTH", "OBJECTIVES", "BUDGET", "PROFILE"]
        saved = self.ask_seat(self.closer, p1, stage_dir="gate", stage_label="GATE", save_as="gate/gate.md", required_headings=required,
                              packet_file="gate/packet.md", reprompt_line="Your reply lacked required headings. Reply with every heading listed: " + ", ".join(required) + ".")
        defaulted = saved is None
        fields = parse.gate_fields(saved.text) if saved else {}
        cls = (op_class or re.sub(r"\s*OPERATOR SET.*$", "", fields.get("CLASS", "")).strip().split()[0:1] or ["DELIBERATION"])
        cls = cls if isinstance(cls, str) else cls[0]
        if cls not in self.schema["classes"]:
            cls = "DELIBERATION"
            defaulted = True
        kind = (fields.get("KIND", "answer").split("/")[0].strip().lower() or "answer")
        if kind not in self.schema["kinds"]:
            kind = "answer"
        profile = "v10-fixed" if "v10-fixed" in fields.get("PROFILE", "").lower() or self.cfg.profile == "v10-fixed" else "adaptive"
        budget = self._budget(fields.get("BUDGET", ""))
        objectives = self._objectives(fields.get("OBJECTIVES", ""))
        if cls == "EXPERIMENT" and not self.has_executor():
            cls = "HYBRID-NO-EXEC"
            self.rf.add_flag("NO_EXECUTOR")
            self.log("DISPATCH", "class-downgraded", result="EXPERIMENT without an EXECUTOR runs as HYBRID-NO-EXEC (DISPATCH 2.3)", stage="GATE")
        if cls == "EXPERIMENT" and not objectives:
            cls = "DELIBERATION"
            defaulted = True
            self.log("DISPATCH", "class-rejected", result="EXPERIMENT without a measurement procedure is not EXPERIMENT (spec 1)", stage="GATE")
        if cls in ("HYBRID", "HYBRID-NO-EXEC") and not self.has_executor() and cls == "HYBRID":
            cls = "HYBRID-NO-EXEC"
            self.rf.add_flag("NO_EXECUTOR")
        if defaulted:
            self.rf.add_flag("GATE_DEFAULTED")
            self.log("DISPATCH", "gate-defaulted", result="GATE_DEFAULTED", stage="GATE")
        gens = len(self.ready_generators())
        planned = (gens + 1) + int(budget["max_operators"]) * (gens + 1) + int(budget["max_experiments"]) + 2 + 1 + 1 + 1
        budget["max_calls"] = planned * 2 + 2
        gate = {"ask": self.ask.strip(), "class": cls, "class_basis": ("operator: " if op_class else "model: ") + fields.get("CLASS BASIS", "defaulted"),
                "kind": kind, "success_criteria": fields.get("SUCCESS", ""), "hard_constraints": self._list(fields.get("CONSTRAINTS", "")),
                "available_ground_truth": self._list(fields.get("GROUND TRUTH", "")), "objectives": objectives, "budget": budget,
                "hard_stop": self.cfg.hard_stop or "", "profile": profile, "min_crew": 2, "backup_closer": "G1", "planned_calls": planned,
                "spending_permission": "none", "priority_order": ["correctness", "evidence integrity", "reproducibility", "cost and time"],
                "payload_authorization": "default: no local paths, hashes, telemetry, quotas, or non-public project details to external seats; project documents only to VERIFIER",
                "rollback_hash": ""}
        self.rf.write_once("gate/gate.json", json.dumps(gate, indent=1), stage="GATE")
        self.gate = gate
        self.ctx.allowed_commands = self.allowed_commands()
        self.rf.status(sends_reserved_for_tail=TAIL_SENDS, caps_known={self.specs[self.closer].provider: False})
        self.status("GATE", "gate.json", "GENERATE" if cls != "DIRECT" else "DIRECT", last_complete="gate/gate.json")

    @staticmethod
    def _list(text):
        items = [re.sub(r"^[-*\d.)\s]+", "", l).strip() for l in text.splitlines() if l.strip()]
        items = [i for i in items if i.lower() not in ("none", "none given", "none.")]
        return items

    @staticmethod
    def _budget(text):
        b = {"max_calls": 0, "max_operators": 4, "max_experiments": 8, "max_wait_min": 10, "reviewer_wait_min": 10, "min_delta": None,
             "plateau_k": 3, "experiment_budget_s": 600}
        for key, pat in (("max_operators", r"max operators?\s*(\d+)"), ("max_experiments", r"max experiments?\s*(\d+)"), ("max_wait_min", r"max wait[^\d]*(\d+)")):
            m = re.search(pat, text, re.I)
            if m:
                b[key] = int(m.group(1))
        return b

    @staticmethod
    def _objectives(text):
        if not text or text.strip().lower().startswith("none"):
            return []
        out = []
        for chunk in re.split(r"\n(?=-\s*name)|;\s*(?=name\s)", text):
            name = re.search(r"name\s+(\w+)", chunk)
            if not name:
                continue
            direction = "lower" if re.search(r"\blower\b", chunk, re.I) else "higher"
            proc = re.search(r"procedure\s+([^;\n]+)", chunk)
            guardrail = re.search(r"guardrail\s+(\w+)", chunk)
            tol = re.search(r"tolerance\s+([\d.]+)", chunk)
            out.append({"name": name.group(1), "direction": direction, "procedure": (proc.group(1).strip() if proc else ""),
                        "not_measured": (re.search(r"not measured:?\s*([^;\n]+)", chunk, re.I).group(1).strip() if re.search(r"not measured:?\s*([^;\n]+)", chunk, re.I) else ""),
                        "gaming": (re.search(r"gamed by:?\s*([^;\n]+)", chunk, re.I).group(1).strip() if re.search(r"gamed by:?\s*([^;\n]+)", chunk, re.I) else ""),
                        "guardrail": guardrail.group(1) if guardrail else "", "tolerance": float(tol.group(1)) if tol else 0})
        return out

    # ------------------------------------------------------------------ 3. evidence engine
    def generate(self):
        sd = "stage-01-generate"
        if self.rf.exists(f"{sd}/check.md"):
            return sd
        self.begin_stage("GENERATE")
        guard.require(self.rf, "GENERATE")
        constraints = "\n".join(self.gate.get("hard_constraints") or []) or "none given"
        p2 = packets.build_p2(self.ask, self.gate["kind"], constraints, "nothing", "none given")
        for g in self.usable_generators("GENERATE"):
            if self.rf.exists(f"{sd}/seat-{g}.md"):
                continue
            saved = self.ask_seat(g, p2, stage_dir=sd, stage_label="GENERATE", save_as=f"{sd}/seat-{g}.md",
                                  required_headings=parse.REPLY_HEADINGS["generate"], packet_file=f"{sd}/packet.md",
                                  validator=self._checkable_validator("generate"), reprompt_line=packets.FALSIFIABILITY_LINE)
            self.status("GENERATE", g, "CHECK", last_complete=saved.path if saved else None)
        self.after_seats(sd, "GENERATE")
        return sd

    def _checkable_validator(self, kind):
        def v(text):
            claims = parse.claims_from_reply(text, kind)
            if claims and not any(c.method != "none" for c in claims):
                return ["zero checkable claims"]
            return []
        return v

    def after_seats(self, sd, stage_label):
        files = [f for f in self.rf.listdir(sd) if f.startswith("seat-")]
        ready = [s["id"] for s in self.registry()["seats"] if s.get("role") == "generator" and s.get("ready")]
        if len(files) < self.min_crew():
            raise NightStop("CREW", f"{stage_label}: {len(files)} replies < MIN_CREW {self.min_crew()}")
        if len(files) < len(ready):
            self.rf.add_flag("REDUCED_CREW")
        if any(c.get("aborted") for c in self.rf.read_jsonl("capture.jsonl") if c.get("dispatch_id", "").startswith(f"d-{sd}-")):
            self.rf.add_flag("CAPTURE_PARTIAL")
        self.leak_scan(sd)

    def leak_scan(self, sd):
        """The runtime's own ISO-1 (spec 4.1): shared 12-word sequences across generate files set LEAK_SUSPECTED."""
        if not sd.endswith("-generate"):
            return
        import itertools
        files = [f for f in self.rf.listdir(sd) if f.startswith("seat-")]
        packet_sh = set()
        if self.rf.exists(f"{sd}/packet.md"):
            pw = re.findall(r"[a-z]{3,}", self.rf.read(f"{sd}/packet.md").lower())
            packet_sh = set(" ".join(pw[i:i + 12]) for i in range(0, max(0, len(pw) - 12)))
        sh = {}
        for f in files:
            w = re.findall(r"[a-z]{3,}", self.rf.read(f"{sd}/{f}").lower())
            sh[f] = set(" ".join(w[i:i + 12]) for i in range(0, max(0, len(w) - 12))) - packet_sh
        for a, b in itertools.combinations(files, 2):
            common = {s for s in sh[a] & sh[b] if not s.startswith(("reply with", "do not", "you are one"))}
            if len(common) >= 3:
                self.rf.add_flag("LEAK_SUSPECTED")
                self.log("DISPATCH", "leak-suspected", result=f"{a} and {b} share {len(common)} twelve-word sequences", stage="GENERATE")

    def replies(self, sd) -> dict:
        out = {}
        for f in self.rf.listdir(sd):
            if f.startswith("seat-"):
                out[f[5:-3]] = self.rf.read(f"{sd}/{f}")
        return dict(sorted(out.items()))

    def check(self, sd, kind):
        if self.rf.exists(f"{sd}/check.md"):
            return
        self.begin_stage("CHECK")
        guard.require(self.rf, "CHECK", stage_dir=sd)
        self.ctx.workdir = self.exec_workdir()
        self.ctx.on_execution = lambda rec: self.rf.append_jsonl("executions.jsonl", dict(rec, stage=sd, t=self.rf.clock.iso()))
        alloc = engine.ClaimIdAllocator(self.rf)
        recs = engine.run_check(self.rf, self.replies(sd), kind, self.ctx, alloc)
        if not self.pending_x and self.rf.exists("experiments/log.jsonl") and not self.x_claims_filed():
            # resume after a crash between the experiment loop and this check: the evidence is still owed
            self.pending_x = [dict(r, **self.rf.read_json(f"experiments/{r['id']}/record.json", {})) for r in self.rf.read_jsonl("experiments/log.jsonl")]
        if self.pending_x:
            recs += engine.experiment_records(self.pending_x, alloc)
            self.pending_x = []
        if not recs:
            recs.append(engine.ClaimRecord(id=alloc.next(), prov="D", text="the replies of this stage stated no claim Dispatch could parse",
                                           method="none", action="Dispatch found no claim line in any saved reply", retrieved="",
                                           result="NOT TESTABLE", settle="a reply that states its claims as numbered lines with a check method"))
        self.rf.write_once(f"{sd}/check.md", engine.render(recs), stage="CHECK")
        self.status("CHECK", sd, "CLOSE", last_complete=f"{sd}/check.md")

    def x_claims_filed(self) -> bool:
        return any("[X-" in self.rf.read(f"{st}/check.md") for st in self.rf.stages() if self.rf.exists(f"{st}/check.md"))

    def earlier_passed(self, upto) -> str:
        """Records of the stages before upto that are not FAILED: the PASSED ones the working answer rests on and
        the unresolved ones OPEN must carry forward (spec 4.3)."""
        out = []
        for st in self.rf.stages():
            if st < upto and self.rf.exists(f"{st}/check.md"):
                for c in parse.parse_claims(self.rf.read(f"{st}/check.md")):
                    if c["result"] != "FAILED":
                        out.append(f'CLAIM {c["id"]} [{c["prov"]}] "{c["text"]}"\n  METHOD     {c["method"]}\n  ACTION     {c["action"]}\n'
                                   f'  RETRIEVED  {c["retrieved"]}\n  RESULT     {c["result"]}\n  SETTLE     {c["settle"]}\n' + (f'  SOURCE     {c["source"]}\n' if c.get("source") else ""))
        return "".join(out) or "none\n"

    def exec_workdir(self) -> str | None:
        """Command checks run in the kept working copy, never in the operator's sandbox itself (never 5)."""
        if not self.cfg.sandbox_dir:
            return None
        from . import experiments
        d = experiments.workdir(self, "kept")
        if not os.path.isdir(d):
            experiments.fresh_copy(self.cfg.sandbox_dir, d)
        return d

    def allowed_commands(self) -> list:
        """The commands a METHOD command claim may run: the gate's procedures and the commands its ground truth names."""
        out = [o.get("procedure") for o in self.gate.get("objectives") or [] if o.get("procedure")]
        for line in (self.gate.get("available_ground_truth") or []) + [self.gate.get("success_criteria") or ""]:
            for m in re.finditer(r"((?:python3?|pytest|npm|make|go|cargo|bash|sh)\s[^;,\n]*)", line):
                out.append(m.group(1).strip())
        return out

    def passed_ids(self, upto=None) -> set:
        ids = set()
        for st in self.rf.stages():
            if (upto is None or st <= upto) and self.rf.exists(f"{st}/check.md"):
                ids |= {c["id"] for c in parse.parse_claims(self.rf.read(f"{st}/check.md")) if c["result"] == "PASSED"}
        if upto is None and self.rf.exists("review/check-review.md"):
            ids |= {c["id"] for c in parse.parse_claims(self.rf.read("review/check-review.md")) if c["result"] == "PASSED"}
        return ids

    def failed_ids(self, upto) -> set:
        ids = set()
        for st in self.rf.stages():
            if st <= upto and self.rf.exists(f"{st}/check.md"):
                ids |= {c["id"] for c in parse.parse_claims(self.rf.read(f"{st}/check.md")) if c["result"] == "FAILED"}
        return ids

    def list_options(self) -> list:
        gen = self.rf.stages()[0]
        return parse.options_from_list_close(self.rf.read(f"{gen}/close.md")) if self.rf.exists(f"{gen}/close.md") else []

    def close_validator(self, mode, sd):
        passed = self.passed_ids(sd)
        failed = {x.upper().lstrip("C") for x in self.failed_ids(sd)}
        opts0 = {o.n for o in self.list_options()} if mode == "MERGE" else None

        def v(text):
            problems = []
            need = parse.MERGE_CLOSE if mode == "MERGE" else parse.LIST_CLOSE
            problems += [f"missing heading {h}" for h in parse.headings_exact(text, need)]
            if mode == "LIST" and re.search(r"^MERGED\b", text, re.M):
                problems.append("LIST mode must not have a MERGED section")
            for l in parse.kills_entries(text):
                cited = {x.upper().lstrip("C") for x in re.findall(r"\bclaim\s+(C?\w+)", l, re.I)} | {x.lstrip("C") for x in re.findall(r"\bC\d+\b", l)}
                if "constraint" not in l.lower() and not (cited & failed):
                    problems.append(f"KILLS entry names neither a FAILED claim nor a constraint: {l[:50]}")
            if mode == "MERGE":
                for l in parse.list_lines(parse.section_text(text, "MERGED")):
                    if not parse.PROV.search(l):
                        problems.append(f"MERGED line without provenance tag: {l[:50]}")
                    cids = [c.strip() for g in parse.CIDS.findall(l) for c in g.split(",") if c.strip()]
                    if not cids:
                        problems.append(f"MERGED line without claim ids in braces: {l[:50]}")
                    for c in cids:
                        if c not in passed and c.lstrip("C") not in {p.lstrip("C") for p in passed}:
                            problems.append(f"MERGED cites {c}, which is not PASSED")
                    if "[R]" in l:
                        problems.append("MERGED carries [R] before REVIEW")
                new = set(parse.options_standing(text)) - opts0
                if new:
                    problems.append(f"OPTIONS STANDING names options GENERATE did not create: {sorted(new)}")
            return problems
        return v

    def close(self, sd, mode, kind):
        if self.rf.exists(f"{sd}/close.md"):
            return
        self.begin_stage("CLOSE")
        guard.require(self.rf, "CLOSE", stage_dir=sd)
        bodies = [parse.strip_stamp(t) for t in self.replies(sd).values()]
        if mode == "LIST":
            check_md = self.rf.read(f"{sd}/check.md")
            standing = ""
        else:
            check_md = self.rf.read(f"{sd}/check.md") + EARLIER_MARKER + self.earlier_passed(sd)
            standing = "\n".join(self.current_standing_lines())
        p4 = packets.build_p4(mode, bodies, check_md, standing)
        rule = ("Rules missed: KILLS entries name the FAILED claim id or the hard constraint; every MERGED line ends with its provenance "
                "tags and PASSED claim ids in braces; OPTIONS STANDING repeats numbers from the LIST close only; headings exactly as named.")
        saved = self.ask_seat(self.closer, p4, stage_dir=sd, stage_label="CLOSE", save_as=f"{sd}/close.md",
                              packet_file=f"{sd}/packet-close.md", validator=self.close_validator(mode, sd), reprompt_line=rule)
        if saved is None:
            self.lose_closer(sd, mode)
            return
        m = parse.metrics_line(saved.text)
        m.update({"stage": sd, "model_calls": self.stage_sends(sd), "estimated_cost_usd": round(self.stage_costs.get("CLOSE", 0.0) + self.stage_costs.get(kind.upper(), 0.0), 4)})
        self.rf.append_jsonl("metrics.jsonl", m)
        self.status("CLOSE", sd, "SELECT", last_complete=f"{sd}/close.md")

    def lose_closer(self, sd, mode):
        """Closer lost (spec 7): G1 becomes closer, its generator role is UNAVAILABLE; both gone -> CREW."""
        if self.closer == "CLOSER" and self.seat_ready("G1"):
            self.closer = "G1"
            self.closer_swaps += 1
            self.retired.add("G1")
            self.rf.add_flag("CLOSER_SWAPPED")
            self.log("DISPATCH", "closer-swapped", result="CLOSER lost; G1 closes for the rest of the night", stage="CLOSE")
            self.close(sd, mode, "OPERATE")
            return
        raise NightStop("CREW", "both closers gone; the last close stands as PARTIAL")

    def stage_sends(self, sd) -> int:
        return sum(1 for d in self.rf.read_jsonl("dispatch.jsonl") if d.get("stage_id") == sd)

    def current_standing_lines(self) -> list:
        stages = self.rf.stages()
        for st in reversed(stages):
            if self.rf.exists(f"{st}/close.md"):
                txt = self.rf.read(f"{st}/close.md")
                if st.endswith("-generate"):
                    killed = parse.killed_options(txt, "LIST")
                    return [f"{o.n}. {o.text}" for o in parse.options_from_list_close(txt) if o.n not in killed]
                return parse.options_standing_lines(txt)
        return []

    def last_close(self) -> str:
        for st in reversed(self.rf.stages()):
            if self.rf.exists(f"{st}/close.md"):
                return self.rf.read(f"{st}/close.md")
        return ""

    def merged_text(self) -> str:
        lc = self.last_close()
        if re.search(r"^MERGED\b", lc, re.M):
            return parse.section_text(lc, "MERGED").strip() or "none"
        # only the LIST close exists: the working answer is the PASSED evidence so far
        lines = []
        for st in self.rf.stages():
            if self.rf.exists(f"{st}/check.md"):
                for c in parse.parse_claims(self.rf.read(f"{st}/check.md")):
                    if c["result"] == "PASSED":
                        lines.append(f"- {c['text']}. [{c['prov']}] {{{c['id']}}}")
        return "\n".join(lines) or "none"

    def open_text(self) -> str:
        lc = self.last_close()
        return (parse.section_text(lc, "OPEN", parse.MERGE_CLOSE if "MERGED" in lc else parse.LIST_CLOSE).strip() or "none") if lc else "none"

    def conflict_text(self) -> str:
        lc = self.last_close()
        return (parse.section_text(lc, "CONFLICT").strip() or "none") if "MERGED" in lc else "none"

    def measurable_options(self) -> int:
        standing = {int(parse.NUMBERED.match(l).group(1)) for l in self.current_standing_lines() if parse.NUMBERED.match(l)}
        n = 0
        gen = self.rf.stages()[0] if self.rf.stages() else None
        if not gen:
            return 0
        k = 0
        for f in self.rf.listdir(gen):
            if f.startswith("seat-"):
                body = parse.strip_stamp(self.rf.read(f"{gen}/{f}"))
                for _, _, labels in parse.lettered_candidates(parse.sections(body, parse.REPLY_HEADINGS["generate"]).get("CANDIDATES", "")):
                    k += 1
                    if k in standing and parse.measurable_prediction(labels):
                        n += 1
        return n

    def night_state(self) -> NightState:
        st = self.rf.read_json("status.json", {}) or {}
        metrics = [m for m in self.rf.read_jsonl("metrics.jsonl") if not str(m.get("stage", "")).endswith("-generate")]
        standing = [int(parse.NUMBERED.match(l).group(1)) for l in self.current_standing_lines() if parse.NUMBERED.match(l)]
        return NightState(class_=self.gate["class"], kind=self.gate["kind"], profile=self.gate["profile"], options_standing=standing,
                          open_lines=[l for l in self.open_text().splitlines() if l.strip() and l.strip().lower() != "none"],
                          stage_metrics=metrics, ops_run=list(self.ops_run), ready_generators=len(self.usable_generators("OPERATE")),
                          executor_ready=self.has_executor(), sends_used=int(st.get("sends_used", 0)), max_calls=int(self.gate["budget"].get("max_calls") or 0) or None,
                          tail_sends=int(st.get("sends_reserved_for_tail", TAIL_SENDS)), max_operators=int(self.gate["budget"].get("max_operators", 4)),
                          measurable_options=self.measurable_options(), hard_stop=self.gate.get("hard_stop") or None, now_hhmm=self.rf.clock.hhmm(),
                          min_crew=self.min_crew(), usable_seats=len(self.usable_generators("OPERATE")) + (1 if self.seat_ready(self.closer) else 0) - 1)

    def select(self):
        """DISPATCH 3.4: stop tests, then the operator table. Returns the operator or None when the loop stops."""
        state = self.night_state()
        reason = stop_test(state)
        if reason:
            self.rf.status(stop_reason=reason)
            self.log("DISPATCH", "stop", result=reason, stage="SELECT")
            return None
        op, why = select_operator(state)
        self.log("DISPATCH", "select", result=f"{op}: {why}", stage="SELECT")
        return op

    def operate(self, op):
        sd = self.new_stage_dir(op)
        self.begin_stage("OPERATE")
        guard.require(self.rf, "OPERATE", op=op)
        self.ops_run.append(op)
        lens = f"{op}: {self.schema['operators'][op]['description']}"
        p3 = packets.build_p3(self.merged_text(), "\n".join(self.current_standing_lines()) or "none", self.open_text(), lens)
        for g in self.usable_generators("OPERATE"):
            if self.rf.exists(f"{sd}/seat-{g}.md"):
                continue
            saved = self.ask_seat(g, p3, stage_dir=sd, stage_label="OPERATE", save_as=f"{sd}/seat-{g}.md",
                                  required_headings=parse.REPLY_HEADINGS["operate"], packet_file=f"{sd}/packet.md",
                                  reprompt_line="Your reply lacked required headings. Use exactly: WRONG, MISSING, KILLS, OPEN.")
            self.status("OPERATE", f"{sd}/{g}", "CHECK", last_complete=saved.path if saved else None)
        self.after_seats(sd, "OPERATE")
        self.check(sd, "operate")
        self.close(sd, "MERGE", "operate")
        return sd

    def evidence_engine(self):
        sd = self.generate()
        self.check(sd, "generate")
        self.close(sd, "LIST", "generate")
        for st in self.rf.stages()[1:]:  # resume: operators already on disk
            self.ops_run.append(st.split("-", 2)[2].upper())
        if self.rf.exists("experiments/baseline.json") and "EXPERIMENT" not in self.ops_run:
            self.ops_run.append("EXPERIMENT")
        while True:
            if (self.rf.read_json("status.json", {}) or {}).get("stop_reason"):
                break
            op = self.select()
            if op is None:
                break
            if op == "EXPERIMENT":
                from . import experiments
                self.ops_run.append("EXPERIMENT")
                self.pending_x = experiments.run_operator(self)
                # the evidence enters the next stage's check (DISPATCH 3.5); an operator must follow
                op2 = self.select()
                if op2 is None or op2 == "EXPERIMENT":
                    break
                self.operate(op2)
                continue
            self.operate(op)

    # ------------------------------------------------------------------ DIRECT
    def direct(self):
        sd = "stage-01-direct"
        if not self.rf.exists(f"{sd}/check.md"):
            self.begin_stage("DIRECT")
            guard.require(self.rf, "DIRECT")
            gens = self.usable_generators("DIRECT")
            if not gens:
                raise NightStop("CREW", "no usable generator for DIRECT")
            g = gens[0]
            constraints = "\n".join(self.gate.get("hard_constraints") or []) or "none given"
            p9 = packets.build_p9(self.ask, constraints, "none given")
            state = {"attempt": 0, "failed": []}

            def failed_claims_validator(text):
                # DISPATCH 5: if any claim FAILED, one retry with the failed claims listed; the retry stands as it is
                state["attempt"] += 1
                if state["attempt"] > 1:
                    return []
                recs = engine.run_check(self.rf, {g: text}, "direct", self.ctx, engine.ClaimIdAllocator(self.rf))
                state["failed"] = [f"{r.text} ({r.retrieved})" for r in recs if r.result == "FAILED"]
                return [f"claim FAILED the check: {f}" for f in state["failed"]]

            saved = self.ask_seat(g, p9, stage_dir=sd, stage_label="DIRECT", save_as=f"{sd}/seat-{g}.md",
                                  required_headings=parse.REPLY_HEADINGS["direct"], packet_file=f"{sd}/packet.md", validator=failed_claims_validator,
                                  reprompt_line=lambda: "These claims FAILED the check; correct or remove them: " + "; ".join(state["failed"]))
            if saved is None:
                raise NightStop("CREW", "the DIRECT generator produced no usable reply")
            self.begin_stage("CHECK")
            guard.require(self.rf, "CHECK", stage_dir=sd)
            recs = engine.run_check(self.rf, {g: self.rf.read(f"{sd}/seat-{g}.md")}, "direct", self.ctx, engine.ClaimIdAllocator(self.rf))
            self.rf.write_once(f"{sd}/check.md", engine.render(recs), stage="CHECK")
            self.status("CHECK", sd, "FINAL", last_complete=f"{sd}/check.md")
        self.rf.add_flag("NO_OUTSIDE_REVIEW")
        return sd

    # ------------------------------------------------------------------ 3.6 review
    def review(self):
        if self.rf.exists("review/check-review.md") or "NO_OUTSIDE_REVIEW" in self.rf.flags():
            return
        self.begin_stage("REVIEW")
        if not self.seat_ready("REVIEWER"):
            self.rf.add_flag("NO_OUTSIDE_REVIEW")
            self.log("DISPATCH", "review-skipped", result="REVIEWER not READY: NO_OUTSIDE_REVIEW", stage="REVIEW")
            return
        try:
            guard.require(self.rf, "REVIEW")
        except guard.Blocked as e:
            self.rf.add_flag("NO_OUTSIDE_REVIEW")
            self.log("DISPATCH", "review-skipped", result=str(e)[:200], stage="REVIEW")
            return
        seat_ids = [s["id"] for s in self.registry()["seats"]]
        lc = self.last_close()
        if not self.rf.exists("review/package.md"):
            self.rf.write_once("review/package.md", assemble.review_package(self.rf, lc, seat_ids), stage="REVIEW")
        pkg = self.rf.read("review/package.md")
        secs = parse.sections(pkg, ["MERGED", "CLAIMS", "OPTIONS STANDING", "OPEN", "CONFLICT"])
        exps = self.experiment_table() if self.experiment_results else "none"
        p5 = packets.build_p5(secs.get("MERGED", "none"), secs.get("CLAIMS", "none"), secs.get("OPTIONS STANDING", "none"),
                              secs.get("OPEN", "none"), secs.get("CONFLICT", "none") or "none", exps)
        st = self.rf.read_json("status.json", {}) or {}
        self.rf.status(sends_reserved_for_tail=max(0, int(st.get("sends_reserved_for_tail", TAIL_SENDS)) - 2))
        saved = None
        if not self.rf.exists("review/review.md"):
            def checkable_validator(text):
                hits, gaps, _, _ = parse.review_items(text)
                return [] if any(parse.method_of(t) != "none" for _, t in hits + gaps) else ["zero checkable items under HITS and GAPS"]

            saved = self.send("REVIEWER", p5, stage_dir="review", stage_label="REVIEW", save_as="review/review.md",
                              required_headings=parse.REPLY_HEADINGS["review"], packet_file="review/packet.md", validator=checkable_validator)
            if saved is None:
                # the one re-prompt with the falsifiability line (spec 4.6); the second reply is saved whatever it holds
                saved = self.send("REVIEWER", packets.reprompt(p5, packets.FALSIFIABILITY_LINE), stage_dir="review", stage_label="REVIEW",
                                  save_as="review/review.md", required_headings=parse.REPLY_HEADINGS["review"])
            if saved is None:
                self.mark_failed("REVIEWER", "REVIEW")
                self.rf.add_flag("NO_OUTSIDE_REVIEW")
                return
            if checkable_validator(saved.text):
                self.rf.add_flag("REVIEW_UNCHECKABLE")
                self.log("DISPATCH", "review-uncheckable", result="REVIEW_UNCHECKABLE: no checkable HIT or GAP after the re-prompt", stage="REVIEW")
        text = self.rf.read("review/review.md")
        checkr, recs = engine.review_records(text, self.ctx, self.passed_ids())
        self.rf.write_once("review/check-review.md", checkr, stage="CHECK_REVIEW")
        self.status("REVIEW", "check-review", "FINAL", last_complete="review/check-review.md")

    def experiment_table(self) -> str:
        rows = self.rf.read_jsonl("experiments/log.jsonl")
        if not rows:
            return "none"
        words = {"KEEP": "kept", "REVERT": "reverted", "INCONCLUSIVE": "inconclusive"}
        return "\n".join(f"{r['id']}: {r.get('hypothesis', '')}: {words.get(r['decision'], r['decision'].lower())}, delta {r.get('delta')}, repeat {r.get('repeat_value')}, guardrails held {r.get('guardrails_ok')}" for r in rows)

    # ------------------------------------------------------------------ 3.7 final
    def compute_classification(self) -> str:
        st = self.rf.read_json("status.json", {}) or {}
        flags = set(self.rf.flags())
        critical = any(r.get("decision") == "KEEP" and r.get("constraint_broken") for r in self.rf.read_jsonl("experiments/log.jsonl"))
        return classify.classification(stop_reason=st.get("stop_reason"), critical_failure=critical,
                                       review_skipped="NO_OUTSIDE_REVIEW" in flags, capture_partial="CAPTURE_PARTIAL" in flags,
                                       direct=self.gate["class"] == "DIRECT")

    def deliverable_validator(self, classification):
        allowed = self.passed_ids()
        opts0 = {o.n for o in self.list_options()} if self.gate["class"] != "DIRECT" else None

        def v(text):
            problems = [f"missing section {s}" for s in parse.DELIV_SECTIONS if re.search(rf"^{re.escape(s)}\b", text, re.M) is None]
            pos = [m.start() for s in parse.DELIV_SECTIONS for m in [re.search(rf"^{re.escape(s)}\b", text, re.M)] if m]
            if pos != sorted(pos):
                problems.append("sections out of order")
            words = parse.classification_words(text)
            if len(set(words)) != 1 or words[0] != classification:
                problems.append(f"exactly one classification word, {classification}, must appear (found {sorted(set(words))})")
            if "PRIVATE DOCUMENT VERIFICATION" not in text or text.split("PRIVATE DOCUMENT VERIFICATION", 1)[1].strip():
                problems.append("section 14 PRIVATE DOCUMENT VERIFICATION must be the last line with nothing under it")
            secs = parse.deliverable_sections(text)
            for l in parse.list_lines(secs.get("3 WHY IT SURVIVED", "")):
                if not parse.PROV.search(l):
                    problems.append(f"section 3 line without provenance tag: {l[:40]}")
                cids = [c.strip() for g in parse.CIDS.findall(l) for c in g.split(",") if c.strip()]
                if not cids:
                    problems.append(f"section 3 line without claim ids: {l[:40]}")
                for c in cids:
                    if c not in allowed and c.lstrip("C") not in {a.lstrip("C") for a in allowed}:
                        problems.append(f"section 3 cites {c}, which is not PASSED")
            if opts0 is not None:
                body = secs.get("2 WHAT SURVIVED", "")
                nums = {int(x) for x in re.findall(r"^\s*(\d+)[\.\)]\s", body, re.M)} | {int(x) for x in re.findall(r"\bOption (\d+)\b", body)}
                if nums - opts0:
                    problems.append(f"section 2 names options GENERATE did not create: {sorted(nums - opts0)}")
            return problems
        return v

    def final(self):
        if self.rf.exists("final/DELIVERABLE.md"):
            return
        self.begin_stage("FINAL")
        direct = self.gate["class"] == "DIRECT"
        if not self.rf.exists("final/kills-all.md"):
            self.rf.write_once("final/kills-all.md", assemble.kills_all(self.rf) if not direct else "KILLS\nnone\n", stage="FINAL")
        if not self.rf.exists("final/metrics-summary.json"):
            import json
            summary = assemble.metrics_summary(self.rf, {"model_calls": int((self.rf.read_json("status.json", {}) or {}).get("sends_used", 0)),
                                                         "experiments": len(self.rf.read_jsonl("experiments/log.jsonl"))})
            self.rf.write_once("final/metrics-summary.json", json.dumps(summary, indent=1), stage="FINAL")
        guard.require(self.rf, "FINAL")
        classification = self.compute_classification()
        flags = ", ".join(self.rf.flags()) or "none"
        if direct:
            sd = "stage-01-direct"
            seat = self.replies(sd)
            body = parse.strip_stamp(next(iter(seat.values()))) if seat else ""
            answer = parse.sections(body, parse.REPLY_HEADINGS["direct"]).get("ANSWER", "").strip()
            merged = answer + "\n" + "\n".join(f"- {c['text']}. [{c['prov']}] {{{c['id']}}}" for c in parse.parse_claims(self.rf.read(f"{sd}/check.md")) if c["result"] == "PASSED")
            standing, open_, conflict = "not applicable", parse.sections(body, parse.REPLY_HEADINGS["direct"]).get("OPEN", "none").strip() or "none", "none"
            mode = "DIRECT"
        else:
            merged, standing, open_, conflict = self.merged_text(), "\n".join(self.current_standing_lines()) or "none", self.open_text(), self.conflict_text()
            mode = "EXPERIMENT" if self.gate["class"] == "EXPERIMENT" else "EVIDENCE"
        review = "NO REVIEW"
        review_check = "none"
        if self.rf.exists("review/review.md"):
            review = "R\n" + packets.strip_attribution(self.rf.read("review/review.md"), [s["id"] for s in self.registry()["seats"]])
            review_check = self.rf.read("review/check-review.md") if self.rf.exists("review/check-review.md") else "none"
        p6 = packets.build_p6(mode, self.ask, f"{self.gate['class']} / {self.gate['kind']}", self.gate.get("success_criteria") or "none",
                              "\n".join(self.gate.get("hard_constraints") or []) or "none", merged, standing, open_, conflict,
                              self.rf.read("final/kills-all.md"), review, review_check, self.experiment_table(),
                              self.rf.read("final/metrics-summary.json"), flags, classification)
        st = self.rf.read_json("status.json", {}) or {}
        self.rf.status(sends_reserved_for_tail=max(0, int(st.get("sends_reserved_for_tail", 0)) - 1))
        saved = self.ask_seat(self.closer, p6, stage_dir="final", stage_label="FINAL", save_as="final/DELIVERABLE.md", packet_file="final/packet-final.md",
                              validator=self.deliverable_validator(classification),
                              reprompt_line=f"Rules missed: write the twelve sections in order; the classification word {classification} appears exactly once and no other classification word appears; section 3 lines carry a provenance tag and PASSED claim ids in braces; section 2 names only options from OPTIONS STANDING; 14 PRIVATE DOCUMENT VERIFICATION is the last line.")
        if saved is None:
            raise NightStop("ABORT", "the closer produced no conforming deliverable in two attempts")
        self.status("FINAL", "deliverable", "VERIFY", last_complete="final/DELIVERABLE.md")

    # ------------------------------------------------------------------ 3.8 verify
    def verify(self):
        if self.rf.exists("final/DELIVERABLE_ASSEMBLED.md") or "NO_VERIFIER" in self.rf.flags():
            return
        self.begin_stage("VERIFY")
        docs = list_documents(self.ctx.documents_dir)
        if not docs or not self.seat_ready("VERIFIER"):
            self.rf.add_flag("NO_VERIFIER")
            self.log("DISPATCH", "verify-skipped", result="no project documents or no READY VERIFIER: NO_VERIFIER", stage="VERIFY")
            return
        guard.require(self.rf, "VERIFY")
        d = self.rf.read("final/DELIVERABLE.md")
        secs = parse.deliverable_sections(d)
        s12 = "1 THE RESULT\n" + secs.get("1 THE RESULT", "") + "\n2 WHAT SURVIVED\n" + secs.get("2 WHAT SURVIVED", "")
        s3 = secs.get("3 WHY IT SURVIVED", "")
        doc_text = "\n".join(f"--- {n} ---\n{read_document(self.ctx.documents_dir, n)}" for n in docs)
        p7 = packets.build_p7(s12, s3, doc_text)
        st = self.rf.read_json("status.json", {}) or {}
        self.rf.status(sends_reserved_for_tail=max(0, int(st.get("sends_reserved_for_tail", 0)) - 1))
        saved = self.ask_seat("VERIFIER", p7, stage_dir="final", stage_label="VERIFY", save_as="final/verifier.md", packet_file="final/packet-verify.md",
                              required_headings=parse.REPLY_HEADINGS["verifier"],
                              reprompt_line="Use exactly these headings: CONTRADICTIONS, CONFIRMED, NOT COVERED, MATERIAL OMISSIONS.")
        if saved is None:
            self.rf.add_flag("NO_VERIFIER")
            return
        if parse.verifier_items(saved.text).get("CONTRADICTIONS"):
            self.rf.add_flag("PROVISIONAL")
            self.log("DISPATCH", "provisional", result="verifier CONTRADICTION: PROVISIONAL", stage="VERIFY")
        self.rf.write_once("final/DELIVERABLE_ASSEMBLED.md", assemble.assembled(d, saved.text), stage="DELIVER")
        self.status("VERIFY", "assembled", "DELIVER", last_complete="final/DELIVERABLE_ASSEMBLED.md")

    # ------------------------------------------------------------------ 3.9 deliver
    def deliver(self):
        import json
        if self.rf.exists("ledger.json"):
            return
        self.begin_stage("DELIVER")
        st = self.rf.read_json("status.json", {}) or {}
        stages = self.rf.stages()
        lc = self.last_close()
        metrics = self.rf.read_jsonl("metrics.jsonl")
        earned = sum(int(m.get("earned_kills", 0) or 0) for m in metrics)
        depri = max([int(m.get("deprioritized", 0) or 0) for m in metrics] or [0])
        rc = parse.parse_claims(self.rf.read("review/check-review.md")) if self.rf.exists("review/check-review.md") else []
        ver = parse.verifier_items(self.rf.read("final/verifier.md")) if self.rf.exists("final/verifier.md") else {}
        checks_all_passed = all(c["result"] == "PASSED" for s in stages if self.rf.exists(f"{s}/check.md") for c in parse.parse_claims(self.rf.read(f"{s}/check.md")))
        open_lines = self.open_text().splitlines()
        for f in classify.derived_flags(deprioritized=depri, earned=earned, open_lines=open_lines, all_checks_passed=checks_all_passed, has_stage=bool(stages)):
            self.rf.add_flag(f)
        flags = classify.assert_known(self.rf.flags())
        # the deliverable's classification word is what the ledger records (CLASS-3)
        d = self.rf.read("final/DELIVERABLE.md")
        words = parse.classification_words(d)
        classification = words[0] if words else self.compute_classification()
        led = assemble.ledger(self.rf, class_=self.gate["class"], profile=self.gate["profile"],
                              stages=[s.split("-", 2)[2].upper() for s in stages] + (["EXPERIMENT"] if "EXPERIMENT" in self.ops_run else []),
                              stop_reason=st.get("stop_reason") or ("" if self.gate["class"] == "DIRECT" else "EXHAUSTED"),
                              options_created=len(self.list_options()), options_standing=len(self.current_standing_lines()), earned=earned, deprioritized=depri,
                              review_hits_passed=sum(1 for c in rc if c["id"].startswith("H") and c["result"] == "PASSED"),
                              review_hits_failed=sum(1 for c in rc if c["id"].startswith("H") and c["result"] == "FAILED"),
                              holds_accepted=len(re.findall(r"HOLD-ACCEPTED", self.rf.read("review/check-review.md"))) if rc else 0,
                              verifier_contradictions=len(ver.get("CONTRADICTIONS", [])), verifier_confirmed=len(ver.get("CONFIRMED", [])),
                              seats_failed=sorted(self.seats_failed), closer_swaps=self.closer_swaps, model_calls=int(st.get("sends_used", 0)),
                              elapsed_s=0, flags=flags, classification=classification,
                              next_question=(parse.deliverable_sections(d).get("12 NEXT QUESTION", "").strip().splitlines() or [""])[0])
        self.rf.write_once("ledger.json", json.dumps(led, indent=1), stage="DELIVER")
        assemble.architecture_lines(self.root, led, self.rf.clock.iso()[:10], len(self.ready_generators()))
        self.rf.status(stage="DONE", step="deliver", next="none", last_complete="ledger.json")

    # ------------------------------------------------------------------ run
    def run(self) -> int:
        try:
            self.init()
            self.registry_stage()
            self.gate_stage()
            cls = self.gate["class"]
            if cls == "DIRECT":
                self.direct()
            elif cls == "EXPERIMENT":
                from . import experiments
                experiments.run_class(self)
            else:
                self.evidence_engine()
            self.review()
            self.final()
            self.verify()
            self.deliver()
            return 0
        except NightStop as e:
            self.rf.status(stage="PARTIAL", step="stopped", next="none", stop_reason=e.reason)
            if not self.rf.exists("NOTE.md"):
                self.rf.write_once("NOTE.md", f"STOP_REASON {e.reason}\n{e.note}\n", stage="PARTIAL")
            self.log("DISPATCH", "stop", result=f"{e.reason}: {e.note}"[:300])
            return 3
        except StopAfter as e:
            self.log("DISPATCH", "stop-after", result=f"test hook: stopped once {e} existed")
            return 5
        except guard.Blocked as e:
            self.rf.status(stage="PARTIAL", step="blocked", next="none", stop_reason="ABORT")
            if not self.rf.exists("NOTE.md"):
                self.rf.write_once("NOTE.md", f"BLOCK {e.stage}\n" + "\n".join(e.reasons) + "\n", stage="PARTIAL")
            return 4
