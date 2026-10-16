export const meta = {
  name: 'pr1-tps-loss-why',
  description: 'Verify why PR-1 (option on) loses decode TPS against main: code trace, data decomposition, adversarial refutation',
  phases: [{ title: 'Verify' }],
}
const SCHEMA = {
  type: 'object',
  properties: {
    claims: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, verdict: { type: 'string', enum: ['confirmed', 'refuted', 'unverifiable'] }, evidence: { type: 'string' } },
      required: ['claim', 'verdict', 'evidence'] } },
    other_contributors: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['claims', 'other_contributors', 'notes'],
}
const COMMON = `Read-only task: do not modify any file, do not run builds, do not ssh anywhere. All files are local.
PR-1 worktree (branch jhan-vnnik-1-layout, head a711aeee83, main 72308ec90c merged): /home/jhan/workspace/ai-runs/tron-split-pr1
main for comparison: run "git -C /home/jhan/workspace/tron show origin/main:<path>" (origin/main = 72308ec90c).
Measured cells (qwen3-4b tp2, 8 users, 256 generated tokens, CPU attention, prompt 1024 and 8192, 3 repetitions, 2026-10-10, Intel Granite Rapids host with AMX):
  summary: /home/jhan/workspace/intel-AMX/exec/results/pr1-E-cpu/summary.md
  per-run records: /home/jhan/workspace/intel-AMX/exec/results/pr1-E-cpu/rt-results.txt
  per-run runtron logs: /home/jhan/workspace/intel-AMX/exec/results/pr1-E-cpu/rt/*.log (names <cell>__cpu__<arm>__rep<N>.log)
Arms: base = main 72308ec90c built with TRON_AMX_DISPATCH=ON, TRON_K_VNNI off (row-major K); new = PR-1 with TRON_K_VNNI=ON and TRON_AMX_DISPATCH=ON; newoff / baseoff = the same binaries with TRON_AMX_DISABLE=1 (the AMX kill switch).
Measured (decode TPS per user): prompt 1024: base 81.07, new 76.01, newoff 75.58, baseoff 72.40; prompt 8192: base 17.29, new 15.39, newoff 15.44, baseoff 14.65.
Key PR-1 facts: in h/tron/models/self_attention.hpp apply_page_tok, the dense AMX page path predicate is "amx_attn_h128g4::eligible<...>(...) && !k_vnni::layout_on<operation_head_size>" (a temporary gate until the next PR adds an AMX kernel that reads the VNNI plane); the software loop scores a VNNI slot's tokens with k_vnni::qk_group (h/tron/kernels/k_vnni.hpp); save_k stores each token's K row with page::set_k_row (4 AVX-512 scatters). qwen3-4b has 128-dimension heads with kv_mul 4 (the AMX-eligible shape on main).
Return structured findings; cite file:line for code claims and the result-file lines for data claims. Plain English, no idioms.`
phase('Verify')
const lenses = [
  { key: 'code', prompt: `${COMMON}
Lens: CODE TRACE. In the PR-1 worktree, trace self_attention.hpp apply_page_tok for a 128-dimension head with the option on. Decide, with file:line evidence:
(1) Is the dense AMX page path (the branch that calls is_dense_amx_page and then the AMX QK kernel qk_rowmajor_128x4 AND the AMX PV kernel weights_times_v_128x4) compiled out for a VNNI slot by the gate? Does skipping it skip BOTH the QK and the PV AMX kernels, so that the software PV path also runs for every page?
(2) On main (origin/main 72308ec90c), would the same full 64-token page of qwen3-4b at decode take the dense AMX path (both kernels)? Cite main's predicate.
(3) List every other decode-time difference between PR-1 (option on) and main for a 128-dimension head, with file:line: the K store (set_k_row scatter vs row store), the AMX Q pack (amx_q_packed: does it still run for a VNNI slot although no kernel consumes it?), attn_stats visit path, range hints, anything else. Say for each whether it plausibly costs decode time.` },
  { key: 'data', prompt: `${COMMON}
Lens: DATA. (1) Check the arithmetic decomposition of the measured decode TPS: is (new - base) approximately equal to (baseoff - base) + (newoff - baseoff) in both cells? Give the residual in TPS and in percentage points. Interpret: the first term is main's own AMX-kernel benefit (lost when the kernel does not run), the second is the reader-and-layout effect with AMX off on both binaries.
(2) From summary.md and rt-results.txt, list the per-repetition TPS of each arm in each cell and whether the repetitions are consistent (sd) and interleaved.
(3) Grep the runtron logs of all four arms (one rep each is enough, both cells) for lines about AMX (availability, kill switch, dispatch, kernels), about the HW attention being disabled, about the configured instance / app cores, and the Version line; report any configuration difference between arms other than the binary and TRON_AMX_DISABLE.
(4) State what the TTFT rows (base 3.175 s vs new 4.003 s; base 52.637 s vs new 117.261 s; baseoff 3.986 s / 122.851 s) say about the prefill: does new behave like baseoff?` },
  { key: 'refute', prompt: `${COMMON}
Lens: ADVERSARIAL. The claimed cause of PR-1's decode TPS loss against main (-6.2 % at prompt 1024, -11.0 % at prompt 8192) is: the temporary gate keeps the dense AMX page path off for VNNI slots, so every page of a 128-dimension head is scored by the AVX-512 reader and the software PV loop instead of main's AMX QK and PV kernels; the reader itself is faster than the row-major dotter (newoff vs baseoff +4.4 % / +5.3 %), which is why the loss is smaller than main's own AMX-off penalty (baseoff vs base -10.7 % / -15.3 %).
Try to REFUTE this. Consider and evaluate each alternative or additional cause against the code and the measured rows: (a) the per-row scatter store at decode costs more than the row store; (b) the AMX Q pack still runs for VNNI slots although nothing consumes it; (c) the reader is slow for kv_mul 4 (register pressure, 4 accumulators) or its passes; (d) cache or TLB effects of the pair-interleaved plane in decode; (e) the merge of main 72308ec90c changed something only in one binary; (f) measurement artifacts: arms not interleaved, another user active, thermal, the band and paired-t values; (g) prefill effects leaking into the decode TPS metric. For each: excluded by which data row or code fact, or still possible and which measurement would settle it. Default to "still possible" when the data cannot exclude it. Conclude whether the claimed cause survives.` },
]
const results = await parallel(lenses.map(l => () => agent(l.prompt, { label: `verify:${l.key}`, phase: 'Verify', schema: SCHEMA }).then(r => ({ lens: l.key, ...r }))))
return results.filter(Boolean)