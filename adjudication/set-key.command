#!/bin/sh
# set-key.command -- put ONE API key into .env, in the RIGHT seat, without the
# key ever appearing on screen, in shell history, or in a process listing.
#
#   ./set-key.command 3     store the Mistral key
#   ./set-key.command       ask which seat
#   ./set-key.command check report which seats are filled (no key shown)
#
# Before writing, it shows you the seat's vendor, the model id already
# configured for that seat, and the vendor's key page -- so you can confirm
# you are holding the right key before you paste.

cd "$(dirname "$0")" || exit 1
[ -f .env ] || { echo "No .env here. Run:  cp .env.example .env"; exit 1; }

seat_vendor() {
  case "$1" in
    1) echo "OpenAI" ;;
    2) echo "Google (Gemini)" ;;
    3) echo "Mistral" ;;
    4) echo "xAI (Grok)" ;;
    5) echo "Anthropic (Claude)" ;;
  esac
}

seat_console() {
  case "$1" in
    1) echo "https://platform.openai.com/api-keys" ;;
    2) echo "https://aistudio.google.com/apikey" ;;
    3) echo "https://console.mistral.ai" ;;
    4) echo "https://console.x.ai" ;;
    5) echo "https://platform.claude.com/settings/keys" ;;
  esac
}

# ---- check mode -----------------------------------------------------------
if [ "$1" = "check" ]; then
  export ADJ_MODE=check
  /usr/bin/python3 - <<'PY'
import re

VENDOR = {"1": "OpenAI", "2": "Google (Gemini)", "3": "Mistral",
          "4": "xAI (Grok)", "5": "Anthropic (Claude)"}
# Only prefixes confirmed in vendor documentation.
SIG = [("sk-ant-", "5", "Anthropic"), ("xai-", "4", "xAI"), ("sk-", "1", "OpenAI")]

env = {}
for line in open(".env"):
    if "=" in line:
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()

print("seat  vendor              key      model id")
print("----  ------------------  -------  --------------------------------")
bad = 0
for n in "12345":
    key   = env.get("ADJ_SEAT_%s_API_KEY" % n, "")
    model = env.get("ADJ_SEAT_%s_MODEL" % n, "") or "(blank)"
    if not key:
        state = "EMPTY  "
    else:
        state = "set    "
        for prefix, owner, name in SIG:
            if key.startswith(prefix):
                if owner != n:
                    state = "WRONG!!"
                    bad += 1
                    print("  ^^ seat %s holds a key whose prefix is %s's. "
                          "Re-run: ./set-key.command %s" % (n, name, n))
                break
    print(" %s    %-18s %s  %s" % (n, VENDOR[n], state, model))

print()
filled = sum(1 for n in "12345" if env.get("ADJ_SEAT_%s_API_KEY" % n))
print("%d of 5 keys filled." % filled)
if bad:
    print("%d seat(s) look like the WRONG vendor's key -- fix before running." % bad)
elif filled == 5:
    print("No vendor mismatches detected. Ready.")
print("Note: Mistral and Google publish no key prefix, so a swap between "
      "those two cannot be detected here -- check those by eye.")
PY
  exit 0
fi

# ---- store mode -----------------------------------------------------------
SEAT="$1"
if [ -z "$SEAT" ]; then
  echo "  1 = OpenAI            2 = Google (Gemini)   3 = Mistral"
  echo "  4 = xAI (Grok)        5 = Anthropic (Claude)"
  printf 'Which seat? '
  read -r SEAT
fi

case "$SEAT" in
  1|2|3|4|5) ;;
  *) echo "Seat must be 1-5. Got: '$SEAT'"; exit 1 ;;
esac

grep -q "^ADJ_SEAT_${SEAT}_API_KEY=" .env || {
  echo "No ADJ_SEAT_${SEAT}_API_KEY line in .env -- wrong folder?"; exit 1; }

MODEL=$(grep "^ADJ_SEAT_${SEAT}_MODEL=" .env | head -1 | cut -d= -f2-)

echo
echo "  ------------------------------------------------------------"
echo "   SEAT $SEAT   ->   $(seat_vendor "$SEAT")"
echo "   model configured : ${MODEL:-(blank)}"
echo "   get the key from : $(seat_console "$SEAT")"
echo "  ------------------------------------------------------------"
printf 'Is the key on your clipboard a %s key? [y/N] ' "$(seat_vendor "$SEAT")"
read -r OK
case "$OK" in
  y|Y|yes|YES) ;;
  *) echo "Cancelled. .env unchanged."; exit 1 ;;
esac

printf 'Paste the key now, then press Return (nothing will appear): '
stty -echo 2>/dev/null
read -r ADJ_KEY_INPUT
stty echo 2>/dev/null
printf '\n'

[ -n "$ADJ_KEY_INPUT" ] || { echo "Nothing entered. .env unchanged."; exit 1; }

export ADJ_KEY_INPUT SEAT
/usr/bin/python3 - <<'PY'
import os, sys

seat = os.environ["SEAT"]
key  = os.environ["ADJ_KEY_INPUT"].strip()
tag  = "ADJ_SEAT_%s_API_KEY=" % seat

VENDOR = {"1": "OpenAI", "2": "Google (Gemini)", "3": "Mistral",
          "4": "xAI (Grok)", "5": "Anthropic (Claude)"}
SIG = [("sk-ant-", "5", "Anthropic"), ("xai-", "4", "xAI"), ("sk-", "1", "OpenAI")]

for prefix, owner, name in SIG:
    if key.startswith(prefix):
        if owner != seat:
            sys.stderr.write(
                "\n  STOP. That key begins with a prefix %s uses, but you are\n"
                "  filling seat %s (%s). Nothing was written.\n"
                "  Re-run:  ./set-key.command %s\n\n" % (name, seat, VENDOR[seat], owner))
            sys.exit(1)
        break

with open(".env") as fh:
    lines = fh.readlines()

for i, line in enumerate(lines):
    if line.startswith(tag):
        lines[i] = tag + key + "\n"
        break
else:
    sys.exit("could not find %s" % tag)

with open(".env", "w") as fh:
    fh.writelines(lines)
os.chmod(".env", 0o600)

print("  Stored for seat %s (%s). %d characters. The key was never displayed."
      % (seat, VENDOR[seat], len(key)))
PY
STATUS=$?
unset ADJ_KEY_INPUT
[ $STATUS -eq 0 ] || exit $STATUS

echo
echo "Keys filled so far (count only):"
grep -cE '^ADJ_SEAT_[0-9]+_API_KEY=.+' .env
