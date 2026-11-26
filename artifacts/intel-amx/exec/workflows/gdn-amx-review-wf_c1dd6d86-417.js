export const meta = {
  name: 'gdn-amx-review',
  description: 'Review the GDN/AMX change (3 commits, 20 files) through 7 lenses, then adversarially verify every finding',
  phases: [{ title: 'Find', detail: '7 reviewers, one lens each' }, { title: 'Verify', detail: '3 skeptics try to refute the findings' }],
}
const R = '/home/jhan/workspace/ai-runs/tron-gdn-amx-review'
const COMMON = `
You review a code change in tron (an LLM inference program, C++20). You are a READER: do not modify any file, do not build, do not ssh to any server, do not run tests. Use absolute paths and "git -C"; never "cd" (a shell hook prints a directory listing). The machine allows 6 CPUs.

The change: 3 commits on top of base 72e1191804 in the frozen worktree ${R} (HEAD cbcb771f61):
  50b5a9c4ef  Add GDN path statistics (TRON_GDN_STATS)                       -> h/tron/models/gdn_stats.hpp, hooks in gdn_execution.hpp, model.hpp, ingest/src/TronCpp.hs, README.stats.md, t/t_gdn_stats.cpp
  28c5dda93d  Advance GatedDeltaNet prompt chains with a chain kernel and an AMX block kernel
                                                                              -> h/tron/kernels/gated_delta_net.hpp (gdn_recurrence_chain, window, slices), h/tron/models/gdn_rolling_executor.hpp (advance, working copy in slice layout), gdn_execution.hpp, h/tron/kernels/amx_gdn_iface.hpp, src/tron/kernels/amx_gdn.cpp, t/t_amx_gdn_numerics.cpp, t/t_gated_delta_net.cpp
  cbcb771f61  AMX attention kernels for 256-dim heads with 4 query heads per KV head -> amx_attn_iface.hpp, amx_attn.cpp, self_attention.hpp, t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp
See it with: git -C ${R} diff 72e1191804 HEAD -- <files>   and   git -C ${R} show <commit> --stat. Read the surrounding code, not only the hunks.
Background (read what you need): the design text /tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/design.txt (sections 5 and 6), the reader reports /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/understand/*.md, and the stand-alone prototype of the kernels with its measured results: /home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121/bench/gdn_kernels.hpp, amx_gdn_bench.cpp, and /home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121/bench/task3-*.txt.
Known facts, do not report them as findings: (1) the chain kernel is meant to give the BYTES of gdn_recurrence, and unit tests on the Xeon server pass for it (108,381 assertions); (2) the block kernel is meant to differ within an error band; (3) the working copy of the executor is now in a "slice layout" on purpose; (4) the kernel sets FTZ/DAZ on purpose because decay products underflow; (5) the three commits are not yet split further (Part 0 and Part A share one commit) - that is known; (6) the model is not on main yet, the base is an open pull request of another author: do not review code that this change does not touch.

Report only findings you can support with a file:line and a concrete failure scenario or a rule it breaks. Rank them. For each finding give: where (file:line in ${R}), what is wrong, the concrete scenario (inputs or state -> wrong result, crash, undefined behaviour, wasted time on a per-token path, a comment or doc that states something false, a test that cannot fail), and the smallest correction. Say "no finding" for an area you checked and found correct, with one line on what you checked. Do not pad.`
const FINDINGS = {
  type: 'object',
  properties: {
    checked: { type: 'array', items: { type: 'string' }, description: 'areas checked and found correct, one line each' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['bug', 'risk', 'test-gap', 'false-claim', 'style', 'cleanup'] },
          problem: { type: 'string' },
          scenario: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['title', 'file', 'line', 'severity', 'problem', 'scenario', 'fix'],
      },
    },
  },
  required: ['checked', 'findings'],
}
const LENSES = [
  { key: 'chain', prompt: `Lens: correctness of the chain path (commit 28c5dda93d, the parts without AMX). Check line by line: gdn_prepare_recurrence_token against gdn_recurrence (same expressions, same rounding points, same order of FP32 operations per lane; would any compiler contraction or reordering be possible?), gdn_recurrence_slice (the joined loops: is every sum the same sequence of fma as in gdn_recurrence for every token, also for n_tokens = 1, for the last token, across window boundaries?), the slice layout helpers (gdn_state_to_slices / gdn_slices_to_state for value_head_dim 16, 80, 128: offsets, widths, the narrow last slice), gdn_recurrence_chain_head (offsets of key head, value head, strides), and the executor: start_from_zero / start_from_checkpoint / write_checkpoint / validate_checkpoint_values / step() on a working copy / advance(): source == destination, a source that other holders read, groups that must write only their own bytes, alignment of every tron_mm_load_ps / store_ps, the window grid arithmetic (first_position, to_boundary), aliasing between output rows and gate rows ("Output may exactly alias the gate row"): the old step() read the gate and wrote the output per token; advance() postprocesses a window after the recurrence - does any caller pass an output buffer that aliases an INPUT row of a LATER token of the same window (mixed_qkv, decay, update, gate)? Check the generated plugin /home/jhan/workspace/intel-AMX/exec/results/gdn-20261120/plugin/qwen_3p5_4b.hpp call sites for buffer reuse (linear, linear_1, linear_2, linear_3, gated_delta_net) and the tests. Also check: noexcept on advance() with allocation or asserts inside, the concepts (gdn_activation_rows), ranges with non-random-access token containers, integer overflow, and what happens for a chain of exactly 1 token with working_copy access.` },
  { key: 'amxgdn', prompt: `Lens: correctness of the AMX block kernel of GDN (h/tron/kernels/amx_gdn_iface.hpp, src/tron/kernels/amx_gdn.cpp, its call site advance_window_with_block_kernel in gdn_rolling_executor.hpp, the tile region bracket in advance()). Derive the block form yourself from gdn_recurrence and check the code against it: tile operand layouts (row-major A operand, pair-interleaved B operand: lane n = even row in the low 16 bits, odd row in the high 16 bits), every tile load address and stride, every tile store address and stride (a tile store writes 16 rows of 64 bytes: can any store run past its buffer?), the transposes, the interleave index tables, the coefficient tables (w_tu by multiplication, lanes u > t), the triangular loop, the refusal test (bit-pattern compares; what about -0.0, NaN payloads, negative values?), the final write, the scratch layout and its static_asserts, strict aliasing of layout_of, the MXCSR scope (is MXCSR restored on every path including the early return? does pack_key_head need it?), and the Note text against the code (every sentence). Compare with the prototype gdn_kernels.hpp to find transcription slips. Check the call site: key_head_block offsets for key_heads_per_group > 1, value head indices, the fallback to gdn_recurrence_chain_head after a refusal (is the output of the refused head recomputed? is the window's data still intact after the kernel wrote into the output rows?), tally updates, begin_region/end_region pairing when advance() returns early or when no full window exists, a nested tile region if the same thread is inside an attention tile region, and thread safety of available(). Check the build wiring in src/tron/CMakeLists.txt and whether a build WITHOUT TRON_AMX_DISPATCH compiles the headers (block_kernel_shape false: is any amx_gdn symbol still referenced? is block_scratch_type well-formed?).` },
  { key: 'stats', prompt: `Lens: the GDN path statistics (commit 50b5a9c4ef plus the tally code of 28c5dda93d). Check gdn_stats.hpp line by line: data races (which thread writes which field, are relaxed atomics enough, the per-forward stamp slots and their fold in end_forward, forwards of two model states at once, EAGLE child states), bounds (worker index 0 = forward thread; n_workers = 1 + pool workers; operation id vs n_operations), the off-state cost on the per-call path, the wall computation across cores, JSON rendering (key names, commas, sizes against the FUSE limit, operations with no jobs), the exit report, FUSE registration and lifetime (weak_ptr, takeover), the forward_scope placement in model.hpp, the generator edit in ingest/src/TronCpp.hs, README.stats.md against the code (every key it names exists and means what it says). Then the hooks: gdn_execution.hpp and gdn_rolling_executor.hpp advance(): are tokens counted exactly once per key head on every path (token path for in-place chains, half path, amx path, a window that falls back, a chain of 1 token on a working copy via step())? Do the cycle fields add up to at most busy_cycles? Is half_full_block_tokens what its comment says (the volume the AMX path would take) when the block kernel is off, unavailable, or when the run has no full window? Are amx_blocks / amx_fallback_blocks counted per value head as documented? Is anything timed inside a per-token loop? Does t_gdn_stats.cpp / the hook test in t_gated_delta_net.cpp check what it claims?` },
  { key: 'attn256', prompt: `Lens: the AMX attention kernels for 256-dim heads (commit cbcb771f61). Check src/tron/kernels/amx_attn.cpp new code against the existing 128 x 4 kernels and against the layouts: packed query layout (8 panels), QK kernel (8 steps of 32 dims into 4 accumulator tiles: load addresses, strides, K page view as 64 rows of 256 bf16), the transposing store helper, PV kernel (4 groups of 64 output dims; V plane offsets for the pair-interleaved layout of h/tron/tensor/v_vnni.hpp at head 256; tile store addresses and row stride into the 16 x 256 output buffer: any overrun?), weight rounding. Check self_attention.hpp: the gates amx_serves_128x4 / amx_serves_256x4, the slot size from plugin::attention_kernels, packed_amx_query, apply_dense_amx_page, the grow-only resize (stale non-zero padding columns? a slot written by another shape? a model with both shapes?), the scratch buffers sized by head, statistics on the new path. Check that the 128 x 4 behaviour is unchanged (the three old kernel bodies must be identical: verify with git diff). Check the tests t_amx_numerics.cpp (do the 256 cases really exercise the 256 kernels, with tolerances that would catch a dropped dimension step?) and t_amx_dispatch_dtype.cpp (fakes for every entry point; link behaviour). Check the Notes and comments for statements that are now false ("the only translation unit", "one shape", "one of the two readers").` },
  { key: 'tronreview', prompt: `Lens: apply the user's review skills to the whole diff. Load each with the Skill tool and follow it: "tron-code-review" (execution-path coverage, stats/counter semantics, forward-pass bookkeeping, asynchronous ownership, cost on per-token paths such as hidden zero fills and copies, meaningful tests) and "folks-code-review" (its 35 checks: dead symbols and includes, debug switches, comments that contradict code, magic literals, duplicated logic, type and initialization choices, names, silent fallbacks, index mismatches, buffer lifetime, hot-path cost, test checks, claim checks, scope checks). Report every violation those skills define, with the check name.` },
  { key: 'style', prompt: `Lens: readability, abstractions and comments. Load each of these skills with the Skill tool and follow it on the diff: "ben-review" (missing shared domain abstractions, argument lists longer than four parameters, representation decisions outside the type that owns the data), "positron-code-review" (comments that hold review narration instead of lasting rationale), "cpp-coding-guide" (named constexpr values with the value in the name in the AMX kernel files, braces, hot-path rules: scratch buffers without a hidden fill, views instead of copies, test the condition first), "simplify-cpp-comments" (comments that restate code or are too long), and "plain-english" for comment prose (one claim per sentence, no idioms, terms from outside the code defined at first use, no semicolons joining claims). Note the repository convention conflict: the GDN headers of the base (gated_delta_net.hpp, gdn_rolling_executor.hpp, gdn_execution.hpp) use lower_snake constexpr names and braceless multi-line bodies; new code in those files follows the file. The AMX kernel files use NAME_<value>. Report concrete places, each with the corrected text or code.` },
  { key: 'tests', prompt: `Lens: do the tests verify intent? For each new or changed test case in t/t_gated_delta_net.cpp (the 5 new chain cases and the stats hook case), t/t_amx_gdn_numerics.cpp, t/t_gdn_stats.cpp, t/t_amx_numerics.cpp and t/t_amx_dispatch_dtype.cpp: name 2 or 3 plausible bugs in the code under test (for example: wrong slice offset for the narrow last slice, the read loop of the next token using the old decay, a window boundary off by one, the block kernel dropping the third piece of the split, a wrong decay product w_tu for u > 15, state written when the kernel refuses, tokens counted twice, a dropped dimension step in the 256 QK kernel) and decide from the test code whether the case would fail. List the bugs no test would catch, with the smallest test that would. Also check: tolerances that are so loose they cannot fail (compute what a real bug would produce), cases that pass by skipping, test names that do not say what is protected, real model slug strings in test sources (a configure-time audit rejects them), tests whose expected values were copied from the implementation, and missing cases the design asks for (design.txt section 5.6 row "Tests"): chains that do not start on a block boundary, the fallback cases, the split rule range.` },
]
phase('Find')
const found = await parallel(LENSES.map(l => () =>
  agent(COMMON + '\n\n' + l.prompt, { label: 'find:' + l.key, phase: 'Find', schema: FINDINGS })
    .then(v => v ? { key: l.key, ...v } : null)))
const all = []
for (const f of found.filter(Boolean)) {
  f.findings.forEach((x, i) => all.push({ id: `${f.key}-${i + 1}`, lens: f.key, ...x }))
}
log(`${all.length} findings from ${found.filter(Boolean).length} reviewers`)
const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'partly', 'unclear'] },
          evidence: { type: 'string', description: 'what you read (file:line) and why the finding holds or does not' },
          corrected_fix: { type: 'string', description: 'the fix you would apply, exact text or code where short; empty when refuted' },
        },
        required: ['id', 'verdict', 'evidence', 'corrected_fix'],
      },
    },
  },
  required: ['verdicts'],
}
phase('Verify')
const N = 3
const chunks = Array.from({ length: N }, () => [])
all.forEach((f, i) => chunks[i % N].push(f))
const verified = await parallel(chunks.map((c, i) => () => c.length === 0 ? Promise.resolve({ verdicts: [] }) :
  agent(COMMON + `\n\nYou are a SKEPTIC. Below are findings of other reviewers about this change. For EACH finding, open the code and try to REFUTE it: is the cited line what the finding says, does the scenario really happen, does another line already prevent it, is the "rule" real (for a style finding: does the skill or the file's own convention really ask for it)? Default to "refuted" when you cannot reproduce the reasoning from the code. For a confirmed finding give the fix you would apply. Findings:\n` + JSON.stringify(c, null, 1),
    { label: 'verify:' + (i + 1), phase: 'Verify', schema: VERDICTS })))
const verdicts = {}
for (const v of verified.filter(Boolean)) for (const x of v.verdicts) verdicts[x.id] = x
return {
  checked: found.filter(Boolean).map(f => ({ lens: f.key, checked: f.checked })),
  findings: all.map(f => ({ ...f, verdict: verdicts[f.id] || null })),
}
