#!/bin/bash
# Rebuild the PR-4 branch jhan-vnnik-4-tail-block (PR4-handoff.md steps 1-3) from the PR-3 head
# jhan-vnnik-3-shared-save: apply the T patch ref/T-4737-merge.diff with --3way (five conflicting
# files, five conflict blocks, each resolved by exact text with probe-pr4/resolve.py, which also adds
# the patch's block checks after PR-3's two shared saves), apply the B patch ref/B-preset.diff, make
# the step-2 edit (#include <cstring> kept in h/tron/kernels/k_vnni.hpp), apply the step-5 pre-review
# fixes, then three commits (step 3). Deterministic. For UNPUBLISHED work only: it resets the branch,
# so it is never run on the branch after the first push (a repair after the push is a focused commit
# on the published head). Re-run after any fix, from a clean worktree.
# Mode d (`bash build-branch.sh d`, PR4-handoff.md step 7.1): no reset. It applies the chain's
# exec/results/pr4-20261012/bench-update.diff (the cost rows, written on delphi-3bda over NFS) on the
# three-commit head and commits it with msgs/d.txt. Guarded the same way (refuses once the branch is
# on origin).
# usage: bash build-branch.sh [d]   (BASE=<ref> overrides jhan-vnnik-3-shared-save)
set -euo pipefail
W=/home/jhan/workspace/ai-runs/tron-split-pr4; BASE=${BASE:-jhan-vnnik-3-shared-save}
HM=/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/handoff-material
T_PATCH=$HM/ref/T-4737-merge.diff
B_PATCH=$HM/ref/B-preset.diff
RESD=/home/jhan/workspace/intel-AMX/exec/results/pr4-20261012
D=$(cd "$(dirname "$0")" && pwd)
G="git -C $W -c core.hooksPath=/dev/null -c rerere.enabled=false"
MODE=${1:-build}
[ -z "$(git -C $W status --porcelain)" ] || { echo "worktree not clean"; exit 1; }
if git -C $W rev-parse --verify -q origin/jhan-vnnik-4-tail-block >/dev/null 2>&1; then
  echo "origin/jhan-vnnik-4-tail-block exists: the branch is published, and this script is for unpublished work only"; exit 1
fi
commit() { $G commit -q --no-verify -F $D/msgs/$1.txt; echo "$1 $($G rev-parse --short=10 HEAD)"; }
if [ "$MODE" = d ]; then
  [ "$($G branch --show-current)" = jhan-vnnik-4-tail-block ] || { echo "not on jhan-vnnik-4-tail-block"; exit 1; }
  [ "$($G rev-list --count $BASE..HEAD)" = 3 ] || { echo "HEAD is not three commits on $BASE ($($G rev-list --count $BASE..HEAD))"; exit 1; }
  [ -s "$RESD/bench-update.diff" ] || { echo "$RESD/bench-update.diff missing or empty"; exit 1; }
  $G apply "$RESD/bench-update.diff"
  st=$($G diff --stat | tail -1 | sed 's/^ *//')
  [ "$st" = "1 file changed, 4 insertions(+), 4 deletions(-)" ] || { echo "unexpected diff stat: $st"; $G diff --stat; exit 1; }
  [ "$($G diff --name-only)" = config/test-benchmarks.json ] || { echo "unexpected file set: $($G diff --name-only | tr '\n' ' ')"; exit 1; }
  $G add config/test-benchmarks.json
  commit d
  echo "branch: $($G branch --show-current); status lines: $($G status --porcelain | wc -l)"
  $G log --oneline $BASE..HEAD
  exit 0
fi
[ "$MODE" = build ] || { echo "usage: bash build-branch.sh [d]"; exit 64; }
$G checkout -q -B jhan-vnnik-4-tail-block $BASE
echo "base: $($G rev-parse --short=10 HEAD) ($BASE)"
edit() {  # edit <file> <python literal old> <python literal new>: exact replacement, exactly one match
  python3 - "$W/$1" "$2" "$3" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old = sys.argv[2].encode().decode('unicode_escape'); new = sys.argv[3].encode().decode('unicode_escape')
s = p.read_text(); n = s.count(old)
if n != 1: print(f"FAIL {p}: {n} matches for {old[:70]!r}"); sys.exit(1)
p.write_text(s.replace(old, new))
PY
}
editf() {  # editf <file> <name>: replace the exact text of edits/<name>.old by edits/<name>.new, exactly one match
  python3 - "$W/$1" "$D/edits/$2.old" "$D/edits/$2.new" <<'PY2'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); old = pathlib.Path(sys.argv[2]).read_text(); new = pathlib.Path(sys.argv[3]).read_text()
s = p.read_text(); n = s.count(old)
if n != 1: print(f"FAIL {p}: {n} matches for {sys.argv[2]}"); sys.exit(1)
p.write_text(s.replace(old, new))
PY2
}
numstat() { $G diff --cached --numstat $BASE | awk '{a+=$1; r+=$2; n++} END {printf "files %d +%d/-%d", n, a, r}'; }
FIVE="h/tron/kernels/amx_attn_iface.hpp h/tron/kernels/k_vnni.hpp h/tron/models/kv_cache.hpp h/tron/tensor/k_vnni.hpp t/t_llama_unit.cpp"
# Step 1.2: the T patch. Expected: rc 1, 5 files applied cleanly, UU for exactly the five files, 3 marker lines each.
set +e; $G apply --3way "$T_PATCH"; rc=$?; set -e
[ "$rc" = 1 ] || { echo "git apply rc=$rc (expected 1: the five conflicting files)"; exit 1; }
uu=$($G status --porcelain | { grep '^UU ' || true; } | awk '{print $2}' | sort | tr '\n' ' ')
[ "$uu" = "$FIVE " ] || { echo "unexpected conflict set: [$uu]"; $G status --porcelain; exit 1; }
for f in $FIVE; do
  [ "$(grep -c -E '^(<<<<<<<|=======|>>>>>>>)' "$W/$f")" = 3 ] || { echo "expected 3 conflict marker lines in $f, found $(grep -c -E '^(<<<<<<<|=======|>>>>>>>)' "$W/$f")"; exit 1; }
done
# Step 1.3: the five blocks by exact text, then the two test-file additions (fails when a block is not found exactly once).
python3 "$HM/probe-pr4/resolve.py" "$W"
for f in $FIVE; do
  [ "$(grep -c -E '^(<<<<<<<|=======|>>>>>>>)' "$W/$f")" = 0 ] || { echo "conflict markers left in $f"; exit 1; }
done
$G add $FIVE
[ "$(numstat)" = "files 10 +1469/-119" ] || { echo "numstat after the T patch: $(numstat) (expected files 10 +1469/-119)"; exit 1; }
# Step 1.4: the B patch (the deb preset line and the README paragraph). Expected: rc 0, both files staged, no UU.
$G apply --3way "$B_PATCH"
[ -z "$($G status --porcelain | { grep '^UU ' || true; })" ] || { echo "the B patch left a conflict"; exit 1; }
[ "$(numstat)" = "files 12 +1476/-121" ] || { echo "numstat after the B patch: $(numstat) (expected files 12 +1476/-121)"; exit 1; }
# Step 2: the one hand edit (PR4-handoff.md section 3, deviation 3): kernels/k_vnni.hpp keeps <cstring> (it calls std::memcpy).
edit h/tron/kernels/k_vnni.hpp \
  '#include <cstddef>\n#include <cstdint>\n#include <immintrin.h>\n' \
  '#include <cstddef>\n#include <cstdint>\n#include <cstring>\n#include <immintrin.h>\n'
$G add h/tron/kernels/k_vnni.hpp
[ "$(numstat)" = "files 12 +1476/-120" ] || { echo "numstat after step 2: $(numstat) (expected files 12 +1476/-120)"; exit 1; }
# Step 5: the pre-review fixes (PR4-handoff.md step 5.3). editf replaces the exact text of edits/<name>.old by
# edits/<name>.new, exactly one match. Each line below names the finding it answers (split-status.md "PR-4 Step 5").
# (1) positron-1, tron-1, wade-1, items-1 (must-fix): Note [K VNNI storage] item 4 described a v_head_fn branch that does
#     not exist in this tree (TRON_CHUNK_SIZE / page::v_ptr); and positron-7: "unchanged" has no reference point.
editf h/tron/models/kv_cache.hpp v-head-fn
# (2) positron-6: present tense for the VNNI column's cost.
editf h/tron/models/kv_cache.hpp vnni-column-tense
# (3) protocol-2 was refuted (the dependency latch is per page, so the Note's sentence is right): not applied.
# (4) protocol-1 (must-fix): k_storage_readable tests the page's own chunk of a sliding-window slot (slot_page), not the
#     slot's first chunk (slot_base), so k_forget_row converts a block back whenever the page's bytes are resident.
editf h/tron/models/kv_cache.hpp storage-readable
# (5) positron-2, tests-1, items-3, buildcfg-3, wade-3, tron-5: the K-instance comment says every later page, and the
#     constant is named for it.
editf t/t_llama_unit.cpp k-instance-comment
edit t/t_llama_unit.cpp '    constexpr size_t page_1_recorded_rows = 41;\n' '    constexpr size_t later_page_recorded_rows = 41;\n'
edit t/t_llama_unit.cpp '      const size_t recorded = pg == 0 ? page_t::page_size : page_1_recorded_rows;\n' '      const size_t recorded = pg == 0 ? page_t::page_size : later_page_recorded_rows;\n'
# (6) tests-3: the other-operation section's comment says what the section proves.
editf t/t_llama_unit.cpp hw-other-op-comment
# (7) positron-11, positron-12: two test comments of the page-state case say the rule and the writer exactly.
editf t/t_k_vnni_layout.cpp page-state-comment
editf t/t_k_vnni_layout.cpp store-row-wrote
# (8) tests-4, tron-4: the page-state case checks k_row_if_row_major (the FPGA staging's in-place read) on both layouts.
editf t/t_k_vnni_layout.cpp row-if-row-major-check
# (9) tests-5: the re-save into a converted block stores other values and reads them back (check_rows's skip is used).
editf t/t_k_vnni_layout.cpp resave-salt-a
editf t/t_k_vnni_layout.cpp resave-salt-b
# (10) tron-3: one row saved again after the final forget must not complete block 1 (the bits above the offset are gone).
editf t/t_k_vnni_layout.cpp forget-bits-above
# (11) cppguide-2, buildcfg-2: the kernels header include of the dispatch test is unused (tensor/k_vnni.hpp has the names).
editf t/t_amx_dispatch_dtype.cpp dead-include
# (12) buildcfg-4: the README's deb paragraph in one-claim sentences.
editf README.ci.md readme-deb-paragraph
# (13) plain-30: Note [Row-major tail block] no longer reads as if block_to_vnni() ran after a whole-block save.
editf h/tron/tensor/k_vnni.hpp tail-block-note-at-once
# Step 3: three commits, whole files per commit (a: the storage side and its tests; b: the reader side and its tests;
# c: the preset and the README).
$G reset -q
$G add h/tron/tensor/k_vnni.hpp h/tron/models/kv_cache.hpp h/tron/models/model.hpp t/t_k_vnni_layout.cpp
commit a
$G add h/tron/models/self_attention.hpp h/tron/kernels/amx_attn_iface.hpp h/tron/kernels/k_vnni.hpp h/tron/scheduler/full.hpp t/t_amx_dispatch_dtype.cpp t/t_llama_unit.cpp
commit b
$G add CMakePresets.json README.ci.md
commit c
echo "branch: $($G branch --show-current); status lines: $($G status --porcelain | wc -l)"
$G log --oneline $BASE..HEAD
echo "$($G diff --numstat $BASE HEAD | awk '{a+=$1; r+=$2; n++} END {printf "files %d +%d/-%d", n, a, r}') against $BASE"
