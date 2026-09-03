#!/bin/bash
# ============================================================================
# Adjudication Five — one-click setup for macOS
#
# DOUBLE-CLICK THIS FILE. That is the whole instruction.
#
# If macOS says "cannot be opened because it is from an unidentified
# developer": right-click it instead, choose Open, then click Open again.
# You only have to do that once.
#
# This script does everything EXCEPT put in your API keys and model IDs.
# It never asks you for a key and never touches the internet except to
# install the Python libraries.
# ============================================================================
set -u
cd "$(dirname "$0")" || exit 1

BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; OFF=$'\033[0m'
say()  { printf "%s\n" "$*"; }
ok()   { printf "${GREEN}✅ %s${OFF}\n" "$*"; }
warn() { printf "${YELLOW}⚠️  %s${OFF}\n" "$*"; }
die()  { printf "${RED}❌ %s${OFF}\n" "$*"; printf "\nPress any key to close."; read -r -n 1; exit 1; }

printf "\n${BOLD}Adjudication Five — setup${OFF}\n"
say "Folder: $(pwd)"
say ""

# ---- 1. Python -------------------------------------------------------------
say "${BOLD}[1/5]${OFF} Checking Python…"
command -v python3 >/dev/null 2>&1 || die "Python 3 is not installed.
Install it from https://www.python.org/downloads/macos/ then double-click this again."
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' \
  || die "Python $PYV found, but 3.11 or newer is required.
Install a newer Python from https://www.python.org/downloads/macos/"
ok "Python $PYV"

# ---- 2. Virtual environment ------------------------------------------------
say "${BOLD}[2/5]${OFF} Building an isolated environment…"
[ -d .venv ] || python3 -m venv .venv || die "Could not create the environment."
ok "Environment ready at $(pwd)/.venv"

# ---- 3. Libraries ----------------------------------------------------------
say "${BOLD}[3/5]${OFF} Installing libraries (takes a minute)…"
./.venv/bin/pip install --quiet --upgrade pip >/dev/null 2>&1
./.venv/bin/pip install --quiet -r requirements.txt || die "Install failed. Are you online?"
./.venv/bin/pip install --quiet -r requirements-dev.txt >/dev/null 2>&1
ok "Libraries installed"

# ---- 4. Your two files -----------------------------------------------------
say "${BOLD}[4/5]${OFF} Creating the two files you fill in…"
if [ -f .env ]; then
  warn ".env already exists — left untouched (your keys are safe)"
else
  cp .env.example .env && ok "Created .env  (your five API keys go here)"
fi
if [ -f profiles.json ]; then
  warn "profiles.json already exists — left untouched"
else
  cp profiles.example.json profiles.json && ok "Created profiles.json  (vendor settings go here)"
fi

# ---- 5. Prove it works -----------------------------------------------------
say "${BOLD}[5/5]${OFF} Running a pretend adjudication to prove it works…"
say "    (fake AI seats, no internet, costs nothing)"
if ./.venv/bin/python run_adjudication.py --demo 2>/dev/null | grep -q "SURVIVOR: c_true"; then
  ok "The machinery works."
else
  die "The demo did not produce the expected answer. Send me this whole window."
fi

# ---- Where things are ------------------------------------------------------
HERE=$(pwd)
cat <<BANNER

${BOLD}────────────────────────────────────────────────────────${OFF}
${GREEN}${BOLD}  SETUP COMPLETE${OFF}
${BOLD}────────────────────────────────────────────────────────${OFF}

Everything lives in:
  ${BOLD}$HERE${OFF}

${BOLD}YOU EDIT THESE TWO — nothing else:${OFF}
  .env            your 5 API keys + 5 model IDs
  profiles.json   how to reach each of the 5 companies

${BOLD}NEXT, IN ORDER:${OFF}
  1. Open .env and fill in your five keys and model IDs
  2. Open profiles.json and replace every FILL-IN from the vendor's docs
  3. Check your work — free, offline, costs nothing:

     cd "$HERE"
     ./.venv/bin/python run_adjudication.py --check-profiles profiles.json

     It prints PROFILES OK when you are done.

${BOLD}READ:${OFF}  START-HERE.md   (the full map)
${BOLD}KEYS:${OFF}  Get-Your-5-AI-Keys.pdf   (tap-the-boxes walkthrough)

${RED}${BOLD}NEVER paste a key into a chat window, and never send .env or
profiles.json to anyone. Every other file here is safe to share.${OFF}

BANNER

printf "Opening the folder in Finder…\n"
open "$HERE" 2>/dev/null
printf "\nPress any key to close this window."
read -r -n 1
