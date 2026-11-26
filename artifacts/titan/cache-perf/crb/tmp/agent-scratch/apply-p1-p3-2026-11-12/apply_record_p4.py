#!/usr/bin/env python3
"""Record, after the review loop of the second session ended (REVIEW_COMPLETE, round 2, 2026-11-13T04:25:23Z):
the review covered the report changes of sections 10 and 11, and the report on disk has a new sha256.
All edits stay on their line. Usage: apply_record_p4.py <record.md> [--write]"""
import hashlib, sys
P = sys.argv[1]
CRB = "/home/jhan/workspace/titan/cache-perf/crb"; EVID = CRB + "/tmp/agent-scratch/apply-p1-p3-2026-11-12"
L = open(P, encoding="utf-8").read().split("\n"); N0 = len(L); n_edits = 0
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
NOW = sha(CRB + "/crb-memory-hierarchy.html"); FIRST = "1333e332428d2680fcb2b6ad4ab4f389f628dd299c0a56e3a4e7adab6d4e9248"
A = open(EVID + "/report.after-section11.html", encoding="utf-8").read().split("\n"); B = open(CRB + "/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")
D = [i + 1 for i, (x, y) in enumerate(zip(A, B)) if x != y]
assert len(A) == len(B) == 979 and D == [49, 232, 233, 253, 356, 440, 442, 488, 502, 503, 504, 508, 779, 780, 889], D
RV = open(CRB + "/crb-memory-hierarchy.html.review.md", encoding="utf-8").read().split("\n")
done = [l for l in RV if l.startswith("## session=20261113T033543Z-w7c2 round=2 role=reviewer status=REVIEW_COMPLETE digest=" + NOW)]
assert len(done) == 1 and "time=2026-11-13T04:25:23Z" in done[0], done
assert any("This includes the changes of both Claude sessions." in l for l in RV) and any("no review of the brief or its generator" in l for l in RV)
assert sha(EVID + "/brief.after-section11.html") == sha(CRB + "/crb-memory-hierarchy-brief.html")
S11 = [i + 1 for i, l in enumerate(L) if l.startswith("## 11. The author's three requests after section 10 (2026-11-12)")][0]


def sub(n, old, new):
    global n_edits
    assert L[n - 1].count(old) == 1, (n, L[n - 1].count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = L[n - 1].replace(old, new); n_edits += 1


def find(prefix, after=0):
    hits = [i + 1 for i, l in enumerate(L) if l.startswith(prefix) and i + 1 > after]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


n = find("The author read the answers of section 10.5 and sent three requests.")
sub(n, "The reviewer agent has not read these changes.",
    "When this section was closed, the reviewer agent had not read these changes. A later review of the report covers them (see the "
    "paragraph on the second session below).")
n = find("A second session of the author works on the report after this section.")
sub(n, "so its reviewer can also read the changes of sections 10 and 11.",
    "so its reviewer can also read the changes of sections 10 and 11. That review ended on 2026-11-12 at 20:25 (2026-11-13 04:25 UTC) "
    "with REVIEW_COMPLETE in round 2. Its scope was the difference between that baseline and the final report, and the reviewer wrote "
    "that this includes the changes of both sessions. It had two findings, both on lines 232 and 233 of the second session. It had no "
    "finding on a line of sections 10 and 11. Among its checks it names the changed port-rate statements against the raw bandwidth "
    "files, the two added bars of the pair chart, the new C listings, the structure check, the geometry check and a render of the pair "
    f"chart. It did not review the brief, the generator or this record. After that review the report on disk has the sha256 `{NOW}`. "
    "Since the first write of the second session only lines 232 and 233 changed.")
hits = [i + 1 for i, l in enumerate(L) if l.startswith("- The reviewer agent of the review loop has not read the changes of this section.")]
assert len(hits) == 2 and hits[0] < S11 < hits[1], hits
sub(hits[0], "- The reviewer agent of the review loop has not read the changes of this section.",
    "- The reviewer agent of the review loop has not read the changes of this section. Added later: a review of the report that ended on "
    "2026-11-12 at 20:25 covers the report lines of this section (section 11, paragraph on the second session).")
sub(hits[1], "- The reviewer agent of the review loop has not read the changes of this section.",
    "- When this section was closed, the reviewer agent had not read its changes. Its later review of the report covers the report lines "
    "(see the paragraph on the second session). It did not review the brief, the generator or this record.")
assert len(L) == N0 and sum(1 for l in L if NOW in l) == 1 and sum(1 for l in L if FIRST in l) == 1
if "--write" in sys.argv: open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits, {len(L) - 1} lines; report now {NOW[:12]}")
