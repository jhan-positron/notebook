#!/usr/bin/env bash
# Build the TARGET .deb for the ci-mimic campaign (2026-09-18) on delphi-3bda.
#
# Target = PR #4424 (origin/jhan-amx-vnniK) merged into MAIN_SHA (the main commit the
# nightly's own .deb of 2026-09-18 is built from), plus a deb-preset commit that turns
# TRON_AMX_DISPATCH and TRON_K_VNNI on. Same "make deb" recipe as exec/results/
# ci-enable-20260917 (outside nix, uv 0.9.5 + ghcup on PATH, 48 jobs pinned to socket 1).
# Writes only under /var/tmp/jhan (our scratch area on the machine).
#
# usage: build-target.sh MAIN_SHA          (run on delphi-3bda; logs to stdout)
set -u
MAIN_SHA=${1:?MAIN_SHA}
REPO=/var/tmp/jhan/tron-ci-enable
WT=/var/tmp/jhan/tron-ci-mimic
OUT=/var/tmp/jhan/ci-mimic-20260918
PR_REF=origin/jhan-amx-vnniK
PRESET_COMMIT=6f37cd2ed9       # CMakePresets: deb preset + TRON_AMX_DISPATCH ON (local branch jhan-amx-deb-preset)
BRANCH=jhan-ci-mimic-target
SOCKET1=72-143,216-287
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo failed >"$OUT/build.status"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/build.status"
say "start MAIN_SHA=$MAIN_SHA"
git -C "$REPO" fetch -q origin || die "fetch"
git -C "$REPO" cat-file -e "$MAIN_SHA^{commit}" || die "MAIN_SHA $MAIN_SHA not in repo"
PR_SHA=$(git -C "$REPO" rev-parse "$PR_REF") || die "PR ref"
say "PR head $PR_SHA ($PR_REF)"
[ -e "$WT" ] && die "worktree $WT already exists; remove it by hand first"
git -C "$REPO" worktree add -q -b "$BRANCH" "$WT" "$PR_SHA" || die "worktree add (branch $BRANCH may exist: git -C $REPO branch -D $BRANCH)"
say "merging $MAIN_SHA into $BRANCH"
git -C "$WT" merge --no-edit -m "Merge main $MAIN_SHA into jhan-amx-vnniK for the ci-mimic target build" "$MAIN_SHA" \
  || { git -C "$WT" diff --name-only --diff-filter=U; die "merge conflict"; }
MERGE_SHA=$(git -C "$WT" rev-parse HEAD)
say "merge commit $MERGE_SHA"
# deb preset: both options ON. Cherry-pick the AMX one-liner, then add TRON_K_VNNI after it.
if git -C "$WT" cherry-pick --no-edit "$PRESET_COMMIT"; then say "cherry-picked $PRESET_COMMIT"; else
  git -C "$WT" cherry-pick --abort 2>/dev/null
  grep -q '"TRON_AMX_DISPATCH": "ON"' "$WT/CMakePresets.json" || \
    sed -i '0,/"ENABLE_FUSE_STATS": "ON"$/s//"ENABLE_FUSE_STATS": "ON",\n        "TRON_AMX_DISPATCH": "ON"/' "$WT/CMakePresets.json"
fi
grep -q '"TRON_K_VNNI": "ON"' "$WT/CMakePresets.json" || \
  sed -i 's/^\(\s*\)"TRON_AMX_DISPATCH": "ON"$/\1"TRON_AMX_DISPATCH": "ON",\n\1"TRON_K_VNNI": "ON"/' "$WT/CMakePresets.json"
python3 - "$WT/CMakePresets.json" <<'PY' || die "preset check"
import json,sys
p=json.load(open(sys.argv[1])); d=[c for c in p['configurePresets'] if c['name']=='deb'][0]['cacheVariables']
assert d.get('TRON_AMX_DISPATCH')=='ON' and d.get('TRON_K_VNNI')=='ON', d
print("deb preset cacheVariables:", json.dumps(d))
PY
if ! git -C "$WT" diff --quiet -- CMakePresets.json; then
  git -C "$WT" commit -q -am "CMakePresets: deb preset compiles the AMX kernels and the VNNI K layout (ci-mimic target build)" || die "commit preset"
fi
HEAD_SHA=$(git -C "$WT" rev-parse HEAD)
say "build head $HEAD_SHA"; git -C "$WT" log --oneline -4
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/make-deb.log)"
t0=$(date +%s)
( cd "$WT" && taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/make-deb.log" 2>&1 || { tail -40 "$OUT/make-deb.log"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
grep -n "TRON_AMX_DISPATCH\|TRON_K_VNNI" "$OUT/make-deb.log" | head -5
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/target.deb"; cp "$DEB" "$OUT/"
( cd "$WT" && taskset -c "$SOCKET1" make test-deb-package-contents ) >"$OUT/test-deb-package-contents.log" 2>&1 && say "test-deb-package-contents ok" || say "WARNING test-deb-package-contents rc=$? (see log)"
# package checks: the AMX kill-switch literal and AMX tile instructions must be present
dpkg-deb --fsys-tarfile "$OUT/target.deb" | tar -xO ./opt/positron/bin/rinzler >"$OUT/rinzler.target" || die "extract rinzler"
AMX_STR=$(strings "$OUT/rinzler.target" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$OUT/rinzler.target" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
VNNI_STR=$(strings "$OUT/rinzler.target" | grep -c -i 'vnni')
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN strings matching vnni=$VNNI_STR"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
python3 - "$OUT/manifest.json" "$MAIN_SHA" "$PR_SHA" "$MERGE_SHA" "$HEAD_SHA" "$(basename "$DEB")" "$(sha256sum "$OUT/target.deb" | cut -d' ' -f1)" "$AMX_STR" "$AMX_INSN" "$VNNI_STR" <<'PY'
import json,sys,datetime
p,main,pr,merge,head,deb,sha,a,b,c=sys.argv[1:11]
json.dump({"built":datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),"main_sha":main,"pr_sha":pr,"merge_sha":merge,"head_sha":head,
 "deb":deb,"deb_sha256":sha,"checks":{"TRON_AMX_DISABLE_literal":int(a),"amx_tile_insns":int(b),"vnni_strings":int(c)},
 "options":{"TRON_AMX_DISPATCH":"ON","TRON_K_VNNI":"ON"},"worktree":"/var/tmp/jhan/tron-ci-mimic","branch":"jhan-ci-mimic-target"},open(p,'w'),indent=1)
PY
cat "$OUT/manifest.json"; echo ok >"$OUT/build.status"; say "DONE $OUT/target.deb"
