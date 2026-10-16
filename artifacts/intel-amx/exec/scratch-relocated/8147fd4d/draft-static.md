# Split plan for PR 4424 (draft, static sections)

## Facts verified 2026-10-09 (UTC)

- PR 4424: draft, base main, head 0a5334ccb6, merge base be0d5565b3, 29 files, +4054/-198, MERGEABLE. origin/main is 165 commits past the merge base (TronCpp.hs changed by 442 lines on main; t_llama_unit +122).
- Reviews: Ben (2026-09-21) asked for a typed VNNI tensor (done via PR 4557 + the typed port) and for folding save_k_helper into save_k(worker_ix) (done via PR 4774). No reviewer asked for a split.
- History seams (first-parent line, all built + tested on delphi-3bda):
  - be0d5565b3..6b939d25d2: layout + AVX reader + FPGA staging + AMX kernel + shared block save (save_k_helper form), 2694+/189-, chain green 2026-10-08 (host suite 93/1/1, smokes, cells +5.3 %/+10.4 % TPS vs main).
  - 6b939d25d2..ba69cb513e: save_k worker fold (PR 4774/4812), 91+/91-, 3bda 6 tests + host suite green.
  - ba69cb513e..9d5c7a389b: row-major tail block + hardware-attention policy (PR 4737), 1459+/113-, 3bda chain green, whole-machine campaign 2026-10-09.
  - 9d5c7a389b..0a5334ccb6: deb preset line + README, 7+/2-.
- Build facts: tron target has -mavx512bf16 PUBLIC (src/tron/CMakeLists.txt:285), so h/tron/kernels/k_vnni.hpp (the AVX-512 reader, _mm512_dpbf16_ps) needs no AMX flag; only amx_attn.cpp has -mamx-*. kernels/k_vnni.hpp, tensor/k_vnni.hpp and model.hpp have zero TRON_AMX_DISPATCH guards; the qk_group call in self_attention.hpp (line 2046) is outside the #ifdef TRON_AMX_DISPATCH region (1895-1945). CMake FATAL_ERRORs TRON_K_VNNI without TRON_AMX_DISPATCH (src/tron/CMakeLists.txt:235-238): a policy line, not a code need; README.ci.md (0a5334ccb6) itself says "the layout does not depend on AMX, only the reader does".
- AGENTS.md:12-13: in a PR stack only the PR based on main may be ready for review; every descendant stays draft; after the parent merges, promote only the next PR.
