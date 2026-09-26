"""SELECT: the spec 6 stop tests in order, then the spec 4.4 operator table. Inputs come from close files,
status.json and the registry; never from a model."""
import datetime as _dt
import re
from dataclasses import dataclass, field

CHECKABLE = re.compile(r"\b(sum|source|doi|command|document|experiment|harness|rerun|run |read |count|measure|compute)\b", re.I)


@dataclass
class NightState:
    class_: str
    kind: str
    profile: str
    options_standing: list
    open_lines: list
    stage_metrics: list            # one dict per operator stage in order: earned_kills, passed, decision_changed
    ops_run: list
    ready_generators: int
    executor_ready: bool
    sends_used: int
    max_calls: int | None
    tail_sends: int
    max_operators: int
    measurable_options: int
    hard_stop: str | None = None   # HH:MM
    now_hhmm: str = ""
    min_crew: int = 2
    usable_seats: int = 99
    experiments_max: int = 8
    options_open_settle: list = field(default_factory=list)


def is_checkable(line: str) -> bool:
    return CHECKABLE.search(line) is not None


def _past(hhmm: str, now: str) -> bool:
    try:
        h = _dt.datetime.strptime(hhmm, "%H:%M").time()
        n = _dt.datetime.strptime(now, "%H:%M").time()
    except ValueError:
        return False
    return n >= h


def stop_test(st: NightState) -> str | None:
    """First true condition of spec 6, or None (rule 8: SELECT the next operator)."""
    if st.usable_seats < st.min_crew:
        return "CREW"
    if st.hard_stop and st.now_hhmm and _past(st.hard_stop, st.now_hhmm):
        return "HARD_STOP"
    if st.max_calls:
        one_operator = st.ready_generators + 1
        if st.sends_used + one_operator + st.tail_sends > st.max_calls:
            return "BUDGET"
    if not st.options_standing:
        return "NONE_STANDING"
    open_checkable = [l for l in st.open_lines if is_checkable(l)]
    if len(st.options_standing) == 1 and not open_checkable:
        return "SUFFICIENT"
    if len(st.stage_metrics) >= 2:
        last2 = st.stage_metrics[-2:]
        if all(int(m.get("earned_kills", 0) or 0) == 0 and int(m.get("passed", 0) or 0) == 0
               and str(m.get("decision_changed", "no")).lower() in ("no", "false", "0") for m in last2):
            return "MARGINAL"
    if select_operator(st) is None:
        return "EXHAUSTED"
    return None


FIXED_ORDER = ["FMEA", "IDOV", "TRIZ", "BAYES"]


def select_operator(st: NightState) -> tuple | None:
    """(operator, precondition that fired) or None. adaptive: spec 4.4 table, first row whose precondition holds
    and whose operator has not run; v10-fixed: FMEA, IDOV, TRIZ, BAYES regardless of preconditions."""
    if len(st.ops_run) >= st.max_operators:
        return None
    if st.profile == "v10-fixed":
        for op in FIXED_ORDER:
            if op not in st.ops_run:
                return (op, "v10-fixed order")
        return None
    n = len(st.options_standing)
    open_unsettled = any(not re.search(r"settle", l, re.I) for l in st.open_lines)
    table = [
        ("EXPERIMENT", st.class_ in ("HYBRID", "EXPERIMENT") and st.executor_ready and st.measurable_options >= 2,
         "class HYBRID or EXPERIMENT, EXECUTOR registered, two options standing differ on a MEASURABLE PREDICTION"),
        ("FMEA", n >= 1, "at least one option standing"),
        ("IDOV", st.kind in ("build", "solve", "strategy"), "KIND is build, solve, or strategy"),
        ("BAYES", n >= 2 or open_unsettled, "at least two options standing, or OPEN has an item without a settle condition"),
        ("TRIZ", n >= 2, "at least two options standing"),
    ]
    for op, ok, why in table:
        if ok and op not in st.ops_run:
            return (op, why)
    return None
