#!/usr/bin/env python3
"""Deterministic timing harness for the rehearsal: prints 'runtime_s <v>' and 'output_hash_changed <0|1>'.

The runtime it reports is a function of importer.py's flags, not of the clock, so a rehearsal is repeatable:
USE_CACHE halves the cost of the schema; SKIP_LARGE is faster still but changes the output on malformed rows.
A tiny alternating jitter models measurement noise across the two runs Dispatch asks for.
"""
import os
import sys

import importer

n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 10000
rows = [["a", "b", "c"] if i % 500 else ["a", "b"] for i in range(n)]
accepted, rejects = importer.import_rows(rows, ["x", "y", "z"])
base = 10.0
if importer.USE_CACHE:
    base = 6.0
if importer.SKIP_LARGE:
    base = 5.0
counter = ".bench_runs"
k = int(open(counter).read()) if os.path.exists(counter) else 0
open(counter, "w").write(str(k + 1))
print(f"runtime_s {base + 0.1 * (k % 2):.1f}")
print(f"output_hash_changed {0 if len(rejects) == n // 500 else 1}")
