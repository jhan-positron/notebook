#!/usr/bin/env python3
"""Record of the second step of 2026-11-12: status notes in the older sections and the new
section 11 (read from record_section11.final.md, which holds no placeholder that this script
does not fill). Edits before section 11 stay on their line, so the line numbers of sections
1 to 10 do not move. The new section goes in front of "## References".
Usage: apply_record_p.py <record.md> <section11.md> [--write]"""
import hashlib, sys

P, SEC = sys.argv[1], sys.argv[2]
CRB = "/home/jhan/workspace/titan/cache-perf/crb"
EVID = CRB + "/tmp/agent-scratch/apply-p1-p3-2026-11-12"
L = open(P, encoding="utf-8").read().split("\n")
assert L[-1] == ""
n_edits = 0


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def differ(a, b):
    A = open(a, encoding="utf-8").read().split("\n"); B = open(b, encoding="utf-8").read().split("\n")
    assert len(A) == len(B), (a, len(A), len(B))
    return [i + 1 for i, (x, y) in enumerate(zip(A, B)) if x != y]


def sub(n, old, new):
    global n_edits
    line = L[n - 1]
    assert line.count(old) == 1, (n, line.count(old), old[:70])
    assert "\n" not in new
    L[n - 1] = line.replace(old, new)
    n_edits += 1


def find(prefix):
    hits = [i + 1 for i, l in enumerate(L) if l.startswith(prefix)]
    assert len(hits) == 1, (prefix, hits)
    return hits[0]


SHA_REPORT = sha(CRB + "/crb-memory-hierarchy.html")
SHA_BRIEF = sha(CRB + "/crb-memory-hierarchy-brief.html")
D_REPORT = differ(EVID + "/report.before.html", CRB + "/crb-memory-hierarchy.html")
D_BRIEF = differ(EVID + "/brief.before.html", CRB + "/crb-memory-hierarchy-brief.html")
D_GEN = differ(EVID + "/make-brief.before.py", CRB + "/make-brief.py")
assert D_GEN == [166, 180, 181] and D_BRIEF == [25, 39, 40], (D_GEN, D_BRIEF)

# ---- Short version, third sentence
sub(7, "were applied, among them Arm's name \"SLC\" in place of \"mesh cache\" (section 10).",
    "were applied: Arm's name \"SLC\" in place of \"mesh cache\" (section 10), then the label \"estimated 64 GB/s\" for the pair port "
    "and the replacement texts P1 to P3 (section 11).")

# ---- word list: the checkers of section 11
n = find("- **Checker**:")
sub(n, "one of the agents of the checks of 2026-11-12 (section 10.7).", "one of the agents of the checks of 2026-11-12 (sections 10.7, 11.5 and 11.7).")

# ---- section 1, files
n = find("| `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html` |")
sub(n, "The state after section 10 has the sha256 `a9b4226b0bb949b73808da668f80ff8bb94c2cea6e7e1fd049925fce665bc5f4` |",
    "The state after section 10 has the sha256 `a9b4226b0bb949b73808da668f80ff8bb94c2cea6e7e1fd049925fce665bc5f4`. "
    f"The state after section 11 has the sha256 `{SHA_REPORT}` |")
n = find("No other project file was changed in the work of sections 2 to 9.")
sub(n, "Section 10 also changed the brief and its generator, and it lists its own backup files.",
    "Section 10 also changed the brief and its generator, and it lists its own backup files. "
    "Section 11 changed the report, the brief and the generator again, and it lists its own copies of the older states.")

# ---- section 2, row R4
n = find("| R4 |")
sub(n, "\"unknown\" in both boxes. See D1: the reason in the request no longer holds |",
    "\"unknown\" in both boxes. See D1: the reason in the request no longer holds. Since 2026-11-12 the box of the pair port says "
    "\"estimated 64 GB/s\" (the author's decision, section 11.2) |")

# ---- section 4, D1 and D2: the author's decisions
n = find("The request says \"unknown\" for the pair port and the mesh cache")
sub(n, "I kept \"unknown\" in both boxes, because the request asks to discuss before I differ.",
    "I kept \"unknown\" in both boxes, because the request asks to discuss before I differ. "
    "Decided by the author on 2026-11-12: the box of the pair port now says \"estimated 64 GB/s\" (section 11.2). "
    "The rest of D1 is kept as it was written before that decision.")
n = find("I did not change these sections. The new open item names them (line 437).")
sub(n, "They need your decision, and possibly the tests of D1.",
    "They need your decision, and possibly the tests of D1. Decided by the author on 2026-11-12: the three statements were replaced "
    "with the texts P1 to P3 (section 11.3).")

# ---- section 6: which rows section 11 applied
n = find("These are outside the request. Each has a proposed correction.")
sub(n, "It replaced only the name there, and these items are still open.",
    "It replaced only the name there. Section 11 then applied ten items in full (F2, F3, F4, F5, F14, F16, F30, F31, F32 and F33) "
    "and F15 for line 110. Their rows are marked \"applied\". All other items are still open.")
for fid, where in (("F2", "11.4"), ("F3", "11.4"), ("F4", "11.3"), ("F5", "11.3"), ("F14", "11.5"), ("F16", "11.5"),
                   ("F30", "11.6"), ("F31", "11.4"), ("F32", "11.3"), ("F33", "11.4")):
    n = find(f"| {fid} |")
    sub(n, f"| {fid} |", f"| {fid} (applied, section {where}) |")
n = find("| F15 |")
sub(n, "| F15 |", "| F15 (applied for line 110, section 11.4. Lines 266 and 408 are open) |")

# ---- section 10.6 and the list "Not done" of section 10
n = find("### 10.6 Replacement texts for the older statements")
sub(n, "(proposed, not applied)", "(proposed here, applied in section 11)")
n = find("The author asked what the new statements would be.")
sub(n, "None of the three texts is in the report.",
    "At the end of section 10 none of the three texts was in the report. Section 11 applied them.")
n = find("- P1 to P3 and F1 to F35 are not applied.")
sub(n, "- P1 to P3 and F1 to F35 are not applied. They wait for the author's decision.",
    "- At the end of section 10, P1 to P3 and F1 to F35 were not applied. Section 11 applied P1 to P3 and the F items that it names.")

# ---- references: the raw rows of the 0.001 %, and the scratch folder of section 11
n = find("- [Ref5] ")
L[n - 1] = L[n - 1].rstrip() + (" Lines 118 to 122 and 128 to 132: the credit-stall cycles of the four links and the mesh cycles "
                                "of case w8M-c2 in the 0.2 s run and in the 2 s run (37,976 credit-stall cycles in 3,599,908,867 mesh cycles).")
n_edits += 1
ref38 = ("- [Ref38] `crb/tmp/agent-scratch/apply-p1-p3-2026-11-12/`, the scratch folder of section 11. `sweep_results.json`: the 72 findings of the "
         "search of section 11.5, by checker. `check3_results.json` and `check4_results.json`: the findings and the verdicts of the checks of "
         "section 11.7. `apply_report_p.py` with `texts_p.py`, `apply_report_p_fixes.py` and `apply_brief_p.py`: the edits. `sentences_p.py`: the "
         "comparison of the approved texts with the report lines. `structure_check.py`, `rates.py` and `render_parts.py`: the check scripts. "
         "`render/`: the renders that were viewed.")

# ---- section 11 in front of the references
sec = open(SEC, encoding="utf-8").read().rstrip("\n")
sec = (sec.replace("@@NREPORT@@", str(len(D_REPORT))).replace("@@LINESREPORT@@", ", ".join(map(str, D_REPORT)))
          .replace("@@SHAREPORT@@", SHA_REPORT).replace("@@SHABRIEF@@", SHA_BRIEF))
assert "@@" not in sec, [w for w in sec.split() if "@@" in w][:5]
k = find("## References")
L[k - 1:k - 1] = sec.split("\n") + [""]
assert L[-1] == "" and L[-2].startswith("- [Ref37]"), L[-2][:40]
L[-1:] = [ref38, ""]

if "--write" in sys.argv:
    open(P, "w", encoding="utf-8").write("\n".join(L))
print(("written, " if "--write" in sys.argv else "dry run ok, ") + f"{n_edits} edits in place, section 11 with {len(sec.split(chr(10)))} lines, "
      f"record now {len(L) - 1} lines; report lines that differ: {len(D_REPORT)}")
