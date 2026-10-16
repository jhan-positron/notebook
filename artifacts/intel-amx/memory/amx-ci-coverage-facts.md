---
name: amx-ci-coverage-facts
description: Verified 2026-09-11 facts on how tron CI treats the AMX code (compile flag, runner fleet, .passed cache trap) and the test-amx proposal page for Hannah
metadata:
  type: project
---

Page: PR3879/new-PRs/PR1/Hannah-AMX-CI.html (2026-09-11), for Hannah Van Eenoo (CI owner,
25 of the last 40 workflow commits). Facts below were checked by two independent readers each.

- PR1 (#3879) already adds -DTRON_AMX_DISPATCH=ON to the CMake `build` job configure line
  (cmake-single-platform.yml:365-367, commit 6a40ff5dbe). It is the ONLY build config with the
  option; presets, nix, coverage lane, `deb` preset (make deb), golden/refresh benchmarks all OFF.
- AMX executes only if the test job lands on an Intel runner AND actually runs tests. FPGA runner
  group: Intel delphi-3af6/17cf/3bd6 (+3bda registered but runner service and start timer
  disabled, 0 jobs); AMD andoria-02/09/14. All request [self-hosted, fpga, test, avx512].
  delphi-3af6 is missing from README.ci.md's inventory; its `intel` label is unverified.
- .passed CACHE TRAP: the `test` fan-in writes /scratch/tron-build/<sha7>/...passed with no
  platform dimension; later runs of the same content hash skip all test steps (RUN_TESTS false).
  Measured 2026-09-05..11 on main (49 runs): test-host ran tests in 12 of 47 jobs (Intel 7, AMD 5),
  35 skipped; test-fpga Intel 9 / AMD 3 / 35 skipped; build compiled 13 of 48.
- Benchmarks: per-commit `benchmark` job AMD-only (oci 2x72core commented out: lab breaker trips);
  nightly benchmark-golden.yml DOES run on Intel hosts but builds main without the flag.
- Skip semantics: t_amx_numerics QK/PV cases WARN+return when available() is false
  (t_amx_numerics.cpp:145-148, 189-192); WARN goes to slice's per-test log, uploaded only on
  failure. Catch2 SKIP() exits 4 = failure in slice unless label skip_return_code_4 -> use an env
  var (TRON_CI_REQUIRE_AMX=1 -> FAIL) instead. slice copies the parent env to tests.
- Proposal: new job test-amx, runs-on [self-hosted, fpga, test, intel, avx512], needs build,
  restores artifact, runs ./gen/t_amx_numerics + ./gen/t_amx_dispatch_dtype directly (slice has no
  per-test filter; restored tree has no CTest registry), add to `test` fan-in needs + assertion.
  Branch protection (verified via API): build, lint, test, test-fpga, test-host, ci-machinery-tests;
  jhan has Maintain not Admin -> Admin must add required checks. Make the workflow PR against main
  after #3879 lands (PR branch workflow is behind main: builder-s label).
- Eligibility nuance: `host` executor = float activations -> t_generate_host never reaches AMX;
  ingested plugins force_hw_attn (TronCpp.hs:233) but positions < engagement point 127 still run
  software attention; kernels need a complete 64-token page. host_bf16 exists only for the
  experimental llama-3-8b-host-precision variant (slug llama-3-8b-host-bf16).
- Probe experiments on 3bda with the stale gen/ (Aug 26-31 binaries) were inconclusive
  (t_generate_host aborted); do not cite them.

**Why:** these facts took ~2 h of API digging and are not written anywhere in the repo.
**How to apply:** reuse for the test-amx PR, the #3997 close-out, and any CI discussion; recount
the job table before quoting numbers older than a week. See [[pr3879-split-progress]],
[[more-testing-round1]].
