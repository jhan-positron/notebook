#!/usr/bin/env python3
"""Record, after the second session wrote its edits on top of the state of section 11 (2026-11-12, 19:35):
the copies of the final state of section 11, and what the second session's write changed.
Both edits stay on their line. Usage: apply_record_p3.py <record.md> [--write]"""
import hashlib, sys
P = sys.argv[1]
CRB = "/home/jhan/workspace/titan/cache-perf/crb"; EVID = CRB + "/tmp/agent-scratch/apply-p1-p3-2026-11-12"
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n_edits = 0
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
MINE, NOW = sha(EVID + "/report.after-section11.html"), sha(CRB + "/crb-memory-hierarchy.html")
A = open(EVID + "/report.after-section11.html", encoding="utf-8").read().split("\n"); B = open(CRB + "/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
D = [i + 1 for i, (x, y) in enumerate(zip(A, B)) if x != y]
assert len(A) == len(B) == 979 and D == [49, 232, 233, 253, 356, 440, 442, 488, 502, 503, 504, 508, 779, 780, 889], D
assert B[48].startswith(A[48][:-len("</div>")]) and B[48].endswith("</div>")          # line 49: the text of section 11 is kept, sentences follow it
assert sum(1 for l in L if MINE in l) == 2 and not any(NOW in l for l in L)             # the record names the state of section 11 twice
assert sha(EVID + "/brief.after-section11.html") == sha(CRB + "/crb-memory-hierarchy-brief.html")
assert sha(EVID + "/make-brief.after-section11.py") == sha(CRB + "/make-brief.py")


def find(prefix):
    hits = [i + 1 for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


def sub(n, old, new):
    global n_edits
    assert L[n - 1].count(old) == 1, (n, L[n - 1].count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = L[n - 1].replace(old, new); n_edits += 1


n = find("| `crb/tmp/agent-scratch/apply-p1-p3-2026-11-12/` | Scratch folder of this section [Ref38].")
sub(n, "`make-brief.check4-state.py`, `record.check4-state.md`)",
    "`make-brief.check4-state.py`, `record.check4-state.md`), copies of the state after this section (`report.after-section11.html`, "
    "`brief.after-section11.html`, `make-brief.after-section11.py`)")
n = find("A second session of the author works on the report after this section.")
sub(n, "None of its other lines is a line of this section. The sha256 in the table is the state after the last write of this section and "
       "before those edits.",
    "None of its other lines is a line of this section. The second session wrote its edits on 2026-11-12 at 19:35. The report on disk then "
    f"has the sha256 `{NOW}`. It differs from the state of this section in the 15 lines of the draft and in no other line. At line 49 the "
    "text of this section is unchanged, and the new sentences follow it. The second session did not change the brief or the generator. It "
    "opened a new review loop in `crb/crb-memory-hierarchy.html.review.md` (session 20261113T033543Z-w7c2). The baseline of that loop is "
    "the reviewed state of sections 2 to 9, so its reviewer can also read the changes of sections 10 and 11. The sha256 in the table is "
    "the state after the last write of this section and before those edits. The scratch folder holds a copy of that state.")
assert len(L) == N0
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines; report now {NOW[:12]}, state of section 11 {MINE[:12]}")
