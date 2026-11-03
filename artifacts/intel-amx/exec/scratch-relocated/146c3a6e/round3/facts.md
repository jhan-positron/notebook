# Measured facts for the round-3 commit 279dfe813ee715f8266e36593104d003679885a5 (local, not pushed yet; parent 7e7f52d761)

Worktree: /home/jhan/workspace/ai-runs/tron-glimmer-amx (HEAD = 279dfe813e). `git show 279dfe813e` = the change.

delphi-3bda run 2026-10-18 23:44-23:46 UTC (worktree /var/tmp/jhan/tron-g16h at 7e7f52d761 + round3.patch, clang 19.1.7,
preset native, TRON_AMX_DISPATCH=ON, incremental build 101 s, fake device SYSTEM_CONFIG=--instance 1,2, cpus 72-143,216-287),
logs in logs/ here:
- t_amx_numerics rc=0: All tests passed (17425 assertions in 4 test cases)
- t_amx_dispatch_dtype rc=0: All tests passed (3694 assertions in 1 test case)
- t_llama_unit rc=0: All tests passed (265452 assertions in 67 test cases)
- t_amx_numerics with TRON_AMX_DISABLE=1 rc=0: test cases: 4 | 2 passed | 2 skipped; assertions: 4111 | 4111 passed; 2 lines "AMX unavailable"
- t_amx_dispatch_dtype with TRON_AMX_DISABLE=1 rc=0: All tests passed (3694 assertions in 1 test case)
Previous numbers in the PR body (head 5061623a34): 17,424 / 4; 5,756 / 1; 265,452 / 67; kill switch 4,110 / 4 with 2 WARN skips.

Object compare on claude-box (zig-bundled clang 19.1.7, -O3, lcheck-obj.sh, objdump normalised, cmp.py / cmp2.py here):
- patched head vs merge base 6198824246: pack<4> 509 = 509 instructions, 0 diff lines; qk<4> 204 = 204, 0 diff; pv<4> 121 = 121,
  diff lines only from the TLS access model (data16 prefixes) and the relocation display of the scratch addresses.
- patched head vs 5061623a34 (the head the perf numbers were measured at): all 10 amx_attn_h128g4 symbols same instruction
  counts; 9 identical; qk<16> (207 instructions) has two adjacent `add` instructions (add $0x40,%rdx / add $0x400,%rsi) in
  swapped order; nothing else differs.

Syntax check of t/t_amx_dispatch_dtype.cpp without TRON_AMX_DISPATCH (lcheck gen-amxoff tree): before the patch 1 warning
("variable 'probe' is not needed and will not be emitted [-Wunneeded-internal-declaration]" at :68), after the patch 0.
With TRON_AMX_DISPATCH: 0 warnings/errors for t_amx_dispatch_dtype.cpp and t_amx_numerics.cpp.

CI at 7e7f52d761 (run 39168934260): "Build Tron" is the nix build (tron-cmake-test-build), it builds t_amx_dispatch_dtype.cpp
WITHOUT the option (the probe warning appears in its log); "Test host" lists t_amx_dispatch_dtype and t_amx_numerics as
passed in 0.5 s each (the SUCCEED fallback cases). nix/cmake-tron-test-build.nix cmake_args (:79-101) has no TRON_AMX_DISPATCH;
CMakeLists.txt:46 defaults it OFF; only .github/workflows/cmake-single-platform.yml:355 sets it ON (that workflow has
workflow_dispatch/workflow_call triggers only, lines 6 and 12).

Catch2 version 3.7.1 (cmake/versions.cmake:26). SKIP precedent: t/t_disk_cache.cpp:182,195,218. t/CMakeLists.txt:619 and :622
register t_amx_numerics and t_amx_dispatch_dtype with LABELS fake (no SKIP_RETURN_CODE); Catch2 returns 4 only when all test
cases are skipped (observed rc 0 with 2 of 4 skipped).

Thread states (GraphQL): OPEN = 4308387058, 4308443056, 4308443061 (outdated), 4308443185, 4308443205, 4308443322,
4308443331, 4308443490, 4308443569, 4308444165, 4308444171 (outdated). Resolved with a jhan rejection = 4308387067,
4308443327, 4308443563. All other threads resolved, applied by commits a6b93f1f71 / 7e7f52d761 (another agent).
