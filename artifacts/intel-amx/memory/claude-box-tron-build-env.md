---
name: claude-box-tron-build-env
description: "How to build/run tron tests on alpha/claude-box (AMD Zen 5, no AMX) without destroying gen/ — nix path, cache-wipe trap, SYSTEM_CONFIG trap, ingest export needs HF_TOKEN"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c5d9163-38c9-4546-a214-1b41b862ce51
  modified: 2026-08-28T04:01:51.302Z
---

Facts learned 2026-08-28 while rebuilding ~/workspace/tron-amx/gen on claude-box (host claude-sw-dev-01, AMD Ryzen 9 9950X, no AMX):

- `gen/` is configured from the nix dev shell. `nix` is NOT on the default PATH; call
  `~/.nix-profile/bin/nix develop --command bash -c '...'` from the repo root (exec/optA-verify.sh
  uses the same pattern). Cache options in use: TRON_AMX_DISPATCH=ON, TRON_AMX_K_MIRROR=ON,
  RelWithDebInfo, BUILD_INGEST_MODELS=ON, BUILD_TEST_MODELS=OFF, BUILD_PRODUCTION_MODELS=OFF,
  preset `native` (clang-19 + lld-19 + ccache from the nix shell).
- NEVER run `cmake --build gen` outside that shell: CMake sees a compiler change and deletes
  gen/CMakeCache.txt and gen/CMakeFiles/ (happened 2026-08-28). Recovery = reconfigure inside
  nix develop with the options above; ninja then re-runs the ingest `torch_export.py` steps
  (command lines changed), and the gated google/gemma-3-27b-it export fails with HTTP 401
  unless HF_TOKEN is set. Fast alternative for one test target: take the exact compile and
  link lines from `ninja -C gen -t commands <target>` and run them by hand against the existing
  gen/src/tron/libtron.a.
- The container environment sets `SYSTEM_CONFIG=--instance 1,2`. With it, every Catch test
  binary aborts in system init ("Server type not set": no resource-map.yaml server type matches
  the AMD CPU). Run tests as `env -u SYSTEM_CONFIG ./gen/t_xxx` from the repo root (ctest
  WORKING_DIRECTORY is the repo root).
- ~/workspace (incl. tron-amx, its gen/, ingest/traces, intel-AMX, ~/.cache/ccache) is NFS-shared
  between claude-box and delphi-3bda: the same working tree, same uncommitted diff, same gen/.
  Do not build on both machines at once; for 3bda verification runs use an isolated worktree on
  3bda-local disk (/var/tmp/jhan, pattern: exec/p3-q-scalar-gate.sh) so edits on claude-box cannot
  leak into the run. `cmake --preset native` here vs `cross-avx512` on 3bda flips gen/'s preset stamp.
- Ingest trace stamps go stale whenever a checkout touches ingest/export/{pyproject.toml,uv.lock}
  (DEPENDS of every torch-export stamp); re-exports of the gated google/gemma-3-* models need
  HF_TOKEN, which neither machine's non-interactive env has (2026-08-28). Workaround used here:
  configure gen/ with -DBUILD_INGEST_MODELS=OFF (drops ingested models; t_amx_*, t_llama_unit,
  runtron, t_generate_host still build).
- No /dev/fuse in the container: t_tronstats_convention (FUSE manifest test) aborts at its mount
  setup here; run it on delphi-3bda (exec/p3b-mirror-accounting.sh pattern). Tests that need
  amx_attn::available() true can link-wrap it: -Wl,--wrap=_ZN4tron8amx_attn9availableEv (t_amx_arena_leak).
- /usr/bin/g++ is GCC 11.4 (no _Float16); fine for standalone harnesses that link
  src/tron/kernels/amx_attn.cpp with `-I h -mamx-tile -mamx-bf16 -mavx512f -mavx512bw
  -mavx512vl -mavx512dq -mavx512bf16 -mavx2 -mfma` (pack functions run; tile kernels must not be
  executed here).

- UPDATE 2026-09-09: nix is GONE on claude-box: `~/.nix-profile` points to
  /nix/var/nix/profiles/per-user/root/profile, which does not exist, and /nix/store is
  absent. Only /usr/bin/g++ 11.4 remains, which cannot compile tron. Until nix is
  reinstalled, every tron build or test must run on delphi-3bda (isolated worktree
  under /var/tmp/jhan, pattern exec/split-verify3.sh, socket 1, guard first).
  ~/workspace/tron/gen and ~/workspace/tron-amx/gen are stale against their trees
  (libtron.a from 2026-06-11 and 2026-09-04) - do not link fresh objects against them.

**Why:** these traps cost a build directory and an hour; none of it is written down in the repo.
**How to apply:** before touching gen/ on claude-box, use the nix wrapper and `env -u SYSTEM_CONFIG`;
for real AMX runs use delphi-3bda per [[delphi-3bda-hardware]]. Related: [[claude-box-pid-exhaustion]].
- 2026-09-17: `~/.nix-profile` is a dangling symlink on claude-box (target /nix/var/nix/profiles/per-user/root/profile missing), so `~/.nix-profile/bin/nix` does not run here any more; check `ls /nix` before planning a nix build on this box. g++ 11.4 (/usr/bin/g++) exists but lacks the `__bf16` type tron's bf16.hpp uses; a bf16 shim (exec/block-store-animation/shim) lets a header-only test compile.

- 2026-09-16: on claude-box the symlink ~/.nix-profile/bin/nix is DANGLING (target missing), so no nix develop / clang-format here. Run the repo clang-format on delphi-3bda instead: ssh delphi-3bda "cd <worktree> && ~/.nix-profile/bin/nix develop --accept-flake-config -c clang-format --dry-run --Werror <file>" (worktrees under ~/workspace are NFS-shared; grep the new text on 3bda first, attr-cache trap).

UPDATE 2026-09-24: nix is gone from claude-box (see [[block-store-animation-page]]). For clang-19 syntax-only checks without delphi-3bda use ~/workspace/ai-runs/lcheck/lcheck.sh (zig 0.14.0 clang + headers mirrored from 3bda; README there). clang-format 19 runs via `uvx --from clang-format==19.1.7`.
