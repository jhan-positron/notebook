#!/usr/bin/env bash
# build-run.sh - compile ktest.cpp together with the real kernel translation
# unit src/tron/kernels/amx_attn.cpp on delphi-3bda and run it there, pinned
# to our half of the machine (cpus 72-143) at nice 10. Run from claude-box:
#   bash build-run.sh            # build + run, writes results.txt + build.log
# The flags are taken from gen/compile_commands.json of the 3bda-local
# worktree /var/tmp/jhan/tron-pr4 (commit ea94e95a4e), i.e. the exact flags
# the project compiles amx_attn.cpp with (-O3, -DTRON_K_VNNI,
# -DTRON_AMX_DISPATCH, spdlog include path, AMX/AVX-512 target flags).
# ktest.cpp gets the same flags plus -ffp-contract=off, so the scalar fp32
# references in it are plain RNE adds and multiplies.
set -u
KT=/home/jhan/workspace/intel-AMX/exec/td-20261016/ktest   # NFS, same path on 3bda
WT=/var/tmp/jhan/tron-pr4
HOST=delphi-3bda
OUR_CPUS=72-143
LOCAL_SHA=$(sha256sum "$KT/ktest.cpp" | cut -c1-64)
# NFS attribute-cache trap: make sure 3bda sees the file we just wrote.
for i in $(seq 1 30); do
  REMOTE_SHA=$(ssh $HOST "sha256sum $KT/ktest.cpp" 2>/dev/null | tail -1 | cut -c1-64)
  [ "$REMOTE_SHA" = "$LOCAL_SHA" ] && break
  sleep 2
done
[ "$REMOTE_SHA" = "$LOCAL_SHA" ] || { echo "3bda still sees a stale ktest.cpp"; exit 1; }
ssh $HOST bash -s "$KT" "$WT" "$OUR_CPUS" <<'REMOTE' 2>&1 | tail -n +1
KT=$1; WT=$2; OUR_CPUS=$3
cd "$WT" >/dev/null 2>&1 || { echo "no worktree $WT"; exit 1; }
echo "=== build $(date -u +%FT%TZ) on $(hostname) worktree=$(git rev-parse --short HEAD) amx_bf16_cpus=$(grep -c amx_bf16 /proc/cpuinfo) load=$(cut -d' ' -f1-3 /proc/loadavg)"
FLAGS=$(python3 - <<'PY'
import json, shlex
cc = json.load(open("gen/compile_commands.json"))
for e in cc:
    if e["file"].endswith("src/tron/kernels/amx_attn.cpp"):
        args = shlex.split(e["command"])
        out = []
        skip = False
        for a in args[1:]:
            if skip: skip = False; continue
            if a == "-o": skip = True; continue
            if a in ("-c", "-fcolor-diagnostics") or a.endswith("amx_attn.cpp"): continue
            out.append(a)
        print(" ".join(shlex.quote(a) for a in out))
        break
PY
)
echo "FLAGS=$FLAGS" > "$KT/build.log"
nice -n10 taskset -c $OUR_CPUS ~/.nix-profile/bin/nix develop --accept-flake-config --command bash -c "
  set -e
  cd $WT
  CXX=clang++-19
  \$CXX $FLAGS -c src/tron/kernels/amx_attn.cpp -o $KT/amx_attn.o
  \$CXX $FLAGS -ffp-contract=off -Wno-unused-variable -Wno-unused-but-set-variable -c $KT/ktest.cpp -o $KT/ktest.o
  \$CXX $KT/ktest.o $KT/amx_attn.o gen/_deps/spdlog-build/libspdlog.a -lpthread -o $KT/ktest
  echo build ok
" >> "$KT/build.log" 2>&1 || { echo "BUILD FAILED"; tail -40 "$KT/build.log"; exit 1; }
tail -1 "$KT/build.log"
sha256sum "$KT/ktest"
echo "=== run $(date -u +%FT%TZ)"
nice -n10 taskset -c $OUR_CPUS "$KT/ktest" > "$KT/results.txt" 2>&1
echo "rc=$?"
echo "=== done $(date -u +%FT%TZ)"
REMOTE
