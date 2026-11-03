# Facts established before the analysis workflow (verified by the main session on 2026-10-20/21)

- PR 5047 "self_attention: Make token selection logic a bit more obvious", author Ben Gamari (bgamari-positron), opened 2026-10-20T15:05Z,
  base branch jhan-vnnik-1-layout (= PR 4956's branch, head a5697f86d3), head bgamari/vnnik-1 = ade89a9d9c. Body: "The previously-proposed
  implementation was a bit spaghetti for my liking." +240/-307 in 9 files. No review comments, no inline comments (as of 2026-10-21 00:00 UTC).
- Two commits: e17a12ff09 (2026-10-20 15:03Z) "self_attention: Make token selection logic a bit more obvious" (touches only
  h/tron/models/self_attention.hpp, +25/-43 by git numstat, incl. an added #include <bit> that commit 2 removes again) and ade89a9d9c (16:18Z) "kv_cache: hide K layout behind row and
  scoring operations" with message "Abstract K scoring and AMX layout selection behind `kv_cache`. Use row operations for saving keys to the
  cache, movement of keys to the FPGA, and remove the public raw K views." (8 files).
- merge-base(PR 5047 head, PR 4956 head) = a5697f86d3 exactly (Ben's branch is PR 4956 head + 2 commits). merge-base(PR 4956 head, main) = 76bb0bf3f4.
- PR 4956 = jhan's "Add the VNNI K layout and its readers" (+1715/-163, 23 files, option TRON_K_VNNI default OFF, CI builds it ON).
- Removed-line attribution (git blame at a5697f86d3, script overlap.py): PR 5047 removes 307 lines; 155 were added by PR 4956, 152 are
  pre-existing main code (CORRECTED 00:35 UTC after fixing the new-file handling of overlap.py; git diff --numstat agrees: 240 added / 307 removed). Per file (removed / of which PR 4956 / pre-existing / added): kv_cache.hpp 87/44/43/84; model.hpp 16/16/0/2;
  self_attention.hpp 76/41/35/22; scheduler/full.hpp 9/9/0/3; tensor/k_vnni.hpp 1/1/0/1; t/heterogeneous_scheduler_compile.cpp 12/0/12/13;
  t/kv_cache_helpers.hpp 0/0/0/26 (new file); t/t_amx_dispatch_dtype.cpp 2/2/0/2; t/t_llama_unit.cpp 104/42/62/87.
  Pre-existing (main) code removed: the public page::k() accessors (8 overloads, kv_cache.hpp ~1976-2038, from commits ea3122b914,
  06b47b2561, 493412716c, 5289dde816, 1be8d93a4e); in self_attention.hpp the dotter-array construction comment+code (b60d48c1b8, 0979f05947,
  de4267f981), the AMX gate comment and apply_dense_amx_page void signature (7a7a1a8eb8), the qk_rowmajor_128x4 call site comment (72083ab161,
  eb146f084f) and #include dotter.hpp (1dc73329ad); test lines in heterogeneous_scheduler_compile.cpp (1ca3a70e21) and t_llama_unit.cpp
  (493412716c, 06b47b2561, 03aaf8cee5, 6a704fc681, ea3122b914, 1cf5c4a619) that poked K through page->k<geometry>(slot, head, token)[0].
- CI on PR 5047 head: "Build Tron" FAILED (run 39468077391, job 118789619687): t/heterogeneous_scheduler_compile.cpp:688:13 error: no member
  named 'k' in 'tron::page<3, 1, 64, 512, ...>' and :688:78 subscripted value is not an array, pointer, or vector. Lines 687-689 at the head:
  `for (size_t i = 0; i < 256; ++i) page->k<software_geometry.kv>(software_operation.binding.kv_slot, 0, 0)[i] = bf16(0.0f);` — the one
  page::k call site Ben did not convert (he converted lines 1085-1177 of the same file). Test, Test host, Test FPGA, Benchmark: skipped.
  Lint, Cursor Bugbot, deb-smoke-tests: pass. PR 4956 head's CI: Build Tron / Test host / Test FPGA all pass.
- t/t_llama_unit.cpp:107 at the head still defines the concept page_k_packed_accepts_geometry via page.k_packed<geometry>(...) (now always false);
  STATIC_REQUIRE_FALSE on it remains (the #ifdef TRON_K_VNNI branch asserting it true was removed).
- GitHub benchmark comment (github-actions, 16:05Z) "Benchmark of commit 251529f": 251529f = "Merge e17a12ff09 into a5697f86d3" = COMMIT 1 ONLY
  merged onto the PR 4956 head, run on andoria-09 ("2 x 96core", an AMD box: no AMX), compared "vs Golden baseline (nightly, multi-repeat)" =
  main nightly data (58e8c54 / 9c5414a / e94d4ac), NOT against the PR base. Rows: llama-3.2-3b tp2 gen -0.51 % inconclusive; ingested-llama-3.1-8b
  tp2 gen +0.06 % no change, parse -0.42 % "regression (3/3)"; llama-3.1-8b-good tp4 gen +0.43 % inconclusive; llama-3.1-8b-good tp2 +0.01 %;
  ingested-gpt-oss-120b tp4 gen +7.18 % "improvement (3/3)", parse -0.47 % no change. The +7.18 % therefore mixes PR 4956 + commit 1 vs main
  and is not evidence about PR 5047 by itself.
- 3bda campaign launched 2026-10-21 00:1x UTC: exec/pr5047-20261020/ (README.md); four binaries b47b/b47h (option OFF) b47bv/b47hv (option ON);
  identity smokes + perf cells llama-8b cpu p1024/p4096/p8192, qwen3-4b fpga p1024/p8192, gpt-oss-120b fpga p1024; REPS 4; deadline 01:30 UTC,
  resumes after the nightly at 13:30 UTC. Results land in exec/results/pr5047-20261020/.
- Prior page in the working dir: random/2026-10-20-pr-5047-line-by-line.html (400 KB, generated 2026-10-20 11:33 local, by an earlier session):
  "both commits, every changed line, and the GPT-OSS benchmark" with a quiz. The new deliverable Ben-PR4956.html must be top-down with diagrams.
