"""
watcher.py
==========
Drop a file in, get a deliverable back. Unattended.

macOS, not WSL2. The spec this came from prescribed polling because
filesystem notifications do not cross the Windows/WSL `/mnt/c` boundary. That
problem does not exist here, but polling is kept anyway for a different and
better reason: it needs no dependency, it cannot miss an event it was not
watching for, and its failure mode is "slow" rather than "silently stopped".
An event-driven watcher that dies leaves no trace; a poll loop that dies
stops updating a file you can look at.

DEBOUNCE, BECAUSE A SYNCING FILE IS NOT A FINISHED FILE. A file must be
unchanged in size and mtime across two consecutive polls before it is picked
up. Reading a Dropbox or iCloud file mid-write yields a truncated ask, and a
truncated ask produces a confident answer to half a question.

IT WILL NOT START WITHOUT A CEILING. This is the one component that spends
money with nobody watching, so the ceiling is a precondition rather than an
option. A watcher under no limit is an open-ended bill with a folder for an
interface.

FILES MOVE, THEY ARE NEVER DELETED. inbox -> processing -> done. A crash
leaves the file in processing/, which is where you look, and nothing is ever
destroyed by a run that went wrong.
"""
from __future__ import annotations

import math
import os
import shutil
import time
import traceback
from dataclasses import dataclass
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))

POLL_SECONDS = 10.0
STABLE_POLLS = 2
"""Consecutive unchanged observations required before a file is read."""


@dataclass
class Folders:
    inbox: str
    processing: str
    done: str
    failed: str
    runs: str

    @classmethod
    def under(cls, root: str) -> Folders:
        """The five folders, each a real directory directly under root.

        SYMLINKS ARE REFUSED, and this is not hypothetical tidiness. With
        failed/ symlinked to inbox/, a run that failed and cost money was
        moved to "failed" and reappeared in the inbox on the next poll --
        re-running, re-paying, and failing again, all night. The whole reason
        failed/ is a separate folder is that a deterministic failure must not
        be retried, and one symlink silently removes that.
        """
        real_root = os.path.realpath(root)
        f = cls(os.path.join(real_root, "inbox"),
                os.path.join(real_root, "processing"),
                os.path.join(real_root, "done"),
                os.path.join(real_root, "failed"),
                os.path.join(real_root, "runs"))
        for d in (f.inbox, f.processing, f.done, f.failed, f.runs):
            if os.path.islink(d):
                raise ValueError(
                    f"{d} is a symlink. The watcher's folders must be real "
                    f"directories: with failed/ pointing at inbox/, a run that "
                    f"failed and cost money reappears in the inbox and is paid "
                    f"for again on every poll."
                )
            os.makedirs(d, exist_ok=True)
        seen: dict[str, str] = {}
        for d in (f.inbox, f.processing, f.done, f.failed, f.runs):
            real = os.path.realpath(d)
            if real in seen:
                raise ValueError(
                    f"{d} and {seen[real]} resolve to the same directory "
                    f"({real}). Each stage must be distinct or a file cannot "
                    f"move out of one."
                )
            if os.path.dirname(real) != real_root:
                raise ValueError(
                    f"{d} resolves to {real}, which is not directly under "
                    f"{real_root}"
                )
            seen[real] = d
        return f


def _stamp(path: str) -> tuple[int, float] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_size, st.st_mtime


def candidates(inbox: str) -> list[str]:
    """Files whose first line starts with Q:. Everything else is ignored.

    A marker rather than an extension, so a stray screenshot or a synced
    conflict copy landing in the folder cannot start a paid run.
    """
    out = []
    for name in sorted(os.listdir(inbox)):
        if not name.lower().endswith((".md", ".txt")) or name.startswith("."):
            continue
        p = os.path.join(inbox, name)
        if os.path.islink(p):
            # A symlink in the inbox points at content nobody put there. It
            # was followed, and whatever it named became the paid ask.
            continue
        if not os.path.isfile(p):
            continue
        if os.path.dirname(os.path.realpath(p)) != os.path.realpath(inbox):
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                first = fh.readline().strip()
        except OSError:
            continue
        if first.upper().startswith("Q:"):
            out.append(p)
    return out


def wait_until_stable(path: str, polls: int = STABLE_POLLS,
                      interval: float = POLL_SECONDS) -> bool:
    """True once size and mtime hold steady. False if the file vanishes."""
    last = _stamp(path)
    if last is None:
        return False
    steady = 0
    while steady < polls:
        time.sleep(interval)
        now = _stamp(path)
        if now is None:
            return False
        if now == last:
            steady += 1
        else:
            steady, last = 0, now
    return True


def read_ask(path: str) -> str:
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    first, _, rest = text.partition("\n")
    return (first.split(":", 1)[1].strip() + "\n" + rest).strip()


MIN_ASK_CHARS = 20
"""Shortest ask worth paying five models to answer.

A file caught mid-write can hold a plausible-looking fragment -- "Q: should
we" -- that debounce cannot distinguish from a finished short question. Two
unchanged observations prove the writer PAUSED, not that it finished.
"""


def _rejects_claimed_file(path: str, ask: str) -> str | None:
    """Why this claimed file must not be paid for, or None.

    Re-validated on the SNAPSHOT WE CLAIMED rather than on what was seen in
    the inbox. The marker check happened before the debounce and was never
    repeated, so a file edited during the debounce window was paid for on
    content the operator had already withdrawn.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
    except OSError as exc:
        return f"could not be read after claiming it: {exc}"
    if not first.upper().startswith("Q:"):
        return (f"first line is {first[:60]!r}, not a Q: marker. It was "
                f"marked when the folder was scanned and is not now, so it "
                f"was edited between the scan and the run.")
    if len(ask.strip()) < MIN_ASK_CHARS:
        return (f"the ask is {len(ask.strip())} characters, below the "
                f"{MIN_ASK_CHARS}-character minimum. A file caught mid-write "
                f"holds a fragment that debounce cannot tell from a finished "
                f"short question, and five models would be paid to answer it.")
    return None


def process(path: str, folders: Folders, max_cost: float,
            profiles_path: str) -> str:
    """One file, start to finish. Returns the run directory."""
    name = os.path.basename(path)
    working = os.path.join(folders.processing, name)

    # CLAIM THE FILE FIRST, THEN VALIDATE WHAT WE CLAIMED.
    #
    # The Q: marker was checked in the inbox, before the debounce, and never
    # revalidated. Changing "Q:" to "N:" during the debounce window therefore
    # produced a paid run on content the operator had just withdrawn, because
    # the decision was made against a snapshot nobody kept. os.rename is
    # atomic within a filesystem, so moving the file out of the inbox is what
    # makes the content stop changing under us -- everything after this reads
    # one immutable snapshot, and that snapshot is what gets paid for.
    shutil.move(path, working)

    from cost_ledger import CeilingReached
    from night_loop import live_night
    from run_adjudication import build_ledger

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = os.path.join(folders.runs, f"{stamp}-{os.path.splitext(name)[0][:40]}")

    ask = read_ask(working)
    reason = _rejects_claimed_file(working, ask)
    if reason is not None:
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "REJECTED.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# Not run\n\n{reason}\n")
        shutil.move(working, os.path.join(folders.failed, name))
        return out

    ledger = build_ledger(max_cost, None, None)
    try:
        live_night(ask, profiles_path, out, ledger=ledger)
        shutil.move(working, os.path.join(folders.done, name))
    except CeilingReached as exc:
        # A ceiling is a clean stop, not a fault. The partial run is on disk.
        #
        # makedirs FIRST. live_night creates the run directory, so a ceiling
        # reached on the very first call -- before it got that far -- left no
        # directory to write PARTIAL.md into. The open() then raised
        # FileNotFoundError from INSIDE this handler, where the sibling
        # except cannot catch it, so process() propagated, the input was
        # stranded in processing/ (neither done nor failed), and the exception
        # unwound watch()'s loop and killed the watcher outright. One run
        # hitting its ceiling stopped every later file in the inbox, overnight,
        # with nobody awake to see it.
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "PARTIAL.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# PARTIAL\n\n{exc}\n")
        shutil.move(working, os.path.join(folders.done, name))
    except Exception:  # noqa: BLE001 - one bad file must not stop the watcher
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "ERROR.md"), "w", encoding="utf-8") as fh:
            fh.write("# Run failed\n\n```\n" + traceback.format_exc() + "\n```\n")
        # failed/, not back to inbox. Returning it would re-run it on the next
        # poll, and a file that fails deterministically would spend money in a
        # loop all night.
        shutil.move(working, os.path.join(folders.failed, name))
    finally:
        # WHAT IT COST, ON EVERY PATH. Written in finally because the runs
        # that most need a cost record are the ones that ended badly: a
        # ceiling stop and a crash both spent money, and neither wrote a
        # figure anywhere the operator would find it in the morning.
        os.makedirs(out, exist_ok=True)
        body = ("\n".join(ledger.render()) if ledger is not None else
                "  no ledger was built, so nothing was measured. Treat the "
                "cost of this run as UNKNOWN, not as zero.")
        with open(os.path.join(out, "COST.md"), "w", encoding="utf-8") as fh:
            fh.write("# Cost\n\n```\n" + body + "\n```\n")
    return out


def watch(root: str, max_cost: float, profiles_path: str | None = None,
          interval: float = POLL_SECONDS, once: bool = False) -> None:
    # NaN fails EVERY comparison, so `max_cost <= 0` was False for it and a
    # NaN ceiling sailed through. Every later comparison against it is also
    # False, which means no ceiling is ever reached: the operator asked for a
    # limit, saw "ceiling $nan per run" printed back, and got none.
    if (max_cost is None or not isinstance(max_cost, (int, float))
            or isinstance(max_cost, bool)
            or not math.isfinite(float(max_cost)) or float(max_cost) <= 0):
        raise ValueError(
            "a watcher needs a spend ceiling. It is the one component that "
            "spends with nobody watching, and without a limit it is an "
            "open-ended bill with a folder for an interface. "
            f"Got {max_cost!r}, which is not a finite positive number of "
            f"dollars."
        )
    profiles_path = profiles_path or os.path.join(HERE, "profiles.json")
    folders = Folders.under(root)
    print(f"watching {folders.inbox}")
    print(f"  ceiling ${max_cost:.2f} per run   poll {interval:.0f}s   "
          f"debounce {STABLE_POLLS} polls")
    print("  a file starts a run only if its FIRST LINE begins with 'Q:'")
    while True:
        try:
            found = candidates(folders.inbox)
        except OSError as exc:
            # The SCAN itself sat outside the backstop, so a single transient
            # listdir failure ended the loop. A watcher that has silently
            # stopped looks exactly like a watcher with an empty inbox, and
            # every later file waits forever.
            print(f"  could not scan {folders.inbox}: {exc}")
            found = []
        for path in found:
            print(f"\n[{datetime.now():%H:%M:%S}] seen {os.path.basename(path)}")
            try:
                stable = wait_until_stable(path, interval=interval)
            except OSError as exc:
                print(f"  could not stat it ({exc}); leaving it")
                continue
            if not stable:
                print("  vanished or still changing; leaving it")
                continue
            print("  stable; starting")
            try:
                out = process(path, folders, max_cost, profiles_path)
                print(f"  done -> {out}")
            except Exception as exc:  # noqa: BLE001
                # process() is written not to raise. This is the backstop, and
                # it exists because the failure it guards against is the worst
                # one this component has: an exception here ends the loop, and
                # a watcher that has silently stopped looks exactly like a
                # watcher with an empty inbox. Every later file waits forever.
                print(f"  UNHANDLED {type(exc).__name__}: {exc}")
                print(f"  {os.path.basename(path)} may be stranded in "
                      f"{folders.processing}; the watcher is still running")
        if once:
            return
        time.sleep(interval)


if __name__ == "__main__":  # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser(description="Folder-triggered night runs.")
    ap.add_argument("root", help="folder holding inbox/ processing/ done/")
    ap.add_argument("--max-cost", type=float, required=True,
                    help="hard per-run ceiling in dollars. Required.")
    ap.add_argument("--poll", type=float, default=POLL_SECONDS)
    ap.add_argument("--once", action="store_true",
                    help="scan once and exit, for testing")
    a = ap.parse_args()
    watch(a.root, a.max_cost, interval=a.poll, once=a.once)
