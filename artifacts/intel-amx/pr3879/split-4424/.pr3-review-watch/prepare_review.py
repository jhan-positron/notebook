import datetime
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "review-80bce9a08d"
original = (ROOT / "body.md").read_text()
draft = original
edits = []


def replace(old, new, rules, location):
    global draft
    assert draft.count(old) == 1, (location, draft.count(old))
    draft = draft.replace(old, new)
    edits.append(dict(rules=rules, location=location, original=old, fix=new))


intro = original.split("### Background")[0].split("\n\n", 1)[1].strip()
replace(intro,
    "This PR (pull request) saves packed attention keys in blocks and shares the work with idle helper threads. "
    "In the measured 1,024-token runs, time to first token fell by 153 ms on 2 devices and 243 ms on 4 devices against PR #4887. "
    "The feature remains disabled in all build presets.",
    [2, 5, 8], "Short version")

replace("### Background\n\nWith the option on,",
    "### Background\n\nThe qwen3-4b model used below is the Qwen3 4-billion-parameter instruction-following model. "
    "The detailed results, decision thresholds and comparison revisions remain in Measurements. "
    "Words used here defines the technical terms.\n\nWith the option on,",
    [1], "Background: model name")

replace("| attention, head, Q, K, V | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors, K holds key vectors, and V holds value vectors. The KV cache stores K and V for past tokens. |",
    "| attention, head, Q, K, V, QK, PV | Attention combines saved token information using scores. A head is one attention computation channel. Q holds query vectors. K holds key vectors. V holds value vectors. The KV cache stores K and V for past tokens. QK is the query-key score calculation. PV combines attention probabilities with value vectors. |",
    [1, 2], "Words used here: QK and PV")

replace("| cell, band, standard deviation, paired t | A cell is one model, parallelism, prompt length, and attention configuration.",
    "| arm, cell, band, standard deviation, paired t | An arm is one binary with its runtime settings. A cell is one model, parallelism, prompt length, and attention configuration.",
    [1], "Words used here: arm")

old = "In the traced runs of 2026-09-14 it was 7 helpers plus the main thread at tp2, and 8 at tp4. Three cases are not shared and store on the thread that calls `save_k`. The first is a pass of at most 16 tokens, for example a decode step of the 8-user runs. The second is a caller that passes one worker: the handwritten plugins, and the unit tests except the three-thread section of `t_llama_unit` (the model and cache unit-test binary). The third is more than 128 workers."
replace(old,
    "In the traced runs of 2026-09-14, tp2 used 7 helpers plus the main thread. "
    "The tp4 run used 8 helpers plus the main thread.\n\nThree cases store on the calling thread alone:\n\n"
    "- A pass has at most 16 tokens, such as a decode step in the 8-user runs.\n"
    "- The caller passes one worker. This covers the handwritten plugins and the unit tests, except the three-thread section of `t_llama_unit` (the model and cache unit-test binary).\n"
    "- The caller passes more than 128 workers.",
    [2, 7, 8], "Background: helper counts and unshared cases")

old = next(line for line in original.splitlines() if line.startswith("- `batch::k_store_window_t` holds"))
replace(old,
    "One `batch::k_store_window_t` exists per minibatch. Its fields are:\n\n"
    "| Field | Purpose and size |\n|---|---|\n"
    "| `next_unit` | Assigns work units. It occupies its own 64-byte cache line, so claims do not invalidate the line that waiting threads poll. |\n"
    "| `opened`, `finished`, `n_units` | Count opened windows, finished helpers and work units. Together they occupy 12 bytes. |\n"
    "| `unit_start` | The unit table: `max_minibatch_size + 1` entries, at 4 bytes per entry. |\n"
    "| `helper_windows` | Each helper's entered-window count. The array has 128 entries and occupies 512 bytes. Its capacity bounds the shared worker count. |\n\n"
    "The generated plugins allow 1,024 items per minibatch. Their window state occupies 4,736 bytes, including alignment padding.",
    [7, 8], "The changes: window fields")

old = next(line for line in original.splitlines() if line.startswith("- `save_k_impl` takes"))
replace(old,
    "`save_k_impl` takes the worker index and worker count. For an unshared store, helpers return immediately. For a shared store, the sequence is:\n\n"
    "1. The main thread creates the work units and resets `next_unit` and `finished` to zero.\n"
    "2. It increments `opened` with release ordering.\n"
    "3. Each helper waits for its W-th shared window with an acquire read of `opened`.\n"
    "4. Every worker claims unit indices with an atomic add. It stores each unit it claims.\n"
    "5. Each helper increments `finished` with release ordering after its claim loop ends. It then returns.\n"
    "6. The main thread waits for all `n_workers - 1` helpers with acquire reads of `finished`. The watchdog checks this wait.\n\n"
    "Release and acquire are C++ memory orders for atomic operations. Writes made before a release become visible through the corresponding acquire. "
    "The main thread therefore observes every helper's row stores before it continues. "
    "The W-th shared call on each helper matches the W-th window opened by main.",
    [2, 7, 8], "The changes: shared-save protocol")

old = next(line for line in original.splitlines() if line.startswith("Note [QK orientation] in the kernel interface"))
replace(old,
    "Note [QK orientation] explains the order of the kernel's matrix operands. "
    "The query rows are the left operand. The packed K plane is the right operand. "
    "This reverses the order used by `main`'s row-major AMX kernel. "
    "The Note identifies the K store and the reader as the two places that perform the extra work. [h/tron/kernels/amx_attn_iface.hpp]",
    [2, 8], "The changes: QK orientation")

replace("That is not more than 16, so no window opens.",
    "This is below the sharing threshold. No window opens.",
    [2], "Decode TPS: threshold")
replace("Decode TPS is inside the band in all three cells, so the expectation holds.",
    "Decode TPS is inside the band in all three cells. This meets the stated expectation.",
    [2], "Decode TPS: result")
replace("inside the 0.40 TPS floor of the band", "inside the minimum band of 0.40 TPS",
    [6], "Decode TPS: band wording")
replace("The three store-path differences named above run in every decode pass, so they are a candidate cause of a difference of that size.",
    "The three store-path differences named above run in every decode pass. Hypothesis: they contribute to this measured difference.",
    [2], "Decode TPS: hypothesis")
replace("The store does not depend on the attention path, so the expected TTFT gain is about the same absolute size as `new` against `head`.",
    "The store does not depend on the attention path. The expected TTFT gain is about the same absolute size as `new` against `head`.",
    [2], "The store under the reader: expectation")

# Separate long result paragraphs without changing their measurements.
for prefix, breaks, location in [
    ("The traces of 2026-09-14", ["With the per-row scatter store,", "PR #3879 is", "The V store,"], "Background: trace results"),
    ("TPS is inside the band in all three cells. TTFT is lower", ["Those gains are smaller", "TTFT is higher by 599 ms"], "Reader results"),
    ("The kernel PR's TPS claim repeats within", ["The two sessions differ", "At tp4, measured"], "Session-control results"),
]:
    old = next(line for line in draft.splitlines() if line.startswith(prefix))
    new = old
    for marker in breaks:
        assert " " + marker in new
        new = new.replace(" " + marker, "\n\n" + marker, 1)
    replace(old, new, [7], location)

# Apply the separately recorded numeric correction to the proposed full text.
for old, new in [("0.88 TPS", "0.87 TPS"), ("0.44 TPS", "0.43 TPS"),
                 ("0.76 TPS", "0.77 TPS"), ("0.96 TPS", "0.95 TPS"),
                 ("1.26 TPS", "1.25 TPS"), ("0.72 TPS", "0.71 TPS"),
                 ("1.34 TPS", "1.33 TPS")]:
    draft = draft.replace(old, new)

(OUT / "description-edits.json").write_text(json.dumps(edits, indent=2) + "\n")
(OUT / "proposed-description.json").write_text(json.dumps({"body": draft}, indent=2) + "\n")
passes = json.loads((OUT / "passes.json").read_text())
passes.append({
    "pass": "plain-english",
    "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "findings": edits,
    "checked": ["Entire fetched PR description", "Three summary sentences: 88, 123 and 36 whitespace-delimited words", "Terminology, claim separation, paragraph structure and technical wording"],
    "limitations": ["Proposed full text saved for review; live description not changed", "Numeric band corrections in proposed text belong to the separate Wade pass"],
})
(OUT / "passes.json").write_text(json.dumps(passes, indent=2) + "\n")

rows = "".join(
    "<tr><td>" + html.escape(", ".join(map(str, e["rules"]))) + "<br>" + html.escape(e["location"]) + "</td><td><pre>" + html.escape(e["original"]) + "</pre></td><td><pre>" + html.escape(e["fix"]) + "</pre></td></tr>"
    for e in edits
)
counts = {rule: sum(rule in e["rules"] for e in edits) for rule in sorted({rule for e in edits for rule in e["rules"]})}
page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PR 4898 review</title>
<style>body{font:16px/1.55 system-ui,sans-serif;background:#fff;color:#17212b;max-width:1200px;margin:40px auto;padding:0 24px}h1,h2{line-height:1.2}a{color:#075aa8}table{width:100%;border-collapse:collapse}td,th{border:1px solid #ccd3d9;padding:12px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.5 ui-monospace,monospace;margin:0}td:first-child{width:13%}.note{background:#eff5fa;padding:18px;border-left:4px solid #176a9e}details{margin:24px 0}summary{cursor:pointer;font-weight:650}button{padding:9px 14px;background:#075aa8;color:white;border:0;border-radius:4px;cursor:pointer}</style>
<h1>PR #4898 review</h1><p class="note"><strong>Short version.</strong> No actionable production-code defect was found. The review found a test that checks completion only after its own thread joins, nine throughput bands rounded at the wrong stage, and description edits listed below.</p>
<p>Reviewed commit <code>80bce9a08d682677f970505eb0f314538a3f4aa8</code> against <code>0ee8671d355863658bbf292a12e04a566ac1af29</code>. Product tests were not rerun. Existing test records and generated code were inspected.</p>
<h2>Separate review passes</h2><ol><li>Normal review: no actionable source finding.</li><li>tron-code-review: capture helper completion immediately when the main save returns, before the test joins its threads.</li><li>wade-code-review: derive throughput decision bands from full-precision standard deviations. Nine displayed bands differ by 0.01 tokens/s/user. None changes a comparison's classification.</li><li>ben-review: no actionable interface or abstraction finding.</li><li>plain-english: terminology, long sentences and paragraph structure, below.</li></ol>
<h2>Description review</h2><p>""" + str(len(edits)) + " edited passages. Rule occurrence counts (a passage may violate more than one rule): " + html.escape(str(counts)) + ". Rules: 1 terminology, 2 one claim per sentence, 5 short summary, 6 literal wording, 7 paragraph structure, 8 short sentences.</p><table><thead><tr><th>Rule / location</th><th>Original</th><th>Correction</th></tr></thead><tbody>" + rows + "</tbody></table>" + """
<h2>Full proposed description</h2><p>This proposal preserves the detailed measurements, test records, limitations and planned follow-ups. It also incorporates the separate numeric-band correction. The live PR description has not been edited.</p><button onclick="navigator.clipboard.writeText(document.getElementById('draft').textContent).then(()=>this.textContent='Copied')">Copy proposed Markdown</button><details><summary>Expand the full proposed description</summary><pre id="draft">""" + html.escape(draft) + "</pre></details></html>"
(OUT / "review.html").write_text(page)
print(json.dumps({"edited_passages": len(edits), "rule_occurrences": counts, "proposed_description_characters": len(draft), "artifact": str(OUT / 'review.html')}))
