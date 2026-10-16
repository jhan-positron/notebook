import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "review-80bce9a08d"
HEAD = "80bce9a08d682677f970505eb0f314538a3f4aa8"
BASE = "0ee8671d355863658bbf292a12e04a566ac1af29"
REVISION = f"Reviewed `{HEAD}` against `{BASE}` (`jhan-vnnik-2-amx`)."
SOURCE = f"https://github.com/positron-ai/tron/blob/{HEAD}/"


def write(name, body, comments=None):
    value = {"commit_id": HEAD, "event": "COMMENT", "body": body}
    if comments:
        value["comments"] = comments
    (OUT / (name + ".json")).write_text(json.dumps(value, indent=2) + "\n")
    print(name, len(body), "characters")


write("post-1-normal", """Normal review — completed before the separate skill passes.

No actionable production-code defect found in the reviewed change.

""" + REVISION + f"""

- Reviewed the nine-file diff, the block transpose and masks, source conversion, cache accessors, generated calls, and relevant callers.
- Traced source-row readiness, publication of shared work, helper completion, and the main thread's completion marks and downstream notifications. [Save implementation]({SOURCE}h/tron/models/model.hpp#L3303)
- Inspected the generated Qwen3 plugin from the build at this commit. Its main call follows the per-token K-channel waits. Its helper call follows the K-producing kernel.
- Checked the recorded feature-on, feature-off and AMX-dispatch-off test results at this commit. AMX means Intel Advanced Matrix Extensions. The disabled-dispatch numerics cases are placeholders. The kill-switch run skips the AMX-specific cases.

`git diff --check` passed during this review. I did not rerun product tests or benchmarks. The recorded host suite has 93 passes, one unidentified skip, and the documented `t_proxy_llama31` failure caused by the missing Python environment. The separate skill passes follow.
""")

inline = {
    "path": "t/t_llama_unit.cpp",
    "start_line": 4002,
    "line": 4005,
    "start_side": "RIGHT",
    "side": "RIGHT",
    "body": """[P2] Observe completion when the main save returns

`shared_save` joins both helper threads before returning to `check(before)` and `check_window`. The second window also starts only after those joins. Thus these assertions would still observe completed stores and final counters if the main-thread wait in `save_k_impl` were removed. They do not check the return-time guarantee that protects the following completion marks and downstream notifications. This conclusion is from control-flow inspection; I have not run that mutation.

Please capture `w.finished.load()` immediately after the main `save_k` call, before joining the test threads. Join the threads for cleanup, then assert that the captured count was `n_workers - 1` when sharing is enabled. Exercise a delayed helper and verify that removing the production wait makes this existing case fail. This tests the synchronization contract without reading the helper-written rows before thread cleanup.

Found in the separate `tron-code-review` pass. The production wait is present at this head.
""",
}
write("post-2-tron", """Separate pass: `tron-code-review`.

One coverage finding is attached to the shared-save test: its external thread joins hide whether the production call itself waited for all helpers.

""" + REVISION + """

Checked the packed and row-major paths, one-token and partial/full-block stores, mixed KV-write flags, worker-count limits, repeated windows, and generated operations that share a slot without writing it. KV means stored attention keys and values. The AMX kill switch does not change the store's layout or sharing decision. I also traced the fresh batch lifetime and the main-only completion marks, dispatch credits and downstream notifications.

The existing records include two mutation checks and feature-on/off runs at this commit. Neither mutation removes the production completion wait. No new product test, mutation run, or hardware workload was executed during this pass. The accepted CI exception tracked by #4865 remains separate from this finding.
""", [inline])

differences = json.loads((OUT / "band-differences.json").read_text())
table = "| Cell | Comparison | Posted band | Band from full-precision data |\n|---|---|---|---|\n"
for row in differences:
    cell = row["cell"].replace("q3-4b-", "").replace("-8u-p", ", prompt ")
    table += f"| {cell} tokens | {row['pair']} | {row['actual'].split(' / ')[0]} | {row['expected'].split(' / ')[0]} |\n"
write("post-3-wade", """Separate pass: `wade-code-review`.

Short version: one non-blocking description finding from checks 6 and 8. Nine throughput decision bands use rounded inputs. None of the comparison classifications changes.

""" + REVISION + """

**[P3] Calculate the band from unrounded standard deviations, then format it.**

Measurements defines the band as twice the larger sample standard deviation, with a minimum of 0.4 TPS. TPS means tokens per second per user. The body-generation script reads the rounded values from `summary.md` before multiplying them. The full-precision values remain in the recorded `pr3-E-cpu/summary.json` repetitions.

For example, the parent binary's standard deviation in the 2-device, 1,024-token cell is 0.4352492521 TPS. Twice that is 0.8704985042 TPS, displayed as **0.87 TPS**. Rounding the standard deviation to 0.44 TPS first produces the posted **0.88 TPS**.

""" + table + """
Please calculate from `summary.json` or the raw repetitions, and update the repeated band values in the prose. `tp2` and `tp4` mean 2 and 4 devices. The time-to-first-token bands do not need this correction.

I independently recomputed all 15 measurement rows and all 15 paired comparisons from the recorded repetitions. Their means, standard deviations, paired t statistics and inside/beyond classifications agree with the description. This finding concerns the displayed bands only.

The other check categories produced no additional source finding. The three commits are topical. The option gates and draft CI filtering match the workflow/configuration files. The current draft has no required checks reported by `gh pr checks --required`; its product jobs are skipped, while the reported lint, infrastructure and Debian smoke checks passed. No source test or sanitizer run was added during this pass. The test-completion finding is recorded once in the preceding `tron-code-review` pass.
""")

write("post-4-ben", """Separate pass: `ben-review`.

No actionable abstraction or interface finding.

""" + REVISION + """

I inspected the five-argument `set_k_block`, `store_k_block`, `save_k_impl`, and runtime `save_k` interfaces, including their callers and existing row-view helpers. Their arguments carry distinct selections or execution context. The worker index/count pair follows the generated kernels' existing convention. The mask and row-pointer array have one production construction site, so their presence does not establish a repeated abstraction problem.

Packed-address arithmetic stays in the tensor operation. The page accessor forwards a typed plane view. The existing source/destination row helpers are reused for the conversion paths. This pass was an interface review; it made no source changes and ran no product tests.
""")

edits = json.loads((OUT / "description-edits.json").read_text())
counts = {rule: sum(rule in e["rules"] for e in edits) for rule in sorted({r for e in edits for r in e["rules"]})}
table = "| Rule | Location and original text | Proposed correction |\n|---|---|---|\n"
for e in edits:
    old = e["original"].replace("|", "\\|").replace("\n", "<br>")
    new = e["fix"].replace("|", "\\|").replace("\n", "<br>")
    table += f"| {', '.join(map(str, e['rules']))} | **{e['location']}**: {old} | {new} |\n"
write("post-5-plain", """Separate pass: `plain-english`, Check mode, on the current PR description.

Short version: 16 passages need terminology, sentence or paragraph edits. The first two summary sentences contain 88 and 123 whitespace-delimited words. A three-sentence limit does not require putting all implementation details and comparisons in those sentences.

""" + REVISION + """

Rule occurrence counts (a passage can violate several rules): """ + ", ".join(f"rule {k}: {v}" for k, v in counts.items()) + """. Rule 1 defines terms, rule 2 separates claims, rule 5 requires a short summary, rule 6 uses literal wording, rule 7 separates points, and rule 8 prefers short sentences.

The replacements retain the detailed measurements and limitations elsewhere in the description. The full proposed description is supplied separately as a collapsed comment. It also includes the numeric-band correction from the Wade pass. The live description has not been edited.

<details>
<summary>Original passages and corrections</summary>

""" + table + "\n</details>\n")

proposed = json.loads((OUT / "proposed-description.json").read_text())["body"]
body = """Full proposed description from the separate `plain-english` review, based on the live description at commit `80bce9a08d`.

This is a suggested replacement, not an edit to the PR. It preserves the author's completed-CI link and incorporates the separate throughput-band correction. The detailed measurements, test limitations and follow-ups remain included.

<details>
<summary>Full proposed description</summary>

""" + proposed + "\n\n</details>\n"
assert len(body) < 65536
(OUT / "post-description-draft.json").write_text(json.dumps({"body": body}, indent=2) + "\n")
print("description-draft", len(body), "characters")
