#!/usr/bin/env python3
"""Merge the text blocks of the writers into one generator copy.

Each writer edited a private copy of gen_design.py and design_numbers.py and owns a list of top-level blocks (assignments
or functions, by name). This script takes each owned block from its owner's copy and puts it at the place of the same
block in the base copy. It also reports every difference that a writer made outside its own blocks (such an edit is not
merged).

Use: python3 merge.py <pe folder> <output folder>
"""
import ast
import os
import shutil
import sys

PE, OUT = sys.argv[1], sys.argv[2]
OWNERS = {
    "gen_design.py": {
        "w1": ["page", "glance_table", "WORDS"],
        "w2": ["s1_intro", "differences_table", "s1_attn", "s2_setup", "s2_notes", "s3_how", "split_table",
               "fig_stack", "fig_flow", "fig_work", "fig_ttft", "fig_tps", "fig_split_pf", "fig_split_dec"],
        "w3": ["s3_say", "fig_lanes", "s4_method", "s4_inputs"],
        "w4": ["clock_note", "factor_rows", "s4_read", "s4_wrong", "threads_note", "pred_table", "fig_pred", "fig_pred_tps"],
        "w5": ["can_table", "s52", "s53", "fig_path", "fig_block", "fig_kernel"],
        "w7": ["ab_table", "ab_notes"],
    },
    "design_numbers.py": {
        "w4": ["factor_basis"],
        "w5": ["cost_model", "block_table", "RUNS_LEAD", "runs_notes", "kernel_rows"],
        "w6": ["NUMERICS_HTML", "ATTN_HTML", "OUTSIDE_HTML"],
        "w7": ["CODE_ROWS", "PLAN_ROWS", "COMPARE_HTML", "COMPARE_ROWS", "OPEN_HTML"],
        "w8": ["REFS"],
    },
}


def blocks(src):
    """{name: (first line, last line)} of the top-level assignments and functions, 1-based. First occurrence of a name wins."""
    out = {}
    for n in ast.parse(src).body:
        name = None
        if isinstance(n, ast.FunctionDef):
            name = n.name
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            name = n.targets[0].id
        if name and name not in out:
            first = min([n.lineno] + [d.lineno for d in getattr(n, "decorator_list", [])])
            out[name] = (first, n.end_lineno)
    return out


def without(src, names):
    """The source with the named blocks replaced by a marker line, to compare what is outside them."""
    b = blocks(src)
    lines = src.split("\n")
    for name in sorted(names, key=lambda k: -b[k][0]):
        a, z = b[name]
        lines[a - 1:z] = [f"<<block {name}>>"]
    return lines


os.makedirs(OUT, exist_ok=True)
for f in os.listdir(f"{PE}/base/gen"):
    if f.endswith(".py"):
        shutil.copy(f"{PE}/base/gen/{f}", f"{OUT}/{f}")
problems = 0
for fname, owners in OWNERS.items():
    base = open(f"{PE}/base/gen/{fname}").read()
    bb = blocks(base)
    merged = base.split("\n")
    repl = []
    for w, names in owners.items():
        src = open(f"{PE}/agents/{w}/gen/{fname}").read()
        try:
            wb = blocks(src)
        except SyntaxError as e:
            print(f"!! {w} {fname}: syntax error {e}")
            problems += 1
            continue
        for name in names:
            if name not in wb or name not in bb:
                print(f"!! {w} {fname}: block {name} missing")
                problems += 1
                continue
            a, z = wb[name]
            new = src.split("\n")[a - 1:z]
            old = base.split("\n")[bb[name][0] - 1:bb[name][1]]
            repl.append((bb[name][0], bb[name][1], new, w, name, new != old))
        # edits outside the owned blocks
        try:
            mine, theirs = without(base, names), without(src, names)
            if mine != theirs:
                import difflib
                d = [l for l in difflib.unified_diff(mine, theirs, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
                print(f"!! {w} {fname}: {len(d)} changed lines OUTSIDE its blocks (not merged):")
                for l in d[:12]:
                    print("      " + l[:200])
                problems += 1
        except KeyError as e:
            print(f"!! {w} {fname}: cannot compare outside blocks ({e})")
            problems += 1
    for a, z, new, w, name, changed in sorted(repl, key=lambda r: -r[0]):
        merged[a - 1:z] = new
    open(f"{OUT}/{fname}", "w").write("\n".join(merged))
    done = sorted((w, name, changed) for _, _, _, w, name, changed in repl)
    print(f"{fname}: merged {len(repl)} blocks, {sum(c for _, _, c in done)} of them changed")
    print("   unchanged blocks: " + ", ".join(f"{w}:{n}" for w, n, c in done if not c))
    ast.parse(open(f"{OUT}/{fname}").read())
# the other writers' copies of the files with no owned block must equal the base
for w in sorted({w for o in OWNERS.values() for w in o} | {"w1", "w2", "w3", "w4", "w5", "w6", "w7", "w8"}):
    for f in ("predict.py", "pagelib.py", "figs_data.py", "figs_design.py", "figs_static.py"):
        if open(f"{PE}/agents/{w}/gen/{f}").read() != open(f"{PE}/base/gen/{f}").read():
            print(f"!! {w}: changed {f} (not merged)")
            problems += 1
    for f in OWNERS:
        if w not in OWNERS[f] and open(f"{PE}/agents/{w}/gen/{f}").read() != open(f"{PE}/base/gen/{f}").read():
            print(f"!! {w}: changed {f}, in which it owns no block (not merged)")
            problems += 1
print(f"{problems} problems")
sys.exit(1 if problems else 0)
