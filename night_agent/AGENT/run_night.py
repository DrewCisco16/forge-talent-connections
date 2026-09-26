#!/usr/bin/env python3
"""Night Agent v11.4 SDK runtime: run one night.

    python3 AGENT/run_night.py <root> --ask ask.md [--seats live|fake] [--model ID] [--model-SEAT ID]
        [--resume runs/na-NNN] [--documents DIR] [--sandbox DIR] [--hard-stop HH:MM] [--max-wait-min N]
        [--net on|off] [--fault Bn[:seat[:stage]]] [--profile adaptive|v10-fixed] [--stop-after FILE]

<root> holds runs/na-NNN/ and architecture/. Live is the default and needs ANTHROPIC_API_KEY in the environment
plus the claude-agent-sdk package; without a key the run exits 2 and never falls back to fake seats silently.
--seats fake runs deterministic seats with provider fake for rehearsal and CI; its deliverable is never a result.
Exit 0: DONE. 2: cannot start. 3: stopped with a labelled STOP_REASON (NOTE.md). 4: a guard blocked.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from AGENT import RUNTIME_VERSION, schema_version  # noqa: E402
from AGENT.check import engine, sources  # noqa: E402
from AGENT.config import RunConfig, default_seats, load_schema  # noqa: E402
from AGENT.records import Clock, RunFolder, next_run_id  # noqa: E402
from AGENT.stages import Night  # noqa: E402


ONE_SHOT = {"B2", "B8"}  # a single bad reply; the retry the spec allows then succeeds


def parse_faults(items):
    out = {}
    for it in items or []:
        parts = it.split(":")
        code = parts[0]
        out[code] = {"seat": parts[1] if len(parts) > 1 and parts[1] else None, "stage": parts[2] if len(parts) > 2 else None,
                     "once": code in ONE_SHOT or (len(parts) > 3 and parts[3] == "once")}
    return out


def build_crew(cfg, specs):
    crew = {}
    if cfg.seats_mode == "fake":
        from AGENT.seats.fake_seat import FakeSeat, LocalExecutor
        world = {}
        for s in specs:
            crew[s.id] = LocalExecutor(s, cfg.sandbox_dir) if s.role == "executor" else FakeSeat(s, cfg.faults, world)
        return crew
    from AGENT.seats.sdk_seat import SDKExecutorSeat, SDKTextSeat
    for s in specs:
        crew[s.id] = SDKExecutorSeat(s, cfg) if s.role == "executor" else SDKTextSeat(s, cfg)
    return crew


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--ask", help="ask.md to copy into the run (required unless --resume)")
    ap.add_argument("--seats", choices=["live", "fake"], default="live")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--model-seat", action="append", default=[], metavar="SEAT=MODEL")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--resume")
    ap.add_argument("--documents")
    ap.add_argument("--sandbox")
    ap.add_argument("--hard-stop")
    ap.add_argument("--max-wait-min", type=float, default=10.0)
    ap.add_argument("--net", choices=["on", "off"], default="on")
    ap.add_argument("--fault", action="append", default=[])
    ap.add_argument("--profile", choices=["adaptive", "v10-fixed"])
    ap.add_argument("--stop-after")
    ap.add_argument("--generators", type=int, default=4)
    ap.add_argument("--dois", help="fixture DOI records (json) for --net off or fake mode")
    ap.add_argument("--fixed-clock", help="test hook: ISO timestamp for every record")
    ap.add_argument("--cli", help="path to the claude binary for the SDK")
    a = ap.parse_args(argv)

    if schema_version() != RUNTIME_VERSION:
        print(f"runtime {RUNTIME_VERSION} does not match SCHEMA {schema_version()}", file=sys.stderr)
        return 2
    cfg = RunConfig(root=os.path.abspath(a.root), ask_path=a.ask or "", seats_mode=a.seats, model=a.model,
                    model_overrides=dict(x.split("=", 1) for x in a.model_seat), effort=a.effort,
                    documents_dir=os.path.abspath(a.documents) if a.documents else None,
                    sandbox_dir=os.path.abspath(a.sandbox) if a.sandbox else None, hard_stop=a.hard_stop,
                    max_wait_s=a.max_wait_min * 60, net=a.net == "on", faults=parse_faults(a.fault), profile=a.profile,
                    resume=a.resume, stop_after=a.stop_after, generators=a.generators, fixed_clock=a.fixed_clock, cli_path=a.cli)
    if cfg.seats_mode == "live" and not os.environ.get("ANTHROPIC_API_KEY"):
        print("live seats need ANTHROPIC_API_KEY in the environment (the SDK does not read .env). Use --seats fake for a rehearsal.", file=sys.stderr)
        return 2
    if cfg.seats_mode == "live":
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError:
            print("live seats need the claude-agent-sdk package: pip install -r AGENT/requirements.txt", file=sys.stderr)
            return 2

    os.makedirs(os.path.join(cfg.root, "architecture"), exist_ok=True)
    run_id = os.path.basename(a.resume.rstrip("/")) if a.resume else next_run_id(cfg.root)
    run_dir = os.path.join(cfg.root, "runs", run_id)
    rf = RunFolder(run_dir, run_id, Clock(cfg.fixed_clock))
    if not rf.exists("ask.md"):
        if not a.ask:
            print("--ask is required for a new run", file=sys.stderr)
            return 2
        with open(a.ask, encoding="utf-8") as f:
            rf.write_once("ask.md", f.read(), seat="OP", action="write")
    specs = {s.id: s for s in default_seats(cfg)}
    crew = build_crew(cfg, list(specs.values()))
    if cfg.seats_mode == "fake" or not cfg.net:
        resolver = sources.FixtureResolver(a.dois) if a.dois else (sources.FixtureResolver(os.path.join(cfg.documents_dir, "dois.json"))
                                                                    if cfg.documents_dir and os.path.exists(os.path.join(cfg.documents_dir, "dois.json"))
                                                                    else sources.OfflineResolver())
    else:
        resolver = sources.CrossrefResolver()
    ctx = engine.CheckContext(documents_dir=cfg.documents_dir, resolver=resolver, executor=crew.get("EXECUTOR"),
                              allowed_commands=[], now=rf.clock.iso())
    night = Night(cfg, rf, specs, crew, ctx, load_schema(), cfg.root)
    # command checks may run only the gate's procedures (DISPATCH 9): filled in once the gate exists
    night.ctx.allowed_commands = []
    if cfg.stop_after:
        night.stop_after = cfg.stop_after
    rc = night.run()
    st = rf.read_json("status.json", {}) or {}
    print(f"{run_id}: stage {st.get('stage')} stop_reason {st.get('stop_reason')} flags {st.get('flags')} sends {st.get('sends_used')}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
