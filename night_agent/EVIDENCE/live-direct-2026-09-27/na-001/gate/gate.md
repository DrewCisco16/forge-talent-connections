CLASS
DIRECT OPERATOR SET

CLASS BASIS
The ask is a single arithmetic reduction over a twelve-row column in a document already present in the project, so a lone reader can produce the figure and a reviewer can re-add the column to confirm it. No executor seat exists and no external repeatable measurement procedure is involved, so neither EXPERIMENT nor HYBRID applies, and orchestration beyond one pass plus a check would add nothing.

KIND
answer

SUCCESS
A single numeric total is stated, together with the twelve individual monthly figures it was built from, so that a reviewer can re-add the listed values and reach the same total. The count of figures summed is exactly twelve. Any row that is blank, non-numeric, duplicated, or ambiguous as to which column holds the monthly figure is named rather than silently included or dropped. Units or currency are carried through as they appear in the source.

CONSTRAINTS
Twelve monthly figures, no more and no fewer. The source is figures.csv. Output is a sum.

GROUND TRUTH
figures.csv, which contains the figures themselves and settles the total by direct re-addition; brief.md, which may define which column or period counts as a monthly figure. I have not read either document, so their actual contents are unknown to me here.

OBJECTIVES
none

BUDGET
Max operators 1 generator plus closer and reviewer, max experiments 0, max wait per reply 10 min.

PROFILE
adaptive
