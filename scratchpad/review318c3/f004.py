"""F-004 re-derived on the REVIEWER's own basis — deliberately NOT the round's.

Round 2's basis: yaml.safe_load both revisions, flatten to leaf paths keyed by
`id`, compare; comments via difflib.SequenceMatcher opcodes.

This basis instead:
  (a) changed VALUES  = unified-diff hunks from `git diff -U0`, every removed
      line paired with its added counterpart, then attributed to an entry id by
      walking the NEW file's text upward for the nearest `- id: X` / `id:`; a
      key present on one side only would show as an unpaired line and is
      counted separately.  No YAML parser involved at all.
  (b) comment BLOCKS = added lines whose strip() starts with '#', grouped into
      maximal runs of consecutive new-file line numbers.
Two independent routes to the same two numbers.
"""
import re, subprocess

ROOT = "/Users/omelnikova/PycharmProjects/PythonProject4-card-318"
F = "meta/architecture/requirements.yml"
A, B = "ef242847", "HEAD"

def git(*a):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True,
                           check=True).stdout

new_lines = git("show", f"{B}:{F}").splitlines()

d = git("diff", "-U0", f"{A}..{B}", "--", F).splitlines()
print("numstat:", git("diff", "--numstat", f"{A}..{B}", "--", F).strip())

hunks = []
cur = None
for line in d:
    if line.startswith("@@"):
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        cur = {"nstart": int(m.group(3)), "rem": [], "add": []}
        hunks.append(cur)
    elif cur is None or line.startswith(("---", "+++", "diff ", "index ")):
        continue
    elif line.startswith("-"):
        cur["rem"].append(line[1:])
    elif line.startswith("+"):
        cur["add"].append(line[1:])

def key_of(s):
    m = re.match(r"\s*-?\s*([A-Za-z_][\w]*):", s)
    return m.group(1) if m else None

def owner(lineno):
    """nearest enclosing entry id, walking the NEW file upward"""
    for i in range(min(lineno, len(new_lines)) - 1, -1, -1):
        m = re.match(r"\s*-\s*id:\s*(\S+)", new_lines[i])
        if m:
            return m.group(1)
        m = re.match(r"\s*id:\s*(\S+)", new_lines[i])
        if m:
            return m.group(1)
    return "?"

changed, added_only, removed_only, added_comments = [], [], [], []
for h in hunks:
    rem_content = [l for l in h["rem"] if l.strip() and not l.strip().startswith("#")]
    add_content = [l for l in h["add"] if l.strip() and not l.strip().startswith("#")]
    # locate each added line's new-file number
    n = h["nstart"]
    for l in h["add"]:
        if l.strip().startswith("#"):
            added_comments.append(n)
        n += 1
    rk = {key_of(l): l for l in rem_content}
    ak = {key_of(l): l for l in add_content}
    for k in rk:
        if k in ak:
            changed.append((owner(h["nstart"]), k, rk[k].strip()[:40], ak[k].strip()[:40]))
        else:
            removed_only.append((owner(h["nstart"]), k))
    for k in ak:
        if k not in rk:
            added_only.append((owner(h["nstart"]), k))

print(f"\nchanged values: {len(changed)}")
for o, k, a, b in changed:
    print(f"  {o}.{k}")
print(f"keys added only : {len(added_only)} {added_only}")
print(f"keys removed only: {len(removed_only)} {removed_only}")

runs = []
for n in added_comments:
    if runs and n == runs[-1][-1] + 1:
        runs[-1].append(n)
    else:
        runs.append([n])
print(f"\nadded comment lines: {len(added_comments)}")
print(f"comment blocks (maximal consecutive runs): {len(runs)}")
for r in runs:
    print(f"  lines {r[0]}-{r[-1]} ({len(r)} lines) in {owner(r[0])}: "
          f"{new_lines[r[0]-1].strip()[:58]}")
tot_add = sum(len(h['add']) for h in hunks)
tot_rem = sum(len(h['rem']) for h in hunks)
print(f"\ntotal added lines {tot_add}, removed {tot_rem}; "
      f"non-comment added {tot_add - len(added_comments)}")
