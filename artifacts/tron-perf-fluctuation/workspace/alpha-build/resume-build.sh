#!/usr/bin/env bash
# Resume the tron build on alpha AFTER the container is relaunched with
# seccomp=unconfined (see ~/workspace/tron-build-fail-alpha.md).
#
# The container root fs (/, /var/tmp, /nix) is ephemeral fuse-overlayfs, so a
# relaunch wipes the Nix install and the checkout. This rebuilds both from
# scratch. /home/jhan and /scratch are NFS and persist.
#
# Usage:  bash ~/workspace/alpha-build-scaffold/resume-build.sh
set -euo pipefail

NIX_VER=2.18.9
SRC=/var/tmp/tron-main
LOG=/home/jhan/workspace/alpha-build-scaffold/resume-build.log
exec > >(tee "$LOG") 2>&1
echo "resume-build starting $(date -u +%FT%TZ)"

# 0. sanity: confirm the seccomp fix is actually in place before doing 3.2G of work
# rc=0 (works) or ENOSYS (kernel/seccomp says "not implemented" — rsync falls
# back to fchmodat) are both fine; only EPERM reproduces the original blocker.
cat > /tmp/fchk.c <<'EOF'
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <fcntl.h>
int main(){int fd=open("/tmp/fchkf",O_CREAT|O_WRONLY,0644);close(fd);
  errno=0; long r=syscall(452,AT_FDCWD,"/tmp/fchkf",0644,0);
  printf("fchmodat2 rc=%ld errno=%d (%s)\n",r,errno,strerror(errno));
  if(r==0||errno==ENOSYS) return 0;
  return 1;}
EOF
gcc -o /tmp/fchk /tmp/fchk.c
if ! /tmp/fchk; then
  echo "ABORT: fchmodat2 returns EPERM — the seccomp blocker is still present."
  echo "       Relaunch the container with seccomp=unconfined (see fail doc)."
  exit 1
fi
echo "fchmodat2 OK (works or ENOSYS) — rsync fallback path is safe."

# 1. install single-user Nix if absent
if ! [ -x /nix/var/nix/profiles/per-user/root/profile/bin/nix ]; then
  mkdir -p /nix /etc/nix
  cat > /etc/nix/nix.conf <<'CONF'
build-users-group =
experimental-features = nix-command flakes
sandbox = true
substituters = https://cache.nixos.org https://tron.cachix.org https://cache.iog.io
trusted-public-keys = cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY= tron.cachix.org-1:frKV7mquRWa4U3F0xjUtBehGgDzRofVj328awV2L+dQ= hydra.iohk.io:f/Ea+s+dFdN+3Y/G+FDgSq+a5NEWhJGzdjvKNGv0/EQ=
accept-flake-config = true
CONF
  cd /var/tmp && rm -rf nix-unpack && mkdir nix-unpack && cd nix-unpack
  curl -sSf -L -o nix.tar.xz "https://releases.nixos.org/nix/nix-${NIX_VER}/nix-${NIX_VER}-x86_64-linux.tar.xz"
  tar xf nix.tar.xz
  "nix-${NIX_VER}-x86_64-linux/install" --no-daemon
fi
export PATH=/home/jhan/.nix-profile/bin:$PATH
nix --version

# 2. fresh checkout of tron main. Prefer the persistent NFS mirror (no auth,
# already holds the objects); best-effort refresh it from GitHub if auth works.
MIRROR=/scratch/jhan/tron-src
git config --global --add safe.directory "$MIRROR" 2>/dev/null || true
( cd "$MIRROR" && git fetch --quiet origin main ) || echo "(mirror refresh skipped; using cached origin/main)"
if ! [ -d "$SRC/.git" ]; then
  git clone --quiet "$MIRROR" "$SRC"
  cd "$SRC"
  git config --global --add safe.directory "$SRC" 2>/dev/null || true
  git fetch --quiet "$MIRROR" 'refs/remotes/origin/main:refs/heads/build-main'
  git checkout --quiet -f build-main
fi
cd "$SRC"
git config --global --add safe.directory "$SRC" 2>/dev/null || true
echo "building tron @ $(git rev-parse --short HEAD)  (want 12804a8 or newer)"

# overlay: exclude gated-HF ingest models (no HF token available; see
# models.local.yaml in the scaffold dir for the why)
cp /home/jhan/workspace/alpha-build-scaffold/models.local.yaml "$SRC/config/models.local.yaml"

# 3. build (cross-avx512 preset for shared artifacts; alpha has AVX-512)
# /dev/shm is only 63M in the relaunched container; use /var/tmp (80G) instead.
mkdir -p /var/tmp/nixtmp
TMPDIR=/var/tmp/nixtmp nix develop --command make CMAKE_PRESET=cross-avx512 build

# 4. report artifact
ls -la "$SRC"/gen/runtron && sha256sum "$SRC"/gen/runtron
echo "BUILD OK. Next: install runtron+libs under /scratch/jhan/, record sha256,"
echo "set harness INSTALL/BIN/EXPECTED_BIN_SHA, then run the 3 campaigns with the"
echo "sys-enabled template ~/workspace/common/perfetto.cfg-template."
