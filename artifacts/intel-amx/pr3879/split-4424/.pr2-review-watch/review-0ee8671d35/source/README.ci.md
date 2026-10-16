# CI/CD Guide

## Overview

| Workflow | File | Purpose | Trigger |
|----------|------|---------|---------|
| GCP Nix | `gcp-nix.yml` | Default CI: lint, Nix builds, runtime handoffs, tests, and benchmarks | PR, merge group, pushes to `main`, manual |
| Debian smoke | `deb-smoke.yml` | Live authenticated Jammy APT check | PR, merge group, pushes to `main`, manual, `workflow_call` |
| CMake and CTest | `cmake-single-platform.yml` | Validate Debian packaging and run legacy checks during cutover | `workflow_call`, manual |
| C++ Code Coverage | `cpp-coverage.yml` | Build and publish C++ coverage reports | Manual only |
| Prime Hugging Face Models | `prime-hf-models.yml` | Maintain pinned model snapshots in the GCP Filestore model cache | Relevant PR/main changes, manual |
| Slice Cost Data Refresh | `bench-refresh.yml` | Full scheduler cost-data measurement and rolling PR maintenance | Weekly when rollout-enabled, manual dry run |
| Slice Cost Data Refresh Health | `bench-refresh-health.yml` | Actions-history freshness check and independent alert | Daily when rollout-enabled; manual, alerts opt-in |
| Benchmark Golden Sample | `benchmark-golden.yml` | Stable nightly benchmark baseline | nightly (08:00 UTC / 01:00 PT), manual |
| Publish .deb Release | `publish-deb.yml` | Package and release artifacts | nightly (01:17 UTC / 17:17 PST), manual with a `channel` input, tags (`v*`), `workflow_call` |
| Build and Publish positron-dice .deb | `positron-dice-deb.yml` | Build, test, and publish the internal Dice worker package | relevant PR changes and pushes to `main` |
| Nix build validation | `nix-build.yml` | devShell evaluation, ingest Haskell source identity, and dead-code detection | PR with Nix/Cabal paths, merge_group/push to main |
| Slice self-tests | `slice.yml` | Hermetic host-only Slice scheduler, routing, and wrapper tests | Relevant PR changes, manual |

Dice improves shared-hardware CI throughput; see [the Dice guide](doc/dice.md)
for its operation and deployment rather than duplicating those details here.
Its package workflow builds on a general runner, then runs package and
migration checks on a general runner alongside the full Dice suite on an
`[self-hosted, fpga, test]` runner. Publication requires both test jobs.

### PR CI Labels

| Label | Effect | Timing | Agent default |
|-------|--------|--------|---------------|
| `Run CI` | Runs draft-gated jobs in default CI and auxiliary workflows | Next PR event; does not trigger or cancel a run | Do not add unless explicitly directed |
| `Skip benchmarks` | Skips benchmarks and reporting; lint, build, and tests still run | Next PR event; does not trigger or cancel a run | Add to every PR unless explicitly directed otherwise |

**Key Rules:**
- Host and FPGA test jobs run in parallel; Slice schedules tests within each job.
- Benchmarks skip `merge_group` events (GitHub's merge queue — the same commit
  gets benchmarked on the subsequent push to main)
- Main CI uses `cancel-in-progress: true` to prevent stale runs (publish-deb
  does not)

Scheduled cost-data refresh, publication, and health checks require repository
variable `SLICE_REFRESH_ROLLOUT_ENABLED=true`. Refresh runs on feature branches
must be dry runs and use the event's exact commit. Refresh restores that commit's
`testRuntime` and `testEnvironment` from a successful GCP Nix push or manual run;
it does not rebuild tests on the measurement runner or reuse prior measurements.
The hosted plan checks the producer's runtime receipt before scheduling hardware.
Like the GCP test executors, refresh keeps host discovery tools ahead of runtime
tools on `PATH`; its checkout-local venv still selects the pinned Python.
The self-hosted measurement job is read-only; a hosted default-branch job owns
PR writes and validates the bot branch and remote head before dispatching
`gcp-nix.yml` and `slice.yml` by branch.
The publisher adds `Skip benchmarks` to its PRs and dispatches GCP Nix with
`skip_benchmarks=true`. This skips performance benchmarks, not Slice timing
measurement or build and test checks. Other manual GCP dispatches retain the
default `skip_benchmarks=false`.
The `2x72core` refresh and its health expectation separately require
`SLICE_REFRESH_2X72_ENABLED=true`. See
[the slice cost-data lifecycle](doc/slice-benchmark-lifecycle.md#rollout-controls)
for rollout and branch validation.

Slice timing data is collected every Sunday at 05:00 UTC (Saturday 22:00 PDT / 21:00 PST).

## Workflows

### GCP Nix (`gcp-nix.yml`)

CI machinery checks and Nix toolchain checks gate merging independently of
product builds to shorten build feedback time.

`Nix Toolchain Contracts` also validates Perfetto release pins and tests CLI
config generation and launchers. It runs on all GCP Nix workflow events, including draft PRs,
without a file-path filter. Nix can reuse an unchanged successful check.

The background full-lint rejection check scopes its state by run, attempt, and
job and removes it after reporting the result. Reused runner temp directories
and leftovers from interrupted earlier runs do not block the next check.

`Fresh Cabal plan` verifies ingestion dependency planning without a cached plan.
Planning-tool dependencies retain normal caching.

Host and FPGA tests share one signed test runtime; benchmarks use a separate
output from the same compilation. Slice executes hardware tests outside Nix
build sandboxes. See [`bin/ci/`](bin/ci/README.md#nix-build-stages) for artifact
preparation and handoff tools.

Test runtime preparation gives each job private weights and prequant caches
under its writable `gen/` tree. Startup migration and eviction stay within those
caches; the authoritative weights directory and cache behavior are unchanged.
Each job populates its own model copies, so tests can need more disk space and
startup time than a run using a warm shared cache.

Branch protection must require the individual build and test checks:
`Lint`, `CI machinery tests`, `Fresh Cabal plan`, `Prepare Tron build inputs`,
`Build ingest`, `Test ingest`, `Build model traces`, `Generate model plugins`,
`Wait for lab cache`, `Build Tron`, `Test host`, `Test FPGA`, and `Test`.
This makes an upstream failure block merging even when dependent jobs are skipped.

### CMake and CTest (`cmake-single-platform.yml`)

`Publish .deb Release` calls this workflow to validate tag and feature-branch
packages with benchmarks skipped. It retains the host toolchain and NFS test
archives. Manual dispatch runs the legacy checks directly, with benchmarks
skipped by default:

```bash
gh workflow run cmake-single-platform.yml --ref YOUR_BRANCH -F skip_benchmarks=true
```

This produces the existing required check names: `build`, `lint`, `test`,
`test-fpga`, `test-host`, and `ci-machinery-tests`. During the GCP Nix cutover,
run it on the final PR commit and wait for both pipelines before merging and
switching branch protection to the GCP Nix checks listed above. If a merge
queue creates a new candidate commit, dispatch this workflow on that queue
branch too while the legacy checks are still required. Each updated candidate
needs its own results. CMake CI has no automatic trigger.

The legacy workflow does not run Debian smoke. Automatic PR and merge queue
coverage comes from the standalone Debian smoke workflow.

### GCP Nix implementation details

The CMake derivation emits separate test and benchmark runtime outputs from one
compilation. Exact signed Nix closures transport those immutable runtimes and
their tool environments. NFS remains responsible for mutable test-passage
markers, benchmark measurements, reports, and model weights.

The build-plan entry point is [`nix/tron-build.nix`](nix/tron-build.nix).

Producers queue their outputs for cache publication. Each consumer acquires
its exact signed inputs and waits for the cache copy if publication is still
in progress.

At job cleanup, even after a failed build, `Build Tron` uses the runner's Python
with a five-minute total budget for waiting for the local publisher queue to
drain and collecting unused paths. Cancellation interrupts that normal cleanup
and runs a separate attempt with a 30-second budget and no queue wait, so a
superseded build can return its runner promptly. The cancellation attempt skips
GC if publication is still pending. Actions step timeouts provide a backstop
of six minutes for normal cleanup and one minute for cancellation cleanup.
If the Nix store filesystem has less than 200 GiB free, it runs
`nix-store --gc --max-freed` with the bytes needed to reach 300 GiB free.
The 100 GiB gap between the trigger and target reduces repeated collection.
The target depends on available collectible paths; deletion can exceed it by
the final path's size. The job retains its roots during collection.
An unreadable or undrained queue skips GC, as does a free-space measurement
error; cleanup errors and helper deadlines produce warnings. Cleanup steps are
best effort, and job roots are released afterward even if cleanup times out.

`Prepare Tron build inputs` runs after model plugin generation. It evaluates
`nix/tron-build.nix` in GCP with the exact generated plugin path, builds the
compiler dependencies, and publishes one plan containing the C++ derivation,
its realized build inputs (including the plugins), pinned CI Python, and
test/benchmark environments. It does not compile Tron.

`Wait for lab cache` checks that metadata for the complete closure has reached
the lab cache, without downloading payloads. It does not prepare or publish
build artifacts. `Build Tron` depends on both successful preparation and cache
readiness. Existing required check names remain unchanged.

`Build Tron` acquires and roots that plan using system Python. It builds the
specified derivation outputs without evaluating the checkout's flake; completed
runtimes can still be reused from the cache. Haskell evaluation plans remain
upstream; the lab handoff retains the derivation graph and realized build inputs
explicitly. Retaining only one of those would leave an incomplete offline build.
Runtime outputs get their own job roots before publication.

The Tron build checks the current runner's Slice platform data before compiling
and global Slice cost-data coverage against the resulting CTest manifest.
[`prepare_handoff.py`](bin/ci/tron-build/prepare_handoff.py) exports runtime paths
and the benchmark identity, and checks prior test passage. A rerun executes tests even
when the same runtime already passed.
`Build Tron` also uploads a runtime receipt with the full checkout SHA and the
canonical test-runtime and test-environment store paths. Slice refresh checks
this receipt and restores the same signed closures used by the test jobs.

### Prime Hugging Face Models (`prime-hf-models.yml`)

[`prime_hf_models.py`](bin/ci/prime_hf_models.py) prepares immutable model versions on the single `weights-writer-v2` runner, independently of product CI.
Priming runs on relevant changes or manual dispatch. Current main versions are retained; retired versions expire after 30 days. Expired PR-only versions can be re-primed.

#### Model cache lock recovery

Readers time out after 30 seconds of lock contention. Before replacing a stale lock, stop affected readers and writer jobs and confirm the old owner is gone. Replace the reported lock file with the same ownership and mode, then re-prime before retrying readers.

### Lint

Lint runs as a hermetic Nix check; identical inputs can reuse a successful result.
Reproduce it locally with:

```bash
nix build .#checks.x86_64-linux.lint-toolchain -L --no-update-lock-file
```

CI runs the checks directly; Lefthook remains the local pre-commit interface.
The named `.#lint` shell uses a compiled `tron-lint-notes` executable for Note
cross-references. GHC builds that executable once and is not part of the lint
runtime; neither is its documentation. The executable is repository-specific
and belongs in the private cache, separate from the audited upstream tools.
Non-Nix users can still run the source checker with GHC and Cabal.
A cache miss can build lint dependencies, including a new Haskell dependency
plan after an `ingest/*.cabal` change.

The workflow uses `bin/ci/run-lint-checks.sh` to report the result of that same
Nix build. Formatter failures produce a named error annotation and a job summary
with the pinned formatting command and the formatter's file list and differences.
The full Nix log remains available. Failures without a formatter diagnostic,
including other lint violations before or after formatting checks, are labeled
"Lint failed without a formatter diagnostic" and receive no formatting advice.

`bin/ci/lint-agent-guidance.py` validates canonical `AGENTS.md` files, exact
`CLAUDE.md` imports, skill ownership/metadata, and relative Markdown links. The
same hook runs `bin/ci/test-lint-agent-guidance.py` to protect the validator
itself.

Lint tools come from `flake.nix`; Ruff, PyYAML, and markdown-it-py are also
pinned in `ci/pyproject.toml` for the optional local CI environment.

The language formatters all run on every build of the check (the derivation
hash — not per-language path filtering — decides whether the check runs at
all):

| Check | Tool |
|-------|------|
| Nix formatting | nixfmt 1.1.0 (RFC style) |
| Haskell formatting | fourmolu 0.19.0.1 |
| Python formatting | ruff 0.15.1 |
| Rust formatting | rustfmt (via toolchain 1.92.0) |
| Shell formatting | shfmt 3.12.0 |

**Not gated in CI**: [ShellCheck](https://www.shellcheck.net/) is not currently
provided by the Nix development shell or enforced by CI because the existing
script backlog is not clean. Do not install an unpinned replacement for
repository checks; add an exact Nix/workflow pin when introducing the gate.

### CI Machinery Tests

Nix reuses successful check results for identical inputs:

| Nix check | Coverage |
|-----------|----------|
| `ci-machinery-contracts` | CI scripts, runtime handoffs, model selection, generated outputs, and publication |
| `cmake-sandbox-configure` | Offline CMake configuration and generated-state recovery |
| `rust-toolchain` | Pinned Rust tools, wrapper consumers, and test-binary staging |
| `perfetto-config` | CLI config generation, launchers, and Perfetto release pins (GCP Nix) |

Both workflows also exercise Cargo vendoring, lint rejection, signed-cache
handoffs, and source invalidation against the runner's Nix installation. See
[`cmake-single-platform.yml`](.github/workflows/cmake-single-platform.yml) and
[`gcp-nix.yml`](.github/workflows/gcp-nix.yml) for the commands.

The machinery check and named `.#ci-machinery` shell have their own dependency
list: Python test tooling, shell utilities, and the CMake/Ninja, compiler, dpkg,
and zstd tools needed by the build/artifact fixtures. Lint formatters and the
Haskell compiler are not part of that list. Lint regression and developer-hook
tests continue to use `.#lint`.

The machinery job also runs `bin/ci/run-ci-helper-suites.sh` and
`python3 -m pytest bin/ci-tests -q -rs`. The capture suite requires the pinned
Perfetto daemon and client for its integration checks.

### Debian Smoke Tests

The `deb-smoke-tests` job runs in `deb-smoke.yml`, independently of GCP Nix and
legacy builds. Its automatic triggers match GCP Nix: pushes to `main`, merge
groups targeting `main`, and PR events `opened`, `synchronize`, `reopened`, and
`ready_for_review`. Draft PRs run the check without a label override or path filter.

Manual dispatch and `workflow_call` accept the boolean `skip_deb_smoke` input,
which defaults to `false`. The legacy CMake workflow has no Debian smoke job
or APT token requirement. The separate `smoke-jammy` job in `publish-deb.yml`
checks authenticated APT access with the built package.

Require the standalone `deb-smoke-tests` check in branch protection. An
administrator must configure this requirement; the workflow alone does not
enforce it. A skipped job satisfies a required check. Keep `skip_deb_smoke` false
for manual or reusable runs used to validate candidates. Automatic events
cannot set this input. When the check is required and runs,
an outage of `apt.positron.internal`, an expired pinned certificate, or a
revoked token blocks merges until a rerun passes or an administrator bypasses
the check.

It runs `bin/ci/ci-run-deb-package-jammy-runtime.sh --apt-only` with a five-minute
job timeout, outside the ten-minute machinery job. It uses the same pinned
Ubuntu image and repository setup as the package installation smoke, without a
package artifact. `apt-get update --error-on=any` checks authenticated metadata
retrieval, TLS trust, and repository signatures for the Positron source only.
It does not check package installation or dependency
resolution. The check runs outside Nix so cached results cannot hide repository
or credential failures.

The `[self-hosted, no-fpga]` runner requires x86_64, Docker access, and container
network access to the image registry and `apt.positron.internal`. The check receives
`POSITRON_APT_LOGIN_TOKEN` only in its step environment. Repository policy must
authorize PR code to receive this token. Missing credentials fail the check;
fork runs without credentials cannot pass this required gate. Reusable callers
must pass the token explicitly.

### Slice Self-Tests (`slice.yml`)

The Slice workflow tests the Slice tooling itself, independently of the Tron
tests that `bin/slice run` schedules:

```
Relevant PR changes / manual dispatch
  └─→ nix build .#checks.x86_64-linux.slice-tests → pytest bin/slice-tests
```

PR runs are filtered to Slice, its self-tests, routing and wrapper helpers,
benchmark-refresh tooling, their configuration and Nix toolchain files, and
`GNUmakefile` (the self-tests exercise its `make` goal refusals under remote
profiles).
The workflow does not run on merge-queue events or pushes to `main`.
Manual dispatch remains available, including for the benchmark-refresh publisher.

The check uses synthetic manifests and processes, so it does not need a built
Tron tree, FPGA hardware, model weights, or benchmark measurements. Nix pins
the test toolchain and tracked source. Nix can reuse an identical derivation
already present in the runner's store or a configured substituter; this
workflow does not publish the result to a binary cache.

### Publish .deb Release (`publish-deb.yml`)

Release packaging on a `[self-hosted, general, heavy]` runner. Timeout: 150 min.
Triggers: nightly at 01:17 UTC (17:17 PST), manual dispatch, version tags
(`v*`).

Also callable via `workflow_call`. The `build` job runs `make deb` and retains
the exact package as a GitHub Actions artifact for one day. The `smoke-jammy`
job downloads that same-run artifact on a self-hosted x86_64 Docker runner,
installs it in a digest-pinned Ubuntu 22.04 container, and verifies that
`preinst` rejects a missing `positron` user or group before unpacking the Tron
payload while the packaged `preinst` and `postinst` allow Debian's
upgrade, remove, and deconfigure error-unwind paths. The smoke also verifies
that `postinst` restores the loader configuration removed by `prerm` during
each unwind. Production account provisioning is owned by
[`positron-ai/osimage`'s base Ansible layer](https://github.com/positron-ai/osimage/blob/main/layers/base/playbook.yaml).
The smoke provisions both
entries, retries the installation, checks the post-installation directory and
metadata contract, and verifies that the packaged tokenizer starts. The
container installs package dependencies from the authenticated Positron
`testing` APT channel. The `POSITRON_APT_LOGIN_TOKEN` GitHub secret supplies
the repository login. APT publication requires this smoke to pass.

#### Publishing from a feature branch

A manual dispatch accepts a `channel` input of `unstable` (the default) or
`testing`. The `resolve-channel` job runs `bin/ci/resolve-apt-channel.sh` to
pick the channel. Dispatches use the input. Tag pushes publish to `testing`.
Everything else publishes to `unstable`. The script refuses `testing`
for `main` and `release-*` refs, because their versions outrank every test
candidate, so only tag pushes and feature branches can reach `testing`.

```bash
gh workflow run publish-deb.yml --ref my-feature-branch -f channel=testing
```

A feature-branch publish runs the same full CI `test` job as a tag push before
it builds the package, so expect the run to take well over an hour. The
`build` job sets `TRON_FEATURE_BRANCH_BUILD=1` for feature branches, and
`bin/get-version.sh` then anchors the version to the nearest version tag
(`v<major>.<minor>.<patch>`, optionally `-devN`, `-tcN`, or `-rcN`), skipping
other `v`-prefixed tags: `2.0.0-tc11+feature.<branch>.<commits since tag>.g<sha8>`.
The Debian form is `2.0.0~1tc11~feature.<branch>.<n>.g<sha8>`. The second `~`
sorts the feature build below its anchor, so `apt upgrade` on a `testing` host
never prefers it; a build anchored to a release candidate or a final release
sorts below that anchor the same way. The build fails when no version tag is
reachable, so a feature build never falls back to a date version that would
outrank the candidates. Install one by pinning its exact version:

```bash
sudo apt install tron=2.0.0~1tc11~feature.my-feature-branch.225.g414f1d27
```

Local builds never set the variable and keep the date-based branch version.

The anchor comes from git, but the channel decides what `apt` installs. If an
anchor tag was never published to `testing`, because its publish failed or
was still running, a feature build cut after it would outrank the candidate
that is there. So a feature-branch publish to `testing` runs
`verify-testing-order` after the smoke test and before `publish-apt`. That
job lists `testing` over SSH with the deploy key
(`bin/ci/list-apt-channel-packages.sh`) and runs
`bin/ci/check-feature-below-candidate.sh`, which refuses the publish unless
the feature build's Debian version sorts below the highest non-feature
`tron` version in the channel. A channel with no such version is refused
too. The check is tested against canned `aptly` output and runs on every
feature publish, not only at rollout.

Feature-branch publishes to `testing` are disabled until the apt server
retains `~feature.` versions separately. `testing` keeps three versions per
package and major version, feature builds share the major-2 bucket with the
test candidates, and distinct feature publishes would evict the oldest
candidates. `publish-deb.yml` sets `FEATURE_TESTING_PUBLISH` to `"0"`, and the
resolver refuses `testing` for feature branches until it is `"1"`. Flip it in
a pull request that links the deployed `apt-server-conf` retention change. The
`testing` channel is also visible to select beta customers.

#### Rollout of the first feature publish to `testing`

Run these steps once, after the retention change is deployed and the flag is
`"1"`, with the channel owner's approval. Record the results in the enabling
pull request.

1. Dispatch the feature branch with `channel=unstable`. Confirm the `test` job
   ran, the `build` log shows a `~feature.` Debian version, and `publish-apt`
   reports `unstable`.
2. Dispatch the same branch with `channel=testing`. Confirm
   `verify-testing-order` names the candidate it compared against and
   `publish-apt` reports `testing`.
3. On the apt server, `aptly repo show -with-packages testing | grep tron`
   lists the feature build beside the retained test candidates, and no
   candidate disappeared.
4. On a `testing` host, `apt-cache policy tron` still names the test candidate
   as the install candidate, and `sudo apt install tron=<feature version>`
   installs the feature build.
5. Dispatch `main` with `channel=testing`. Confirm `resolve-channel` fails and
   nothing publishes.
6. Roll back by removing the feature build on the server with
   `aptly repo remove testing 'tron (= <feature version>)'` and republishing
   the `testing` snapshot per the `apt-server-conf` runbook, then reinstall
   the candidate on the host with `sudo apt install tron=<candidate version>`.

CMake-installed targets are stripped. Version-tag builds retain the unstripped
Rinzler artifact for 90 days to support symbolization with a matching load map
or core.

Debian package versions come from `bin/get-deb-version.sh`, which derives from
the raw Git version in `bin/get-version.sh` and applies Debian-specific
pre-release ordering (`dev` < `tc` < `rc` < final release). It also maps
characters outside Debian's version grammar to `.` so branch-derived suffixes
remain installable. A `+feature.` marker from a feature-branch build becomes
`~feature.` so the build sorts below the tag it is anchored to. Both the
Makefile artifact name and CPack metadata use this helper. The Nix
`ci-machinery-contracts` check runs `bin/ci/test-get-deb-version.sh` on every
pull request, and the publish workflow runs it again before packaging.

## Runner Infrastructure

### Runner Inventory

Runners are registered at the **org level** and shared to the tron repo. Visible
at repo Settings → Actions → Runners (requires Admin or CI Admin role).

**FPGA runner group** (6 runners):

| Runner | Host | Labels | CPU |
|--------|------|--------|-----|
| andoria-02-0 | andoria-02 | `fpga test benchmark avx512 2x96core hostname:andoria-02` | 2x 96-core Genoa |
| andoria-09-0 | andoria-09 | `fpga test benchmark avx512 2x96core hostname:andoria-09` | 2x 96-core Genoa |
| andoria-14 | andoria-14 | `fpga test benchmark avx512 2x96core hostname:andoria-14` | 2x 96-core Genoa |
| delphi-17cf-0 | delphi-17cf | `fpga test intel avx512 2x72core hostname:delphi-17cf shared-nightly` | 2x 72-core Intel Granite Rapids 6960P |
| delphi-3bd6-0 | delphi-3bd6 | `fpga test benchmark intel avx512 oci 2x72core hostname:delphi-3bd6` | 2x 72-core Intel Granite Rapids 6962P |
| delphi-3bda-0 | delphi-3bda | `fpga test benchmark intel avx512 oci 2x72core hostname:delphi-3bda shared-nightly` | 2x 72-core Intel Granite Rapids 6962P |

`delphi-3bda` is a separate Delphi host, not a misspelling of
`delphi-3bd6`. The regular benchmark workflows route `2x72core` jobs through
runner labels, including `oci`, rather than hostname spelling. That lets
`delphi-3bd6` and `delphi-3bda` share the OCI Intel benchmark class while
keeping `delphi-17cf` out of baseline comparisons.

**Default runner group** (9 runners on 2 hosts):

| Runner(s) | Host | Labels |
|-----------|------|--------|
| org-general-vm1-{0..7} (8 instances) | github-runner-1 (VM) | `cpu no-fpga general hostname:github-runner-1` |
| positron-prod-01-runner | positron-prod-01 | `prod service positron-prod-01` (not used by tron) |

**NixOS builders**:

| Runner(s) | Labels | Machine type |
|-----------|--------|--------------|
| nixos-general-small-* | `nix builder-s` | `n2-custom-8-16384` |
| nixos-general-medium-* | `nix builder-m` | `n2-custom-16-32768` |
| nixos-autoscale-* (readers) | `nix builder` | `n2-custom-16-98304` |
| nixos-autoscale-weights-writer-* | `nix weights-writer-v2` | `c3-highcpu-8` |

The general profiles omit the model-weights mount.
`prime-hf-models` uses the writer's `weights-writer-v2` label for its writable
GCP Filestore mount.

### Runner Labels

Labels are matched **literally** by GitHub Actions (no wildcards or regex).
Multiple labels at different specificity levels can be assigned to the same
runner, similar to Docker image tagging (e.g., `fpga_01.05.03`, `fpga`).
Workflows currently use the generic `fpga` label only.

**Label groups for non-FPGA jobs**: `cpu`, `no-fpga`, and `general` are all
assigned to the same 8 runners and are interchangeable. Current workflows use
`general` (benchmark-report), `[general, heavy]` (publish-deb build), and
`no-fpga` (`deb-smoke-tests`, publish-deb runtime smoke, and APT upload).

**Targeting a specific host**: All runners have a `hostname:<name>` label (e.g.,
`hostname:andoria-09`).

**Shared nightly scheduling**: The `shared-nightly` label marks runners managed
by a daytime/nighttime schedule. During the day, the GitHub runner is active;
at night, systemd timers stop it so the host can be used for nightly inference
or measurement. Current scheduled FPGA runners: `delphi-17cf`,
`delphi-3bda`.

**Who can modify labels**: Admin or CI Admin role.

### FPGA Bitfile Labels

Runners can be tagged with firmware-specific labels (e.g., `fpga_01.05.03`)
for version-pinned targeting if needed, but workflows currently use the generic
`fpga` label only. This keeps CI running on any available FPGA runner without
requiring label updates on bitfile changes.

### Required System Tools

GCP Nix supplies compilers and build tools through its pinned Nix environments.
Debian validation and packaging use the host toolchain described
in [README.dependencies.md](README.dependencies.md).

Local Make and CMake preset builds keep `/tmp/ccache-$USER`, avoiding NFS home
directories and preserving existing caches. The Nix CI build uses
`/opt/positron/.cache/ccache-nix` with group-writable cache files when writable
inside the sandbox; otherwise it compiles without CCache. Cache statistics
appear in the build log.

### NFS Mounts

| Path | Purpose | Retention |
|------|---------|-----------|
| `/scratch/test/cache/` | Benchmark reuse by source or runtime identity | Can be cleared anytime |
| `/scratch/tron-build/` | Test-passage markers and Debian validation archives | Three-day source-key lifetime |
| `/scratch/tron-benchmark/` | Persistent benchmark data (JSON per commit per host) | Indefinite (no reaping) |
| `/opt/positron/weights/huggingface/` | Model weights | Permanent |
| `/tools/` | Shared binaries (uv, etc.) | Permanent |
| `/ice/infra/apt/ubuntu/pool/main` | Legacy apt pool path (no longer written by CI) | Permanent |

The `/scratch` export uses NFS `sec=sys`: access checks compare numeric UID/GID,
not usernames. Use `bin/ci/ci-shared-nfs.sh` to create cross-UID-writable
directories, create permanent markers only when absent, and publish files
through unique same-directory temporaries and atomic rename.

### Access and Permissions

- **Runner visibility**: Admin or CI Admin role in the tron repo
- **Label management**: Admin or CI Admin role
- **FPGA bitfile updates**: No documented process currently
- **Runner outages / FPGA issues**: Contact Mitchell Stokes. Future: dedicated
  sys admin role.

## Job Patterns

### Runtime Environments

Nix pins build and runtime environments, including Python and UV. Test and
benchmark jobs also populate checkout-local virtual environments with
`uv sync --frozen`. Debian validation and packaging retain their host toolchain.

GCP's `Test ingest` job and the legacy CMake build invoke
`make test-ingest-python`, which runs `ingest/runtime/tests` and `ingest/export`
with both source roots on `PYTHONPATH`. The target uses the pinned Nix Python
inside `nix develop` and the lock-backed export venv otherwise. The legacy
build installs that venv with `uv sync --frozen --extra test` to include its
pinned test runner.

### CMake Flags

```bash
cmake -B gen --preset native \
  -DBUILD_TEST_MODELS=ON \
  -DBUILD_INGEST_MODELS=ON \
  -DTRON_AMX_DISPATCH=ON \
  -DTRON_K_VNNI=ON
```

The build job leaves `TRON_PAGE_SHARE_COUNTERS` at its default (OFF), so the
`gen/runtron` in the benchmark runtime carries no page-share
instrumentation (`h/tron/kernels/page_share_counters.hpp` and five hook blocks
in `h/tron/models/self_attention.hpp`). The `coverage` preset in
`CMakePresets.json` sets the option ON; `cpp-coverage.yml` builds that preset
(`make build-coverage`) and runs the host tests, so the hooks are compiled there
and exercised by `t_llama_unit`. `t_page_share_counters` compiles the counter
header with its own define in every lane. A binary built with the option that
counted at least one KV page visit prints a four-line `[page-share]` summary to
stderr at normal exit.

`TRON_AMX_DISPATCH=ON` compiles the AMX software-attention kernels and their
dispatch (see Note [AMX attention dispatch] in
`h/tron/kernels/amx_attn_iface.hpp`) so CI covers that code. The `deb` preset
also sets the option ON, so the released package carries the kernels and
selects them at run time only on hosts with AMX. Every other preset leaves it
at its default OFF. The kernel cases of `t_amx_numerics` execute AMX only when
the test job lands on a Granite Rapids runner; elsewhere they skip with a
warning.

`TRON_K_VNNI=ON` stores the K cache of 128-dim heads in the AMX VNNI layout
(VNNI = Vector Neural Network Instructions: the pair-interleaved operand layout
of the AMX tile multiply). The option is OFF by default in every other build.
Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` describes the layout.
With the option on, the whole test suite runs on the VNNI layout.
`t_k_vnni_layout` and the `save_k` case of `t_llama_unit` exercise the VNNI
store, the reader and the page copy. The VNNI kernel case of `t_amx_numerics`
exercises the store and the AMX kernel `qk_vnni_128x4`. That case compiles in
every `TRON_AMX_DISPATCH=ON` build, with or without this option, and executes
AMX only on a Granite Rapids runner, as above. The
`coverage` preset (built by the manual-only `cpp-coverage.yml`) sets neither
option. It keeps the row-major K layout covered. In the legacy CMake workflow
the bundled `gen/runtron` is built with `TRON_AMX_DISPATCH=ON` and
`TRON_K_VNNI=ON`. So its benchmark job measures the VNNI K layout when it uses
the artifact. When it falls back to the local rebuild (`make gen/config/test`
sets neither option) it measures the row-major layout. The GCP Nix benchmark
runtime (`nix/cmake-tron-test-build.nix`) sets neither option and measures the
row-major layout.

`BUILD_INGEST_MODELS=ON` enables the ingest pipeline integration in the C++
build. GCP Nix also requires the complete test model profile. Developers can
still opt out for a specialized local configuration with
`-DBUILD_INGEST_MODELS=OFF`.

The `native` preset is the default Linux build tree, used by `make` and by the
CI build. No preset adds `-march=native`: tron, pos, rinzler and the generated
model code always compile with an explicit AVX2 and AVX-512 flag set, so
binaries that link them need an AVX-512 host. On a Linux host without AVX-512,
`make` still builds; Note [Cross-Compile for AVX-512] in `GNUmakefile` lists the
test targets that refuse to run there.

### Result Reuse

Nix store paths identify immutable build and tool closures. A changed
input changes the relevant output identity without a separate cache-key list.
An empty NFS passage marker records that one exact test-runtime and
test-environment pair passed both executor jobs. The first workflow attempt may
reuse that marker; a GitHub rerun always executes the host and FPGA tests.

Benchmark reuse is keyed by the exact benchmark payload, tracked source,
machine class, and host identity. Completed measurements are cached separately
from the report copy for each commit and host. Cache hits restore that report;
a GitHub rerun forces fresh measurements. Missing or invalid runtime closures
fail without falling back to a local rebuild.

### FPGA Test Sequencing

The exact test environment supplies `tron-test-host` and `tron-test-fpga`.
They invoke Slice's host and FPGA filters, with a minimum two-slice allocation
for FPGA tests.

### Concurrency Control

Default CI uses:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

This cancels in-progress runs when a new push arrives on the same PR or branch.
The publish-deb workflow does not currently define a concurrency group.

## Benchmarking

Default CI benchmarks pushes to `main` and eligible PRs, skipping merge-group
events. `Skip benchmarks` suppresses PR benchmarks and reporting on the next
PR event; label changes do not trigger or cancel a run. Benchmark reports are
posted as PR comments.

Separately, `2x72core` jobs require the `oci` self-hosted runner label. This
machine-level label restricts which runners can execute that benchmark class and
keeps non-OCI Intel hosts out of baseline comparisons. Assignment of the label
to runners is managed by the [Ansible scripts][ansible].

### Data Flow

```
benchmark ──► /scratch/tron-benchmark/<sha7>.<host>.json
                                    ↓
benchmark-report ──► reads all shards ──► updates PR comment
```

Report filenames use the first seven commit characters and the benchmark host
name. The report job generates the combined Markdown summary.

The benchmark-report job uses `peter-evans/find-comment` +
`peter-evans/create-or-update-comment` to maintain a single comment per PR
(avoids the race condition of parallel runners overwriting each other).

### Forcing Re-run

Use GitHub's **Re-run jobs** action. Rerunning a host or FPGA test job executes
its tests even when Build Tron is not rerun and its original handoff reused an
exact passage marker. Benchmark retries force fresh measurements for the
selected commit and runner identity.

For benchmark configuration details, see `bin/ci/benchmark_save.py`.

## Reproducing CI Locally

Enter the supported Nix development environment, use the same public targets
as local development, and run the CI machinery checks and Nix toolchain checks:

```bash
nix develop --accept-flake-config
make build-test
make format
make lint
make test-agent-guidance
nix build .#checks.x86_64-linux.ci-machinery-contracts \
  .#checks.x86_64-linux.cmake-sandbox-configure \
  .#checks.x86_64-linux.rust-toolchain \
  .#checks.x86_64-linux.slice-tests -L
nix develop .#slice-tests -c python3 -m pytest bin/slice-tests
bin/ci/test-cargo-vendor-helper-guard.sh
bin/ci/run-ci-helper-suites.sh
bin/ci/test-lint-check-regressions.sh
python3 -m pytest bin/ci-tests -q -rs
bin/ci/test-nix-ingest-source-identity.sh
nix build '.#.legacyPackages.x86_64-linux.perfetto-config-check' \
  --no-accept-flake-config --option allow-import-from-derivation false \
  --no-update-lock-file -L
bin/slice route
```

The Perfetto entry point runs the same test as
`checks.x86_64-linux.perfetto-config` without evaluating Haskell checks.
Automatic Haskell check discovery is unchanged.

Use `nix develop .#cmake-sandbox` to inspect or reproduce the CMake sandbox
with the same compiler, build tools, and dependency inputs used by its check.

For a `local-shared-dice` or `local-legacy` verdict, run `make test-host` and
`make test-fpga`. For `distributed-dice`, add `REMOTE=1`. A `blocked` verdict
blocks FPGA work; do not bypass it.

Lab test jobs also require their model-weight and `/scratch/` mounts. See
[Runtime Environments](#runtime-environments) for the Nix and UV handoff and
[README.dependencies.md](README.dependencies.md) for local setup.

## Changing CI Jobs

### Before Making Changes

1. Understand caching — changes may invalidate existing caches
2. Check job dependencies — downstream jobs may be affected
3. Test locally using `make` targets (see [Reproducing CI Locally](#reproducing-ci-locally))

### Checklist for New/Modified Jobs

- [ ] Does it need FPGA hardware? → Use appropriate runner labels
- [ ] Does it add new secrets? → Document in appropriate place
- [ ] Does it affect benchmarks? → Coordinate with benchmark owners
- [ ] Timeout set appropriately?
- [ ] Dependencies (`needs:`) correct?

### Security Practices

- All third-party actions pinned to commit SHA: `uses: action@<sha> # <tag>`.
  See [README.dependencies.md](README.dependencies.md#github-actions) for the
  full SHA table and update instructions.
- `make lint` enforces SHA pins — tag-only refs are blocked. See
  [README.dependencies.md](README.dependencies.md#ci-enforcement).
- No secrets in workflow files — use NFS mounts or GitHub secrets

### Adding Lint Checks

1. Define the local pre-commit command in `lefthook.yml`
2. Add the matching direct CI command and pinned tools to `flake.nix`
3. Run `nix build .#checks.x86_64-linux.lint-toolchain -L`

## Artifact Strategy

Default CI transports immutable build inputs and compiled runtimes as signed
Nix closures. NFS holds passage markers, benchmark measurements and reports,
model weights, and the archives used by Debian validation. Build diagnostics
remain in the job logs.

Release artifacts (.deb packages) are published via the shared
`positron-ai/github-actions/publish-apt.yml` reusable workflow, which uploads
to the internal apt server over SSH from a self-hosted runner. The
`resolve-channel` job in `publish-deb.yml` picks the channel through
`bin/ci/resolve-apt-channel.sh`: the `channel` input for manual dispatches,
`testing` for tag pushes, and `unstable` otherwise.

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|--------------|------------|
| Nix formatting fails | Nix source not formatted | `nix fmt -- <path>.nix` |
| Lint fails on format | Code not formatted | `make format` locally |
| Wait for lab cache is running | Build-plan closure metadata has not reached the lab cache | Inspect the wait log for the missing store path and elapsed time |
| Tron build timeout (120 min) | Closure realization or compilation stalled | Inspect CMake and Ninja output in the `Build Tron` job |
| FPGA test hangs | Hardware contention | Check runner state |
| Benchmark missing shards | Runner offline | Check runner status |
| Cache not working | NFS mount issue | Verify `/scratch/` accessible |
| Benchmark shows NaN | Baseline run failed (e.g., OOM) | Check baseline data; see #2062 |

### Debugging Tools

- `bin/ci/download-sporadic-ci-failures.py` — Fetch CI failure logs
- `bin/ci/analyze-sporadic-ci-failures.py` — Analyze failure patterns
- `bin/ninjatracing` — Generate build trace

### Runner State

```bash
sudo systemctl status actions.runner.*
sudo /opt/positron/bin/tronpost --targets 81:00.0,41:00.0
```

## Related Links

- [Actions Performance Metrics](https://github.com/positron-ai/tron/actions/metrics/performance)
- [Actions Usage Metrics](https://github.com/positron-ai/tron/actions/metrics/usage)

[ansible]: https://github.com/positron-ai/positron-infrastructure/tree/main/ansible
