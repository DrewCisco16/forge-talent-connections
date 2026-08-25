"""
test_operator_surface.py — the watcher, the domain profiles, the harness.

WHY THIS FILE EXISTS. watcher.py is the one component that spends money with
nobody watching, and it was at 0% coverage. Every branch in it is a decision
about whether to start a paid run or move a file somewhere it will never be
retried, taken while the operator is asleep.

domains.py is data, but it is data that selects which GATES run. A malformed
entry does not crash -- it silently produces a run with fewer checks.
"""
from __future__ import annotations

import os

import pytest

import domains as D
import validation_harness as VH
import watcher as W

NEVER_OPENED = "/nonexistent/settings-that-must-not-be-read.json"
"""A settings path these tests hand to the watcher and nothing ever opens.

live_night is monkeypatched in every test below, so the path is carried and
discarded. It used to read "profiles.json" -- the OPERATOR's real settings
file, gitignored because it holds live endpoints beside live keys. Nothing
opened it, but naming it invited the next change to, and a test that reaches
an untracked local file is a test of that machine. A path that cannot exist
fails loudly if anything ever does open it.
"""

# ===========================================================================
# the watcher: what may start a paid run
# ===========================================================================

def _inbox(tmp_path, name, text):
    f = W.Folders.under(str(tmp_path))
    p = os.path.join(f.inbox, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)
    return f, p


class TestOnlyADeliberateFileStartsARun:

    def test_a_file_marked_with_q_is_picked_up(self, tmp_path):
        f, _ = _inbox(tmp_path, "ask.md", "Q: should we build or buy?\n\ndetail")
        assert len(W.candidates(f.inbox)) == 1

    def test_an_unmarked_file_is_ignored(self, tmp_path):
        """A marker rather than an extension, so a stray note, a screenshot, or
        a cloud-sync conflict copy landing in the folder cannot spend money."""
        f, _ = _inbox(tmp_path, "notes.md", "just some notes I dropped here")
        assert W.candidates(f.inbox) == []

    def test_a_sync_conflict_copy_without_the_marker_is_ignored(self, tmp_path):
        f, _ = _inbox(tmp_path, "ask (conflicted copy).md", "Q was the old text")
        assert W.candidates(f.inbox) == []

    def test_the_marker_is_case_insensitive(self, tmp_path):
        f, _ = _inbox(tmp_path, "ask.md", "q: lowercase marker\n")
        assert len(W.candidates(f.inbox)) == 1

    def test_a_dotfile_is_ignored(self, tmp_path):
        f, _ = _inbox(tmp_path, ".hidden.md", "Q: sneaky\n")
        assert W.candidates(f.inbox) == []

    def test_a_wrong_extension_is_ignored(self, tmp_path):
        f, _ = _inbox(tmp_path, "ask.pdf", "Q: not plain text\n")
        assert W.candidates(f.inbox) == []

    def test_a_directory_is_never_a_candidate(self, tmp_path):
        f = W.Folders.under(str(tmp_path))
        os.makedirs(os.path.join(f.inbox, "subdir.md"))
        assert W.candidates(f.inbox) == []

    def test_the_marker_line_is_stripped_from_the_ask(self, tmp_path):
        _, p = _inbox(tmp_path, "ask.md", "Q: build or buy?\n\nmore context here")
        got = W.read_ask(p)
        assert got.startswith("build or buy?")
        assert "more context here" in got
        assert not got.startswith("Q:")

    def test_candidates_are_returned_in_a_stable_order(self, tmp_path):
        f = W.Folders.under(str(tmp_path))
        for n in ("c.md", "a.md", "b.md"):
            with open(os.path.join(f.inbox, n), "w") as fh:
                fh.write("Q: should we build the ingest service or buy one?\n")
        assert [os.path.basename(p) for p in W.candidates(f.inbox)] == \
            ["a.md", "b.md", "c.md"]


class TestTheFileMustStopChangingBeforeItIsRead:

    def test_a_steady_file_is_stable(self, tmp_path):
        _, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")
        assert W.wait_until_stable(p, polls=1, interval=0.0) is True

    def test_a_vanished_file_is_not_stable(self, tmp_path):
        """A file removed mid-debounce must not start a run against a path
        that no longer exists."""
        _, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")
        os.remove(p)
        assert W.wait_until_stable(p, polls=1, interval=0.0) is False

    def test_a_file_still_being_written_resets_the_count(self, tmp_path, monkeypatch):
        """Reading a half-synced file would send a truncated question to five
        paid models."""
        _, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")
        seq = iter([(10, 1.0), (20, 2.0), (30, 3.0), (30, 3.0), (30, 3.0)])
        monkeypatch.setattr(W, "_stamp", lambda _p: next(seq, (30, 3.0)))
        assert W.wait_until_stable(p, polls=2, interval=0.0) is True


class TestTheWatcherRefusesToRunUnbounded:

    def test_no_ceiling_is_refused(self, tmp_path):
        """The one component that spends with nobody watching. Without a limit
        it is an open-ended bill with a folder for an interface.

        The path is a real temporary directory rather than a literal /tmp one:
        watch() must raise before touching the filesystem, and a hardcoded
        /tmp path would still be wrong if it ever stopped doing so."""
        for bad in (None, 0, -1.0):
            with pytest.raises(ValueError, match="spend ceiling"):
                W.watch(str(tmp_path / "never-created"), bad, once=True)
        assert not (tmp_path / "never-created").exists(), (
            "the ceiling was checked after the folders were made")

    def test_a_ceiling_is_accepted(self, tmp_path):
        W.watch(str(tmp_path), 1.0, interval=0.0, once=True)
        assert os.path.isdir(os.path.join(str(tmp_path), "inbox"))


class TestWhereAFileEndsUp:

    def _folders(self, tmp_path):
        return W.Folders.under(str(tmp_path))

    def test_a_successful_run_moves_the_file_to_done(self, tmp_path, monkeypatch):
        f, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: [])
        W.process(p, f, 1.0, NEVER_OPENED)
        assert os.path.exists(os.path.join(f.done, "ask.md"))
        assert not os.path.exists(p)

    def test_a_ceiling_is_a_clean_stop_not_a_failure(self, tmp_path, monkeypatch):
        """The partial run is on disk and was paid for. Filing it as failed
        would invite a re-run that pays for the same rounds again."""
        from cost_ledger import CeilingReached

        f, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")

        def broke(*_a, **_k):
            raise CeilingReached("per-run", 3.0, 3.0, 0.5)
        monkeypatch.setattr("night_loop.live_night", broke)
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert os.path.exists(os.path.join(f.done, "ask.md"))
        with open(os.path.join(out, "PARTIAL.md")) as fh:
            assert "PARTIAL" in fh.read()

    def test_a_crash_files_it_as_failed_and_keeps_the_traceback(self, tmp_path,
                                                               monkeypatch):
        f, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")

        def boom(*_a, **_k):
            raise RuntimeError("the panel exploded")
        monkeypatch.setattr("night_loop.live_night", boom)
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert os.path.exists(os.path.join(f.failed, "ask.md"))
        with open(os.path.join(out, "ERROR.md")) as fh:
            assert "the panel exploded" in fh.read()

    def test_a_failed_file_is_not_returned_to_the_inbox(self, tmp_path,
                                                       monkeypatch):
        """A file that fails deterministically would be re-run on every poll
        and spend money in a loop all night."""
        f, p = _inbox(tmp_path, "ask.md", "Q: should we build the ingest service or buy one?\n")
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
        W.process(p, f, 1.0, NEVER_OPENED)
        assert W.candidates(f.inbox) == []

    def test_one_bad_file_does_not_stop_the_watcher(self, tmp_path, monkeypatch):
        f = W.Folders.under(str(tmp_path))
        for n in ("bad.md", "good.md"):
            with open(os.path.join(f.inbox, n), "w") as fh:
                fh.write("Q: should we build the ingest service or buy one?\n")
        seen = []

        def sometimes(ask, profiles, out, **_k):
            seen.append(out)
            if len(seen) == 1:
                raise RuntimeError("first one fails")
            return []
        monkeypatch.setattr("night_loop.live_night", sometimes)
        W.watch(str(tmp_path), 1.0, interval=0.0, once=True)
        assert len(seen) == 2, "the watcher stopped at the first failure"


# ===========================================================================
# domain profiles: data that selects which gates run
# ===========================================================================

class TestTheDomainProfiles:

    def test_every_domain_is_reachable_by_its_key(self):
        assert set(D.BY_KEY) == {d.key for d in D.ALL}
        assert len(D.ALL) == 6

    def test_keys_are_unique(self):
        """A duplicate key silently shadows a profile, so one domain would
        quietly run another's gates."""
        keys = [d.key for d in D.ALL]
        assert len(keys) == len(set(keys))

    def test_every_domain_names_at_least_one_gate(self):
        """A domain with no gates produces a run where nothing is checked and
        every claim escalates -- a panel that cannot eliminate anything."""
        for d in D.ALL:
            assert d.gates, d.key

    def test_every_named_gate_is_one_the_engine_can_build(self):
        """A typo here does not crash. It silently produces a run with fewer
        checks than the profile advertises -- claims quietly unchecked."""
        from run_adjudication import _SELECTABLE_GATES
        for d in D.ALL:
            for g in d.gates:
                assert g in _SELECTABLE_GATES, (
                    f"{d.key} names gate {g!r}, which the engine cannot build. "
                    f"Buildable: {', '.join(sorted(_SELECTABLE_GATES))}")

    def test_every_buildable_gate_actually_builds(self):
        """A registry entry whose factory raises is a gate an operator can
        select and never get."""
        from run_adjudication import _SELECTABLE_GATES
        for name, factory in _SELECTABLE_GATES.items():
            gate = factory()
            assert hasattr(gate, "check"), name
            assert hasattr(gate, "applies_to"), name

    def test_every_primary_claim_kind_is_a_real_kind(self):
        from adjudication_orchestrator import ClaimKind
        valid = {k.value for k in ClaimKind}
        for d in D.ALL:
            for k in d.primary_claim_kinds:
                assert k in valid, f"{d.key} names unknown claim kind {k!r}"

    def test_every_domain_has_operator_facing_text(self):
        """These strings are the entire interface for someone formulating a
        problem. A blank one leaves them guessing what to type."""
        for d in D.ALL:
            for fieldname in ("title", "blurb", "artifact_is", "candidate_is"):
                assert getattr(d, fieldname).strip(), f"{d.key}.{fieldname}"
            assert d.artifact_examples and d.candidate_examples, d.key

    def test_a_red_gated_domain_carries_its_prompt(self):
        """A refusal with no explanation reads as a bug and gets worked around."""
        for d in D.ALL:
            if d.red_gate:
                assert d.red_prompt.strip(), d.key

    def test_the_patent_domain_is_red_gated(self):
        """Claim content and prosecution strategy must never reach a panel of
        third-party model vendors."""
        assert D.BY_KEY["patent"].red_gate is True


# ===========================================================================
# validation harness
# ===========================================================================

class TestTheValidationHarness:
    """The harness that proves the statistics on seats with KNOWN behaviour.

    It exists so the capture-recapture maths can be checked against ground
    truth, which no live run can provide: on a real panel nobody knows what
    the seats missed.
    """

    def _prompt(self, pass_index=0):
        import adjudication_orchestrator as AO
        return f"## Lens\n{AO.DEFAULT_PASSES[pass_index].name}\n\nbody"

    def test_a_seat_reports_only_the_defects_assigned_to_this_pass(self):
        """A seat that reported every defect on every pass would make the
        per-pass yield curve meaningless."""
        seat = VH.make_seat(set(VH.SEEDED))
        first = seat(self._prompt(0))
        second = seat(self._prompt(1))
        assert first != second

    def test_a_seat_that_catches_nothing_returns_no_claims(self):
        assert VH.make_seat(set())(self._prompt(0)).strip() == ""

    def test_a_seat_emits_parseable_claim_lines(self):
        """The harness must exercise the same extractor the live path uses, or
        it validates a pipeline nobody runs."""
        import adjudication_orchestrator as AO
        out = VH.make_seat(set(VH.SEEDED))(self._prompt(0))
        if out.strip():
            claims = AO.line_claim_extractor(out, "seat_1", "p1")
            assert claims

    def test_the_harness_runs_end_to_end_and_returns_an_orchestrator(self, capsys):
        orch = VH.run("demo", {"seat_1": set(VH.SEEDED), "seat_2": set(VH.SEEDED)})
        assert orch.verdicts or orch.escalation_queue


class TestTheWatcherCeilingMustBeARealNumber:
    """Codex H5. NaN fails EVERY comparison, so `max_cost <= 0` was False for
    it and a NaN ceiling sailed through. Every later comparison against it is
    also False, so no ceiling is ever reached: the operator asked for a limit,
    saw "ceiling $nan per run" printed back, and got none.
    """

    def test_a_nonfinite_ceiling_is_refused(self, tmp_path):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError, match="spend ceiling"):
                W.watch(str(tmp_path / "n"), bad, once=True)

    def test_a_non_numeric_ceiling_is_refused(self, tmp_path):
        for bad in ("5.00", None, [], True):
            with pytest.raises(ValueError, match="spend ceiling"):
                W.watch(str(tmp_path / "n"), bad, once=True)

    def test_the_refusal_names_what_it_got(self, tmp_path):
        """'A watcher needs a ceiling' when the operator supplied one reads as
        a bug in the tool rather than a problem with their value."""
        with pytest.raises(ValueError, match="not a finite positive number"):
            W.watch(str(tmp_path / "n"), float("nan"), once=True)

    def test_nothing_is_created_before_the_ceiling_is_validated(self, tmp_path):
        root = tmp_path / "never"
        with pytest.raises(ValueError):
            W.watch(str(root), float("nan"), once=True)
        assert not root.exists()

    def test_a_real_ceiling_is_still_accepted(self, tmp_path):
        W.watch(str(tmp_path / "ok"), 1.50, interval=0.0, once=True)
        assert (tmp_path / "ok" / "inbox").is_dir()


class TestTheWatcherClaimsItsInputBeforePaying:
    """Codex H14. The Q: marker was checked in the inbox, before the debounce,
    and never revalidated. Two unchanged size and mtime observations prove the
    writer PAUSED, not that it finished."""

    def _folders(self, tmp_path):
        return W.Folders.under(str(tmp_path))

    def _write(self, folders, name, text):
        p = os.path.join(folders.inbox, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def test_a_marker_removed_during_debounce_is_not_paid_for(
            self, tmp_path, monkeypatch):
        """The operator withdrew it. The decision had been made against a
        snapshot nobody kept."""
        f = self._folders(tmp_path)
        p = self._write(f, "ask.md", "N: actually never mind, withdrawn\n\nbody")
        called = {"n": 0}
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: called.__setitem__("n", 1) or [])
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert called["n"] == 0, "a withdrawn file was paid for"
        assert os.path.exists(os.path.join(f.failed, "ask.md"))
        with open(os.path.join(out, "REJECTED.md")) as fh:
            assert "not a Q: marker" in fh.read()

    def test_a_half_written_ask_is_not_paid_for(self, tmp_path, monkeypatch):
        """A file caught mid-write holds a fragment that debounce cannot tell
        from a finished short question, and five models would be paid for it."""
        f = self._folders(tmp_path)
        p = self._write(f, "ask.md", "Q: should we\n")
        called = {"n": 0}
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: called.__setitem__("n", 1) or [])
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert called["n"] == 0
        with open(os.path.join(out, "REJECTED.md")) as fh:
            assert "mid-write" in fh.read()

    def test_a_complete_ask_still_runs(self, tmp_path, monkeypatch):
        f = self._folders(tmp_path)
        p = self._write(f, "ask.md",
                        "Q: should we build the ingest service or buy one?\n")
        called = {"n": 0}
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: called.__setitem__("n", 1) or [])
        W.process(p, f, 1.0, NEVER_OPENED)
        assert called["n"] == 1


class TestTheWatcherFolderTopology:
    """Codex H15."""

    def test_a_symlinked_stage_folder_is_refused(self, tmp_path):
        """With failed/ pointing at inbox/, a run that failed and cost money
        reappeared in the inbox and was paid for again on every poll -- all
        night. The whole reason failed/ is separate is that a deterministic
        failure must not be retried."""
        f = W.Folders.under(str(tmp_path))
        os.rmdir(f.failed)
        os.symlink(f.inbox, f.failed)
        with pytest.raises(ValueError, match="symlink"):
            W.Folders.under(str(tmp_path))

    def test_an_inbox_symlink_to_an_external_file_is_ignored(self, tmp_path):
        """It points at content nobody put in the folder, and whatever it
        named became the paid ask."""
        outside = tmp_path / "outside.md"
        outside.write_text("Q: content from outside the watched folder\n")
        root = tmp_path / "root"
        f = W.Folders.under(str(root))
        os.symlink(str(outside), os.path.join(f.inbox, "link.md"))
        assert W.candidates(f.inbox) == []

    def test_real_folders_are_still_accepted(self, tmp_path):
        f = W.Folders.under(str(tmp_path))
        assert os.path.isdir(f.inbox) and os.path.isdir(f.failed)


class TestTheWatcherAlwaysLeavesACostRecord:
    """Codex M5."""

    def test_a_successful_run_writes_a_cost_report(self, tmp_path, monkeypatch):
        f = W.Folders.under(str(tmp_path))
        p = os.path.join(f.inbox, "ask.md")
        with open(p, "w") as fh:
            fh.write("Q: should we build the ingest service or buy one?\n")
        monkeypatch.setattr("night_loop.live_night", lambda *a, **k: [])
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert os.path.exists(os.path.join(out, "COST.md"))

    def test_a_crashed_run_still_writes_one(self, tmp_path, monkeypatch):
        """The runs that most need a cost record are the ones that ended
        badly: they spent money and wrote no figure anywhere."""
        f = W.Folders.under(str(tmp_path))
        p = os.path.join(f.inbox, "ask.md")
        with open(p, "w") as fh:
            fh.write("Q: should we build the ingest service or buy one?\n")
        monkeypatch.setattr("night_loop.live_night",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
        out = W.process(p, f, 1.0, NEVER_OPENED)
        assert os.path.exists(os.path.join(out, "COST.md"))

    def test_a_scan_failure_does_not_end_the_loop(self, tmp_path, monkeypatch):
        """A watcher that has silently stopped looks exactly like a watcher
        with an empty inbox, and every later file waits forever."""
        calls = {"n": 0}

        def flaky(_inbox):
            calls["n"] += 1
            raise OSError("transient listdir failure")
        monkeypatch.setattr(W, "candidates", flaky)
        W.watch(str(tmp_path), 1.0, interval=0.0, once=True)
        assert calls["n"] == 1
