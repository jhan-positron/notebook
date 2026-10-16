## Short version

The CI that gates every pull request builds tron with `TRON_AMX_DISPATCH` and `TRON_K_VNNI` off. The tests of the AMX attention kernels and of the VNNI K layout therefore never execute in required CI: some are compiled out, the two AMX test files compile to a placeholder. This issue tracks the CI change that makes them run, and the one case that needs AMX hardware.

## Words used here

- Required CI: the GitHub workflow every pull request must pass (gcp-nix.yml), whose C++ test build comes from `nix/cmake-tron-test-build.nix`.
- `TRON_AMX_DISPATCH`: the CMake option that compiles the AMX (Intel Advanced Matrix Extensions) attention kernels and their dispatch (PR #3879).
- `TRON_K_VNNI`: the CMake option that stores the K cache of 128-dimension heads in the AMX VNNI layout (PR #4424, to be split into a stack of four PRs).
- deb preset: the CMake preset in `CMakePresets.json` that builds the released package. It sets `TRON_AMX_DISPATCH=ON` today and will set `TRON_K_VNNI=ON` with the last PR of the stack.

## What runs today

| Build configuration | Where | Switches | Runs on every PR? |
|---|---|---|---|
| PR CI test build | gcp-nix.yml via nix/cmake-tron-test-build.nix (lines 80-93) | both off | yes |
| deb preset (the package) | CMakePresets.json | AMX on; VNNI on after the stack lands | no (builds the package, runs no tests) |
| legacy CMake lane | .github/workflows/cmake-single-platform.yml | both on | no (manual dispatch, and as the test gate of publish-deb.yml) |

So the released package runs code that the pull-request tests never exercise with the switches on.

## Tests affected

- Already on main (PR #3879): `t_amx_numerics` and `t_amx_dispatch_dtype` compile to a placeholder case ("build without TRON_AMX_DISPATCH - nothing to test") in the PR CI build.
- PR #4424 and its split: `t_k_vnni_layout` (its cache-level cases sit under `#ifdef TRON_K_VNNI` and are compiled out), the VNNI cases of `t_llama_unit` (they take the row-major path), the VNNI cases of `t_amx_dispatch_dtype` and `t_amx_numerics` (placeholders).

The repository test policy (AGENTS.md, "Test policy") asks that every committed test runs in a required CI suite, or that the user approves an exception explicitly.

## What is asked

1. Make the PR CI test build compile both options. Two ways:
   - (a) add `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON` to the existing test build in `nix/cmake-tron-test-build.nix`. Cost: the row-major K path of 128-dimension heads is then compiled by no PR CI (only the manual coverage lane, cpp-coverage.yml, which runs by workflow_dispatch).
   - (b) add a second test build with both options next to the current one. Cost: a second C++ build and test run per pull request.
2. Decide what to do about the one case that needs AMX hardware: the bit-identity case of `t_amx_numerics` returns early when `amx_attn_h128g4::available()` is false. The PR CI test jobs run on runners labeled `fpga, test, avx512` (gcp-nix.yml lines 464, 555, 622); none is labeled for AMX. Either an AMX-capable runner joins the required test jobs, or that case is an accepted, documented skip in CI (it runs by hand on the Granite Rapids test machine).

## Until this lands

The affected tests run by hand on the Granite Rapids test machine and in the legacy CMake lane. The pull requests of the VNNI K stack state this gap in their Verification sections and refer to this issue. The author of the stack has approved proceeding on that basis until the CI change lands.

## References

- Test policy: AGENTS.md, section "Test policy".
- PR CI test build: nix/cmake-tron-test-build.nix. Legacy lane flags: .github/workflows/cmake-single-platform.yml. Preset: CMakePresets.json.
- PR #3879 (AMX kernels), PR #4424 (VNNI K layout; to be split into four stacked PRs).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
