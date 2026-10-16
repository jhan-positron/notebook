"""Diff -> per-unit code excerpts for the PR 4424 diagram pages.

One DiffFile per target file. It parses `git diff -U3 BASE HEAD -- FILE`,
records which NEW (head) line numbers were added and where deleted lines sit
(anchored at the head line number that follows them), and renders a unit (a
list of head line ranges) as HTML rows with base and head line numbers.
Context lines come from the head file itself, so a unit may show whole
functions, not only the diff's +-3 lines.

Run as a script to dump the added-line runs and deletion anchors of a file:
  python3 difflib_units.py h/tron/models/kv_cache.hpp
"""
import html
import subprocess

WT = "/home/jhan/workspace/ai-runs/tron-vnnik-i4500m"
BASE = "be0d5565b3"   # main, the PR's base
HEAD = "9d5c7a389b"   # PR 4424 head (2026-10-08)


def git(*args):
    return subprocess.run(["git", "-C", WT, *args], check=True,
                          capture_output=True, text=True).stdout


class DiffFile:
    def __init__(self, file, base=BASE, head=HEAD):
        self.file, self.base, self.head = file, base, head
        self.head_lines = git("show", f"{head}:{file}").split("\n")
        if self.head_lines and self.head_lines[-1] == "":
            self.head_lines.pop()
        try:
            self.base_lines = git("show", f"{base}:{file}").split("\n")
            # the same count as wc -l: drop the empty string after the final
            # newline (the head list above does the same)
            if self.base_lines and self.base_lines[-1] == "":
                self.base_lines.pop()
        except subprocess.CalledProcessError:   # new file
            self.base_lines = []
        # the commits of the PR (base..head): blame may attribute an added line
        # (a brace the diff re-matched) to a base-side commit, which is not one
        # of the commits that "last touched the added lines"
        self.pr_shas = set(git("log", "--format=%H", f"{base}..{head}").split())
        self.added = set()       # head line numbers that are '+' lines
        self.deleted = {}        # anchor head line number -> [(old_no, text)]
        diff = git("diff", "-U3", base, head, "--", file).split("\n")
        old_no = new_no = None
        for line in diff:
            if line.startswith("@@"):
                parts = line.split()
                old_no = int(parts[1][1:].split(",")[0])
                new_no = int(parts[2][1:].split(",")[0])
                continue
            if old_no is None:
                continue
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                self.added.add(new_no)
                new_no += 1
            elif line.startswith("-"):
                self.deleted.setdefault(new_no, []).append((old_no, line[1:]))
                old_no += 1
            elif line.startswith("\\"):
                continue
            else:
                old_no += 1
                new_no += 1
        self.n_added = len(self.added)
        self.n_deleted = sum(len(v) for v in self.deleted.values())

    # -- units ---------------------------------------------------------------
    def unit_rows(self, ranges, tail_dels=False):
        """Rows for inclusive head-line ranges: (kind, old_no, new_no, text),
        kind in {'add', 'del', 'ctx', 'gap'}."""
        rows = []
        for i, (a, b) in enumerate(ranges):
            if i > 0:
                rows.append(("gap", None, None, ""))
            part = []
            for n in range(a, b + 1):
                for old, text in self.deleted.get(n, []):
                    part.append(("del", old, None, text))
                kind = "add" if n in self.added else "ctx"
                part.append((kind, None, n, self.head_lines[n - 1]))
            if tail_dels:
                for old, text in self.deleted.get(b + 1, []):
                    part.append(("del", old, None, text))
            while part and part[-1][0] == "ctx" and part[-1][3].strip() == "":
                part.pop()
            rows.extend(part)
        return rows

    def blame_commits(self, ranges):
        """Short ids of the commits that last touched the ADDED lines."""
        shas = []
        for a, b in ranges:
            out = git("blame", "-l", "-s", "-L", f"{a},{b}", self.head, "--",
                      self.file)
            for ln in out.split("\n"):
                if not ln:
                    continue
                sha = ln[:40]
                try:
                    lineno = int(ln[41:].split(")")[0].strip())
                except ValueError:
                    continue
                if lineno in self.added and sha in self.pr_shas and sha[:10] not in shas:
                    shas.append(sha[:10])
        return shas

    def added_runs(self):
        runs = []
        for n in sorted(self.added):
            if runs and runs[-1][1] == n - 1:
                runs[-1][1] = n
            else:
                runs.append([n, n])
        return [tuple(r) for r in runs]

    def coverage(self, unit_ranges):
        """Added head lines and deletion anchors not covered by any range."""
        covered = set()
        for a, b in unit_ranges:
            covered.update(range(a, b + 1))
        miss_add = sorted(n for n in self.added if n not in covered
                          and self.head_lines[n - 1].strip() != "")
        miss_del = sorted(n for n in self.deleted if n not in covered)
        return miss_add, miss_del


def render_rows(rows):
    # Rows are display:block spans; no newline between them (inside <pre> a
    # newline between block boxes would add an empty line).
    out = []
    for kind, old, new, text in rows:
        if kind == "gap":
            out.append('<span class="row gaprow"><span class="ln"></span>'
                       '<span class="ln"></span><span class="gap">&#8942;</span></span>')
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
    d = DiffFile(sys.argv[1])
    print(f"{d.file}: {len(d.base_lines)} base lines, {len(d.head_lines)} head lines, "
          f"{d.n_added} added, {d.n_deleted} deleted")
    print("ADDED runs (head line numbers):")
    for a, b in d.added_runs():
        print(f"  {a}-{b}  ({b - a + 1} lines)  first: {d.head_lines[a-1].strip()[:72]}")
    print("DELETED anchors (head line number -> count):")
    for n in sorted(d.deleted):
        print(f"  {n}: {len(d.deleted[n])}  first: {d.deleted[n][0][1].strip()[:72]}")
