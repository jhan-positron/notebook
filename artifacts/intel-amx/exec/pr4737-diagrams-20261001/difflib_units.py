"""Diff -> per-unit code excerpts for the PR 4737 kv_cache.hpp page.

Parses `git diff -U3 BASE HEAD -- FILE`, records which NEW line numbers were
added and where deleted lines sit (anchored at the new line number that
follows them), and renders a unit (a list of new-line ranges) as HTML rows
with head line numbers. Context lines come from the head file itself, so a
unit may show whole functions, not only the diff's +-3 lines.
"""
import html
import subprocess

WT = "/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-i4500"
BASE = "30c4ac82cb"
HEAD = "bb32a80774"
FILE = "h/tron/models/kv_cache.hpp"


def git(*args):
    return subprocess.run(["git", "-C", WT, *args], check=True,
                          capture_output=True, text=True).stdout


def parse():
    head_lines = git("show", f"{HEAD}:{FILE}").split("\n")
    if head_lines and head_lines[-1] == "":
        head_lines.pop()
    diff = git("diff", "-U3", BASE, HEAD, "--", FILE).split("\n")
    added = set()           # new line numbers that are '+' lines
    deleted = {}            # anchor new line number -> [(old_no, text)]
    old_no = new_no = None
    for line in diff:
        if line.startswith("@@"):
            # @@ -a,b +c,d @@
            parts = line.split()
            old_no = int(parts[1][1:].split(",")[0])
            new_no = int(parts[2][1:].split(",")[0])
            continue
        if old_no is None:
            continue
        if line.startswith("+"):
            added.add(new_no)
            new_no += 1
        elif line.startswith("-"):
            deleted.setdefault(new_no, []).append((old_no, line[1:]))
            old_no += 1
        elif line.startswith("\\"):
            continue
        else:
            old_no += 1
            new_no += 1
    return head_lines, added, deleted


HEAD_LINES, ADDED, DELETED = parse()


def unit_rows(ranges, tail_dels=False):
    """Rows for the given inclusive new-line ranges.

    Returns a list of (kind, old_no, new_no, text) with kind in
    {'add', 'del', 'ctx', 'gap'}.
    """
    rows = []
    for i, (a, b) in enumerate(ranges):
        if i > 0:
            rows.append(("gap", None, None, ""))
        part = []
        for n in range(a, b + 1):
            for old, text in DELETED.get(n, []):
                part.append(("del", old, None, text))
            kind = "add" if n in ADDED else "ctx"
            part.append((kind, None, n, HEAD_LINES[n - 1]))
        if tail_dels:
            for old, text in DELETED.get(b + 1, []):
                part.append(("del", old, None, text))
        # drop trailing blank context lines of this range
        while part and part[-1][0] == "ctx" and part[-1][3].strip() == "":
            part.pop()
        rows.extend(part)
    return rows


def blame_commits(ranges):
    """Short ids of the commits that last touched the ADDED lines of the ranges."""
    shas = []
    for a, b in ranges:
        out = git("blame", "-l", "-s", "-L", f"{a},{b}", HEAD, "--", FILE)
        for ln in out.split("\n"):
            if not ln:
                continue
            sha = ln[:40]
            try:
                lineno = int(ln[41:].split(")")[0].strip())
            except ValueError:
                continue
            if lineno in ADDED and sha[:10] not in shas:
                shas.append(sha[:10])
    return shas


def render_rows(rows):
    # Rows are display:block spans; no newline between them (inside <pre> a
    # newline between block boxes would add an empty line).
    out = []
    for kind, old, new, text in rows:
        if kind == "gap":
            out.append('<span class="row gaprow"><span class="ln"></span><span class="ln">'
                       '</span><span class="gap">&#8942;</span></span>')
            continue
        o = "" if old is None else str(old)
        n = "" if new is None else str(new)
        sign = {"add": "+", "del": "-", "ctx": " "}[kind]
        out.append(f'<span class="row {kind}"><span class="ln">{o}</span>'
                   f'<span class="ln">{n}</span><span class="sg">{sign}</span>'
                   f'{html.escape(text)}</span>')
    return "".join(out)


def counts(rows):
    add = sum(1 for r in rows if r[0] == "add")
    dele = sum(1 for r in rows if r[0] == "del")
    return add, dele


if __name__ == "__main__":
    import sys
    # Dump: every added line number run and every deletion anchor.
    runs = []
    for n in sorted(ADDED):
        if runs and runs[-1][1] == n - 1:
            runs[-1][1] = n
        else:
            runs.append([n, n])
    print("ADDED runs (new line numbers):")
    for a, b in runs:
        print(f"  {a}-{b}  ({b - a + 1} lines)  first: {HEAD_LINES[a-1].strip()[:70]}")
    print("DELETED anchors (new line number -> count):")
    for n in sorted(DELETED):
        print(f"  {n}: {len(DELETED[n])}  first: {DELETED[n][0][1].strip()[:70]}")
    print("total added", len(ADDED), "total deleted", sum(len(v) for v in DELETED.values()))
