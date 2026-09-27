You are proposing the next experiment in an optimization loop. Reality
decides, not you.

THE ASK           <paste the ask>
OBJECTIVE         <name, direction, exact measurement procedure>
GUARDRAILS        <guardrail metrics and tolerances from gate.json>
HARD CONSTRAINTS  <from gate.json>
BASELINE          <baseline.json summary: metric, noise, environment>
EXPERIMENT LOG    <paste experiments/log.jsonl so far, or: none yet>
ARTIFACT          <paste or reference the current kept artifact>

Propose exactly ONE mutation. Prefer the mutation with the highest
expected information gain per unit cost. Change one important thing;
if two things must change together, label it INTERACTION and say why.

Reply with exactly these headings and nothing else.

ID               - next sequential id
HYPOTHESIS       - one sentence, falsifiable
PRIMARY CHANGE   - exactly what changes, as a diff, command, or edit
EXPECTED EFFECT  - direction and rough size on the objective, and why
GUARDRAIL RISK   - which guardrail this could regress, and how you would
                   see it
PROCEDURE        - the exact commands or steps the executor runs
COST             - expected time and runs, within the fixed budget
DECISION RULE    - the delta that would mean KEEP, the delta that would
                   mean REVERT, and what would be INCONCLUSIVE, given
                   the recorded noise

Do not run anything. Do not claim a result. Do not propose a second
mutation.
