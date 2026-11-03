---
name: pr5047-ben-refactor-review
description: "2026-10-20/21: Ben's PR 5047 (bgamari/vnnik-1, 2 commits on the PR 4956 head a5697f86d3) unpacked top-down in random/Ben-PR4956.html (generator exec/pr5047-20261020/gen_page.py + page_template.html); 3bda campaign exec/pr5047-20261020/ (4 binaries b47b/b47h OFF, b47bv/b47hv ON; cells llama/qwen/gpt-oss); CI 'Build Tron' red at t/heterogeneous_scheduler_compile.cpp:688"
metadata:
  type: project
---

jhan 2026-10-20 (pasted request): are all PR 5047 changes about PR 4956 code? unpack what Ben's changes do and the problems
they address, top down, with diagrams, file Ben-PR4956.html; test on 3bda with llama3.1-8b (+ other models) for a perf regression.

Verified facts (2026-10-21 00:xx UTC):
- PR 5047 base branch = jhan-vnnik-1-layout (PR 4956's branch); head ade89a9d9c = a5697f86d3 + e17a12ff09 (commit 1: self_attention
  token selection -> 64-bit live mask, score after the loop) + ade89a9d9c (commit 2: page::score_k / try_score_k_amx / set_k_row(expr),
  page::k() x8 and k_packed() removed, save_k one line, full.hpp k_head_fn always get_k_row = memcpy for row-major too, test helpers
  t/kv_cache_helpers.hpp set_k_tag/k_tag). PR body: "a bit spaghetti". Requested reviewer: jhan.
- Removed lines 307 = 155 PR 4956 + 152 pre-existing main (git blame at a5697f86d3; scratchpad overlap.py); added 240. Pre-existing =
  Rhys's page::k() accessors (493412716c, 06b47b2561, ea3122b914), Alexey's dotter std::array (0979f05947), jhan's gate (7a7a1a8eb8,
  72083ab161), Rhys's tests (03aaf8cee5, 6a704fc681, 1cf5c4a619, 1ca3a70e21). So NOT all changes address PR 4956 code.
- layout_on counts BASE kv_cache 19 / self_attention 2 / model 1 / full 1 -> HEAD 13 / 0 / 0 / 0.
- CI Build Tron FAILED (run 39468077391): t/heterogeneous_scheduler_compile.cpp:687-689 still calls page->k<...>(slot,0,0)[i]; Ben
  converted lines 1085-1177 only. t_llama_unit.cpp:106-107 concept page_k_packed_accepts_geometry is stale (k_packed gone).
- GitHub benchmark comment "commit 251529f" = commit 1 only merged on a5697f86d3, vs nightly main golden baseline, on andoria-09
  (AMD, no AMX): gpt-oss +7.18 % is not a PR-vs-base measurement.
- Perf risks on the production (OFF) build: FPGA staging memcpy (256 B per KV head per staged token); on the ON build: AMX gate now
  evaluated at run time (is_dense_amx_page + s_pages + try_score_k_amx -> false) and a bf16 detour in set_k_row(expr).
- Campaign: exec/pr5047-20261020/ (README.md): chain launched 00:09:39 UTC Oct 21 (pid 1513417), steps B I D T R, REPS 4, deadline
  01:30 UTC, NOT_BEFORE 2026-10-21T13:30:00Z; results exec/results/pr5047-20261020/ (results.md/json by gen_report.py); page regenerated
  with `python3 exec/pr5047-20261020/gen_page.py`. Dry run in a stub sandbox passed (one forced build failure -> ARM_FILTER).
- An earlier session's page random/2026-10-20-pr-5047-line-by-line.html covers every line; Ben-PR4956.html is the top-down companion.
- Workflow wf_d8ce6160-022 (96 agents, 2026-10-21 00:12-01:45 UTC): 162 claims kept, 10 disputed on details. Extra findings folded into
  the page: whitespace-insensitive blame = 123 PR 4956 / 184 main removed lines; added 240 = 78 PR4956-only / 95 main-only / 41 mixed /
  26 new file; stale comments self_attention.hpp:1723-1727 ("always applies the page") and gof.hpp:61-67 (pointer into the page);
  vacuous probe page_k_accepts_raw_index (t_llama_unit.cpp:117-119 names Page::head_size, which does not exist); CI (option ON) never
  compiles the AMX branch of try_score_k_amx; PR 4957 does not merge onto Ben's head (6 conflict hunks, 3 files); s_pages is zero-filled
  (tensor() : data() {}); the exit report's forward timer (T1) reproduces the +0.5 % prefill delta at p4096/p8192 with identical visit counts.
- Interim 3bda perf (01:30 UTC, 1-2 of 4 reps): OFF decode inside the band everywhere; llama p8192 prefill +0.19 s (+0.5 %) beyond the
  0.15 s band on both option values; ON pair llama p8192 decode -1.5 % (t -9.8). Kill-switch follow-up cell prepared: killswitch.sh
  (arms baseoff/headoff, l8b p8192) to run after chain.done = ok; gen_report/gen_page know the headoff:baseoff pair.

**How to apply:** when the chain finishes (chain.done = ok), rerun gen_page.py, re-check the perf verdict sentence of the Short
version, and post nothing to GitHub unless jhan asks. Related: [[vnnied-k-in-place-project]], [[split-4424-plan]], [[glimext-20261018-campaign]].


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-20/21 Ben-PR4956.html + 3bda campaign exec/pr5047-20261020/ (4 binaries OFF/ON); CI red at heterogeneous_scheduler_compile.cpp:688; 307 removed = 155 PR 4956 + 152 older main

## Chain final (2026-10-21 14:43 UTC)
- chain.done = ok: B=ok x4, I=ok, D=ok, T=ok, report written (exec/results/pr5047-20261020/results.md + results.json). Verdict: no degradation beyond the band in any of the 10 pairs over 6 cells, 4 of 4 repetitions. All must-match identity pairs identical (256 tokens).
- One pair inside the band by the 0.4 TPS floor only: l8b-tp2-8u-p8192-cpu headv:basev -0.32 TPS (-1.4 %), t = -8.2, 2 x larger sd = 0.14 TPS. Hypothesis: commit 1's restructured software loop (page::score_k) + the run-time AMX decline, 100 % of K tokens on the software path in that cell. Option-OFF p8192 prefill +0.138 s of a 0.150 s band (+0.4 %).
- Kill-switch cell (killswitch.sh: l8b p8192 off binaries under TRON_AMX_DISABLE=1, 4 reps, takes production down) NOT yet run; run only when the gate driver is finished, the CI lease is clear and nobody is on 3bda. gen_report/gen_page know the pair headoff:baseoff.
- Page Ben-PR4956.html regenerated 2026-10-21 ~15:40 UTC: floor-only note + verdict clause (gen_page.py floor_pairs/floor_note), no_semicolons render pass (capitalizes plain words, keeps lowercase project names), dumbbell delta labels placed right/left/below to avoid collisions (verified with cairosvg: strip style=height:auto, set width/height attrs), template 'What to tell Ben' items carry the measured answers (+0.2/+0.1/-0.8 % FPGA copy cells, -0.6/-1.4 % option-ON cells, 4 reps done).
- Kill-switch cell DONE 2026-10-21 15:53 UTC (4 reps): l8b-tp2-8u-p8192-off baseoff 21.39 TPS / 78.79 s prefill, headoff 21.46 TPS / 81.04 s; pair headoff:baseoff decode +0.3 % (inside), prefill +2.25 s (+2.9 %) DEGRADATION beyond the 0.166 s band. The restructured software path (page::score_k) is slower in prefill at 100 % software share; scaled by the 2.8 % share of the shipped configuration = ~0.06 s est. of the +0.138 s option-off p8192 delta. Page regenerated (verdict sentence keeps the 10 shipped pairs apart from the diagnostic cell; 'What to tell Ben' item carries the result + a profile suggestion). Hypothesis for the cause (unverified): per-visit work of score_k in prefill (live-mask build, declined AMX visit, per-row dotter calls).
- Rule slip 2026-10-21: ran a read-only 'git -C /var/tmp/jhan/tron-bp4v log' (forbidden tree). Nothing changed. Do not run git there at all; read the tip from exec/results/<campaign>/build-<tag>.txt instead.
