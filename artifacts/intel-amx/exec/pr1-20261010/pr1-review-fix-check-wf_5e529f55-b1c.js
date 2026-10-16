export const meta = {
  name: 'pr1-review-fix-check',
  description: 'Independent review of the PR-1 review-fix diff: Wade-style code review and an adversarial check of the new staging test',
  phases: [{ title: 'Review' }],
}
const SCHEMA = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit', 'ok'] }, file: { type: 'string' }, claim: { type: 'string' }, evidence: { type: 'string' } },
      required: ['severity', 'file', 'claim', 'evidence'] } },
    notes: { type: 'string' },
  },
  required: ['findings', 'notes'],
}
const COMMON = `Read-only: do not modify files, do not run builds or tests, do not ssh. Worktree: /home/jhan/workspace/ai-runs/tron-split-pr1 (branch jhan-vnnik-1-layout of positron-ai/tron). The diff under review is the UNCOMMITTED working-tree change: run "git -C /home/jhan/workspace/ai-runs/tron-split-pr1 diff". It answers review comments on PR #4868:
 (a) Cursor Bugbot: k_vnni store_row/load_row had no token bound check (packed V asserts in v_vnni_access::pair_base) -> TRON_ASSERT_LT(token, Rows) added in store_row and load_row (h/tron/tensor/k_vnni.hpp).
 (b) P2: t/t_phase1_integration.cpp "gof populate pulls KV data from page_info lambdas": the K callbacks now gather each head's row from a packed k_vnni_tensor plane into populate's per-head scratch (load_row + k_destination_row) and return the scratch; after populate the staged bytes are compared per token, head, dimension through the K swizzle hw_off = (e % nwords) * hbm_word_width + e / nwords (as t/t_gof_dma.cpp "GOF K swizzle element ordering" does). Mutation claim: removing "+ h * HW_BAKED_HEAD_SIZE" from the scratch address in src/tron/gof.cpp gof::populate must make this case fail.
 (c) P2: t/t_llama_unit.cpp check_page_range_reductions: the widened split-vs-unsplit bounds (0.05 on the weighted V sum, relative 1e-6 on s_star) now apply only when k_vnni::layout_on<head_size>; the row-major build keeps main's 0.02 and absolute 2e-6 (first site) / relative 2e-6 (second site, unchanged from main).
 (d) P3: t/t_k_vnni_layout.cpp poison comment reworded to the observed contract.
 (e) optional: h/tron/models/model.hpp uses k_destination_row<head_size>(row).set(kout) for the stack row.
Return structured findings with file:line evidence. Plain English, no idioms. Mark "ok" findings for the checks you ran that passed, so the record shows what was checked.`
phase('Review')
const results = await parallel([
  () => agent(`${COMMON}
Task: a code review of the whole diff in the style of the repository's reviewers. Load the skills "Wade-code-review" and "tron-code-review" (via the Skill tool) and apply their checks to the diff: dead symbols and includes, comments that contradict code, magic literals, duplicated logic, names, hot-path cost (the asserts are in the row store/load path: estimate the cost and compare with v_vnni_access::pair_base's assert), test checks (does the new test have a consumer for every value row, does it bypass the changed path, duplicate coverage with t_gof_dma), claims wider than the code. Also check the C++: std::vector<std::array<k_row_t, NKV>> with alignas(64) k_row_t (over-aligned allocation), std::make_unique<k_plane_t[]>(NKV) for an alignas(64) trivially constructible type, k_source_row<HS>(k_data[t][h].v) overload resolution (array decays to const bf16*; the other overload takes a view), the capture of the unique_ptr by reference in the lambda, bf16::to_bits() existence, INFO/REQUIRE usage, that hbm_word_width (h/pos/config.hpp:73) and gof::k.position_ptr are accessible from t_phase1_integration.cpp with its includes and "using namespace tron;".`, { label: 'review:wade', phase: 'Review', schema: SCHEMA }),
  () => agent(`${COMMON}
Task: ADVERSARIAL check of item (b), the extended staging test, and item (c).
(b1) Trace src/tron/gof.cpp gof::populate and k_hwcacheblock::set_position (h/pos/hwattention.hpp and its .cpp) to confirm: the per-head pointers are collected first and copied afterwards; the swizzle formula hw_off = (e % nwords) * hbm_word_width + e / nwords with nwords = HS / hbm_word_width matches set_position's K transposition for head_size 128 (cite the code and t/t_gof_dma.cpp "GOF K swizzle element ordering"); position_ptr(pos, head) returns the staged head of position pos.
(b2) Mutation: if the scratch address in populate loses "+ h * HW_BAKED_HEAD_SIZE", does the new case fail? Walk through what each callback writes and what set_position copies. Also consider a second mutation: populate passes the right scratch but the scheduler callback in h/tron/scheduler/full.hpp ignores it; is that covered by this unit test (no: say so) and by what else?
(b3) Is anything in the new test code wrong or undefined: the alignment of k_data rows for k_source_row<HS> (default Aligned flag = true), store_row into token index t < 64, the planes' lifetime vs the lambdas, the static_assert condition, the expected-value formula k_data[t][i / HS].v[i % HS] = 0x3C00 + t*100 + i (any NaN or inf bit patterns? 0x3C00 + 3*100 + 1023 = ?), and that V handling is unchanged.
(c1) Confirm from "git -C /home/jhan/workspace/tron show origin/main:t/t_llama_unit.cpp" (lines around 2615-2630 and 2750-2760) which bounds main has at the two sites, and that the diff restores exactly those for the row-major build and keeps the VNNI bounds otherwise. State whether the row-major build's pass under main's bounds is known from data or still needs the test run (it needs the run; say so).`, { label: 'review:adversarial', phase: 'Review', schema: SCHEMA }),
])
return results.filter(Boolean)