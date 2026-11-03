#!/usr/bin/env python3
"""Assemble the final body of one re-expressed draft PR.

Usage: python3 assemble_body.py N [--tests FILE] [--dry]
  N       2, 3 or 4 (the branch: PR2', PR3', PR4').
  --tests a local copy of exec/results/benstack-20261021/tests.txt (default: fetched from delphi-3bda over ssh).
  --dry   use made-up test rows (to check the pipeline before the gate reports); refuses to write the final file.

Reads bodies/prN-body.md, bodies/stack-section.md and status.json (pr_url per branch), builds the 3bda table from the
tests.txt rows of tags bpN and bpNv, substitutes BDA_TABLE_PRN and STACK_SECTION, runs the plain-English checks and the
word count, and writes bodies/prN-final.md. It never posts anything.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.join(HERE, "status.json")
BODIES = os.path.join(HERE, "bodies")
TESTS_REMOTE = "/home/jhan/workspace/intel-AMX/exec/results/benstack-20261021/tests.txt"
ORDER = ["t_k_vnni_layout", "t_amx_numerics", "t_amx_dispatch_dtype", "t_llama_unit", "t_heterogeneous_scheduler"]


def fetch_tests(path):
    if path:
        return open(path).read()
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "delphi-3bda", "cat " + TESTS_REMOTE],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ssh failed: " + r.stderr.strip())
    return r.stdout


def parse_rows(text, n):
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 4:
            continue
        tag, test, assertions, rc = parts[0], parts[1], parts[2], parts[3]
        envskips = parts[4] if len(parts) > 4 else ""
        message = " | ".join(parts[5:]) if len(parts) > 5 else ""
        if tag in (f"bp{n}", f"bp{n}v"):
            rows.append((tag, test, assertions, rc, envskips, message))
    # a repeated gate appends new rows: the last row per (tag, test) is the one that counts
    last = {}
    for r in rows:
        last[(r[0], r[1])] = r
    return [last[k] for k in dict.fromkeys((r[0], r[1]) for r in rows)]


def dry_rows(n):
    rows = []
    for tag in (f"bp{n}", f"bp{n}v"):
        for t in ORDER:
            rows.append((tag, t, "DRY 1,000 assertions in 10 test cases", "0", "env=[] skips=0", ""))
    if n == 2:
        rows.append(("bp2v", "t_amx_numerics-killswitch", "DRY 0 assertions (WARN: AMX path absent, case skipped)", "0",
                     "env=[TRON_AMX_DISABLE=1] skips=3", "AMX unavailable on this host - QK precision check skipped"))
    if n == 4:
        rows.append(("bp4v", "t_llama_unit-killswitch", "DRY 1,000 assertions in 10 test cases", "0", "env=[TRON_AMX_DISABLE=1] skips=0", ""))
    return rows


def compact(assertions):
    """'1,234 assertions in 56 test cases' -> '1,234 / 56'; anything else is kept as written."""
    m = re.search(r"(\d[\d,]*) assertions? in (\d+) test cases?", assertions)
    if m:
        return f"{m.group(1)} / {m.group(2)}"
    if re.fullmatch(r"\d+", assertions):
        return f"{int(assertions):,}"
    return assertions


def skips_of(envskips, message):
    """'env=[...] skips=3' plus the skip lines -> (3, ['QK precision check', ...])."""
    m = re.search(r"skips=(\d+)", envskips or "")
    count = int(m.group(1)) if m else 0
    names = re.findall(r"AMX unavailable on this host - (.+?) skipped", message or "")
    return count, names


def join_names(names):
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def table(rows, n, head):
    by_tag = {}
    for tag, test, assertions, rc, envskips, message in rows:
        by_tag.setdefault(tag, []).append((test, assertions, rc, envskips, message))
    lines = ["| Configuration | Build | Unit tests (assertions) | Result |", "|---|---|---|---|"]
    bullets = []
    counts = {}
    tag_results = {}
    for tag, meaning in ((f"bp{n}", "the option off"), (f"bp{n}v", "the option on")):
        tests = by_tag.get(tag, [])
        plain = [t for t in tests if not t[0].endswith("-killswitch")]
        kill = [t for t in tests if t[0].endswith("-killswitch")]
        cells = []
        fails = []
        skipped = []
        for test, assertions, rc, envskips, message in sorted(plain, key=lambda t: ORDER.index(t[0]) if t[0] in ORDER else 99):
            cells.append(f"`{test}` {compact(assertions)}")
            counts.setdefault(tag, {})[test] = assertions
            if rc != "0":
                fails.append(f"`{test}` (rc {rc})")
            sk, names = skips_of(envskips, message)
            if sk:
                skipped.append(f"`{test}` skips {sk} ({join_names(names) or 'reason in the log'})")
        result = f"{len(plain) - len(fails)} of {len(plain)} pass" if plain else "no rows"
        if fails:
            result += ", failed: " + ", ".join(fails)
        if skipped:
            result += ", skipped: " + ", ".join(skipped)
        tag_results[tag] = (plain, fails, skipped)
        lines.append(f"| `{tag}` ({meaning}) | ok at `{head[:10]}` | " + ". ".join(cells) + " | " + result + " |")
        for test, assertions, rc, envskips, message in kill:
            base = test.replace("-killswitch", "")
            sk, names = skips_of(envskips, message)
            res = "pass" if rc == "0" else f"FAILED (rc {rc})"
            if sk:
                res += f", {sk} checks skipped"
            lines.append(f"| `{tag}` under the kill switch | same binary | `{base}` {compact(assertions)} | {res} |")
    # one finding per tag, or one for both when both are clean
    off, on = f"bp{n}", f"bp{n}v"
    both_clean = all(tag in tag_results and not tag_results[tag][1] and not tag_results[tag][2] for tag in (off, on))
    if both_clean and counts.get(off) == counts.get(on):
        bullets.append(f"- `{off}` and `{on}`: every test passes. The assertion counts are the same under both values of the option.")
    elif both_clean:
        diffs = []
        for test in ORDER:
            a, b = counts.get(off, {}).get(test), counts.get(on, {}).get(test)
            if a and b and a.isdigit() and b.isdigit() and a != b:
                d = int(b) - int(a)
                diffs.append(f"`{test}` runs {abs(d):,} {'more' if d > 0 else 'fewer'} assertions with the option on ({int(a):,} against {int(b):,})")
        bullets.append(f"- `{off}` and `{on}`: every test passes." + (" " + ". ".join(diffs) + "." if diffs else ""))
    else:
        for tag in (off, on):
            if tag not in tag_results or not tag_results[tag][0]:
                continue
            plain, fails, skipped = tag_results[tag]
            if not fails and not skipped:
                bullets.append(f"- `{tag}`: every test passes.")
            else:
                parts = []
                if fails:
                    parts.append("failed: " + ", ".join(fails))
                if skipped:
                    parts.append("skipped: " + ", ".join(skipped))
                bullets.append(f"- `{tag}`: {len(plain) - len(fails)} of {len(plain)} pass. " + ". ".join(parts) + ".")
    for tag in (off, on):
        for test, assertions, rc, envskips, message in [t for t in by_tag.get(tag, []) if t[0].endswith("-killswitch")]:
            base = test.replace("-killswitch", "")
            sk, names = skips_of(envskips, message)
            verdict = "passes" if rc == "0" else f"fails (rc {rc})"
            if sk:
                bullets.append(f"- `{tag}` under the kill switch: `{base}` skips {sk} checks ({join_names(names) or 'see the log'}) "
                               f"with the message \"AMX unavailable on this host\", and its {compact(assertions)} remaining assertions pass. "
                               f"The kill switch reports AMX as unavailable. The skips are the expected result."
                               if rc == "0" else
                               f"- `{tag}` under the kill switch: `{base}` {verdict} with {sk} checks skipped ({join_names(names)}).")
            else:
                bullets.append(f"- `{tag}` under the kill switch: `{base}` {verdict} with no skipped check, {compact(assertions)} assertions.")
    return "\n".join(lines) + "\n\nWhat the table says:\n\n" + "\n".join(bullets)


def stack_section(status):
    s = open(os.path.join(BODIES, "stack-section.md")).read()
    urls = {}
    for k in ("2", "3", "4"):
        u = status["branches"].get(k, {}).get("pr_url", "pending")
        m = re.search(r"/pull/(\d+)", u or "")
        urls[k] = f"#{m.group(1)}" if m else None
    for k, ph in (("2", "PR2_URL"), ("3", "PR3_URL"), ("4", "PR4_URL")):
        # the PR # column
        s = s.replace(f"| {ph} |", f"| {urls[k]} |" if urls[k] else "| not yet open |")
        # the State column
        s = s.replace(f"draft until {ph} is taken", f"draft until {urls[k]} is taken" if urls[k] else "draft until the previous draft PR is taken")
    return s


def checks(body):
    counted = "\n".join(l for l in re.sub(r"## Words used here.*?(?=\n## )", "", body, flags=re.S).splitlines())
    words = len(counted.split())
    problems = []
    if ";" in body:
        problems.append(f"semicolons: {body.count(';')}")
    sp = re.findall(r"\bso that\b|\bbecause\b|\bsince\b|\bwhich means\b", body, flags=re.I)
    if sp:
        problems.append(f"splitting words: {sp}")
    if re.search(r"pull request", body, flags=re.I):
        problems.append("'pull request' present")
    left = re.findall(r"FILL_\w+|BDA_TABLE_PR\d|STACK_SECTION|PR\d_URL", body)
    if left:
        problems.append(f"placeholders left: {left}")
    if words >= 2000:
        problems.append(f"word count {words} >= 2000")
    if not body.rstrip().endswith("🤖 Generated with [Claude Code](https://claude.com/claude-code)"):
        problems.append("missing the generated-with line at the end")
    return words, problems


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("2", "3", "4"):
        sys.exit(__doc__)
    n = int(args[0])
    dry = "--dry" in args
    tests_path = args[args.index("--tests") + 1] if "--tests" in args else None
    status = json.load(open(STATUS))
    b = status["branches"][str(n)]
    body = open(os.path.join(BODIES, f"pr{n}-body.md")).read()
    rows = dry_rows(n) if dry else parse_rows(fetch_tests(tests_path), n)
    if not rows:
        sys.exit(f"no tests.txt rows for bp{n}/bp{n}v yet")
    body = body.replace(f"BDA_TABLE_PR{n}", table(rows, n, b.get("gate_head", b["head"])))
    body = body.replace("STACK_SECTION", stack_section(status).rstrip() + "\n")
    words, problems = checks(body)
    print(f"PR{n}': {len(rows)} test rows, {words} words (Words section excluded)")
    for p in problems:
        print("PROBLEM:", p)
    out = os.path.join(BODIES, f"pr{n}-final.md")
    if dry:
        print("dry run: not writing", out)
        print(body[body.find("Unit tests on 3bda"):body.find("### Pending")])
        return 1 if problems else 0
    open(out, "w").write(body)
    print("wrote", out)
    print("next: verify the worktree head, push the branch, then\n"
          f"  gh pr create --draft --repo positron-ai/tron --base {b['base']} --head {b['branch']} "
          f"--label \"Skip benchmarks\" --title \"{b.get('title', '<title>')}\" --body-file {out}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
