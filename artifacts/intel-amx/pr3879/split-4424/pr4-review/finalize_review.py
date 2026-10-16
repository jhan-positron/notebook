from pathlib import Path
import html
import json
import re

p = Path(__file__).parent
head = 'e7d06a126766272f73483ef886c77d37c807a5ff'
base = 'dfafd13dce74376ebc762eafa9763684dd021d03'
url = 'https://github.com/positron-ai/tron'

def source(path, line, label=None):
    return f'<a href="{url}/blob/{head}/{path}#L{line}">{html.escape(label or f"{path}:{line}")}</a>'

body = (p / 'body-proposed.md').read_text()
body = body.replace(
    'The measured accelerator-assisted throughput is within the comparison band of the main branch.',
    'The measured accelerator-assisted throughput differs from the main branch by less than the experiment’s threshold for a change.')
body = body.replace(
    'The relevant Perfetto spans are',
    'Perfetto records timed operations as spans.\nThe relevant spans are')
body = body.replace(
    '- **EAGLE:** Unit tests cover its storage-view state.',
    '- **Forward-path coverage:** The new conversion assertions call helpers directly. A test through the real forward path is still needed to protect the conversion call and its ordering after staging.\n- **EAGLE:** Unit tests cover its storage-view state.')
body = body.replace(
    '[h/tron/kernels/dotter.hpp:174–208]',
    f'[dotter implementation]({url}/blob/{head}/h/tron/kernels/dotter.hpp#L174)')
body = body.replace(
    '[nix/cmake-tron-test-build.nix]',
    f'[Nix test configuration]({url}/blob/{head}/nix/cmake-tron-test-build.nix)')
body = body.replace(
    '[.github/workflows/cmake-single-platform.yml:355–356]',
    f'[CMake configuration]({url}/blob/{head}/.github/workflows/cmake-single-platform.yml#L355)')
body = body.replace(
    '[.github/workflows/publish-deb.yml:55–70]',
    f'[publishing trigger]({url}/blob/{head}/.github/workflows/publish-deb.yml#L55)')
old = (p / 'body-latest.md').read_text()
tables = re.findall(r'(?:^\|.*\n)+', old, re.M)
assert len(tables) == 10
assert all(t in body for t in tables)
assert len(body) < 65536
(p / 'body-proposed.md').write_text(body)

notes = json.loads((p / 'notes.json').read_text())
notes['wade'] = {
    'coverage': 'Check 33: same production-forward coverage gap as the Tron pass.',
    'description_corrected': [
        'Checks 6 and 17: the measured bf16/128 dotter loads vectors; its constructor does not convert the query to fp32.',
        'Checks 6 and 8: the earlier parent tie at token 247 does not prove the current binary has the same tie.',
        'Checks 7 and 8: draft CI product jobs were skipped; the package campaign is pending; host suite had a failure and an unidentified skip.'
    ],
    'preference': 'Check 30: consider avoiding per-slot atomic mask reads in k_forget_row when no packed layout can be enabled. No timing or disassembly establishes the cost.',
    'limits': ['Automated spelling and near-identifier checks unavailable: spellchecker not installed.', 'No independent build, hardware run, UBSan run, or production-forward mutation.'],
    'history': 'Four topical nonmerge commits. No fixup cluster. No posted review or bot findings at snapshot.'
}
notes['ben'] = {
    'verdict': 'No additional findings.',
    'evidence': 'k_storage_ref pairs physical storage and its state index. Row access reuses const_k_row_view and k_row_view. set_k_block shrinks from five runtime arguments to four. copy_storage_slot retains five independent inputs; the count predates this PR.'
}
(p / 'notes.json').write_text(json.dumps(notes, indent=2) + '\n')

groups = [
    ('1, 2, 3A, 3B, 4, 5, 33', 'Tests and measurements', 'Inspected assertions, gates, names, fixture consumers, mutation logs and binary revisions. Found missing coverage through the production forward path. Placeholder and skipped AMX checks are disclosed.'),
    ('6, 7, 8, 9, 17', 'Claims and description', 'Corrected the dotter explanation, unsupported current-binary tie claim, pending campaign language and CI coverage. Preserved all ten original result tables.'),
    ('10, 11, 12, 35', 'Scope, history and ownership', 'Inspected all 13 changed files and four nonmerge commits. No unrelated hunk or fixup cluster found. Shared storage headers have test consumers. No posted reviews or bot findings were available to reconcile.'),
    ('13, 14, 15, 16, 18–25', 'Code and prose', 'Inspected names, declarations, constants, consumers, helpers, comments, trace changes and placement. Extracted added prose and ran the width check. Automated spelling and near-identifier checks did not run because the spellchecker was unavailable.'),
    ('26–29, 31', 'Ownership and concurrency', 'Traced saved masks, physical storage references, pending page lifetime, worker join, staging drain, EAGLE view reset and transfer-buffer ownership. No confirmed defect in the inspected paths.'),
    ('30, 32', 'Cost and observability', 'Conversion has its own trace span. Eager dotter construction is a measured-path hypothesis, not an established cause. The disabled-layout mask loop is a separate performance preference below.'),
    ('34', 'Workarounds', 'The hardware-operation row-major policy is an intended design choice linked to issue #4500. Existing rollback and CI limitations remain tied to issues #4444 and #4865.'),
]
rows = ''.join(f'<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{html.escape(c)}</td></tr>' for a,b,c in groups)

report = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PR 4901 — four review passes</title>
<style>
body{{margin:0;background:#f7f8fa;color:#172330;font:16px/1.6 system-ui,sans-serif}}
main{{max-width:1000px;margin:auto;padding:36px 24px}}h1{{font-size:30px}}h2{{font-size:23px;margin-top:36px}}h3{{font-size:18px}}
a{{color:#005d9d}}code{{font-size:.9em;overflow-wrap:anywhere}}section,.intro{{background:white;border:1px solid #d3dbe2;border-radius:8px;padding:20px 24px;margin:20px 0}}
.finding{{border-left:5px solid #b66000;padding-left:18px}}.fixed{{border-left:5px solid #007f72;padding-left:18px}}.muted{{color:#465766}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #d3dbe2;padding:10px}}th{{background:#eaf0f5}}
.flow{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}.step{{background:#edf4fa;border:1px solid #789ab4;border-radius:5px;padding:8px 12px}}.critical{{background:#fff2df;border-color:#b66000}}
li{{margin:8px 0}}blockquote{{border-left:3px solid #9aaeba;margin-left:0;padding-left:15px}}details{{margin:16px 0}}
</style><main>
<h1>PR 4901: four separate review passes</h1>
<p><a href="{url}/pull/4901">Open pull request</a> · Head <code>{head}</code><br>Base <code>{base}</code></p>
<div class="intro"><h2>Short version</h2>
<p>The review found a missing test through the real model execution path. No new correctness defect was confirmed in the inspected code. The description was rewritten to preserve measured results and expose unresolved results, skipped checks and pending experiments.</p></div>
<p><strong>Terms:</strong> A forward pass is one model execution over scheduled tokens. K is the attention-key cache. VNNI is the packed layout used for matrix reads. AMX is the CPU matrix instruction set. FPGA is the accelerator card. Staging copies cached rows into transfer buffers. EAGLE is a speculative-decoding storage view.</p>

<section><h2>1. General review</h2>
<p>Inspected the entire diff, immediate callers and relevant unchanged ownership code. No confirmed new correctness defect was found in those paths.</p>
<ul><li>Full and partial saves, mixed-layout scoring, dense-page selection, append and token reuse, storage copies, EAGLE storage, staging and the package preset were inspected.</li>
<li>The author's token mismatches and AMX-disabled performance regression remain unresolved. Neither successful focused tests nor passing draft checks establish merge readiness.</li>
<li>The reviewed implementation was measured at <code>ea94e95a4e</code>. The published head adds only four benchmark-record rows. That difference was checked in Git.</li></ul>
</section>

<section><h2>2. tron-code-review</h2>
<div class="finding"><h3>Coverage: protect the production conversion call</h3>
<p><strong>Location:</strong> {source('h/tron/models/model.hpp',1847)}.</p>
<p>The new save tests invoke <code>state.convert_pending_k_blocks()</code> themselves. Their assertions verify the helper but do not protect its call from the real forward path. [{source('t/t_llama_unit.cpp',4066)}]</p>
<blockquote><code>state.convert_pending_k_blocks();<br>check_blocks(/*converted=*/true);</code></blockquote>
<p>The existing heterogeneous forward test creates four live tokens. It checks forward statistics and does not complete a 16-token block or assert conversion. [{source('t/heterogeneous_scheduler_compile.cpp',914)}]</p>
<p><strong>Consequence:</strong> deleting the production call, or moving it before the staging barrier, is not distinguished by the new conversion assertions. This is a coverage finding, not an observed production failure.</p>
<p><strong>Smallest remedy:</strong> extend an existing forward test to complete a previously partial block. After return, check the packed-state bit and retained K values. Use the production entry point throughout. For the ordering contract, hold a staging reader until the barrier and verify its row-major reads before release.</p>
<p><strong>Discriminating check:</strong> removing the production conversion call must fail the new forward test. This mutation was proposed, not run.</p></div>
<h3>Inspected ordering</h3>
<div class="flow" role="img" aria-label="Workers join, staging drains, queued blocks convert, logits are delivered">
<span class="step">Workers join</span><span>→</span><span class="step">Staging drains</span><span>→</span><span class="step critical">Queued blocks convert</span><span>→</span><span class="step">Logits delivered</span></div>
<p class="muted">Control-flow order only. No timing or duration is implied. [{source('h/tron/models/model.hpp',1836)}]</p>
<p>Pending entries retain the physical storage offset and its layout-state index. Scheduler-owned books keep pages alive through the forward pass. EAGLE resets its view after that pass. Staging copies source rows into owned transfer buffers before submitting the transfer. The later transfer reads those buffers, not the K plane being converted.</p>
<p><strong>Conditions inspected:</strong> layout on and off, AMX enabled and disabled, hardware and software operation policies, empty and partial runs, mixed layouts, append and reuse, and restored storage. This was source inspection. No new hardware workload, EAGLE model execution or sanitizer run was performed.</p>
</section>

<section><h2>3. wade-code-review</h2>
<p><strong>Check 33 — coverage:</strong> the production-entry test gap above also applies in this pass.</p>
<div class="fixed"><h3>Checks 6 and 17 — description corrected</h3>
<p>The old description said, “The generic dotter converts its 128-value query row to fp32 at construction.” The measured path selects the specialized <code>bf16</code>, 128-value dotter. Its constructor loads four vectors. [{source('h/tron/models/self_attention.hpp',1950)}; {source('h/tron/kernels/dotter.hpp',174)}]</p>
<p>So that conversion cannot explain the measured construction cost. The rewritten description states the actual specialization and keeps eager construction as an unmeasured hypothesis.</p>
<p><strong>Checks 6 and 8:</strong> the parent revision's exact tie at token 247 does not establish the same tie in this binary. The rewrite requests current-binary logits and labels the explanation as a hypothesis.</p>
<p><strong>Checks 7 and 8:</strong> the rewrite names CI workflows, triggers and option settings. It distinguishes passing infrastructure checks from skipped product jobs. It also preserves the failed host test, unidentified skip and pending package campaign.</p></div>
<h3>Check 30 — nonblocking performance preference</h3>
<p>Could the disabled-layout configuration return before scanning per-slot masks? The changed token-clear path calls <code>k_forget_row</code>, whose loop reads the converted-block and saved-row atomics even when no packed layout is enabled. [{source('h/tron/models/kv_cache.hpp',2478)}; {source('h/tron/models/kv_cache.hpp',2562)}]</p>
<p>The smallest change would be a compile-time guard when the feature is disabled. Insufficient data: disassembly or an option-off append benchmark is needed to establish emitted cost. This preference is not an explanation for the measured AMX-disabled regression, which used the layout option enabled.</p>
<h3>Check record</h3><table><thead><tr><th>Check numbers</th><th>Area</th><th>Result and limits</th></tr></thead><tbody>{rows}</tbody></table>
</section>

<section><h2>4. ben-review</h2>
<p>No additional abstraction or parameter-list finding.</p>
<ul><li><code>k_storage_ref</code> names the shared concept that pairs a physical storage slot with its layout-state entry. Pending conversion uses that pair.</li>
<li>The row helpers reuse the existing <code>const_k_row_view</code> and <code>k_row_view</code> types.</li>
<li><code>set_k_block</code> changes from five runtime parameters to four. The five inputs of <code>copy_storage_slot</code> predate this PR. Their count alone does not justify a refactor.</li></ul>
</section>

<section><h2>Validation and description update</h2>
<ul><li><strong>Run during this review:</strong> Git diff and history inspection, <code>git diff --check</code>, added-prose extraction, the prose width check, and GitHub head, body, comments and checks queries.</li>
<li><strong>Read from the author's records:</strong> focused tests, saved-row and hardware-policy mutations, the host-suite log, and CPU/FPGA benchmark summaries. No independent build or hardware benchmark was run.</li>
<li><strong>Unavailable:</strong> automated spelling and near-identifier checks, a production-forward mutation, a sanitizer run, and an EAGLE model run.</li>
<li><strong>Source records:</strong> <code>/home/jhan/workspace/intel-AMX/exec/results/pr4-20261012/</code>, especially <code>tests-pr4.txt</code>, the two mutation-result files, <code>host-suite-pr4.txt</code>, <code>pr4-E-cpu/summary.md</code> and <code>pr4-E-fpga/summary.md</code>. Benchmark-summary headers contain stale revision text. The per-arm binary versions identify the measurements.</li>
<li><strong>plain-english:</strong> rewrote the opening, explanations, evidence limits and CI section. Retained all ten original result tables, measured revisions, unresolved investigations and pending campaign. Retained the existing glossary so readers can interpret the terms.</li></ul>
<p>Review artifacts: <a href="body-original.md">original description</a>, <a href="body-latest.md">author's latest description before the edit</a>, <a href="body-proposed.md">rewritten description</a>, <a href="notes.json">structured findings</a>, <a href="pr.diff">reviewed diff</a>.</p>
</section></main></html>'''
(p / 'review.html').write_text(report)
print(f'Prepared description: {len(body)} characters; all {len(tables)} tables retained.')
print('Wrote review.html and completed separate-pass notes.')
