export const meta = {
  name: 'review-fix-diff',
  description: 'Review the unreviewed fix diff of the GDN/AMX branch (cbcb771f61 -> aacdd287c0), then try to refute each finding',
  phases: [{ title: 'Find' }, { title: 'Verify' }],
}

const COMMON = `
You review a C++ change in the git worktree /home/jhan/workspace/ai-runs/tron-gdn-amx (branch jhan-gdn-amx).
The change under review is ONLY the diff between commit cbcb771f61 (already reviewed) and commit aacdd287c0 (final head):
  git -C /home/jhan/workspace/ai-runs/tron-gdn-amx diff cbcb771f61 aacdd287c0 -- <files>
That diff holds the fixes made after an earlier review. Nobody has reviewed it and it has never been compiled with the real build (only a syntax check ran).
Background: tron is an inference program. GDN = GatedDeltaNet, a recurrent layer type. The branch adds (a) a "chain kernel" that advances a run of prompt tokens (bit-identical to the per-token recurrence), (b) an AMX block kernel that advances 32 tokens at once (amx_gdn.cpp), (c) AMX attention kernels for 256-wide heads, (d) GDN counters (gdn_stats.hpp, TRON_GDN_STATS=1).
Hard rules:
- Read-only. Do not edit, build, commit, or run tests. Do not use ssh. Do not touch any machine named delphi-* (measurements run there now). Do not use the network.
- You may run git commands and read files with at most 2 processes at a time.
- Report only defects that the fix diff introduced or left in the lines it touched. Do not report style taste.
- Every finding needs file, line (at the final head) and concrete evidence (quote the code).
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'integer' },
          severity: { type: 'string', enum: ['bug', 'test-wrong', 'test-vacuous', 'doc', 'nit'] },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['title', 'file', 'line', 'severity', 'problem', 'evidence', 'fix'],
      },
    },
    checked: { type: 'string' },
  },
  required: ['findings', 'checked'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted'] },
          reason: { type: 'string' },
          corrected_fix: { type: 'string' },
        },
        required: ['title', 'verdict', 'reason'],
      },
    },
  },
  required: ['verdicts'],
}

const LENSES = [
  {
    key: 'executor',
    prompt: `Lens: the executor refactor. Files: h/tron/models/gdn_rolling_executor.hpp, h/tron/models/gdn_execution.hpp, h/tron/kernels/gated_delta_net.hpp.
Check that behaviour is preserved by the fix diff:
- advance() now takes a gdn_token_rows reference bundle instead of 5 row arguments. Check lifetimes (a bundle of references built from temporaries at the call site), const-correctness, template deduction (aggregate CTAD) and that every call site passes rows in the right order (mixed_qkv, output_gate, decay_input, update_input, output).
- step() now calls a shared convolve_token helper. Compare the old and new code line by line: same arithmetic, same order of writes, same state updates, for the in-place path (decode) and the working-copy path.
- The tile-region calls are now inside #ifdef TRON_AMX_DISPATCH plus if constexpr (block_kernel_shape). Check that begin/end stay balanced on every path (early return, refusal fallback) and that a build without the option still compiles.
- static_asserts that tie gdn_window_tokens, the slice width and gdn_stats::BLOCK_TOKENS_32: are they true for every instantiation the tests and the model use (128x128, 80, 16 value columns)? A static_assert that fires for the narrow test geometries is a build break.
- work_tally bookkeeping: tokens counted once, on the right path (token / chain / amx), fallback blocks counted.`,
  },
  {
    key: 'kernels',
    prompt: `Lens: the AMX kernel files. Files: src/tron/kernels/amx_gdn.cpp, h/tron/kernels/amx_gdn_iface.hpp, src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/models/self_attention.hpp, h/tron/models/model.hpp.
The fix diff renamed literals to named constants with the value in the name (for example KQ_ROW_BYTES_256, REFUSE_CORRECTION_BITS_0X71800000, EVEN_LANES_0X88, ODD_LANES_0XDD, BF16_MASK_0XFFFF0000). For EVERY replaced literal compare the old literal with the new constant's value and with its name. A changed value is a bug. A name whose suffix differs from its value is a finding.
Also check:
- std::launder in layout_of: correct use, right header included.
- self_attention.hpp: a scratch tensor changed to {uninitialized}. Prove from the code that every element is written before any read on every path that uses it. If one path reads an element first, that is a bug.
- static_asserts added in the 128 branches: true for every instantiation.
- BLOCK_SCRATCH_BYTES_118144 and scratch_layout: does the size constant still equal sizeof of the layout (is there a static_assert)?
- any behaviour change hidden in a "comment only" hunk.`,
  },
  {
    key: 'tests',
    prompt: `Lens: the new and changed tests. Files: t/t_gated_delta_net.cpp, t/t_amx_gdn_numerics.cpp, t/t_gdn_stats.cpp, t/CMakeLists.txt.
These test cases were added by the fix diff and have NEVER been compiled by the real build or run: "advance gives full windows to the block kernel and counts them", "advance gives a refused block to the chain kernel", the whole-executor advance run inside run_chain_case, "refuses a block with an output that is not finite", "restores the caller's MXCSR", "reads the start matrix through an exact split from 2^-103 up", and the changed stats hook case in t_gdn_stats.cpp.
For each: read the test and the code under test (gdn_rolling_executor.hpp advance(), amx_gdn.cpp, gdn_stats.hpp) and predict whether it compiles and passes on an AMX host and on a host without AMX. Work the expected numbers by hand (window alignment to the absolute token position first_position, number of full 32-token windows, tally fields, which value head is refused, what the fallback produces).
Report: (a) assertions that will fail (severity test-wrong), with the hand computation; (b) cases that cannot fail when the logic breaks (severity test-vacuous); (c) compile errors you can prove from the declarations (severity bug).
Example of what to check: a chain that starts at first_position 5 with 128 tokens has windows [5,32), [32,64), [64,96), [96,128), [128,133): three full windows, not four.`,
  },
  {
    key: 'stats-docs',
    prompt: `Lens: counters and documents. Files: h/tron/models/gdn_stats.hpp, h/tron/models/gdn_execution.hpp (hooks), README.stats.md, README.ci.md, CMakeLists.txt (option help), t/t_gdn_stats.cpp, t/t_tronstats_convention.cpp, ingest/src/TronCpp.hs.
The fix diff renamed the path "column_half" / "half" to "chain" (PATH_NAMES, JSON keys chain_head_tokens, chain_recurrence_cycles, chain_full_block_tokens, the exit line "head_tokens per op (token/chain/amx)") and removed the unused copy_cycles counter, and added a per-worker exit line.
Check:
- grep the whole worktree at the final head for leftovers: half_head_tokens, half_recurrence, half_full_block, column_half, column-half, copy_cycles. Any leftover in code, tests or documents is a finding.
- every counter that the documents name exists in the code with that exact name, and every FUSE leaf / JSON key in the code is in README.stats.md.
- the hooks in gdn_execution.hpp fill every counter that the report prints (a counter that is printed and never incremented is a finding), and no hook reads the clock when the switch is off.
- the per-worker exit line: index range, division by zero when a worker has 0 head tokens, format matches what README.stats.md says.
- t_gdn_stats.cpp expectations match the renamed keys.`,
  },
]

const results = await pipeline(
  LENSES,
  l => agent(COMMON + '\n' + l.prompt + '\nReturn your findings. "checked" = two or three sentences on what you verified and found correct.',
    { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS }),
  (found, l) => {
    if (!found || !found.findings.length) return { lens: l.key, checked: found ? found.checked : 'agent failed', findings: [], verdicts: [] }
    return agent(COMMON + `\nYou are a skeptic. Another reviewer (lens: ${l.key}) reported the findings below. For EACH finding, try to REFUTE it by reading the code at the final head (and the diff). A finding survives only when you can point to the lines that prove it. Verdict "refuted" when the claim is wrong, "partly" when the defect is real but smaller or elsewhere, "confirmed" when it is right. Give a corrected fix when the proposed fix is wrong.\n\nFindings:\n${JSON.stringify(found.findings, null, 1)}`,
      { label: `verify:${l.key}`, phase: 'Verify', schema: VERDICTS })
      .then(v => ({ lens: l.key, checked: found.checked, findings: found.findings, verdicts: v ? v.verdicts : [] }))
  }
)
return results.filter(Boolean)
