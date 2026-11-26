#!/usr/bin/env python3
"""Fill the page template with the real files and the saved run outputs."""
import html
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).parent
D = pathlib.Path("/home/jhan/workspace/random/from-claude/lint-tla-lean-on-tron")
TRON = pathlib.Path("/home/jhan/workspace/ai-runs/tron-env-vars/tron-main")
OUT = pathlib.Path("/home/jhan/workspace/random/from-claude/lint-tla-lean-on-tron.html")


def read(p):
    return pathlib.Path(p).read_text(encoding="utf-8")


def lines(path, first, last):
    return "\n".join(read(path).splitlines()[first - 1:last])


def between(text, start, stop, include_stop=True):
    i = text.index(start)
    j = text.index(stop, i)
    if include_stop:
        j += len(stop)
    return text[i:j]


def block(text, header):
    """One '=== header ...' block of the model checker output."""
    i = text.index(header)
    j = text.find("\n=== ", i + 1)
    return text[i:j if j != -1 else None].rstrip()


PROMPT = """You left a `#if 0` block in the diff, and I told you to delete it.
Turn that correction into a deterministic check for this repository.

1. State the rule in one sentence. Quote the bad line and the fixed line.
2. Choose the strongest place that can decide the rule: first the type system or
   a compiler flag, then a lint rule, then a test. Use a sentence in AGENTS.md
   only when no check can decide the rule, and say why.
3. Write the check. Its message must say why the pattern is wrong and what to
   write instead. The reader is an agent that has not seen this conversation.
4. Prove the check: show that it fails on the bad line and passes on the fixed line.
5. Run it on the whole tree. Report the old hits and record them in a baseline.
   Do not fix them now.
6. Wire the check as README.ci.md "Adding Lint Checks" says."""

rules_py = read(D / "lint-example/lint-source-rules.py")
tla = read(D / "CaptureSlot.tla")
lean = read(D / "ChunkCount.lean")
model = read(D / "outputs/model-check.txt")

fill = {
    "PROMPT": PROMPT,
    "SKILL": read(D / "lesson-to-lint/SKILL.md").rstrip(),
    "RULE_ROW": between(rules_py, "  # The correction:", '    good="#if TRON_HAS_AMX",\n  ),'),
    "LINT_OUT": read(D / "outputs/lint-source-rules.txt").rstrip(),
    "WIRING": read(D / "lint-example/wiring.diff").rstrip(),
    "ENV_OUT": read(D / "outputs/lint-env-vars.txt").rstrip(),
    "HOOK_OUT": read(D / "outputs/claude-hook.txt").rstrip(),
    "MODEL_REAL": "$ python3 -I capture_slot_check.py\n" + block(model, "=== The design as written"),
    "MODEL_BUG1": block(model, "=== Seeded bug 1"),
    "MODEL_SECONDS": "0.01",
    "CPP_TAKESTART": lines(TRON / "src/pos/trace_capture.cpp", 281, 286),
    "TLA_TAKESTART": between(tla, "TakeStart ==", "/\\ UNCHANGED <<slotId, stopReq, sigusr1, nextId>>"),
    "TLA_RULES": between(tla, "\\* A SIGUSR1 capture never runs", "OwnJob == (worker # \"idle\" /\\ slot # \"empty\") => (slotId = job)"),
    "LEAN": lean[lean.index("/-- The C++ expression"):].rstrip(),
    "RANGE_OUT": "$ python3 -I chunk_count_check.py\n" + read(D / "outputs/chunk-count-range-test.txt").rstrip(),
    "HARNESS_OUT": "$ bash chunk_evenly_harness/run.sh\n" + read(D / "outputs/chunk-evenly-harness.txt").rstrip(),
    "CPP_MERGE": lines(TRON / "h/tron/models/model.hpp", 260, 271),
}

page = read(HERE / "template.html")
for key, value in fill.items():
    marker = f"@@{key}@@"
    assert page.count(marker) == 1, (key, page.count(marker))
    page = page.replace(marker, html.escape(value, quote=False))
left = re.findall(r"@@[A-Z0-9_]+@@", page)
assert not left, left
OUT.write_text(page, encoding="utf-8")
print(f"wrote {OUT} ({len(page):,} bytes)")
