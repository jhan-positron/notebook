#!/usr/bin/env bash
# i4500fix-20260928: build the FIX .deb on delphi-3bda (runs ON delphi-3bda).
# The package = the ci-mimic target of 2026-09-18 (main 3faba6d0fd + PR #4424 head 30c4ac82cb + the deb preset with
# TRON_AMX_DISPATCH and TRON_K_VNNI on, commit 29a8a54740) plus the issue #4500 fix commit, cherry-picked on claude-box
# as 96a39b8278 (branch jhan-amx-vnniK-i4500 = 78e2da7511 on the PR head). Same "make deb" recipe as
# exec/ci-mimic-20260918/build-target.sh (outside nix, uv 0.9.5 + ghcup on PATH, 48 jobs pinned to socket 1).
# Also extracts the canonical-AMX deb of exec/canon-ci-20260918 (the base binary) when its root/ is missing.
# Writes only under /var/tmp/jhan. usage: build-deb.sh   (logs to stdout; marker $OUT/build.status = running|ok|failed)
set -u
COMMIT=${COMMIT:-8198eab4cc}
REPO=/home/jhan/workspace/tron          # the repo that owns the /var/tmp/jhan worktrees (NFS); the commit lives there
WT=/var/tmp/jhan/tron-i4500deb
OUT=/var/tmp/jhan/i4500fix-20260928
CANON=/var/tmp/jhan/canon-ci-20260918
SOCKET1=72-143,216-287
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo failed >"$OUT/build.status"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/build.status"
say "start COMMIT=$COMMIT"
git -C "$REPO" cat-file -e "$COMMIT^{commit}" || die "commit $COMMIT not in $REPO"
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$COMMIT" || die "worktree add"
else
  git -C "$WT" checkout -q --detach "$COMMIT" || die "checkout"
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$REPO" rev-parse "$COMMIT^{commit}")" ] || die "HEAD is not $COMMIT"
say "worktree $WT at $(git -C "$WT" rev-parse HEAD)"; git -C "$WT" log --oneline -4
python3 - "$WT/CMakePresets.json" <<'PY' || die "preset check"
import json,sys
p=json.load(open(sys.argv[1])); d=[c for c in p['configurePresets'] if c['name']=='deb'][0]['cacheVariables']
assert d.get('TRON_AMX_DISPATCH')=='ON' and d.get('TRON_K_VNNI')=='ON', d
print("deb preset cacheVariables:", json.dumps(d))
PY
grep -q "Row-major tail block" "$WT/h/tron/kernels/k_vnni.hpp" || die "the fix is not in the worktree (NFS attribute cache?)"
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/make-deb.log)"
t0=$(date +%s)
( cd "$WT" && taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/make-deb.log" 2>&1 || { tail -40 "$OUT/make-deb.log"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/fix.deb"; cp "$DEB" "$OUT/"
( cd "$WT" && taskset -c "$SOCKET1" make test-deb-package-contents ) >"$OUT/test-deb-package-contents.log" 2>&1 && say "test-deb-package-contents ok" || say "WARNING test-deb-package-contents rc=$? (see log)"
rm -rf "$OUT/root"; mkdir -p "$OUT/root"; dpkg-deb -x "$OUT/fix.deb" "$OUT/root" || die "dpkg-deb -x"
RZ=$OUT/root/opt/positron/bin/rinzler; [ -x "$RZ" ] || die "no rinzler in the package"
AMX_STR=$(strings "$RZ" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$RZ" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
VNNI_STR=$(strings "$RZ" | grep -c -i 'vnni')
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN strings matching vnni=$VNNI_STR"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
if [ ! -x "$CANON/root/opt/positron/bin/rinzler" ]; then
  [ -s "$CANON/target.deb" ] || die "canon deb missing"
  mkdir -p "$CANON/root"; dpkg-deb -x "$CANON/target.deb" "$CANON/root" || die "dpkg-deb -x canon"
  say "canon deb extracted to $CANON/root"
fi
python3 - "$OUT/manifest.json" "$COMMIT" "$(git -C "$WT" rev-parse HEAD)" "$(basename "$DEB")" "$(sha256sum "$OUT/fix.deb" | cut -d' ' -f1)" "$(sha256sum "$RZ" | cut -d' ' -f1)" "$AMX_STR" "$AMX_INSN" "$VNNI_STR" <<'PY'
import json,sys,datetime
p,commit,head,deb,sha,rz,a,b,c=sys.argv[1:10]
json.dump({"built":datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),"commit":commit,"head_sha":head,
 "base":"ci-mimic target 29a8a54740 = main 3faba6d0fd + PR 4424 30c4ac82cb + deb preset AMX+VNNI","fix_commit_on_pr_head":"78e2da7511",
 "deb":deb,"deb_sha256":sha,"rinzler_sha256":rz,"checks":{"TRON_AMX_DISABLE_literal":int(a),"amx_tile_insns":int(b),"vnni_strings":int(c)},
 "options":{"TRON_AMX_DISPATCH":"ON","TRON_K_VNNI":"ON"},"worktree":"/var/tmp/jhan/tron-i4500deb"},open(p,'w'),indent=1)
PY
cat "$OUT/manifest.json"; echo ok >"$OUT/build.status"; say "DONE $OUT/fix.deb"
