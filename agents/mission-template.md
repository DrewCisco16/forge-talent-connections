# MISSION — copy to `mission.md` and fill before any run

Playbook p.2. **Blank permissions or spending limits do not authorize action.**

```
Run ID / date ..................
Owner / decision-maker .......... Andrew Francisco
Lane (choose exactly ONE) ....... [ ] FORGE  [ ] ABO  [ ] J4V  [ ] DBA  [ ] HOME

What useful result must exist at the end?
  ..................................................................

Done means these observable checks pass (up to THREE):
  1. ..............................................................
  2. ..............................................................
  3. ..............................................................

Lead agent / card ............... agents/cards/________.md
Route (ONE controller) .......... [ ] A ChatGPT Remote  [ ] B Claude Dispatch  [ ] C Claude Code
Host or cloud environment ....... ..............................
Time limit (minutes) ............ ........   Extra spend cap (USD) ... $0.00
Maximum attempts ................ ........
Approved output folder / branch . ..............................
Out of scope / must NOT be sent . ..............................
```

**Suggested first run: 25 minutes, $0 extra spend, one draft plus one revision.**
Proposed defaults, not authorization. Record actual limits above.

---

## First request to any new agent — use verbatim (Playbook p.9)

> Read the project instructions and mission. List the files loaded, proposed
> edits and permissions needed. **Make no changes yet.**

Review once before allowing the scoped build.

---

## If this mission is scheduled, it also needs (Playbook p.20)

```
Execution location .............. [ ] cloud routine  [ ] local schedule
Schedule + timezone ............. ................ America/New_York
LAST ALLOWED RUN / EXPIRY ....... ................  ← REQUIRED. No expiry, no launch
Per-run time / cost / attempts .. ................
Daily run / spend cap ........... ................
Exact draft output destination .. ................
TESTED notification destination . ................  ← tested, not assumed
WHERE TO DISABLE THE TRIGGER .... ................  ← write the exact location

[ ] A manual run produced the expected artifact and stopped
[ ] Timeout / cost / duplicate-run controls are tested; approval is recorded
```

**Default: no self-triggering chains, no overlapping runs, no automatic deploy,
merge or send.** A cloud routine survives host shutdown; a local schedule needs
the app open and the machine awake — do not substitute one for the other.

---

## On stop (Playbook p.22)

```
Saved state: artifact path, last completed step, relevant log ...........
EXACT next step on resume — do not restart everything ...................
What would unblock this? ................................................
Who decides / review date ...............................................
```
