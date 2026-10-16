#!/usr/bin/env bash
# Build the TARGET .deb of the pr4424ci campaign (2026-10-09) on delphi-3bda.
#
# Target = PR #4424 (VNNI K) at COMMIT (the PR head after main was merged in; it is also pushed to origin) plus ONE
# local commit that adds "TRON_K_VNNI": "ON" after "TRON_AMX_DISPATCH": "ON" in the "deb" configure preset of
# CMakePresets.json (the PR's own preset carries only the AMX switch; the deb preset of main compiles the AMX kernels
# since PR #4505). That commit lives in the build worktree only and is never pushed.
# Same "make deb" recipe as exec/i4500b-20260930/build-deb.sh and exec/ci-mimic-20260918/build-target.sh: outside nix,
# uv 0.9.5 + ghcup on PATH, 48 jobs pinned to socket 1 (cpus 72-143,216-287 = our half of the machine; Bill's half is
# socket 0). Package checks: the TRON_AMX_DISABLE literal, AMX tile instructions, vnni strings.
# Writes only under /var/tmp/jhan: the worktree $WT and the output directory $OUT (target.deb, rinzler.target,
# manifest.json, build.status = running|ok|failed, make-deb.log).
#
# The worktree is created detached at COMMIT; the preset commit is made on a LOCAL branch named jhan-pr4424ci-target
# so that bin/get-version.sh appends the branch name to the deb version (2026.10.08-<sha>-jhan-pr4424ci-target): the
# campaign's preflight refuses to restore a version containing "jhan", and the "installed" lines of the logs then show
# at a glance which arm is in place. (A detached HEAD gives a nightly-looking version such as 2026.09.30-2fd11e32.)
#
# usage: ssh delphi-3bda bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/build-target.sh COMMIT
#        (or COMMIT=<sha> bash build-target.sh; logs to stdout; about 30-40 min)
set -u
COMMIT=${1:-${COMMIT:-}}; [ -n "$COMMIT" ] || { echo "usage: build-target.sh COMMIT"; exit 2; }
REPO=/home/jhan/workspace/tron          # the NFS repo that owns the /var/tmp/jhan worktrees; COMMIT must be in it (fetch fallback below)
WT=/var/tmp/jhan/tron-pr4424ci
OUT=/var/tmp/jhan/pr4424ci-20261009
BRANCH=jhan-pr4424ci-target
SOCKET1=72-143,216-287
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo failed >"$OUT/build.status"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/build.status"
say "start COMMIT=$COMMIT"
if ! git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null; then
  say "commit $COMMIT not in $REPO; fetching origin"
  git -C "$REPO" fetch -q origin || die "git fetch origin"
  git -C "$REPO" cat-file -e "$COMMIT^{commit}" 2>/dev/null || die "commit $COMMIT not in $REPO after the fetch"
fi
FULL=$(git -C "$REPO" rev-parse "$COMMIT^{commit}") || die "rev-parse $COMMIT"
if [ ! -e "$WT/.git" ]; then
  git -C "$REPO" worktree add --detach "$WT" "$FULL" || die "worktree add"
else
  git -C "$WT" checkout -q --detach "$FULL" || die "checkout --detach $FULL in the existing worktree"
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$FULL" ] || die "HEAD is not $FULL"
# a local branch for the version marker (see the header); -B resets a leftover branch of an earlier build
git -C "$WT" checkout -q -B "$BRANCH" || die "checkout -B $BRANCH (is it checked out in another worktree? git -C $REPO worktree list)"
say "worktree $WT at $(git -C "$WT" rev-parse HEAD) on branch $(git -C "$WT" branch --show-current)"; git -C "$WT" log --oneline -4
# the merged issue #4500 fix must be in the tree (NFS attribute-cache trap: a stale read would build the wrong tree)
grep -q "Row-major blocks under hardware attention" "$WT/h/tron/models/kv_cache.hpp" || die "'Row-major blocks under hardware attention' not in $WT/h/tron/models/kv_cache.hpp (the merged fix is missing, or the NFS attribute cache is stale)"
# deb preset: add TRON_K_VNNI after TRON_AMX_DISPATCH inside the "deb" configure preset only (one-line text edit, no JSON rewrite)
python3 - "$WT/CMakePresets.json" <<'PY' || die "preset edit"
import re, sys
path = sys.argv[1]
text = open(path).read()
if '"TRON_K_VNNI": "ON"' in text:
    print("TRON_K_VNNI already ON somewhere in CMakePresets.json; no edit")
    sys.exit(0)
m = re.search(r'"name":\s*"deb"', text)
assert m, 'no "deb" preset'
rest = text[m.end():]
# the next "configurePresets" entry starts with another "name": stay inside the deb preset
end = re.search(r'"name":\s*"', rest)
block = rest[:end.start()] if end else rest
lm = re.search(r'^(\s*)"TRON_AMX_DISPATCH": "ON"(,?)\s*$', block, re.M)
assert lm, 'the deb preset has no "TRON_AMX_DISPATCH": "ON" line'
indent, comma = lm.group(1), lm.group(2)
if comma:
    new_line = f'{indent}"TRON_AMX_DISPATCH": "ON",\n{indent}"TRON_K_VNNI": "ON",'
else:
    new_line = f'{indent}"TRON_AMX_DISPATCH": "ON",\n{indent}"TRON_K_VNNI": "ON"'
block2 = block[:lm.start()] + new_line + block[lm.end():]
open(path, "w").write(text[:m.end()] + block2 + rest[len(block):])
print("inserted TRON_K_VNNI after TRON_AMX_DISPATCH in the deb preset")
PY
python3 - "$WT/CMakePresets.json" <<'PY' || die "preset check"
import json,sys
p=json.load(open(sys.argv[1])); d=[c for c in p['configurePresets'] if c['name']=='deb'][0]['cacheVariables']
assert d.get('TRON_AMX_DISPATCH')=='ON' and d.get('TRON_K_VNNI')=='ON', d
print("deb preset cacheVariables:", json.dumps(d))
PY
if ! git -C "$WT" diff --quiet -- CMakePresets.json; then
  git -C "$WT" diff -- CMakePresets.json
  git -C "$WT" commit -q -am "CMakePresets: deb preset compiles the VNNI K layout (pr4424ci target build, local only)" || die "commit preset"
fi
HEAD_SHA=$(git -C "$WT" rev-parse HEAD)
say "build head $HEAD_SHA"; git -C "$WT" log --oneline -3
[ "$(git -C "$WT" status --porcelain | grep -vc '^??' )" = 0 ] || { git -C "$WT" status --short | head; die "worktree not clean (the deb version would carry -dirty)"; }
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/make-deb.log)"
t0=$(date +%s)
( cd "$WT" && taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/make-deb.log" 2>&1 || { tail -40 "$OUT/make-deb.log"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
grep -n "TRON_AMX_DISPATCH\|TRON_K_VNNI" "$OUT/make-deb.log" | head -5
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/target.deb"; cp "$DEB" "$OUT/"
( cd "$WT" && taskset -c "$SOCKET1" make test-deb-package-contents ) >"$OUT/test-deb-package-contents.log" 2>&1 && say "test-deb-package-contents ok" || say "WARNING test-deb-package-contents rc=$? (see log)"
# package checks: the AMX kill-switch literal and AMX tile instructions must be present; vnni strings are reported
dpkg-deb --fsys-tarfile "$OUT/target.deb" | tar -xO ./opt/positron/bin/rinzler >"$OUT/rinzler.target" || die "extract rinzler"
AMX_STR=$(strings "$OUT/rinzler.target" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$OUT/rinzler.target" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
VNNI_STR=$(strings "$OUT/rinzler.target" | grep -c -i 'vnni')
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN strings matching vnni=$VNNI_STR"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
python3 - "$OUT/manifest.json" "$COMMIT" "$FULL" "$HEAD_SHA" "$(basename "$DEB")" "$(sha256sum "$OUT/target.deb" | cut -d' ' -f1)" "$(sha256sum "$OUT/rinzler.target" | cut -d' ' -f1)" "$AMX_STR" "$AMX_INSN" "$VNNI_STR" "$WT" "$BRANCH" <<'PY'
import json,sys,datetime
p,commit,full,head,deb,sha,rz,a,b,c,wt,br=sys.argv[1:13]
json.dump({"built":datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),"commit":commit,"commit_sha":full,"head_sha":head,
 "deb":deb,"deb_sha256":sha,"rinzler_sha256":rz,"checks":{"TRON_AMX_DISABLE_literal":int(a),"amx_tile_insns":int(b),"vnni_strings":int(c)},
 "options":{"TRON_AMX_DISPATCH":"ON","TRON_K_VNNI":"ON"},"worktree":wt,"branch":br,
 "note":"PR 4424 at commit + one local preset commit (TRON_K_VNNI ON in the deb preset); never pushed"},open(p,'w'),indent=1)
PY
cat "$OUT/manifest.json"; echo ok >"$OUT/build.status"; say "DONE $OUT/target.deb"
