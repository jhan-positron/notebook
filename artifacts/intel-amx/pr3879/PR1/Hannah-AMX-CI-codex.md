# Nightly CI: run Qwen3-4B through AMX on delphi

Prepared for Hannah, 2026-09-11. Based on the CI configuration, PR #3879 at `544ca05c7a`, and read-only checks on `delphi-3bda`, including that day's nightly Qwen startup logs. This is an implementation checklist; these changes have not been applied.

Tracking issue: [tron #4347 — CI: enable and verify AMX attention for eligible models](https://github.com/positron-ai/tron/issues/4347).

**Merging #3879 alone is insufficient.** It enables AMX in the CMake CI build, but nightly system CI installs a separately built `.deb` that still leaves AMX disabled. For sustained Qwen AMX coverage, nightly also needs a Qwen test phase with software attention selected in the inference server's environment.

The target here is [System CI (Rinzler 72-core Intel system OCI version)](https://github.com/positron-ai/systems_test/blob/main/.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml), which runs inference on `delphi-3bda.positron.internal`.

## What is already in place

| Item | Verified state | Additional action |
|---|---|---|
| CMake CI build | #3879 sets `-DTRON_AMX_DISPATCH=ON`. | None for that build. It is not the nightly package build. |
| Nightly inference machine | The workflow already targets delphi-3bda, an AMX-capable Intel Granite Rapids machine. | Keep this DUT; changing the client runner's CPU does not enable AMX in the server. |
| Runtime kill switch | `TRON_AMX_DISABLE` is unset in the inspected engine environment files and user override file. | Keep it unset for the AMX phase. There is no need to set it to `0`. |
| Qwen model shape | Both ingested Qwen3-4B tp2 and tp4 use head size 128, 32 query heads and 8 KV heads: the supported ratio of 4. These executors use bf16 activations. | Use these existing variants. |
| Qwen attention policy | `USE_HW_ATTN` is unset; Qwen enables FPGA attention by its model default. | Override it for the dedicated software-attention phase described below. |

The nightly logs directly confirmed Qwen's effective policy. These excerpts are shortened:

```text
2026-09-11 04:52:39 UTC  ingested-qwen-3-4b-instruct-2507-tp2
  HW attention enabled ... engagement=127 ... (model default)
2026-09-11 04:55:20 UTC  ingested-qwen-3-4b-instruct-2507-tp4
  HW attention enabled ... engagement=127 ... (model default)
```

**The default is per model; `USE_HW_ATTN` is per process.** Tron reads the variable once. When unset, it uses each model's default. Setting it to `0` selects software attention for all models in that server process. The installed `platformd` version, `0.10.7`, does not set this variable per model. [Tron policy](https://github.com/positron-ai/tron/blob/632c6181edcee4ff5743cb5c91a92a99d6f6099b/h/tron/models/hw_attn_config.hpp), [matching platformd environment generation](https://github.com/positron-ai/platformd/blob/v0.10.7/internal/services/inference/service.go#L1000).

## Required changes

### 1. Enable AMX in the package that nightly actually installs

**Owner: tron maintainers / package-build owner.**

- Merge #3879, then configure the nightly package build with `TRON_AMX_DISPATCH=ON`.
- The direct implementation is to add `"TRON_AMX_DISPATCH": "ON"` to the `deb` configure preset's `cacheVariables`, or pass `-DTRON_AMX_DISPATCH=ON` in the actual CMake configure command used by `make deb`.
- This enables AMX in the released package too. If the intended scope is CI only, produce a separate AMX-enabled CI package and explicitly install that package in the nightly workflow instead.
- Coordinate the selected delivery path with [#3993](https://github.com/positron-ai/tron/issues/3993), which tracks explicit artifact ISA/build contracts and a distinct AMX artifact profile and validation path.
- Publish and install the new package before running the Qwen test. Record its version, source commit and AMX build setting in the CI evidence; an older apt package is not sufficient.

The current chain is `publish-deb.yml` → `make deb` → `cmake --preset deb` → published package → nightly `apt-get install -y tron`. None of those package configure settings currently enables AMX. The package installed during the host check was `2026.09.11-632c6181`, from before #3879. [Publish workflow](https://github.com/positron-ai/tron/blob/main/.github/workflows/publish-deb.yml#L105), [package configure command](https://github.com/positron-ai/tron/blob/main/GNUmakefile#L426), [deb preset](https://github.com/positron-ai/tron/blob/main/CMakePresets.json#L68), [nightly installation](https://github.com/positron-ai/systems_test/blob/main/.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml#L49).

#### Repository, files, and how to change them

The concrete path below enables the released `.deb`. It is one implementation of the package choice above.

| Repository | File | Proposed edit |
|---|---|---|
| `positron-ai/tron` | [`CMakePresets.json`](https://github.com/positron-ai/tron/blob/main/CMakePresets.json) | In `configurePresets`, find the entry whose `name` is `deb`. Add `"TRON_AMX_DISPATCH": "ON"` inside that entry's `cacheVariables`. Keep the top-level CMake option's default OFF for other builds. |
| `positron-ai/tron` | [`.github/workflows/publish-deb.yml`](https://github.com/positron-ai/tron/blob/main/.github/workflows/publish-deb.yml) | After `make … deb` in the `Build .deb` step, assert that `gen-deb/CMakeCache.txt` contains exactly `TRON_AMX_DISPATCH:BOOL=ON`. Record that setting with the source SHA and package version in the build output and retained artifact metadata. This catches a future package configuration regression. |
| `positron-ai/systems_test` | [`.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml`](https://github.com/positron-ai/systems_test/blob/main/.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml) | After the apt installation, record `dpkg-query -W tron` on the DUT. Invoke the AMX preflight/test from sections 2–3 before accepting the package for this test; a successful apt command or a newer version number alone does not prove AMX was compiled. |

The preset edit is a single additional key, alongside the existing package settings:

```json
"ENABLE_FUSE_STATS": "ON",
"TRON_AMX_DISPATCH": "ON"
```

The package-build assertion can be:

```sh
grep -qx 'TRON_AMX_DISPATCH:BOOL=ON' gen-deb/CMakeCache.txt
```

With this preset approach, the existing `GNUmakefile` `deb` target already selects the right preset. The alternative is to edit its actual `cmake --preset deb` command instead of adding the preset key; do not assume `make TRON_AMX_DISPATCH=ON deb` forwards an arbitrary make variable to CMake.

### 2. Add a Qwen AMX phase with the correct server environment

**Owner: systems_test / inference-launch configuration owner.**

Run the existing Qwen3-4B tp2 and tp4 variants in a dedicated phase with:

```text
USE_HW_ATTN=0
TRON_AMX_DISABLE unset
```

- Apply these settings to **every rinzler process serving the Qwen phase on delphi**, before it starts. Exporting them only in the GitHub Actions client shell does not propagate them through SSH, platformd or systemd automatically.
- Restart or relaunch the affected inference engines after selecting the environment. Both attention switches are cached within the process; changing a file while the server runs does not switch its behavior.
- Scope the override to the Qwen AMX phase. Restore the previous configuration and relaunch the engines before subsequent tests that expect FPGA attention, including on failure or cancellation.
- Implement this in the nightly launcher/provisioning flow. Do not rely on hand-edited `/etc/rinzler/instance-*.env`: platformd regenerates those files when engine configuration changes.

On the inspected host, `rinzler@.service` reads both `/etc/rinzler/instance-%i.env` and the optional `/opt/positron/user/config.env`. Neither contained either attention variable. The latter is a shared override, so a workflow that uses it must preserve its other settings and restore its prior state; it is not a Qwen-only setting.

For the workload, use a normal contiguous prompt of at least 128 tokens, followed by generation. The existing 1024-token performance prompt is sufficient for the page-length requirement. AMX needs a complete, visible 64-token KV page; shorter or partially visible pages use the AVX path. [Dispatch conditions](https://github.com/positron-ai/tron/blob/544ca05c7a954f892f0e23ccb465f74ad46bea5e/h/tron/models/self_attention.hpp#L1371).

#### Repository, files, and how to change them

**Repository: `positron-ai/systems_test`.** Use a dedicated script under the existing nightly DUT lease. The following script name and commands are proposed additions, not existing interfaces.

| File | Proposed edit |
|---|---|
| [`.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml`](https://github.com/positron-ai/systems_test/blob/main/.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml) | In `Update DUT and run suite`, after the package installation and before `uv run system_ci`, run `uv run python -m scripts.amx_qwen_ci run`. Propagate a nonzero exit code so an AMX failure fails the job. Extend the existing `cleanup()` trap to call the script's idempotent `restore` command before clearing the DUT lease. Retain its evidence directory as an artifact even on failure. |
| `scripts/amx_qwen_ci.py` **(new)** | Implement `run` and `restore`. Use the existing `Andoria.from_env()`, SSH connection, `provision_models()` and readiness helpers from `testlib/inventory.py`. Run `ingested-qwen-3-4b-instruct-2507-tp2` and `…-tp4` separately, with a fresh set of server processes for each variant. Generate through the existing OpenAI-compatible API using a 1024-token prompt and a bounded output length. |
| `tests/test_amx_qwen_ci.py` **(new)** | Test restoration after success, generation failure and cancellation; preservation of unrelated user settings; restart/environment verification for every serving engine; and propagation of a failed AMX phase to a nonzero script exit. Mock the SSH/provisioning calls for these tests. |

Implement the environment handling in the new script as follows:

1. Before changing anything, save whether `/opt/positron/user/config.env` exists, its contents, ownership and permissions in a backup identified by the nightly lease ID. This is a DUT runtime file, not a repository file.
2. While the exclusive nightly lease is held, update only the attention settings in that file: set `USE_HW_ATTN=0`, remove any `TRON_AMX_DISABLE` assignment, and enable the proposed verification flag from section 3. Preserve unrelated entries. Check that another service environment source does not reintroduce the kill switch; fail if the actual process environment disagrees.
3. Provision each Qwen variant, wait for platformd to finish reconciling, and explicitly restart the corresponding `rinzler@<instance>.service` instances if provisioning retained existing processes. Verify new process IDs, the requested model, readiness, and the selected environment before sending requests. Do not accept the model-name provisioning cache as evidence that the environment changed.
4. In `finally`, restore the saved file state, restart the affected engines and verify the normal environment is restored. The workflow's `cleanup()` trap calls `restore` again as a fallback. Restoration must be idempotent and must not erase the original AMX failure; a restoration failure also fails the job and prevents normal tests from proceeding with the override still active.

The installed platformd/systemd integration already reads this user file, so this approach requires no platformd source change. It temporarily affects all inference engines on the DUT; the dedicated phase and lease provide the scope. Reuse the existing [provisioning helpers](https://github.com/positron-ai/systems_test/blob/main/testlib/inventory.py) rather than adding a per-model environment field that the installed platformd API does not support.

### 3. Make the nightly result prove Qwen reached AMX

**Owner: AMX author, with systems_test integration.**

- Require the runtime AMX availability probe to succeed in the Qwen server processes. Fail this phase if the build omits AMX, the kill switch disables it, or CPU/OS tile support is unavailable.
- Add test instrumentation that records or asserts actual execution of the production AMX page path during the Qwen workload, covering its QK and PV kernels. Require at least one verified page completion for each tested Qwen variant.
- Retain the package provenance, model name, effective attention settings, runtime availability result and execution evidence in the nightly output.
- Confirm the server startup log says `HW attention disabled ... USE_HW_ATTN=0` for this phase. That proves the software-attention setting; the separate execution evidence proves AMX was selected within it.

A successful generation, an AMX CPU flag, or a passing kernel test alone does not prove that Qwen generation reached the AMX dispatch. The proposed `test-amx` job in [Hannah-AMX-CI.html](Hannah-AMX-CI.html) exercises kernel tests; it does not supply this Qwen end-to-end assertion.

#### Repositories, files, and how to change them

**Repositories: `positron-ai/tron` and `positron-ai/systems_test`.** A small opt-in diagnostic in the server, checked by the new nightly script, is enough. `TRON_AMX_CI_VERIFY` and the log events below are **proposed additions**; they do not exist in #3879 today.

| Repository | File | Proposed edit |
|---|---|---|
| `positron-ai/tron` | [`src/rinzler.cpp`](https://github.com/positron-ai/tron/blob/544ca05c7a954f892f0e23ccb465f74ad46bea5e/src/rinzler.cpp#L4206) | In `main()`, after logging initialization and instance labeling, check whether `TRON_AMX_CI_VERIFY` is exactly `1`. If so, emit an `AMX_CI_STATUS` event with the build/runtime result. Under `#ifdef TRON_AMX_DISPATCH`, call `tron::amx_attn_h128g4::available()` and exit nonzero if false. In the compile-off branch, emit `compiled=0` and exit nonzero. Include the AMX interface header as needed. The compile-off error must remain compiled into an OFF build. |
| `positron-ai/tron` | [`h/tron/models/self_attention.hpp`](https://github.com/positron-ai/tron/blob/544ca05c7a954f892f0e23ccb465f74ad46bea5e/h/tron/models/self_attention.hpp#L1532) | In `self_attention<model>::state`, cache whether verification is enabled and add a thread-safe latch for the first completed AMX page in that model state. Immediately **after** `apply_dense_amx_page<geometry>()` returns in `apply_page_tok()`, emit `AMX_CI_DISPATCH model=<enclosing_state.cfg.id> completed_dense_page=1` once when verification is enabled. That return means the real QK, PV and accumulator update completed. Add explicit standard-library includes for any new atomic/environment handling. |
| `positron-ai/systems_test` | `scripts/amx_qwen_ci.py` **(new, shared with section 2)** | Set `TRON_AMX_CI_VERIFY=1` in the scoped server override. For each variant and engine, require `compiled=1 available=1` from that new process and a matching page-completion event during its first Qwen generation request. Save the status, dispatch event, model, PID/service invocation and package version under `output/amx-qwen/`. Missing or mismatched evidence must make `run` exit nonzero. |
| `positron-ai/systems_test` | `tests/test_amx_qwen_ci.py` **(new, shared with section 2)** | Add evidence-parser cases for a valid run, an OFF build, unavailable AMX, startup status without dispatch, wrong model, old process/invocation, an event before the request, and an engine with no completion event. Only the valid case passes. |

The intended evidence format is, for example:

```text
AMX_CI_STATUS compiled=1 available=1
AMX_CI_DISPATCH model=ingested-qwen-3-4b-instruct-2507-tp2 completed_dense_page=1
```

`completed_dense_page=1` is an event confirming a completed page, not a total execution counter. Instrument the production dispatch call site, not just the standalone QK/PV kernels, which numerical unit tests can call independently.

Make the verification request the first generation workload after each engine restart. Readiness checks before it should only query status/model listings. Capture a journal cursor immediately before the request, then accept only completion events after that cursor from the expected model and new service invocation. Address each engine directly, or verify that requests through the proxy exercised every expected engine; do not infer that from request count. If a launcher performs warmup generation, make that an explicit verified Qwen request or use a resettable counter instead of the first-completion latch.

Validate the implemented changes once with an AMX-enabled package on delphi, once with an OFF build, and once with the kill switch deliberately set in a fresh process. The latter two must fail preflight. Also test the parser's missing-dispatch case: successful startup alone must never pass the phase. Normal runs with `TRON_AMX_CI_VERIFY` unset should retain their existing behavior.

## Performance and correctness validation

If this phase reports performance, establish a software-attention baseline using the **same binary and workload** with `USE_HW_ATTN=0` and `TRON_AMX_DISABLE=1`, then launch a fresh process with the kill switch unset for the AMX run. Keep placement and request settings equal. Compare correctness using agreed numerical/quality tolerances.

Keep these results separate from the existing FPGA-attention performance thresholds. Forcing software attention changes the workload's execution path; the current nightly FPGA numbers are not an AMX-versus-AVX baseline.

## Completion checklist

- [ ] Nightly installs a package containing #3879, built with `TRON_AMX_DISPATCH=ON`.
- [ ] Qwen tp2 and tp4 run on delphi with `USE_HW_ATTN=0` and `TRON_AMX_DISABLE` unset in their actual server processes.
- [ ] The prompt and generation exercise full, visible KV pages.
- [ ] CI fails if AMX is unavailable or Qwen records no real AMX execution.
- [ ] Logs retain the build, environment and execution evidence.
- [ ] Normal attention settings are restored before subsequent nightly phases.
- [ ] Any AMX performance results use an appropriate software-attention baseline.

`USE_HW_ATTN=0` is required here for sustained software-attention coverage, not for every possible AMX instruction. With an AMX-enabled package and Qwen's normal FPGA default, eligible early CPU attention can already reach AMX: sequence positions below the engagement point of 127 remain in software. Package enablement is still necessary in either case.
