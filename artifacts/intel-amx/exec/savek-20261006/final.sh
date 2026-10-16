#!/usr/bin/env bash
# savek-20261006 final step (runs ON delphi-3bda after chain.sh): rebuild t_llama_unit at the FINAL commit of the fold
# branch in the chain's VNNI worktree (/var/tmp/jhan/tron-savek) and in the row-major one, run it, and run the
# ingest Haskell tests once more. The commits after the chain's COMMIT change one test and one comment only.
# Usage (on 3bda): COMMIT=<full sha> bash final.sh
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
B=$EXEC/i4525-20260922/build2.sh
NAME=savek-20261006
RES=$EXEC/results/$NAME
LOG=$EXEC/logs/$NAME-final.log
REPO=/home/jhan/workspace/tron
COMMIT=${COMMIT:?}
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
CONF_VNNI='--preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON -DCMAKE_CXX_FLAGS='
CONF_RM='--preset cross-avx512 -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=OFF -DCMAKE_CXX_FLAGS='
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
ts() { date -u +%FT%TZ; }
exec >>"$LOG" 2>&1
rm -f "$RES/final.done"
echo "=== $NAME final started $(ts) COMMIT=$COMMIT ==="
while ci_lease_busy 600 || other_user_active 2>/dev/null; do echo "$(ts) waiting: CI lease busy or another person active"; sleep 120; done
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-savek SUFFIX=final CONFIGURE_ARGS="$CONF_VNNI" TARGETS="t_llama_unit" TESTS="t_llama_unit" JOBS=64 bash "$B"
echo "$(ts) VNNI t_llama_unit: $(cat "$RES/build-final.done") $(cat "$RES/tests-final.txt")"
env RES="$RES" SRC="$REPO" COMMIT="$COMMIT" WT=/var/tmp/jhan/tron-savekrm SUFFIX=finalrm CONFIGURE_ARGS="$CONF_RM" TARGETS="t_llama_unit" TESTS="t_llama_unit" JOBS=64 bash "$B"
echo "$(ts) row-major t_llama_unit: $(cat "$RES/build-finalrm.done") $(cat "$RES/tests-finalrm.txt")"
t0=$(date +%s)
( cd /var/tmp/jhan/tron-savek && nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c 'bin/ingest-cabal test 2>&1 | tail -40; echo "ingest-cabal-test rc=${PIPESTATUS[0]}"' ) >"$RES/ingest-test-final.txt" 2>&1
echo "$(ts) ingest tests done in $(( $(date +%s) - t0 )) s: $(grep -E 'rc=|examples,' "$RES/ingest-test-final.txt" | tr '\n' ' ' | cut -c1-300)"
v=$(cat "$RES/build-final.done"); r=$(cat "$RES/build-finalrm.done"); i=$(grep -o 'ingest-cabal-test rc=[0-9]*' "$RES/ingest-test-final.txt")
if [ "$v" = ok ] && [ "$r" = ok ] && [ "$i" = "ingest-cabal-test rc=0" ]; then echo ok >"$RES/final.done"; else echo "failed vnni=$v rm=$r $i" >"$RES/final.done"; fi
echo "=== $NAME final finished $(ts): $(cat "$RES/final.done") ==="
