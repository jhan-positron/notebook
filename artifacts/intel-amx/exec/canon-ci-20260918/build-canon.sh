#!/usr/bin/env bash
# Build the CANONICAL-AMX .deb for the canon-ci campaign (2026-09-18) on delphi-3bda.
#
# Canonical AMX = PR #3879 as merged into main (2026-09-15). This package is MAIN_SHA (the main commit
# the nightly's own .deb of 2026-09-18 and both arms of the ci-mimic campaign were built from) plus
# ONE cherry-picked commit: the deb preset line TRON_AMX_DISPATCH=ON (6f37cd2ed9, branch
# jhan-amx-deb-preset). No PR #4424 code. main has no TRON_K_VNNI option, so nothing to turn off.
# Same "make deb" recipe as exec/ci-mimic-20260918/build-target.sh (outside nix, uv 0.9.5 + ghcup on
# PATH, 48 jobs pinned to socket 1). Writes only under /var/tmp/jhan (our scratch area on the machine).
#
# usage: build-canon.sh MAIN_SHA          (run on delphi-3bda; logs to stdout)
set -u
MAIN_SHA=${1:?MAIN_SHA}
REPO=/var/tmp/jhan/tron-ci-enable
WT=/var/tmp/jhan/tron-ci-canon
OUT=/var/tmp/jhan/canon-ci-20260918
PRESET_COMMIT=6f37cd2ed9       # CMakePresets: deb preset + TRON_AMX_DISPATCH ON (branch jhan-amx-deb-preset)
PR3879_MERGE=3fd5edaa66        # the merge commit of PR #3879 into main (2026-09-15); must be an ancestor of MAIN_SHA
BRANCH=jhan-ci-canon
SOCKET1=72-143,216-287
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo failed >"$OUT/build.status"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/build.status"
say "start MAIN_SHA=$MAIN_SHA"
git -C "$REPO" fetch -q origin || die "fetch"
git -C "$REPO" cat-file -e "$MAIN_SHA^{commit}" || die "MAIN_SHA $MAIN_SHA not in repo"
git -C "$REPO" cat-file -e "$PRESET_COMMIT^{commit}" || die "preset commit $PRESET_COMMIT not in repo"
git -C "$REPO" merge-base --is-ancestor "$PR3879_MERGE" "$MAIN_SHA" || die "MAIN_SHA does not contain the PR #3879 merge $PR3879_MERGE"
say "MAIN_SHA contains the PR #3879 merge $PR3879_MERGE"
[ -e "$WT" ] && die "worktree $WT already exists; remove it by hand first"
git -C "$REPO" worktree add -q -b "$BRANCH" "$WT" "$MAIN_SHA" || die "worktree add (branch $BRANCH may exist: git -C $REPO branch -D $BRANCH)"
if git -C "$WT" cherry-pick --no-edit "$PRESET_COMMIT"; then say "cherry-picked $PRESET_COMMIT"; else
  git -C "$WT" cherry-pick --abort 2>/dev/null
  say "cherry-pick did not apply; inserting the preset line by sed"
  grep -q '"TRON_AMX_DISPATCH": "ON"' "$WT/CMakePresets.json" || \
    sed -i '0,/"ENABLE_FUSE_STATS": "ON"$/s//"ENABLE_FUSE_STATS": "ON",\n        "TRON_AMX_DISPATCH": "ON"/' "$WT/CMakePresets.json"
  git -C "$WT" diff --quiet -- CMakePresets.json && die "preset line not inserted"
  git -C "$WT" commit -q -am "CMakePresets: compile the AMX attention kernels into the .deb package (canon-ci build)" || die "commit preset"
fi
python3 - "$WT/CMakePresets.json" <<'PY' || die "preset check"
import json,sys
p=json.load(open(sys.argv[1])); d=[c for c in p['configurePresets'] if c['name']=='deb'][0]['cacheVariables']
assert d.get('TRON_AMX_DISPATCH')=='ON', d
assert 'TRON_K_VNNI' not in d, d
print("deb preset cacheVariables:", json.dumps(d))
PY
grep -q "TRON_K_VNNI" "$WT/CMakeLists.txt" && die "CMakeLists.txt mentions TRON_K_VNNI: this is not plain main"
# exactly one commit on top of MAIN_SHA, touching only CMakePresets.json
N_COMMITS=$(git -C "$WT" rev-list --count "$MAIN_SHA..HEAD"); [ "$N_COMMITS" = 1 ] || die "expected 1 commit on top of MAIN_SHA, found $N_COMMITS"
CHANGED=$(git -C "$WT" diff --name-only "$MAIN_SHA" HEAD | tr '\n' ' '); [ "$CHANGED" = "CMakePresets.json " ] || die "files changed vs MAIN_SHA: $CHANGED"
HEAD_SHA=$(git -C "$WT" rev-parse HEAD)
say "build head $HEAD_SHA (main $MAIN_SHA + preset)"; git -C "$WT" log --oneline -3
git -C "$WT" diff "$MAIN_SHA" HEAD
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/make-deb.log)"
t0=$(date +%s)
( cd "$WT" && taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/make-deb.log" 2>&1 || { tail -40 "$OUT/make-deb.log"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
grep -n "TRON_AMX_DISPATCH\|TRON_K_VNNI\|amx_attn.cpp.o" "$OUT/make-deb.log" | head -5
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/target.deb"; cp "$DEB" "$OUT/"
( cd "$WT" && taskset -c "$SOCKET1" make test-deb-package-contents ) >"$OUT/test-deb-package-contents.log" 2>&1 && say "test-deb-package-contents ok" || say "WARNING test-deb-package-contents rc=$? (see log)"
# package checks: the AMX kill-switch literal and AMX tile instructions must be present
dpkg-deb --fsys-tarfile "$OUT/target.deb" | tar -xO ./opt/positron/bin/rinzler >"$OUT/rinzler.target" || die "extract rinzler"
AMX_STR=$(strings "$OUT/rinzler.target" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$OUT/rinzler.target" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
VNNI_STR=$(strings "$OUT/rinzler.target" | grep -c -i 'vnni')
KVNNI_STR=$(strings "$OUT/rinzler.target" | grep -c -x TRON_K_VNNI)
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN strings matching vnni=$VNNI_STR TRON_K_VNNI literal=$KVNNI_STR (must be 0)"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
[ "$KVNNI_STR" -eq 0 ] || die "TRON_K_VNNI literal present: not a canonical build"
python3 - "$OUT/manifest.json" "$MAIN_SHA" "$PRESET_COMMIT" "$HEAD_SHA" "$(basename "$DEB")" "$(sha256sum "$OUT/target.deb" | cut -d' ' -f1)" "$AMX_STR" "$AMX_INSN" "$VNNI_STR" "$KVNNI_STR" "$PR3879_MERGE" <<'PY'
import json,sys,datetime
p,main,preset,head,deb,sha,a,b,c,k,pr=sys.argv[1:12]
json.dump({"built":datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),"main_sha":main,"preset_commit":preset,"head_sha":head,
 "contains_pr3879_merge":pr,"pr4424_included":False,
 "deb":deb,"deb_sha256":sha,"checks":{"TRON_AMX_DISABLE_literal":int(a),"amx_tile_insns":int(b),"vnni_strings":int(c),"TRON_K_VNNI_literal":int(k)},
 "options":{"TRON_AMX_DISPATCH":"ON"},"worktree":"/var/tmp/jhan/tron-ci-canon","branch":"jhan-ci-canon"},open(p,'w'),indent=1)
PY
cat "$OUT/manifest.json"; echo ok >"$OUT/build.status"; say "DONE $OUT/target.deb"
