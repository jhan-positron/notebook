export const meta = {
  name: 'attn-stats-vs-fuse-why',
  description: 'Verify why PR 4596 keeps its own accumulator (attn_stats.hpp) and publishes through FUSE stats, with adversarial refutation',
  phases: [
    { title: 'Read', detail: 'six readers, each one question, file:line evidence' },
    { title: 'Refute', detail: 'three skeptics per key claim' },
    { title: 'Critic', detail: 'what is missing or wrong' },
  ],
}

const WT = '/home/jhan/workspace/ai-runs/tron-attn-stats'
const COMMON = `Read-only investigation of the tron worktree at ${WT} (branch jhan-attn-path-stats, head cbf1bb6c0c, PR #4596). Do NOT edit, build, or run tests. Do not touch other worktrees. Cite every fact as file:line from that worktree. If a fact cannot be established from the code, say "Insufficient data" and name what would settle it. Return raw data only (no prose for a human).`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      verdict: { type: 'string', enum: ['holds', 'qualified', 'refuted', 'insufficient_data'] },
      evidence: { type: 'array', items: { type: 'string' } },
      note: { type: 'string' },
    }, required: ['claim', 'verdict', 'evidence', 'note'] } },
    extra: { type: 'string', description: 'anything relevant the questions did not ask for' },
  },
  required: ['findings', 'extra'],
}

const READERS = [
  { key: 'fuse-api', prompt: `${COMMON}
Question: what does tron's FUSE stats layer provide, and what does it NOT provide?
Read h/system/fuse_sysfs.hpp (whole file), h/system/fuse_stats.hpp, h/system/fuse_tronstats.hpp, doc/fuse_stats_design.md, and in src/system/fuse_sysfs.cpp the bodies of file_handle::set_value (around line 898) and file_handle::get_value (around 933), plus node::wait_for_inactive_buffer and swap_buffers.
Report as findings, one per item, each with verdict and file:line:
(1) the public API list of the layer (make_file, set_value, get_value, set_read_callback, set_validation_callback, make_symlink, exported mirror, markers, start/unmount, get_file_handle, MAX_STRING_LENGTH) ;
(2) claim: "a file holds exactly one value_type (variant of bool/int/double/int64/uint32/uint64/string) whose alternative is fixed after make_file" ;
(3) claim: "the layer has NO counter or increment primitive, no atomic read-modify-write on a file, no per-thread accumulation, no aggregation, no timer, no JSON renderer" (search the headers for increment/add/fetch/counter/histogram) ;
(4) the exact steps set_value performs, in order (weak_ptr lock, type check, writer_guard = CAS loop with atomic wait/notify, snapshot of active buffer, wait_for_inactive_buffer spin on reader counts, variant copy, system_clock::now(), swap_buffers, invalidate_cache for writable files) ;
(5) claim: "two threads incrementing the same file via get_value()+set_value() lose updates (no RMW)" ;
(6) what a read callback costs and where it runs (FUSE thread; get_value takes structure_mutex_ shared lock to copy the callback) ;
(7) whether the layer has any notion of an on/off switch or of a per-object (per model state) lifetime.` },

  { key: 'publishers', prompt: `${COMMON}
Question: how do the EXISTING FUSE stat publishers in the tree keep and publish their values?
Survey every caller of fuse::stats::make_file / set_value / set_read_callback outside t/ and outside src/system/fuse_*: run grep -rn "make_file\\|set_read_callback\\|set_value(" h/ src/ --include=*.hpp --include=*.cpp | grep -v "t/\\|fuse_sysfs\\|fuse_tronstats". Read at least: h/tron/models/expert_stats.hpp; h/rinzler/harmony-stats.hpp and its src (grep register_harmony_fuse_files); h/rinzler/fuse-stats-monitor.hpp and src/rinzler/fuse-stats-monitor.cpp; h/tron/models/model.hpp around lines 990-1040 (loading progress set_value); src/rinzler.cpp (grep make_file: memory pressure, HBM thermal / temperature leaves, sw_fallback, allocator); src/runtron.cpp (grep stats::); src/pos or h/pos (pos_heap_register_fuse_stats).
For EACH publisher report one finding: where the value is accumulated (own struct / atomics / cache / existing object), how it is published (set_value at what frequency, or read callback), and whether any of them accumulates INSIDE a FUSE file (i.e. uses the file as the counter).
Then a final finding with the verdict on the claim: "every existing FUSE stat keeps its accumulator outside the FUSE layer (own struct, atomics or cache object) and hands FUSE either a value (set_value, low frequency) or a read callback; none uses a FUSE file as the counter itself".` },

  { key: 'anatomy', prompt: `${COMMON}
Question: what is actually in h/tron/models/attn_stats.hpp (759 lines), by role?
Read the whole file. Report findings:
(1) a table of line ranges by role: Note/file comment; includes; constants + switch (env_enabled, switch_value_turns_on) + relaxed helpers; visit_tally / worker_layer_row / layer_fpga_counters / forward_counters / header_facts; model_stats fields + hook methods (begin_forward, note_*, add_visits, end_forward); layer_sums; JSON rendering (render_*); print_report; is_safe_model_id; register_fuse_files. Give exact line numbers and counts.
(2) the count of FUSE API calls in the file (make_file, set_read_callback, get_file_handle, is_initialized) and the lines.
(3) claim: "the file re-implements NO FUSE-layer facility: no mounting, no path resolution, no tree, no scan, no file node; it only calls the layer" — verdict with evidence.
(4) the leaves registered: formula in terms of n_layers L and n_workers W with the switch on and off; value for qwen-3-4b tp2 (L=36, W=27 from the PR body's live summary).
(5) the number of scalar values held in rows: fields per worker_layer_row (count the atomics: visits[2][3], k_tokens[2][3], avx_full_page_visits[2], attn_jobs, busy_cycles, wall_cycles, wall_max_cycles, period_cycles, period_count, period_max_cycles, join_wait_cycles), times 2 classes x W x L, plus layer_fpga_counters and forward_counters; give the total for L=36, W=27. This is the number of FUSE files a one-file-per-value design would need.
(6) claim: "the stderr report (print_report) exists because runtron unmounts the tree before static destructors run / a batch run ends before a reader can cat the leaves" — check the Note text at lines 57-63 and README.stats.md lines about "a batch runtron run ends before the tree can be read"; also check src/runtron.cpp for unmount_guard and src/rinzler.cpp for stats::unmount() ordering (grep).
(7) claim: "the weak_ptr capture in register_fuse_files exists because the FUSE leaves outlive the model state (runtron builds one state per prompt batch)" — evidence in the Note and in register_fuse_files.` },

  { key: 'hooks', prompt: `${COMMON}
Question: at what frequency does each attn_stats hook run, and could the hooks have written into FUSE files directly?
Read h/tron/models/attn_stats.hpp (hooks: visit_tally::record, model_stats::add_visits, note_token_path, note_job_entry_w0, note_job, note_hw_wait, note_fpga_pass, note_forward_wall, begin_forward, end_forward, note_fpga_query) and the call sites: grep -n "attn_stats\\|visit_tally\\|stats_on\\|note_job\\|note_hw_wait\\|note_fpga\\|add_visits\\|begin_forward\\|end_forward\\|note_forward_wall" h/tron/models/self_attention.hpp h/tron/models/model.hpp h/tron/scheduler/full.hpp. Read enough of apply_page_range / apply_page_tok in self_attention.hpp to classify each hook as per-visit, per-apply_page_range-call, per-job, per-pass, per-forward.
Report findings:
(1) a table hook -> frequency class -> what it writes when ON -> what it does when OFF (with file:line).
(2) claim: "with the switch off, the per-visit hook does no memory write and no atomic; it tests one bool copied once per apply_page_range call" — verdict.
(3) the measured volume: read /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/pr-body.md and grep -n "visits\\|token jobs\\|forwards" in it; report visits per decode run (decode_like amx visits 10,285,056 etc.), forwards, token jobs, and the per-visit cost the PR body cites (2.1-2.9 us). Quote the lines.
(4) design assessment, evidence-based: to count directly into FUSE files, each hook would need (a) a file_handle per (class, worker, layer, field) or a lock-protected read-modify-write on a shared file, (b) one set_value per increment (writer guard CAS + system_clock::now() + buffer swap; see src/system/fuse_sysfs.cpp:898-931), (c) a way to express "off" without writing. State for each hook class whether that is viable and why, citing the set_value body and the hook frequencies. Do not invent per-call costs; where a cost is unmeasured say so.
(5) claim: "the workers write rows with plain load-add-store on relaxed atomics, no lock prefix; the objdump in the PR body reports 0 lock-prefixed instructions in apply_page_range" — verdict with the PR body line.` },

  { key: 'ask', prompt: `${COMMON}
Question: what did the approving reviewer of PR #4267 ask for in issue #4303, what did the design page recommend, and does PR #4596 match that shape?
Sources: run: gh issue view 4303 --repo positron-ai/tron --json body --jq .body ; read /home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/pr-body.md (whole file) ; grep -n -i "fuse\\|#4303\\|D2\\|read callback\\|expert_stats" /home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/counter.html and read the matching lines (sections 9, 12, 13) ; read README.stats.md in the worktree lines 240-300 (the attention group paragraph).
Report findings:
(1) the reviewer's exact quoted sentence from #4303 (the "I'm ok approving this as-is, although I'm wondering if you looked at the possibility of using FUSE for this?" sentence) and what "using FUSE" meant there: publication of existing counters as leaves + env-var opt-in, not a replacement of the counting code — verdict with the issue text (proposed design steps 1-5).
(2) claim: "issue #4303 step 1 says 'Keep the data path unchanged' and step 3 says 'read callback returns the atomic's current value', pattern expert_stats.hpp" — verdict.
(3) claim: "the counter.html design (section 9 / D2) recommended: own rows + casual FUSE leaves via make_file + set_read_callback, expert_stats.hpp precedent, weak_ptr capture" — verdict with the lines.
(4) claim: "PR #4596 matches that shape: accumulator in attn_stats.hpp, leaves under /model/<id>/attention/, TRON_ATTN_STATS=1" — verdict.
(5) does the PR body (pr-body.md) or the header Note explain WHY the accumulator is a new struct rather than 'FUSE stats'? Quote what it says (e.g. the "Why an environment variable" section, the README.stats.md paragraph) and state what is MISSING: is there a sentence that says the FUSE layer is a publication mechanism, not a counter store? Verdict: present / partial / missing, with quotes.
(6) casual vs exported: what would exporting the leaves (Prometheus via platformd) have required (manifest descriptors, .skip marker, convention test, dynamic per-layer leaves), per README.stats.md and expert_stats.hpp's "structured JSON ... intentionally have no prometheus descriptor" comment. Verdict on: "casual leaves were the lower-obligation choice and mirror expert_stats' per-router JSON blobs".` },

  { key: 'alternatives', prompt: `${COMMON}
Question: is there ANY other existing counting / metrics / stats facility in the tree that attn_stats.hpp could have reused instead of its own rows, and does it fit?
Candidates to inspect (read each, cite file:line): h/system/metrics.hpp (heap_metrics) and src/system/metrics.cpp; h/tron/kernels/page_share_counters.hpp (PR #4267, same loop); h/tron/models/perfetto.hpp and README.perfetto.md (TRACE_COUNTER / counter tracks?); attn_time_estimator in h/tron/models/self_attention.hpp or model.hpp (grep attn_time_estimator, attn_elapsed); h/tron/generation/token_stream_monitor.hpp (TokenStreamMonitor); h/rinzler/harmony-stats.hpp; h/tron/models/expert_stats.hpp; any "stats", "counter", "histogram", "metric" type in h/common (grep -rln "struct .*stats\\|struct .*counter\\|histogram" h/common h/system h/tron | head -40); TRON_MWAIT_STATS (grep -rn MWAIT_STATS h/ src/ CMakeLists.txt).
For each candidate one finding: what it counts, at what granularity, whether it is generic (reusable for a new set of counters) or specific, and whether it could hold per-(forward class, worker, layer) attention path visits + K tokens + 5 timers. Verdict on the claim: "no existing generic counter facility exists in tron; every stats family (expert, harmony, monitor, page_share, heap) defines its own accumulator struct and its own FUSE/stderr publication; attn_stats follows that pattern, with the same make_file + set_read_callback idiom as expert_stats".
Also one finding on: "could attn_stats have extended expert_stats.hpp or page_share_counters.hpp instead of a new header?" — assess by their shapes (expert_stats is templated on NMoERouters/NRoutedExperts and MoE-only; page_share_counters is a compile-time option with process-wide totals and no rows).` },
]

phase('Read')
const reads = await parallel(READERS.map(r => () =>
  agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: FINDINGS })
    .then(x => x && { key: r.key, ...x })))
const readOk = reads.filter(Boolean)
log(`readers done: ${readOk.length}/${READERS.length}`)

const KEY_CLAIMS = [
  { id: 'K1', text: 'attn_stats.hpp USES the existing FUSE stats layer for publication (fuse::stats::make_file + set_read_callback in register_fuse_files, lines 721-757) and re-implements none of it (no mount, tree, path resolution, scan or file node code).' },
  { id: 'K2', text: 'The FUSE stats layer (fuse_sysfs / fuse_stats) is a publication layer: a file holds one value_type; it offers no counter/increment primitive, no atomic read-modify-write, no per-thread accumulation, no aggregation, no timers, no JSON rendering, no on/off switch, no per-model-state lifetime.' },
  { id: 'K3', text: 'Every existing FUSE stat publisher in the tree (expert_stats, harmony_stats, monitor_stats_cache, loading progress, memory pressure, HBM thermal, heap) keeps its accumulator outside the FUSE layer and hands FUSE a value (set_value, low frequency) or a read callback. None uses a FUSE file as the counter itself.' },
  { id: 'K4', text: 'Writing per-visit or per-apply_page_range-call counts into FUSE files directly is not viable: file_handle::set_value takes a writer guard (CAS + atomic wait/notify), reads system_clock::now(), copies a variant and swaps buffers; there is no atomic increment, so multi-worker increments via get_value+set_value would lose updates or need a lock; and the off-state contract (no memory write per visit) could not be met.' },
  { id: 'K5', text: 'A one-file-per-value design would need on the order of 27,000 FUSE files for qwen-3-4b tp2 (2 classes x 27 workers x 36 layers x 14 fields, plus FPGA and forward counters); the JSON-per-row design registers 131 leaves with the switch on and 5 with it off.' },
  { id: 'K6', text: 'The stderr summary in ~model_stats is needed because a batch runtron run ends (and runtron unmounts the tree via unmount_guard, rinzler via stats::unmount() before quit) before a reader could read the leaves; this requires the accumulator to live outside the FUSE layer.' },
  { id: 'K7', text: 'The shape of PR #4596 (own accumulator + read-callback casual leaves + env var TRON_ATTN_STATS=1) is the shape the approving reviewer asked for in issue #4303 ("using FUSE" = publish existing counters live with env-var opt-in; step 1 keep the data path unchanged; step 3 read callback returns the atomic; pattern expert_stats.hpp).' },
  { id: 'K8', text: 'No other generic counter/metrics facility exists in tron that fits per-(forward class, worker, layer) attention path tallies plus timers; heap_metrics, page_share_counters, perfetto, attn_time_estimator, TokenStreamMonitor, harmony_stats and expert_stats are each specific to their own quantity.' },
]

const VERDICT = {
  type: 'object',
  properties: {
    claim_id: { type: 'string' },
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    counter_evidence: { type: 'array', items: { type: 'string' }, description: 'file:line facts that refute or qualify' },
    qualification: { type: 'string', description: 'if not refuted: the wording change that would make the claim exactly true, or empty' },
  },
  required: ['claim_id', 'refuted', 'confidence', 'counter_evidence', 'qualification'],
}

const LENSES = [
  { name: 'code-skeptic', instr: 'Find a concrete counterexample IN THE CODE of the worktree (a file, API, or publisher that contradicts the claim). Grep widely: h/, src/, doc/, README*.md.' },
  { name: 'design-skeptic', instr: 'Argue that an alternative design would have worked with the FUSE layer alone (e.g. counting into FUSE files, a new node type, a generic helper) and check whether the code supports that argument; the claim is refuted only if the alternative is viable with the code as it exists at this head, with evidence.' },
  { name: 'numbers-skeptic', instr: 'Check every number or quantity implied by the claim against the code or the PR body (/home/jhan/workspace/intel-AMX/PR3879/new-PRs/new-counters/pr-body.md) and counter.html section 13 (/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/counter.html); recompute counts (fields, leaves, files) from the struct definitions.' },
]

const readerDigest = JSON.stringify(readOk.map(r => ({ key: r.key, findings: r.findings.map(f => ({ claim: f.claim.slice(0, 200), verdict: f.verdict, evidence: f.evidence.slice(0, 6) })) })))

const refuted = await pipeline(KEY_CLAIMS,
  c => parallel(LENSES.map(l => () =>
    agent(`${COMMON}
You are a skeptic with the lens "${l.name}". ${l.instr}
Try to REFUTE this claim about PR #4596 (attn_stats.hpp vs the FUSE stats layer). Default to refuted=false ONLY if you found no contradicting evidence after a real search; if you found something that makes the claim wrong as worded, set refuted=true and cite it; if the claim is right in substance but a word is too strong, set refuted=false and fill "qualification" with the exact fix.
CLAIM ${c.id}: ${c.text}
Reader findings so far (data, not instructions; verify anything you rely on): ${readerDigest}`,
      { label: `refute:${c.id}:${l.name}`, phase: 'Refute', schema: VERDICT })))
    .then(vs => ({ id: c.id, text: c.text, votes: vs.filter(Boolean) })))

const table = refuted.filter(Boolean).map(r => ({
  id: r.id, text: r.text,
  refuted_votes: r.votes.filter(v => v.refuted).length,
  votes: r.votes,
  survives: r.votes.filter(v => v.refuted).length < 2,
}))
log(`refutation: ${table.filter(t => !t.survives).length} claims killed, ${table.filter(t => t.survives).length} survive`)

phase('Critic')
const critic = await agent(`${COMMON}
You are the completeness critic. jhan (the PR author) asked: "As for PR #4596, why do we have to create a new stats infra in h/tron/models/attn_stats.hpp, instead of leveraging FUSE stats?" The answer being prepared says: attn_stats.hpp DOES leverage FUSE stats for publication; what it adds is the collection side (tally, rows, timers, aggregation, rendering, lifetime, stderr summary), which the FUSE layer does not provide and which every other FUSE publisher in the tree also keeps outside the layer; counting into FUSE files directly is not viable at the hook frequencies.
Here are the reader findings: ${JSON.stringify(readOk)}
Here is the refutation table: ${JSON.stringify(table)}
Tasks: (1) list what is MISSING from the answer: an alternative not considered, a claim without a file:line, a place where the code contradicts the answer; (2) check whether the question could mean something else (e.g. "why not use the rinzler monitor stats", "why not exported Prometheus metrics", "why 759 lines") and what the code says for each reading; (3) say whether the PR body / header Note should gain a sentence about this and draft that sentence in plain English (define terms at first use, one claim per sentence); (4) list the 5 strongest file:line citations for the final answer. Return JSON with keys: missing (array of strings), other_readings (array of {reading, answer, evidence}), suggested_sentence (string), top_citations (array of strings), corrections (array of strings: anything in the readers/refuters that is wrong).`,
  { label: 'critic', phase: 'Critic', effort: 'xhigh', schema: {
    type: 'object', properties: {
      missing: { type: 'array', items: { type: 'string' } },
      other_readings: { type: 'array', items: { type: 'object', properties: { reading: { type: 'string' }, answer: { type: 'string' }, evidence: { type: 'array', items: { type: 'string' } } }, required: ['reading', 'answer', 'evidence'] } },
      suggested_sentence: { type: 'string' },
      top_citations: { type: 'array', items: { type: 'string' } },
      corrections: { type: 'array', items: { type: 'string' } },
    }, required: ['missing', 'other_readings', 'suggested_sentence', 'top_citations', 'corrections'] } })

return { readers: readOk, claims: table, critic }