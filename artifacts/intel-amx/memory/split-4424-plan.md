---
name: split-4424-plan
description: "2026-10-10: plan to split PR 4424 into a 4-PR stack (PR-1 layout+AVX reader+FPGA staging+build, PR-2 AMX kernel on the plane, PR-3 shared block save, PR-4 tail block+HW policy+deb preset); evidence = hunk classification + probe branch jhan-split-probe (ai-runs/tron-split-probe: 76a0160b72 = PR-1 tree, 3c56db9a95 = PR-1+S, both 0 syntax errors in 22 lcheck cells); deliverable PR3879/new-PRs/split-4424/split-plan.md; codex reviews into split-plan-codex.md, update appended; decisions D1-D7 open"
metadata:
  node_type: memory
  type: project
  originSessionId: 8147fd4d-377d-40bd-ae3a-3103383074b7
  modified: 2026-10-10T00:24:24.831Z
---

Request (jhan 2026-10-09 ~23:40 UTC, ultracode, cwd PR3879/new-PRs/split-4424): is PR 4424 one integral whole or
several features; if the latter, propose a split and a merge order, but only if technically sound ("do not force
to do it only because I request it"). Premise offered: "VNNI-K is independent of AMX". Then: write the suggestion
to split-plan.md; codex reviews it into split-plan-codex.md; update ours after reading codex's and APPEND the update
to split-plan.md.

Findings (verified 2026-10-10 00:xx UTC):
- Concern totals at head 0a5334ccb6 vs merge base be0d5565b3 (8 classifier agents): L layout +1026/-116, R AVX reader
  +427/-13, G FPGA staging +37/-17, A AMX kernel on the plane +247/-18, S shared block save +813/-17, T tail block +
  HW policy (= PR 4737 content) +1338/-10, B build +30/-5.
- Dependencies: A needs L only; S needs L only; T needs A, S, R, G (S<->T coupled at head: block_to_vnni calls
  store_block; the row-bit loop sits in S's save_k); L without R does not compile with the option on (software loop
  calls page::k()). So PR-1 = L+R+G+B, PR-2 = A, PR-3 = S, PR-4 = T (+ deb preset).
- Probe (worktree ~/workspace/ai-runs/tron-split-probe, branch jhan-split-probe from ba69cb513e, NOT pushed):
  3c56db9a95 = A removed (+61/-279), 76a0160b72 = S also removed (+72/-673) = candidate PR-1 tree, 23 files
  +1846/-160 vs base (57 % tests). 22-cell lcheck matrix (gen/gen-amxoff x VNNI on/off x 5 test TUs + amx_attn.cpp)
  = 0 errors at baseline and after both stages; independent verifier: 0 leftover symbols, nothing wrongly removed,
  5 comment residues (kernels/k_vnni.hpp:3-5, 44-45; tensor/k_vnni.hpp:178-179; src/tron/CMakeLists.txt:232-234;
  t_llama_unit.cpp:429). Temporary code in PR-1: dense AMX gate `&& !k_vnni::layout_on<...>` in apply_page_tok,
  t_amx_dispatch_dtype dense clause, one diagram line + one Note item.
- Premise: holds at code level (0 TRON_AMX_DISPATCH guards in the layout/reader headers; qk_group call outside the
  #ifdef region; -mavx512bf16 PUBLIC at src/tron/CMakeLists.txt:285; AMX-off+VNNI-on compiles). Does NOT hold at
  benefit level on AMX hosts: PR-1 alone with the option on = AVX reader for every page = est. -7..-11 % decode TPS
  vs main's AMX (2026-09-14 vnnioff 73.93 vs base 79.59 TPS at prompt 1024); +4..5 % vs the dotter without AMX.
- Sizes of the four PRs (actual trees): 1846/160, 279/61, 673/72, 1459/113 (+ preset 7/2).

STATUS 2026-10-10 00:4x UTC: codex review (split-plan-codex.md) = supports the 4-PR stack; 5 corrections verified and
accepted (PR-4 invariant = converted-block bit, not "16 bits set"; required CI gap: gcp-nix.yml test build sets neither
option, cmake-single-platform.yml is dispatch-only -> new D8 (a) add TRON_K_VNNI to nix/cmake-tron-test-build.nix;
PR-2 tree had to be built: 4d3a042225 on jhan-split-probe-pr2 = PR-1 + A, 1 real conflict (kv_cache consumers list)
+ Note [QK orientation] sentence, 22/22 lcheck cells 0 errors; T's intrinsic dependency = store_block not the window;
token identity limited to the measured cells qwen3-4b tp2 1u 256 tok CPU p1024/p8192). Refused: builds on claude-box
(no nix). Plain-English check: 78 style violations left in v1 (line refs preserved), 5 number errors fixed in place
(per-file counts were changed-line counts; tests = 965/1846 = 52 %). Update 1 APPENDED to split-plan.md (U1.1-U1.8).
git rerere in ~/workspace/tron recorded the kv_cache.hpp resolution (54 entries). Panel (3 planners + judge) of
wf_b3743267-d3e DONE 01:0x UTC: all 3 planners + judge = same 4-PR stack and order (skeptic 8/10 chosen); new D9
("Run CI" label on drafts: gcp-nix.yml 190-191/316-317/404-405 skip build+test on drafts; AGENTS.md:16-18 = user
directs) and D10 (keep PR-3 = tested S form with ~15 lines masked partial-block logic that PR-4 replaces). TRAP: two
planner agents APPENDED sections to split-plan.md on their own (U1.9 + "Update 1 addendum"); facts verified and kept,
attribution written in U2.1; next time mark planner prompts read-only ("do not write to split-plan.md"). Update 2
(U2.1-U2.6) APPENDED 01:0x UTC. Host of this container = claude-agentsrv (not sw-dev-01). Branch protection API = 404
(Insufficient data). Probe branches: jhan-split-probe (3c56db9a95, 76a0160b72), jhan-split-probe-pr2 (4d3a042225).

HANDOFF 2026-10-10 01:4x UTC (jhan: "write split-handoff.md ... another agent will execute the split"): split-4424/split-handoff.md
= decision sheet D1-D10 with defaults, inputs table, stack table (branches jhan-vnnik-1-layout/-2-amx/-3-shared-save/-4-tail-block),
step-by-step construction (PR-1 = topical commits from 76a0160b72 + D2 + 5 comment rewrites + kill-switch sentence + main merge;
PR-2 = PR2-diff patch; PR-3 = S-diff patch; PR-4 = T-4737-merge.diff + B-preset.diff + comparison vs head merged with main),
syntax matrix, grep lists, 3bda rules + per-PR chain table, claims per PR, body rules, traps, do-not list. Durable copies of the
scratchpad material in split-4424/handoff-material/ (ref patches, probe scripts + logs, hunk classification, body snapshot).

CODEX REVIEW OF THE HANDOFF (split-handoff-review.md, 2026-10-10 04:02 UTC) answered in split-handoff-update1.md
(04:3x UTC; split-handoff.md itself NOT edited: jhan had it open in vim). 10 points, all accepted: D8 must precede the
first test-bearing commit (AGENTS.md:20-26) and option (a) needs BOTH flags (placeholders SUCCEED without
TRON_AMX_DISPATCH); matrix.sh ignored the compiler exit status -> fixed (rc per cell, MATRIX OK/FAILED verdict,
EXPECTED cells); pr1check/run.sh parametrized; build-test.sh all.done ignores the kill-switch rc and the plugin grep;
smoke expectations per cell (FPGA p1024 differs at token 52 even for PR-4); the PR-1 kill-switch sentence must be
reverted by PR-2 (was wrongly in the allowed final differences); new ref/S-diff-4d3a..ba69.patch (9 files, incl.
amx_attn_iface.hpp); compare the final tree AFTER the cost-row commit; `bin/slice route` before hardware work
(AGENTS.md:78-88); protected sections = placeholders, drafts in split-status.md from the FETCHED body. NEW D11 build
host: jhan's codex AGENTS.md:26-28 designates sw-dev-01 for builds; ssh from agentsrv fails on a CHANGED HOST KEY (do
not bypass); nix state there = Insufficient data; this project always built on 3bda. jhan decides D6/D8/D11.

2026-10-10 05:xx UTC: Update 1 FOLDED into split-handoff.md (jhan closed vim, had made no edits); new-PRs.html written
(generator split-4424/gen_new_prs.py, figures as inline SVG built by the script, PNG renders in split-4424/svg/ checked
with cairosvg: decomposition blocks, lineage vs 4424 history, dependency graph, size bars, three dumbbells for decode
TPS / TTFT / FPGA decode with old-base provenance). Page is a local file (doctype wrapper), NOT published as an artifact.

CODEX SECOND REVIEW (05:25 UTC, replaces the first): 3 findings + 2 edits, all verified and FOLDED into split-handoff.md
(Update 2, 05:4x UTC; response appended to split-handoff-update1.md): D8 (a)/(b) still leave the AMX identity case
unexecuted (gcp-nix.yml test jobs run on runners labeled fpga/test/avx512, no AMX label; t_amx_numerics returns early)
-> needs an AMX runner in a required job or jhan's written exception; deb-smoke.yml is --apt-only (no build), cpp-coverage
is workflow_dispatch only -> option (a) gives up option-off per-PR coverage; D8 change = new step 1.4 commit + allowed
difference (4); A2 row = PR-3 only; B-preset.diff already carries the README deb sentences. Codex confirmed the matrix
scripts' verdict logic (9 controls) and that S-diff-4d3a..ba69.patch reproduces ba69cb513e's tree exactly.

DECISIONS (jhan 2026-10-10 ~06:00 UTC): D1 = four PRs; D6 = the executor writes the WHOLE body of each new PR
(Short version + Background included; the protected-section rule is PR 4424's own body only); D11 = build on delphi-3bda
(not sw-dev-01). Recorded in split-handoff.md section 0 + new section 0.1 "D8 in plain words". D8 DECIDED 06:3x UTC = (c): jhan approves the tests running by hand on 3bda + the legacy lane until the CI change lands;
ISSUE #4865 filed (positron-ai/tron, assignee jhan, no names) tracks adding both options to nix/cmake-tron-test-build.nix
(a or b) + an AMX runner for the identity case; jhan works it with the CI owner. PR-1 is UNBLOCKED (D1 four, D6 executor
writes bodies, D8 c + #4865, D11 3bda). Remaining defaults: D2 drop, D3 minimal, D4 A before S, D5 cells, D7 tag, D9 no Run CI, D10 tested form.

PR-1 HANDOFF (jhan 2026-10-10 ~06:5x UTC): split-4424/create-PR1-handoff.md = PR-1-only spin-off of split-handoff.md
with all decisions resolved (D1 four, D2 drop, D3 one clause, D6 executor writes the whole body, D7 local tag, D8 (c) +
#4865 cited under Verification, D9 no Run CI (PR-1 opens ready for review so CI runs), D11 3bda). Steps: tag; branch
jhan-vnnik-1-layout from be0d5565b3 in ai-runs/tron-split-pr1; six topical commits from the tree 76a0160b72; the
"needs no AMX dispatch" commit (D2 + 5 comment rewrites + kill-switch sentence; PR-1-only text listed in split-status.md
for PR-2); merge origin/main; 22+38-cell matrix; format checks; 3bda chain A (VNNI) / A3 (option on + AMX off) / B
(row-major) / F / A0 main binary / C host suite / D smokes / E cells; body outline (9 sections); open ready for review,
Skip benchmarks, assignee jhan. Status file = split-status.md. Another agent executes it.

**How to apply:** the plan file is the deliverable; after codex's review append "Update" sections, never rewrite the
original text. Decisions open for jhan: D1 4 vs 3 PRs, D2 drop the CMake FATAL_ERROR in PR-1 (recommended), D3 gate
scope, D4 A before S, D5 cell sets, D6 protected sections per PR, D7 tag/close 4424, D8 CI coverage (a/b/c),
D9 Run CI label on drafts, D10 PR-3 form (a recommended). Delete the probe worktree
(git worktree remove, from claude-box is fine; never prune) only when jhan says the split is decided or dropped.
Related: [[merge-4737-into-4424]], [[pr4812-merge-4774-onto-4424-head]], [[savek-worker-fold]],
[[issue-4500-fix-implementation]], [[breakup-pr3879-plan]], [[remind-protected-section-proposal]],
[[claude-box-tron-build-env]] (lcheck usage).
