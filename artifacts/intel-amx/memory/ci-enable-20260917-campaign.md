---
name: ci-enable-20260917-campaign
description: "2026-09-17 DONE: built the nightly-style tron .deb with TRON_AMX_DISPATCH on (preset deb one-liner, commit 6f37cd2ed9 on local branch jhan-amx-deb-preset, worktree /var/tmp/jhan/tron-ci-enable on 3bda, PUSHED to origin 2026-09-18, no PR yet); packaged rinzler has 86 AMX instructions + TRON_AMX_DISABLE text (nightly 31b80a18: 0/0); run-time check with qwen3-4b: probe granted + 873 M AMX-busy cycles (cpu-on), 0 (kill switch), 501 M under FPGA attention (open question); package for Rhys at /var/tmp/jhan/ci-enable-deb/; report PR3879/new-PRs/CI-enable/Thursday-report.md + for-Rhys-andoria-AMD-test.md"
metadata: 
  node_type: memory
  type: project
  originSessionId: e961bb62-6371-4178-8c22-42772c040878
  modified: 2026-09-17T19:57:53.313Z
---

Request (jhan 2026-09-17): execute section 1 of the nightly-AMX-check page on delphi-3bda, confirm
AMX compiled in a CI-style package and running with qwen3-4b, write instructions for Rhys's test on
the AMD nightly machine (andoria-b1a3). Report: PR3879/new-PRs/CI-enable/Thursday-report.md (plain
English), instructions: for-Rhys-andoria-AMD-test.md (same folder).

Facts:
- `make deb` works on 3bda OUTSIDE nix (the makefile refuses it inside): PATH needs
  /tools/uv/0.9.5 and ~/.ghcup/bin; ~/.local/bin/uv (0.11.21) came first on PATH (CI pins 0.9.5).
  Clang 19.1.7 = the CI builder's version. 12 min total with NPROC_BUILD=48 pinned to socket 1
  (ingest-deps 36 s, deb 10 min 50 s, test-deb-package-contents 39 s). Torch exports ran without
  an HF token. Build log exec/results/ci-enable-20260917/make-deb.log (preset block line 272 has
  TRON_AMX_DISPATCH="ON"; step 310/398 compiles kernels/amx_attn.cpp.o).
- Package tron_2026.09.17-6f37cd2e-jhan-amx-deb-preset_amd64.deb, 137,904,212 bytes, sha256
  a2dc67bafbd690bbfc9e795064ea7dd93484f44bae39bac1178f1b13b7ec8a87 (branch name is part of the
  Debian version -> sorts above 2026.09.17-31b80a18, below any 2026.09.18 nightly).
- Packaged rinzler 232,814,656 bytes: strings TRON_AMX_DISABLE 1, objdump 86 AMX instructions
  (32 tdpbf16ps/40 tileloadd/12 tilestored/1 ldtilecfg/1 tilerelease, +12 tilezero uncounted),
  nm 0 (stripped); unstripped gen-deb/rinzler 945 MB: nm 10, objdump 86.
- Run-time check (exec/ci-enable-20260917/runtime-check.sh, results exec/results/ci-enable-20260917/):
  deb extracted to /var/tmp/jhan/ci-enable-root, packaged rinzler run as ONE engine on our half
  (--instance 2,4 cards 90/93, port 13100, LD_LIBRARY_PATH to the deb's lib, cwd the extracted
  opt/positron; rinzler has RUNPATH $ORIGIN and reads /opt/positron/{config,weights} by absolute
  path). Arms cpu-on / cpu-off / default (nightly qwen setting = FPGA attention): probe granted /
  none / granted; EXE.AMX_BUSY during 3 decode-only requests 873,318,988 / 0 / 501,350,140 cycles;
  idle 0 in all arms; single-user decode 219 / 214 / ~200 tok/s (not a TPS measurement).
  The 57% count under FPGA attention contradicts the page's "one page per query" expectation;
  resolving measurement = TRON_PAGE_SHARE_COUNTERS build in both arms (not done).
- Verification pass (wf_be0461e4-7a2, 9 agents) corrected: the perf CSV misread (per-CPU mode is fine),
  16 cycles = throughput not latency, the engine is NOT run-to-run deterministic here (repeats of the
  same prompt at temperature 0 differ inside one arm; one cpu-on answer == one cpu-off answer), the
  146,752-byte rinzler growth is not the AMX code (different main commits, 10 merges apart), CI
  build step 21 min (2026-09-16) / 19 min (2026-09-17), not 24.
- Prefix cache trap: a warm-up with the same prompt makes later requests decode-only
  (usage.prompt_tokens_details.cached_tokens = 910); good for isolating decode, bad if you meant
  to measure prefill.
- tron names hugepage files by slice (slice-4-of-8, slice-5-of-8 for --instance 2,4), not by
  --hugepage_file; the first script version left 128 pages held until removed by hand; fixed.
- Running our engine next to the active production unit rinzler@1 (Bill's half, instance 0,2)
  was fine for a functional check: separate socket, cards, slices. Guard used: lease + other-user
  (bill excluded) + campaign flock, not campaign_guard_acquire (it refuses next to serving).
- NOT done: package not installed on 3bda (shared machine); jammy container smoke needs the apt
  token + Docker; branch PUSHED to origin 2026-09-18 (jhan asked); PR not opened (jhan decides).

**Why:** the nightly cannot show the AMX gain until the deb preset carries the option; this run
proves the one-line fix produces a working AMX package and leaves a tested file for the AMD check.
**How to apply:** to open the PR: `git -C /var/tmp/jhan/tron-ci-enable push -u origin
jhan-amx-deb-preset && gh pr create`. After the first AMX nightly: check the publish-deb log for
amx_attn.cpp.o, run strings/objdump on the DUT, grep the env files for TRON_AMX_DISABLE. See
[[nightly-amx-check-20260916]], [[amx-busy-perf-counter]], [[amd-amx-fallback-test]],
[[3bda-shared-with-bill]].
