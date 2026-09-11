#!/usr/bin/env bash
# run_night.sh -- launch the overnight loop on THIS machine.
#
#   autoresearch/run_night.sh <tag> [--hours 8] [--model claude-opus-5]
#                                   [--max-iter 60] [--patience 10]
#                                   [--no-push] [--print-only]
#
# In order: refuse a dirty tree or a duplicate run, build the project
# virtualenv if there is none, create branch autoresearch/<tag>, record the
# baseline score, then start Claude Code in a detached tmux session under a
# hard wall-clock timeout with program.md as its brief.
#
# Permissions come from autoresearch/settings.json: a scoped allowlist, not a
# blanket bypass. In non-interactive mode anything outside it is denied.
#
# Windows machines (the ASUS ProArt, the HP Envy) run this inside WSL2 Ubuntu.
# On a Mac it wraps the run in caffeinate so the lid can close on power.
# Disable sleep at the OS level regardless; see autoresearch/README.md.
set -euo pipefail

die() { echo "run_night: $*" >&2; exit 2; }
usage() { sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

TAG=""; HOURS=8; MODEL=claude-opus-5; MAX_ITER=60; PATIENCE=10; PUSH=--push; PRINT_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --hours) HOURS="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --max-iter) MAX_ITER="$2"; shift 2 ;;
    --patience) PATIENCE="$2"; shift 2 ;;
    --no-push) PUSH=""; shift ;;
    --print-only) PRINT_ONLY=1; shift ;;
    -h|--help) usage ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$TAG" ] || die "one tag only"; TAG="$1"; shift ;;
  esac
done
[ -n "$TAG" ] || usage
case "$TAG" in *[!A-Za-z0-9._-]*) die "tag may contain only letters, digits, . _ -" ;; esac

ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$ROOT"
SESSION="autoresearch-$TAG"
BRANCH="autoresearch/$TAG"
SETTINGS="$ROOT/autoresearch/settings.json"

command -v claude >/dev/null || die "claude CLI not found; install Claude Code first and sign in with: claude /login"
command -v tmux   >/dev/null || die "tmux not found; install it (apt install tmux / brew install tmux)"
[ -f "$SETTINGS" ] || die "missing $SETTINGS"
tmux has-session -t "$SESSION" 2>/dev/null && die "session $SESSION is already running (one writer per repo)"
[ -z "$(git status --porcelain)" ] || die "working tree is not clean; commit or stash first"
git rev-parse --verify -q "$BRANCH" >/dev/null && die "branch $BRANCH already exists; choose a new tag"
git fetch -q origin || echo "run_night: fetch failed; continuing offline" >&2

VENV="$ROOT/autoresearch/.venv"
[ -x "$ROOT/adjudication/.venv/bin/python" ] && VENV="$ROOT/adjudication/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "run_night: building virtualenv at $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r adjudication/requirements-dev.txt
fi

git checkout -q -b "$BRANCH"
printf '{"commit": "%s", "max_iter": %d, "patience": %d}\n' \
  "$(git rev-parse HEAD)" "$MAX_ITER" "$PATIENCE" > autoresearch/.base

echo "run_night: recording the baseline (about three minutes)"
# shellcheck disable=SC2086
"$VENV/bin/python" autoresearch/score.py --record baseline $PUSH || die "the baseline did not pass its own gates; nothing launched"

LOG="$ROOT/autoresearch/night-$TAG.log"
RUNNER="$ROOT/autoresearch/night-$TAG.sh"
PROMPT="Read program.md at the repository root and run its loop until autoresearch/score.py prints STOP. You are on branch $BRANCH and the baseline row is already recorded. The command python on PATH is the project virtualenv."
cat > "$RUNNER" <<RUN
#!/usr/bin/env bash
export PATH="$VENV/bin:\$PATH"
cd "$ROOT"
timeout ${HOURS}h claude --model "$MODEL" --settings "$SETTINGS" --permission-mode acceptEdits --verbose -p "$PROMPT" 2>&1 | tee "$LOG"
echo "run_night: claude exited; results in autoresearch/results.tsv" | tee -a "$LOG"
RUN
chmod +x "$RUNNER"

KEEPAWAKE=""
command -v caffeinate >/dev/null && KEEPAWAKE="caffeinate -dims "

if [ "$PRINT_ONLY" = 1 ]; then
  echo "would run in tmux session $SESSION:"; echo "  ${KEEPAWAKE}$RUNNER"; exit 0
fi

tmux new-session -d -s "$SESSION" "${KEEPAWAKE}$RUNNER"
cat <<MSG
run_night: started.
  branch    $BRANCH
  session   tmux attach -t $SESSION      (detach again with Ctrl-b d)
  log       tail -f $LOG
  results   cat autoresearch/results.tsv
  stop      tmux kill-session -t $SESSION
  limit     ${HOURS}h wall clock, $MAX_ITER attempts, patience $PATIENCE
MSG
