# tron build failure on alpha (claude-box)

Date: 2026-08-09
Goal: build runtron from tron `origin/main` (commit `12804a8`, 2026-08-09) on
the `claude-alpha` container so it recognizes the two newly-registered models
`ingested-qwen-3-4b-instruct-2507` and `ingested-qwen-3-30b-a3b-instruct-2507`.

**Outcome: could not complete the build in this container.** Two independent
container restrictions block Nix; I worked around the first, the second is a
container-launch security setting that cannot be changed from inside the
container. The models themselves are confirmed present in tron main (they build
elsewhere) — this is purely an alpha/claude-box environment problem, not a tron
problem.

## What I was doing

```
git clone (local mirror) -> /var/tmp/tron-main, checkout origin/main 12804a8
# Nix not preinstalled; installed single-user Nix 2.18.9 to /nix
cd /var/tmp/tron-main
nix develop --command make CMAKE_PRESET=cross-avx512 build
```

`cross-avx512` preset chosen because alpha is AMD Ryzen 9 9950X: it has AVX-512,
but shared artifacts are meant to be built with `BUILD_NATIVE=OFF` + explicit ISA
(see Note [Cross-Compile for AVX-512] in GNUmakefile). The build needs
`BUILD_INGEST_MODELS=ON` because the qwen-3 models are `source: generated`
(ingest-pipeline-generated C++), which pulls in the haskell.nix ingest toolchain.

## Blocker 1 (WORKED AROUND): fuse-overlayfs rejects group-chown with EINVAL

Container root fs is `fuse-overlayfs`. Any ownership change that alters the group
returns `EINVAL`:

```
chown 0:1 file      -> EINVAL   ("changing ownership ...: Invalid argument")
chmod -R on a dir   -> EPERM    (overlayfs-in-userns)
```

This broke the Nix installer ("changing ownership of /nix/store: Invalid
argument") and derivations like `pkg-config-wrapper`.

Fixes applied:
- Nix single-user install with `build-users-group =` (empty) in
  `/etc/nix/nix.conf`.
- **`sandbox = true`** in `/etc/nix/nix.conf`. User namespaces ARE available in
  this container (`unshare --user --mount` works;
  `/proc/sys/user/max_user_namespaces` = 2147483647), so the Nix sandbox builds
  each derivation in a private tmpfs mount namespace, avoiding the overlayfs
  chown path. Verified: `pkg-config-wrapper-0.29.2.drv` builds cleanly once
  sandbox is on.

Also added the project's binary caches to `/etc/nix/nix.conf`
(`tron.cachix.org`, `cache.iog.io`) so most derivations are fetched, not built.

## Blocker 2 (COULD NOT FIX from inside): seccomp EPERMs fchmodat2

Even under the sandbox, the haskell.nix derivation
`source-repository-package.drv` (a cabal git dependency of the ingest Haskell
project) fails:

```
rsync: [receiver] failed to set permissions on ".../test/.Test.hs.Rw9lun":
       Operation not permitted (1)
rsync error: some files/attrs were not transferred (code 23)
```

Root cause, confirmed with a direct syscall probe on alpha:

```
fchmodat(268):   rc=0   ok
fchmodat2(452):  rc=-1  Operation not permitted   <-- seccomp returns EPERM
```

- The nix-store `rsync` is **3.4.1**, which calls `fchmodat2`.
- The container's seccomp filter returns **EPERM** (not ENOSYS) for `fchmodat2`.
- rsync only falls back to the legacy `fchmodat` on ENOSYS/EINVAL, not EPERM, so
  it treats the EPERM as a hard failure and aborts with code 23.
- The host's own `/usr/bin/rsync` is **3.2.7** (predates fchmodat2) and works
  fine — which is why ordinary shell rsync succeeds but the Nix build's rsync
  does not.

This is the classic "old seccomp profile + new glibc/tooling" problem: a
container whose seccomp default action is `SCMP_ACT_ERRNO(EPERM)` for unlisted
syscalls breaks any program that probes a newer syscall expecting ENOSYS.

### Why I could not fix it in-container

- The correct fixes are all at **container launch** (outside my reach):
  - relaunch claude-box with `--security-opt seccomp=unconfined`, or
  - use an updated seccomp profile whose default action is
    `SCMP_ACT_ERRNO(ENOSYS)` (Docker >= 20.10 / recent moby default), or
  - launch with a runtime that passes newer syscalls through.
- The only in-container workaround is an `LD_PRELOAD` shim that intercepts
  `fchmodat2` and retries as `fchmodat` — I attempted this and it was blocked by
  the Claude Code safety classifier (a syscall-interception library reads as
  malicious out of context). I did not attempt to bypass that block.
- Replacing the nix-store rsync 3.4.1 with an older one, or patching the
  haskell.nix internal derivation, is possible in principle but deep and
  fragile, and would have to be redone on every haskell.nix bump.

## Recommended remediation (fastest first)

1. **Relaunch claude-box on alpha with `--security-opt seccomp=unconfined`**
   (or an ENOSYS-default seccomp profile). Then the recipe below completes with
   no code changes. This is a ~1-line change for whoever owns the container.
2. If the container cannot be relaunched, build tron on a normal (non-container)
   host or a VM where fchmodat2 is allowed.
3. As a last resort, build the ingest deps via the documented non-Nix path
   (`make ingest-deps` + native GHC/Cabal/clang-19), which uses cabal's own
   fetch instead of nix-store rsync — but this requires bootstrapping the full
   native toolchain and C++ deps by hand and was not attempted.

## Recipe that should work once the container is fixed

```
# /etc/nix/nix.conf already has: build-users-group=(empty), sandbox=true,
# substituters incl. tron.cachix.org + cache.iog.io, accept-flake-config=true
cd /var/tmp/tron-main            # origin/main @ 12804a8, or fresh clone
nix develop --command make CMAKE_PRESET=cross-avx512 build
# then install for delphi:
#   copy gen/runtron + required libs to /scratch/jhan/<install>/, record sha256,
#   update the campaign harness INSTALL/BIN/EXPECTED_BIN_SHA.
```

## State left behind on alpha

- `/nix` — single-user Nix 2.18.9, populated store (fetched deps cached).
- `/etc/nix/nix.conf` — sandbox on, caches + keys added, build-users-group empty.
- `/var/tmp/tron-main` — origin/main checkout at 12804a8 on branch `build-main`.
- `/var/tmp/tron-build*.log` — build attempt logs.
- No changes made to the tron source; no runtron binary produced.

## Impact on the requested campaigns

All three requested 20-round campaigns (qwen-3-4b, qwen-3-30b-a3b, gpt-oss-20b on
the new binary) are **blocked** on this build: the frozen Aug-6 binary
(`/scratch/jhan/tron-perfetto-vanilla-install-20260806/bin/runtron`) does not
know the qwen-3 models (verified: its model registry lists only qwen-2.5-32b),
so it cannot run two of the three. Nothing was launched on delphi-3bda.
