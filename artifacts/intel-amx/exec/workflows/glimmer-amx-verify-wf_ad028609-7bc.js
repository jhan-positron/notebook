export const meta = {
  name: 'glimmer-amx-verify',
  description: 'Verify the code facts and the measurement recipe for Muse Glimmer kv_mul-16 AMX support, then judge the implementation design',
  phases: [
    { title: 'Read', detail: 'five readers, one area each' },
    { title: 'Refute', detail: 'two refuters per reader output' },
    { title: 'Design', detail: 'two proposals, one judge' },
  ],
}

const CTX = `
Context (do not re-derive): tron is the inference program; runtron its CLI. A read-only checkout of tron main is at
/home/jhan/workspace/ai-runs/tron-main-ro (HEAD 26b6df7d82; origin/main is 6198824246, one merge ahead; if a file you
cite differs between the two, say so: use \`git -C /home/jhan/workspace/tron diff 26b6df7d82 6198824246 -- <path>\`).
Goal of the project: make the AMX software-attention kernels (h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp,
dispatch in h/tron/models/self_attention.hpp) serve kv_mul 16 (16 query heads per KV head, head size 128) in addition to
today's kv_mul 4, for the model Muse Glimmer 30B (32 query heads, 2 KV heads, head 128, 52 layers of which 39 are
sliding-window 2048 software-only layers and 13 full-attention layers that go to the FPGA when USE_HW_ATTN is unset).
Constraint from the user: implement on main, preserve the current code as much as possible (minimal diff, no refactor,
no rename unless unavoidable). The existing design report is /home/jhan/workspace/intel-AMX/muse-glimmer/muse-glimmer-amx.html
(read its section 4 change list; your job is to verify or correct it against the code, not to trust it).
Report facts with file:line citations from the tree above. Never guess; if you cannot verify, say "unverified" and why.
Use bash (grep -n, sed -n) with absolute paths; the shell cwd resets between calls.
`

const FACTS_SCHEMA = {
  type: 'object',
  properties: {
    area: { type: 'string' },
    facts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, claim: { type: 'string' }, citation: { type: 'string' }, confidence: { type: 'string', enum: ['verified', 'unverified'] } },
      required: ['id', 'claim', 'citation', 'confidence'] } },
    changes_needed: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, lines: { type: 'string' }, today: { type: 'string' }, change: { type: 'string' }, why: { type: 'string' } },
      required: ['file', 'lines', 'today', 'change', 'why'] } },
    risks: { type: 'array', items: { type: 'string' } },
    corrections_to_report: { type: 'array', items: { type: 'string' }, description: 'where muse-glimmer-amx.html section 4 is wrong or incomplete' },
  },
  required: ['area', 'facts', 'changes_needed', 'risks', 'corrections_to_report'],
}

const READERS = [
  { key: 'kernels', prompt: `${CTX}
Area: the kernels. Read ALL of h/tron/kernels/amx_attn_iface.hpp and src/tron/kernels/amx_attn.cpp in the tree.
Establish, with line citations:
1. Every place the number 4 (the group size) is baked in: constants, loop bounds, the "columns 4..15 zero" contract, the
   transposing store in qk_rowmajor_128x4 (rows 0..3 only), the P conversion loop in weights_times_v_128x4, comments and Notes.
2. The exact AVX-512 transpose used (unpacklo/hi_ps, unpacklo/hi_pd, shuffle_f32x4 0x88). Derive which selector pairs
   (stage-3 selector, stage-4 selector) produce output rows 4..7, 8..11, 12..15 of a full 16x16 transpose; state the
   derivation lane by lane so a reviewer can check it. (Expected: row 4q+k uses stage-3 0x88 for q in {0,2} and 0xdd for
   q in {1,3}, stage-4 0x88 for q in {0,1} and 0xdd for q in {2,3}; verify or refute.)
3. Whether the tile multiply counts change with 16 live columns (QK: 4 dim steps x 4 token blocks; PV: 2 halves x 2 slices x 4).
4. The thread_local P scratch: rows 4..15 are zero padding "never written after thread init"; what happens if one thread
   serves a 16-group model (all rows written) and later a 4-group call (do stale rows matter? note output row i comes from A row i).
5. The Q pack buffer size (Q_PACK_ELEMS_2048 = 16 x 128) and whether 16 heads x 128 dims fit exactly.
6. The two possible minimal implementations: (A) add a template parameter group_heads to the three kernels, keep the
   bodies, instantiate explicitly for 4 and 16 in amx_attn.cpp; (B) add a runtime size_t group_heads argument. For each,
   list every signature that changes and every caller/fake that must change (grep amx_attn_h128g4 across h/ src/ t/).
7. shape_ok and eligible: the minimal change to accept kv_mul 16 as well.
Write the changes_needed list for this area at the line level.` },
  { key: 'dispatch', prompt: `${CTX}
Area: the dispatch and caller buffers in h/tron/models/self_attention.hpp (grep -n amx_attn_h128g4 and kv_mul there; read
lines 240-300, 1520-1570, 1640-1700, 1700-1830, 1840-1960 at least), and attn_accum / scratchpad sizes
(scratch_query_width, scratch_query_heads, scratch_kv_heads, max_minibatch_size) and h/tron/models/attn_stats.hpp.
Establish with citations:
1. Every buffer the AMX path uses and whether its size follows the geometry (s_pages tensor<kv_mul,64>, amx_o 16x128,
   amx_qpack slot 4096 B, corr/m_new/sum arrays) or is hard-coded to 4.
2. Every comment that says "4 heads", "rows 0..3", "columns 4..15", "kv_mul-4 shape" and would become wrong with 16.
3. The three dispatch sites (around 1536, 1743, 1879): what they evaluate; whether anything else in the dense path
   assumes 4 (e.g. the static_assert on sizeof(s_pages), the packed-Q resize comment).
4. The dense-page predicate is_dense_amx_page with sliding_window_size: for a 2048 window and 64-token pages, how many
   pages per (layer, KV head) are dense at steady state; where the planner drops out-of-window pages (h/tron/models/model.hpp ~2476-2497).
5. attn_stats: does the "AMX-eligible" / avx_full_page_visits accounting or the header line (shape, amx_available,
   "fitting shape") derive from amx_attn_h128g4::shape_ok / eligible, so it follows automatically, or is 4 hard-coded there too?
6. Stack use: with kv_mul 16, s_pages is 16x64 fp32 = 4 KB and amx_o 8 KB per call; are these inside a worker thread with a
   known stack size (grep stack size settings) - any risk?
7. For an ingested plugin (Muse Glimmer is one): confirm software attention for its software_only layers goes through
   apply_page_range in self_attention.hpp (same template) and that activation_scalar is bf16 for the tp executors
   (h/tron/models/common.hpp btensor_t element). Cite.` },
  { key: 'tests', prompt: `${CTX}
Area: the tests and build wiring. Read t/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp (whole files), the references in
t/t_llama_unit.cpp and h/tron/tensor/v_vnni.hpp to amx_attn_h128g4, t/CMakeLists.txt around lines 600-630, CMakeLists.txt
line 46 (TRON_AMX_DISPATCH), CMakePresets.json (deb preset, native preset), and src/tron/kernels CMake rules for the -mamx flags.
Establish with citations:
1. What t_amx_numerics covers today (pack layout test, QK vs dotter, PV envelope) and exactly how to add kv_mul-16 cases
   with the least new code (e.g. templating the fixtures on the group size and running both 4 and 16), including the
   q_pack layout test's "padding columns stay untouched" branch which has no padding at 16.
2. t_amx_dispatch_dtype: it defines CPU fakes for every amx_attn_h128g4 entry point in its own TU and drives a 4-head /
   1-KV-head model. If the kernels become templates on group size, what must the fakes become (explicit specializations?
   definitions of the primary template?) so that the linker still never pulls amx_attn.o; and how to add a kv_mul-16
   model case (16 heads / 1 KV head) cheaply. Check how the probe's q array is sized.
3. Whether any other test or tool references the kernel names (grep -rn "128x4\\|GROUP_HEADS_4\\|amx_attn_h128g4" over
   h/ src/ t/ tools/ stats/ doc/ README*.md).
4. The build recipe used on delphi-3bda for AMX worktrees: read /home/jhan/workspace/intel-AMX/exec/td-20261016/build-variant.sh
   and /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/chain.sh (the build step) and report the exact cmake
   configure line (preset native, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON), the targets, where ingest traces come from,
   and how fake-label tests are run on 3bda (SYSTEM_CONFIG handling; see also exec/split-verify3.sh for the test invocation).` },
  { key: 'blast', prompt: `${CTX}
Area: blast radius of accepting kv_mul 16. Which models become AMX-eligible (head size 128 and kv_mul == 16, on a bf16
executor)? Sources: config/models.yaml (every model entry; the llama plugin's llm_configuration values in h/tron/plugins/*.hpp
and config/model_definitions.py), and the generated ingested-plugin headers, which exist only in build trees on delphi-3bda:
run \`ssh delphi-3bda 'grep -rl "attention_geometry" /var/tmp/jhan/tron-td-clean/gen --include=*.hpp | head -50'\` and then
grep each header for its attention_geometry{...} line (pattern attention_geometry{N, kv_geometry{M, H}}) and list
(model, n_heads, n_kv_heads, head_size, kv_mul). Also report for each: sliding-window layers vs full (software_only vs
kv_slot_candidate counts in the header) so the reader knows how much CPU attention the model has.
Also: which models have kv_mul 8 with head 128 (they stay ineligible; just list them). Confirm Muse Glimmer's header
(ingested_meta_models_Muse_Glimmer_30B.hpp) geometry line and its 39/13 operation split with line numbers from the 3bda copy.
Finally: is any production-tagged model (config/models.yaml tags) among the newly eligible set other than Glimmer? That
decides whether the change touches production numerics beyond Glimmer.` },
  { key: 'measure', prompt: `${CTX}
Area: the measurement recipe. The user wants, on delphi-3bda: Muse Glimmer runtron runs with the attention path counters on
(TRON_ATTN_STATS=1) to see AVX / AMX / FPGA (AoF) visit counts per layer, and decode and prefill performance with AMX on vs
off (TRON_AMX_DISABLE=1), same binary. Read these scripts fully and extract the recipe:
- /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/campaign.sh and chain.sh and README.md (runtron cells on our half,
  arms as environments, FUSE leaf snapshots, exit report, placement() per tp, hugepage file, guard, serving takeover via
  platformd, restore);
- /home/jhan/workspace/intel-AMX/exec/sync4424-20261002/campaign.sh (the functions library the td probe sources: RES, LOG,
  placement, guards, watch_run, status) and /home/jhan/workspace/intel-AMX/exec/q4b-fpga-20260921/dut.sh (serving-down/up);
- /home/jhan/workspace/intel-AMX/exec/lib-guard.sh function list (campaign_guard_acquire, ci_lease_busy, rinzler_stop_serving,
  rinzler_takeover_if_idle, other_user_active, blackout_active);
- /home/jhan/workspace/intel-AMX/exec/attnstats-20261002/gen_compare.py (how the exit report / leaves are parsed).
Report: (1) the exact runtron command shape for an ingested model on our half (model name for Glimmer: find the runtron
model slug for tp2 and tp4 from config/models.yaml lines 684-712: slug + executor -> e.g. ingested-meta-models--Muse-Glimmer-30B-tp2;
confirm the naming rule from another ingested model used in attnstats-20261002, ingested-qwen-3-4b-instruct-2507-tp2);
(2) which log lines give decode TPS ("average tok/s"), prefill time ("Parsing the prompt took"), TTFT; how earlier
campaigns computed prefill throughput (grep exec/sync4424* exec/wedperf* exec/results for "prefill" or "TTFT" or "Parsing");
(3) how the attention stats exit report looks (7 lines per model state; per-layer avx/amx/fpga fields) and where the FUSE
leaves are; (4) the guard sequence and the platformd takeover, and the time constraints (takeover hold 01:40-04:30 UTC,
nightly lease ~03:37-13:20 UTC); (5) weights: does runtron need anything beyond the model name (default_weights
positron-ai/meta-models--Muse-Glimmer-30B-ingest-best-gptq; check on 3bda whether /opt/positron/weights holds it:
ssh delphi-3bda 'ls /opt/positron/weights/huggingface/ /opt/positron/weights/huggingface/positron-ai 2>/dev/null | grep -i glimmer'
and how earlier runtron runs of ingested models found their weights (grep -rn "default_weights\\|--weights\\|hf_id" in the
scripts and in tron README.models.md); (6) known traps listed in those scripts' headers (FUSE stale mount, hugepage wait,
RUNPATH, NFS script replacement). Propose the cell list: tp2 and tp4, 8 users, prompts 1024 and 2048 (window limit), 256
generated tokens, arms amxon/amxoff, USE_HW_ATTN unset (13 FPGA layers) plus a USE_HW_ATTN=0 control; estimate the
wall time per run from earlier logs of similar runs (cite the log).` },
]

const REFUTE_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, verdict: { type: 'string', enum: ['holds', 'refuted', 'unverifiable'] }, evidence: { type: 'string' } },
      required: ['id', 'verdict', 'evidence'] } },
    missing: { type: 'array', items: { type: 'string' }, description: 'facts or changes the reader should have found but did not' },
  },
  required: ['verdicts', 'missing'],
}

phase('Read')
const results = await pipeline(
  READERS,
  r => agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: FACTS_SCHEMA }),
  async (facts, r) => {
    if (!facts) return null
    const lenses = ['wrong-line-or-wrong-file: re-open every citation and check the text says what the claim says',
                    'incompleteness: what did the reader miss? grep independently for every other place the group size 4 or the kernel names are assumed']
    const votes = await parallel(lenses.map((lens, i) => () => agent(`${CTX}
You are a skeptical refuter (lens: ${lens}). Below is a reader's fact sheet for area "${r.key}". For EVERY fact id, re-verify
it against the tree and give a verdict; default to "refuted" when the citation does not support the claim. Then list what is
missing. Fact sheet (JSON):
${JSON.stringify(facts, null, 1)}`, { label: `refute:${r.key}:${i}`, phase: 'Refute', schema: REFUTE_SCHEMA })))
    return { key: r.key, facts, refutations: votes.filter(Boolean) }
  }
)

const verified = results.filter(Boolean)
log(`verified areas: ${verified.map(v => v.key).join(', ')}`)

phase('Design')
const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    approach: { type: 'string' },
    diff_outline: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, hunk: { type: 'string' }, sketch: { type: 'string' } }, required: ['file', 'hunk', 'sketch'] } },
    est_changed_lines: { type: 'number' },
    reviewer_objections: { type: 'array', items: { type: 'string' } },
    tests: { type: 'array', items: { type: 'string' } },
  },
  required: ['approach', 'diff_outline', 'est_changed_lines', 'reviewer_objections', 'tests'],
}
const factsBlob = JSON.stringify(verified.map(v => ({ key: v.key, facts: v.facts, refutations: v.refutations })), null, 1)
const designs = await parallel([
  ['A-template', 'Approach A: template parameter group_heads (values 4 and 16) on pack_q_group / qk_rowmajor / weights_times_v, bodies generalized, explicit instantiation in amx_attn.cpp, shape_ok accepts 4 or 16, keep namespace amx_attn_h128g4 and every other name; the _128x4 suffix becomes _128 (or keep it and explain).'],
  ['B-runtime', 'Approach B: a runtime size_t group_heads argument on the three kernels, loop bounds runtime, the 16-row transpose behind a branch; shape_ok accepts 4 or 16; keep every name.'],
].map(([k, desc]) => () => agent(`${CTX}
Verified facts for all five areas (JSON): ${factsBlob}
Design ${desc}
Produce the full diff outline hunk by hunk for every file (kernels header, kernels .cpp, self_attention.hpp comments and
calls, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp fakes and new case, any other reference found). Minimize the diff;
preserve the existing code; match the file's naming rules (value-suffix constant names like GROUP_HEADS_4; literals need
names per the C++ guide). Then list the objections a strict reviewer (Wade: dead symbols, names, comments that contradict
code, magic literals, tests that bypass the changed path) would raise against this approach, honestly.`, { label: `design:${k}`, phase: 'Design', schema: DESIGN_SCHEMA })))

const JUDGE_SCHEMA = { type: 'object', properties: {
  winner: { type: 'string' }, reasoning: { type: 'string' },
  grafts: { type: 'array', items: { type: 'string' } },
  final_change_list: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, change: { type: 'string' } }, required: ['file', 'change'] } },
  open_questions_for_user: { type: 'array', items: { type: 'string' } } },
  required: ['winner', 'reasoning', 'grafts', 'final_change_list', 'open_questions_for_user'] }
const judged = await agent(`${CTX}
Judge the two designs below for: correctness, diff size (the user said "preserve the current code as much as possible"),
performance of the hot loop (per-page kernels, decode), reviewer acceptance (Wade/Ben/Runar style reviews in positron-ai/tron),
testability. Pick one, graft the best ideas of the other, and write the final file-by-file change list. Also name
decisions only the user can make (e.g. whether the namespace name amx_attn_h128g4 stays).
Designs: ${JSON.stringify(designs.filter(Boolean), null, 1)}`, { label: 'judge', phase: 'Design', schema: JUDGE_SCHEMA })

return { verified, designs: designs.filter(Boolean), judged }