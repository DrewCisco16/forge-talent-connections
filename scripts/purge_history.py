#!/usr/bin/env python3
"""
purge_history.py -- rebuild this branch's commits with the leaked blob replaced.

THE INCIDENT. Commit 2a51e25 committed the device fleet context pack verbatim to
this PUBLIC repository, publishing third-party personal data: 8 phone numbers and
2 carrier/order identifiers, belonging to people who did not consent to it. HEAD
was redacted in 5f12aba, but the original blob remains in the branch's history and
in PR #12's diff views. Redaction at HEAD does not unpublish a blob.

WHAT THIS DOES. Walks every commit from the merge-base with main to the branch
head and rewrites each so that PATH holds GOOD_BLOB -- the redacted version --
instead of whatever it held. Author, committer, message, dates and parent
structure are preserved exactly.

WHAT IT DOES NOT DO, BY CONSTRUCTION. Move any ref, delete any object, or touch
the remote. It prints the new head SHA and stops. Moving the branch ref is a
separate, explicit human act; this script cannot do it even by accident, and that
is deliberate -- a script that both rewrites and publishes is one typo from
destroying work.

WHY PLUMBING RATHER THAN filter-branch. commit-tree and write-tree only CREATE
objects. Nothing existing is destroyed, so the original history stays fully
intact and reachable by its old SHAs until someone deliberately moves a ref. The
operation is therefore reversible right up to the force-push.

VERIFIED 2026-09-15 in a throwaway clone:
    17 commits rebuilt, 4 trees changed
    old tree 9309d1ce == new tree 9309d1ce   <- the working tree does not change
    replacement blob 7509dc21 asserted clean by redaction_guard before any write

READ scripts/../agents/27-pii-incident-runbook.md BEFORE RUNNING THIS.
A history rewrite is necessary here and it is NOT sufficient. The runbook says
what it leaves behind and who has to clear that.

Usage:  python3 scripts/purge_history.py <path-to-repo>
"""
import os, subprocess, sys

REPO = sys.argv[1]
PATH = "agents/context/device-fleet.md"
GOOD_BLOB = "7509dc21f66068fddbc97cb497909fd2ba2341d4"   # the redacted version, from 5f12aba

def git(*a, **kw):
    env = dict(os.environ); env.update(kw.pop("env", {}))
    r = subprocess.run(["git","-C",REPO,*a], capture_output=True, text=True, env=env, **kw)
    if r.returncode: sys.exit(f"git {' '.join(a)}\n{r.stderr}")
    return r.stdout.strip()

base = git("merge-base","origin/main","HEAD")
head = git("rev-parse","HEAD")
commits = git("rev-list","--reverse",f"{base}..HEAD").split()
print(f"base   {base[:12]}\nhead   {head[:12]}\ncommits to rebuild: {len(commits)}")

# Confirm the good blob exists and is clean.
good = git("cat-file","-p",GOOD_BLOB)
sys.path.insert(0,os.path.join(REPO,"scripts"))
import redaction_guard as rg
assert not rg.scan_text(good, PATH), "the replacement blob is NOT clean -- aborting"
print(f"replacement blob {GOOD_BLOB[:12]} verified clean ({len(good.splitlines())} lines)")

idx = os.path.join(REPO, ".git", "purge-index")
mapping = {base: base}
changed = 0

for c in commits:
    tree = git("rev-parse", f"{c}^{{tree}}")
    # Does this commit carry the path, and with the wrong blob?
    cur = subprocess.run(["git","-C",REPO,"rev-parse",f"{c}:{PATH}"],
                         capture_output=True, text=True)
    has = cur.returncode == 0
    needs = has and cur.stdout.strip() != GOOD_BLOB

    if needs:
        if os.path.exists(idx): os.remove(idx)
        git("read-tree", tree, env={"GIT_INDEX_FILE": idx})
        git("update-index","--cacheinfo",f"100644,{GOOD_BLOB},{PATH}",
            env={"GIT_INDEX_FILE": idx})
        tree = git("write-tree", env={"GIT_INDEX_FILE": idx})
        changed += 1

    parents = git("rev-list","--parents","-n","1",c).split()[1:]
    new_parents = []
    for p in parents:
        new_parents.append(mapping.get(p, p))

    meta = git("show","-s","--format=%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd", c).split("\x00")
    msg  = git("show","-s","--format=%B", c)
    args = ["commit-tree", tree]
    for p in new_parents: args += ["-p", p]
    env = {"GIT_AUTHOR_NAME":meta[0],"GIT_AUTHOR_EMAIL":meta[1],"GIT_AUTHOR_DATE":meta[2],
           "GIT_COMMITTER_NAME":meta[3],"GIT_COMMITTER_EMAIL":meta[4],"GIT_COMMITTER_DATE":meta[5]}
    r = subprocess.run(["git","-C",REPO,*args], input=msg, capture_output=True, text=True,
                       env={**os.environ, **env})
    if r.returncode: sys.exit(r.stderr)
    mapping[c] = r.stdout.strip()

if os.path.exists(idx): os.remove(idx)
new_head = mapping[head]
print(f"\ncommits whose tree changed: {changed}")
print(f"NEW HEAD: {new_head}")
print(f"old tree {git('rev-parse', head + '^{tree}')}")
print(f"new tree {git('rev-parse', new_head + '^{tree}')}")
print("\nNo ref was moved. Nothing was deleted.")
