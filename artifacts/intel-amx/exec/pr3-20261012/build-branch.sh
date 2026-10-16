#!/bin/bash
# Rebuild the PR-3 branch jhan-vnnik-3-shared-save (PR3-handoff.md steps 1-3) from the PR-2 head
# jhan-vnnik-2-amx: apply the patch ref/S-diff-4d3a..ba69.patch with --3way (three conflicting files,
# four conflict blocks, each resolved by exact text with probe-pr3/resolve.py), make the step-2 edit
# (the two non-bf16 conversion statements of store_k_block use k_destination_row), apply the step-5
# pre-review fixes, then three commits (step 3). Deterministic. For UNPUBLISHED work only: it resets
# the branch, so it is never run after the first push (a repair after the push is a focused fourth
# commit on the published head). Re-run after any fix, from a clean worktree.
# usage: bash build-branch.sh   (BASE=<ref> overrides jhan-vnnik-2-amx)
set -euo pipefail
W=/home/jhan/workspace/ai-runs/tron-split-pr3; BASE=${BASE:-jhan-vnnik-2-amx}
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
PATCH=$HM/ref/S-diff-4d3a..ba69.patch
D=$(cd "$(dirname "$0")" && pwd)
G="git -C $W -c core.hooksPath=/dev/null -c rerere.enabled=false"
[ -z "$(git -C $W status --porcelain)" ] || { echo "worktree not clean"; exit 1; }
if git -C $W rev-parse --verify -q origin/jhan-vnnik-3-shared-save >/dev/null 2>&1; then
  echo "origin/jhan-vnnik-3-shared-save exists: the branch is published, and this script is for unpublished work only"; exit 1
fi
$G checkout -q -B jhan-vnnik-3-shared-save $BASE
echo "base: $($G rev-parse --short=10 HEAD) ($BASE)"
commit() { $G commit -q --no-verify -F $D/msgs/$1.txt; echo "$1 $($G rev-parse --short=10 HEAD)"; }
edit() {  # edit <file> <python literal old> <python literal new>: exact replacement, exactly one match
  python3 - "$W/$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old = sys.argv[2].encode().decode('unicode_escape'); new = sys.argv[3].encode().decode('unicode_escape')
s = p.read_text(); n = s.count(old)
if n != 1: print(f"FAIL {p}: {n} matches for {old[:70]!r}"); sys.exit(1)
p.write_text(s.replace(old, new))
PY
}
numstat() { $G diff --cached --numstat $BASE | awk '{a+=$1; r+=$2; n++} END {printf "files %d +%d/-%d", n, a, r}'; }
# Step 1: the patch. Expected: rc 1, 6 files applied cleanly, UU for exactly the three files below.
set +e; $G apply --3way "$PATCH"; rc=$?; set -e
[ "$rc" = 1 ] || { echo "git apply rc=$rc (expected 1: the three conflicting files)"; exit 1; }
uu=$($G status --porcelain | { grep '^UU ' || true; } | awk '{print $2}' | sort | tr '\n' ' ')
[ "$uu" = "h/tron/kernels/amx_attn_iface.hpp h/tron/models/model.hpp h/tron/tensor/k_vnni.hpp " ] || { echo "unexpected conflict set: [$uu]"; $G status --porcelain; exit 1; }
# The four blocks, by exact text (fails when a block is not found exactly once).
python3 "$HM/probe-pr3/resolve.py" "$W"
for f in h/tron/kernels/amx_attn_iface.hpp h/tron/models/model.hpp h/tron/tensor/k_vnni.hpp; do
  [ "$(grep -c -E '^(<<<<<<<|=======|>>>>>>>)' "$W/$f")" = 0 ] || { echo "conflict markers left in $f"; exit 1; }
done
$G add h/tron/kernels/amx_attn_iface.hpp h/tron/models/model.hpp h/tron/tensor/k_vnni.hpp
[ "$(numstat)" = "files 9 +682/-78" ] || { echo "numstat after step 1: $(numstat) (expected files 9 +682/-78)"; exit 1; }
# Step 2: the two-line edit (PR3-handoff.md section 3, deviation 2): the same view through k_destination_row.
edit h/tron/models/model.hpp \
  '                  view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,\n                      seq<geometry.kv.head_size>>{conv[0]}\n                      .set(kout);\n' \
  '                  k_destination_row<geometry.kv.head_size>(conv[0]).set(kout);\n'
edit h/tron/models/model.hpp \
  '                  view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE,\n                      seq<geometry.kv.head_size>>{conv[i]}\n                      .set(kout);\n' \
  '                  k_destination_row<geometry.kv.head_size>(conv[i]).set(kout);\n'
$G add h/tron/models/model.hpp
[ "$(numstat)" = "files 9 +678/-78" ] || { echo "numstat after step 2: $(numstat) (expected files 9 +678/-78)"; exit 1; }
# Step 5: the pre-review fixes (PR3-handoff.md step 5.3; the kept findings of workflow wf_4ecf815b-c31, recorded in
# split-status.md "PR-3 Step 5"). editf replaces the exact text of edits/<name>.old by edits/<name>.new, exactly one match.
editf() {
  python3 - "$W/$1" "$D/edits/$2.old" "$D/edits/$2.new" <<'PY2'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old = pathlib.Path(sys.argv[2]).read_text(); new = pathlib.Path(sys.argv[3]).read_text()
s = p.read_text(); n = s.count(old)
if n != 1: print(f"FAIL {p}: {n} matches for {sys.argv[2]}"); sys.exit(1)
p.write_text(s.replace(old, new))
PY2
}
# (1) tron-1, wade-1, items-1, items-2: store_block checks its block index, as store_row checks its token index.
editf h/tron/tensor/k_vnni.hpp store-block-assert
# (2) positron-1, plain-8: Note [Shared block save] names the store path the 0.86 ms measurement describes, the test server and the model.
editf h/tron/models/model.hpp note-opening
# (3) wade-9: a comment on k_store_block.
editf h/tron/models/model.hpp k-store-block-comment
# (4) concurrency-3: the worker_ix assert message formats n_workers, not n_workers - 1.
editf h/tron/models/model.hpp worker-assert
# (5) plain-5: no semicolon in the join-watchdog message.
editf h/tron/models/model.hpp watchdog-message
# (6) plain-1, wade-4, positron-2: the save_k overload comment names run() and run_main_help.
editf h/tron/models/model.hpp overload-comment
# (7) plain-9: the helper-side Haskell comment in short sentences; wade-10, tron-3: Var for worker_ix and n_workers, as kernelCall.
editf ingest/src/TronCpp.hs hs-helper-comment
edit ingest/src/TronCpp.hs '[Var $ asCpp $ attentionKey kvWrite, ExprLit "worker_ix", ExprLit "n_workers"]' '[Var $ asCpp $ attentionKey kvWrite, Var "worker_ix", Var "n_workers"]'
edit ingest/src/TronCpp.hs '[Var $ asCpp $ attentionKey kvWrite, LiteralExpr (IntLit 0), ExprLit "n_workers"]' '[Var $ asCpp $ attentionKey kvWrite, LiteralExpr (IntLit 0), Var "n_workers"]'
# (8) wade-2: the section of the block-save case that repeats the (block 2, full mask) row of the loop above goes.
editf t/t_k_vnni_layout.cpp layout-section-delete
# (9) tests-1, tests-2, tests-4, concurrency-1, plain-6, wade-5, tron-2, plain-2: the three-thread section of the save_k case
#     (exact claim count, each helper's window count, the cut-only-at-a-change check, a second window, the section name).
edit t/t_llama_unit.cpp '  const kv_slot_id slot = operation.binding.kv_slot;\n' '  // Not const: the three-thread section moves it to the next operation'"'"'s slot.\n  // snapshot and check below read it by reference.\n  kv_slot_id slot = operation.binding.kv_slot;\n'
editf t/t_llama_unit.cpp three-thread-section
# Step 3: three commits, whole files per commit.
$G reset -q
$G add h/tron/tensor/k_vnni.hpp h/tron/models/kv_cache.hpp t/t_k_vnni_layout.cpp
commit a
$G add h/tron/models/model.hpp h/tron/models/common.hpp h/tron/kernels/amx_attn_iface.hpp t/t_llama_unit.cpp
commit b
$G add ingest/src/TronCpp.hs ingest/test/LoopyTronSpec.hs
commit c
echo "branch: $($G branch --show-current); status lines: $($G status --porcelain | wc -l)"
$G log --oneline $BASE..HEAD
echo "$($G diff --numstat $BASE HEAD | awk '{a+=$1; r+=$2; n++} END {printf "files %d +%d/-%d", n, a, r}') against $BASE"
