#!/usr/bin/env bash
# Build PR 4557 head (baseline) and the plain-names revert on delphi-3bda,
# socket 1 only; compare libtron.a disassembly; run the four unit tests.
set -uo pipefail
WT=/var/tmp/jhan/tron-i4525-style
SRC=/home/jhan/workspace/ai-runs/tron-i4525-style
OUT=/var/tmp/jhan/tron-i4525-style-tests
BASE=c5d44bd86fe97914d2d3c7144b8045ebfad9fba0
CPUS=72-143,216-287
NIX="$HOME/.nix-profile/bin/nix develop --accept-flake-config --command"
TARGETS="t_llama_unit t_amx_numerics t_heap_v2 t_amx_dispatch_dtype"
FILES="h/tron/tensor/v_vnni.hpp src/tron/kernels/amx_attn.cpp t/t_heap_v2.cpp t/t_llama_unit.cpp"
log(){ echo "[$(date -u +%FT%TZ)] $*"; }
mkdir -p $OUT/base $OUT/new
if [ ! -d $WT ]; then
  log "worktree add"; git -C /home/jhan/workspace/tron worktree add --detach $WT $BASE || exit 1
fi
cd $WT || exit 1
git checkout --quiet --detach $BASE && git checkout -- . && log "tree at $(git rev-parse --short HEAD), clean: $(git status --short | wc -l) changes"
if [ ! -f gen/CMakeCache.txt ]; then
  log "configure"
  taskset -c $CPUS $NIX bash -c "cmake --preset native -DAVX512=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF" > $OUT/configure.log 2>&1 || { log "configure FAILED"; tail -20 $OUT/configure.log; exit 1; }
fi
log "build baseline"
taskset -c $CPUS $NIX bash -c "cmake --build gen -j 48 --target $TARGETS -- -k 0" > $OUT/build-base.log 2>&1 || { log "baseline build FAILED"; grep -E 'error|FAILED' $OUT/build-base.log | head -20; exit 1; }
cp gen/src/tron/libtron.a $OUT/base/; for t in $TARGETS; do cp gen/$t $OUT/base/; done
objdump -d --no-show-raw-insn $OUT/base/libtron.a > $OUT/base/libtron.dis
log "baseline done: $(wc -l < $OUT/base/libtron.dis) disassembly lines"

log "sync edited tree"
rsync -rlc --exclude=/.git --exclude=/gen --exclude='/gen-*' --exclude=/ingest/traces --exclude=/ingest/dist-newstyle --exclude=/compile_commands.json $SRC/ $WT/ || exit 1
git status --short
log "changed files: $(git status --short | wc -l) (expect 4)"

log "clang-format check (repo toolchain)"
$NIX bash -c "clang-format --version; clang-format --dry-run -Werror $FILES" > $OUT/clang-format.log 2>&1; echo "clang-format exit $?" | tee -a $OUT/clang-format.log
log "lint-notes"; $NIX bash -c "bin/lint-notes" > $OUT/lint-notes.log 2>&1; echo "lint-notes exit $?" | tee -a $OUT/lint-notes.log
log "whitespace"; git --no-pager diff --check $BASE -- ':!lib/**' > $OUT/whitespace.log 2>&1; echo "whitespace exit $?" | tee -a $OUT/whitespace.log
log "cassert"; grep -l '#include <cassert>' $FILES > $OUT/cassert.log 2>&1; echo "cassert hits: $(wc -l < $OUT/cassert.log) (expect 0)"

log "build new"
taskset -c $CPUS $NIX bash -c "cmake --build gen -j 48 --target $TARGETS -- -k 0" > $OUT/build-new.log 2>&1 || { log "new build FAILED"; grep -E 'error|FAILED' $OUT/build-new.log | head -40; exit 1; }
grep -c -E '^\[[0-9]+/[0-9]+\]' $OUT/build-new.log | xargs -I{} log "new build steps: {}"
cp gen/src/tron/libtron.a $OUT/new/; for t in $TARGETS; do cp gen/$t $OUT/new/; done
objdump -d --no-show-raw-insn $OUT/new/libtron.a > $OUT/new/libtron.dis
if cmp -s $OUT/base/libtron.dis $OUT/new/libtron.dis; then log "libtron.a disassembly IDENTICAL"; else log "libtron.a disassembly DIFFERS: $(diff $OUT/base/libtron.dis $OUT/new/libtron.dis | wc -l) diff lines"; fi
for t in $TARGETS; do
  objdump -d --no-show-raw-insn $OUT/base/$t > $OUT/base/$t.dis; objdump -d --no-show-raw-insn $OUT/new/$t > $OUT/new/$t.dis
  if cmp -s $OUT/base/$t.dis $OUT/new/$t.dis; then log "$t disassembly IDENTICAL"; else log "$t disassembly differs: $(diff $OUT/base/$t.dis $OUT/new/$t.dis | grep -c '^[<>]') changed lines (test code changed; rodata strings differ)"; fi
done

log "run tests (socket 1)"
for t in $TARGETS; do
  taskset -c $CPUS ./gen/$t > $OUT/$t.out 2>&1; rc=$?
  log "$t exit $rc: $(grep -E 'test cases|All tests passed|assertions' $OUT/$t.out | tail -2 | tr '\n' ' ')"
done
log "DONE"
