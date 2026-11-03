Status at PR #5015 (AMX attention for kv_mul 16), 2026-10-19.

The required CI build is now the nix build (`nix/cmake-tron-test-build.nix`, used by the "Build Tron" job of `gcp-nix.yml`), and its cmake_args (:79-101) do not set `TRON_AMX_DISPATCH`. The option defaults OFF (`CMakeLists.txt:46`). Only `.github/workflows/cmake-single-platform.yml:355` sets it ON, and that workflow has `workflow_dispatch` and `workflow_call` triggers only. So on every PR the AMX test binaries run their `SUCCEED` fallback cases ("Test host" lists `t_amx_dispatch_dtype` and `t_amx_numerics` as passed in 0.5 s each), and the 16-head dispatch and numerics cases that PR #5015 adds execute only on an AMX host by hand.

The one-line fix for option 1 in this lane is `-DTRON_AMX_DISPATCH=ON` in the cmake_args of `nix/cmake-tron-test-build.nix`. Two consequences to decide with the CI owner before that PR:

- The line adds the kernel translation unit to libtron (`src/tron/CMakeLists.txt:219-223`). On a runner with AMX (the Granite Rapids hosts in the runner inventory) the dense full pages of every bf16 attention with head size 128 and kv_mul 4 or 16 then go through the kernels, in every test of that lane, including the model tests the same cmake_args require (`-DTRON_REQUIRE_ALL_MODEL_TESTS=ON`). Those tests would then compare outputs produced through the AMX path.
- On a runner without AMX the kernel cases skip. Since PR #5015 (commit 4c4b7b8864) the QK and PV cases of `t_amx_numerics` use Catch2 `SKIP`, so the summary reads `test cases: 4 | 2 passed | 2 skipped` with exit code 0 (Catch2 returns 4 only when every case is skipped); before, `WARN` and return counted them as passed.

The PR #5015 review thread that raised this: https://github.com/positron-ai/tron/pull/5015#discussion_r4308387058. The PR author chose to keep the CI change out of that kernel PR and in this issue.
