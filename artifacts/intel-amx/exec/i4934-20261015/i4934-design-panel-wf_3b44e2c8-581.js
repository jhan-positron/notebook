export const meta = {
  name: 'i4934-design-panel',
  description: 'Critique the issue 4934 candidate design from three lenses, refute each finding, propose concrete edits',
  phases: [
    { title: 'Critique', detail: 'three lenses: concurrency, performance parity, reviewability+tests' },
    { title: 'Refute', detail: 'two skeptics per must-change finding' },
  ],
}

const COMMON = `
You are reviewing a candidate design for a performance fix in positron-ai/tron (C++ LLM inference engine). Read-only: do NOT modify, create or delete any file. Do not run builds, do not ssh.
Trap: a Bash 'cd DIR && ...' prints a directory listing first in this container; use absolute paths and 'git -C DIR'.
Inputs (read them first):
- The design: /home/jhan/workspace/intel-AMX/exec/i4934-20261015/design-v1.md
- The verified fact base (8 subsystem readers + refuters): /home/jhan/workspace/intel-AMX/exec/i4934-20261015/understand-digest.txt (481 lines; read the sections relevant to your lens, at least 'loop', 'savek', 'kvcache', 'tests').
- The code: worktree W=/home/jhan/workspace/ai-runs/tron-i4934 at PR #4901 head 175b1837b9 (identical to /home/jhan/workspace/ai-runs/tron-split-pr4). Key files: h/tron/models/self_attention.hpp (apply_page_range ~1456-1680, apply_page_tok 1856-2088), h/tron/models/model.hpp (run_forward ~1782-1860, convert_pending_k_blocks ~3160-3185, k_store window/units 3186-3236, store_k_block 3236-3343, save_k_impl 3344-3460), h/tron/models/kv_cache.hpp (page state ~2130-2240, 2500-2630), h/tron/tensor/k_vnni.hpp, h/tron/kernels/k_vnni.hpp, h/tron/kernels/dotter.hpp, h/tron/threading.hpp (thread_pool 689-800), h/tron/models/common.hpp (batch, k_store_window), t/t_k_vnni_layout.cpp, t/t_llama_unit.cpp (save_k case ~3851-4265, reductions fixture ~2501-2551), t/heterogeneous_scheduler_compile.cpp (forward case ~1050-1200), t/t_amx_dispatch_dtype.cpp. PR #4898 (parent) files: 'git -C $W show dfafd13dce:<path>'.
- The repository's C++ guide and comment conventions: $W/CLAUDE.md, $W/AGENTS.md (read the parts about Notes, named constants, comments).
Goal of the fix: with TRON_AMX_DISABLE=1 (kill switch) PR #4901 must decode and prefill as fast as PR #4898 (parity), and with AMX on it must not be slower than PR #4901; FPGA-attention behaviour and gains (issue #4500) unchanged.
Return only the structured output. Every finding needs file:line evidence or a concrete measurement/argument; mark severity must_change (the design is wrong or will not reach the goal) / should_change (clear improvement) / nit. Say "Insufficient data" rather than guess.`

const CRITIQUE = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'Short version, at most 5 sentences' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      severity: { type: 'string', enum: ['must_change', 'should_change', 'nit'] },
      change: { type: 'string', description: 'which design change (1-4, measurement, tests) or "new"' },
      claim: { type: 'string' },
      evidence: { type: 'string' },
      proposed_edit: { type: 'string', description: 'concrete code-level edit or test, with file and function names' },
    }, required: ['id', 'severity', 'change', 'claim', 'evidence', 'proposed_edit'] } },
    answers_to_open_questions: { type: 'array', items: { type: 'object', properties: {
      question: { type: 'string' }, answer: { type: 'string' }, evidence: { type: 'string' },
    }, required: ['question', 'answer', 'evidence'] } },
  },
  required: ['summary', 'findings', 'answers_to_open_questions'],
}

const LENSES = [
  { key: 'concurrency', prompt: COMMON + `
LENS concurrency and memory model. Check every change for races, ordering and lifetime: (a) change 2's per-page block-mask read before the query loop: who can write the bits during an apply_page_range call (ready vs pending sections, other minibatches' save_k, note_k_block_saved on helper threads, the conversion, k_forget_row/copy_from under the tree lock), and whether reading page::k_vnni_blocks for a page with no relevant token is safe (read kv_cache.hpp k_vnni_blocks, k_state_ix, eagle_view_active; what "a book may have no active KV slot" means for the page struct; look at how apply_page_range obtains the page and the slot); (b) change 3's parallel conversion: are pool workers idle and may main block in parallel_for at that point (read run_forward and Note [Plugin-owned worker launch]); can the scheduler thread or any other thread touch the pages during the forward end; are duplicates the only way two entries name one block (also: two logical slots mapping to the same storage, EAGLE view, k_storage_ref equality); is sort+unique correct on (pg, storage.offset, storage.state_ix, block); does k_block_to_vnni_at's release fetch_or publish the bytes to the next pass's readers on other cores (acquire loads at the readers); any TRON_ASSERT inside k_block_to_vnni_at that could fire on a worker; the latch_trigger of parallel_for (alignment/mwaitx requirements, see threading.hpp:93-95 and how other callers use parallel_for); (c) change 4's atomic short-row counter in the window struct: reset/visibility ordering relative to opened/finished; (d) change 1: the plane fetch after the loop vs the old first-token fetch; anything in the epilogue that depended on the removed locals. Also answer open questions 1-4 of the design.` },
  { key: 'performance', prompt: COMMON + `
LENS performance parity. Judge whether the design reaches the goal and what could still be slower than PR #4898 under the kill switch: (a) walk the new per-visit and per-token instruction sequence of change 1 versus PR #4898's (git show dfafd13dce:h/tron/models/self_attention.hpp lines ~1930-2000) and list every remaining difference on the common path (VNNI page, no row-major rows), including the per-page block-mask read of change 2 (count per decode step and per 8-user 8192-token prefill), the s_pages fill, the plane fetch, the two mask tests, qk_group's argument; estimate each in ns with the arithmetic and say which could be measurable (a decode step at tp2 prompt 1024 is about 13.6 ms, at prompt 8192 about 67 ms; prefill 117 s); (b) compiler risk: will clang keep make_dot_q out of the common path (it is only called in the rows != 0 branch), will std::countr_zero compile to tzcnt, is block_token_mask a table load or 4 ops; is there any risk that the bigger function body changes register allocation of the hot loop (compare with the probe, which did not change TTFT); (c) change 3: estimate the serial cost today (288 block_to_vnni per user block completion: 16 x 256 B memcpy from L3-resident lines + store_block 64 loads/4 transposes/64 stores; give ns per block with stated assumptions) versus parallel_for over num_workers tasks (enqueue cost per task, latch, the task's loop) for 36 and 288 entries; and the alternative of overlapping with logit delivery (enqueue before the listener-notification tasks, join before q_batches.clear()); say which to pick for v1; (d) change 4: estimate the recording loop's cost per 8-user 8192-token prefill (2.36e6 iterations, each: token_jobs_do_kv, token_jobs, page_of, offset_in_page, note_k_row_saved = k_state_ix + relaxed load + acquire load + asserts) and whether skipping it is worth the window-struct change; (e) AMX-on: list every change on the AMX-on path (dense gate without the per-visit atomic load; the software-visited tail page now without dotter construction; the conversion parallel) and confirm none adds cost; (f) FPGA path: confirm the loop change keeps row-major blocks scattered through the history correct (the mask comes from the page, not from an assumption about the tail) and no extra cost in the staging. Answer open questions 2 and 3.` },
  { key: 'review', prompt: COMMON + `
LENS reviewability, conventions and tests (the PR will be reviewed by strict reviewers: see the check list in /home/jhan/.claude/skills/Wade-code-review/SKILL.md if present, else apply: no dead symbols, no magic literals (NAME_<value> constants in AMX-owned files), comments must match code, Notes updated, no claims wider than the code, tests with consumers, mutation checks). Check: (a) every comment and Note that the design makes stale: the loop comments at self_attention.hpp 1946-1990 and 2042-2050, the dense-gate comment 1903-1931, Note [K VNNI storage] and Note [Row-major tail block] sentences about who scores row-major rows and when the conversion runs, the kernels/k_vnni.hpp header comment (callers keep bits clear), amx_attn_iface.hpp:49-51 'same AVX dotter' (already stale), model.hpp comments at 3160-3185 and 3419-3437; list each with the replacement text in plain English (one claim per sentence, define terms at first use); (b) named constants: k_convert_parallel_min (value and name per the NAME_<value> rule for AMX-owned files, which files count as AMX-owned?), block_token_mask's table; (c) tests to add or update and where: a bit-exact check that the post-loop row scoring equals dotter<bf16,128> and dotter<float,128> on a page with VNNI and row-major blocks mixed (which fixture: t_k_vnni_layout's reader case at :466 uses store_row only; the t_llama_unit reductions fixture at :2501-2551 is float-only), a case that drives the parallel branch of convert_pending_k_blocks (more than k_convert_parallel_min blocks, duplicates included) and checks every block converted exactly once (how to observe: block bits + bytes), a check that the AMX dense gate still refuses a page with a row-major block when the mask is passed in (t_amx_dispatch_dtype 'unrecorded rows' section); which existing mutation checks (M1 completion comparison, M2 hardware policy, M3 removing the forward's call) still discriminate and what new mutation would cover change 1 (e.g. scoring row-major rows through qk_group must fail a test) and change 3 (dropping the dedupe must fail a test); (d) commit split: propose topical commits with subjects in the repository's style (look at 'git -C $W log --oneline -12'); (e) anything in the design that widens a claim beyond the code (e.g. "bit-identical to PR #4901").` },
]

const REFUTE = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      verdict: { type: 'string', enum: ['holds', 'refuted', 'uncertain'] },
      reason: { type: 'string' },
    }, required: ['id', 'verdict', 'reason'] } },
  },
  required: ['verdicts'],
}

const critiques = await parallel(LENSES.map(l => () => agent(l.prompt, { label: 'critique:' + l.key, phase: 'Critique', schema: CRITIQUE })))
const named = {}
LENSES.forEach((l, i) => { named[l.key] = critiques[i] })

const toRefute = []
LENSES.forEach((l, i) => {
  const c = critiques[i]
  if (!c) return
  c.findings.filter(f => f.severity !== 'nit').forEach(f => toRefute.push({ lens: l.key, f }))
})
log(toRefute.length + ' must/should findings to refute')

const refuted = await parallel(toRefute.map(item => () =>
  parallel([0, 1].map(k => () => agent(COMMON + `
You are SKEPTIC ${k + 1} of 2. Try to REFUTE the finding below (lens "${item.lens}") by reading the code and the fact base yourself. Default to 'uncertain' when you cannot verify. 'holds' only when the evidence checks out AND the proposed edit is necessary or clearly better than the design as written.
Finding ${item.f.id} [${item.f.severity}] on change ${item.f.change}:
claim: ${item.f.claim}
evidence: ${item.f.evidence}
proposed edit: ${item.f.proposed_edit}
`, { label: 'refute:' + item.f.id + ':' + (k + 1), phase: 'Refute', schema: REFUTE })))
    .then(vs => ({ lens: item.lens, finding: item.f, votes: vs.filter(Boolean).map(v => v.verdicts[0]) }))
))

return { critiques: named, refuted }