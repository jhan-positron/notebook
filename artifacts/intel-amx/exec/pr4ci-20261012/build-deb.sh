#!/usr/bin/env bash
# Build ONE of the two .deb packages of campaign W (exec/pr4ci-20261012) on delphi-3bda: ARM=base from main (72308ec90c)
# or ARM=target from PR-4's head. Forked 2026-10-12 from exec/pr4424ci-20261009/build-target.sh (one arm, with a preset
# edit); the chain exec/pr4-20261012/chain2.sh calls it twice (step deb), serially, on our half, after wait_slot.
#
# Both arms are built the same way. A worktree /var/tmp/jhan/tron-pr4ci-$ARM is created detached at the commit and then
# put on the LOCAL branch jhan-pr4ci-$ARM (never pushed), so that bin/get-version.sh appends the branch name to the deb
# version (2026.10.<build day>-<8 chars>-jhan-pr4ci-$ARM; the date part is the build day). The campaign's preflight
# refuses to restore a version that contains "jhan", and the "installed" lines of the logs show which arm is in place.
# (A detached HEAD gives a nightly-looking version such as 2026.09.30-2fd11e32: refused below.)
# No preset edit for either arm (the 2026-10-09 script added "TRON_K_VNNI": "ON" to the deb preset of CMakePresets.json):
# PR-4's own CMakePresets.json carries it in the deb preset, and main's must not gain it. The preset is CHECKED instead:
# TRON_AMX_DISPATCH ON for both arms (main's deb preset compiles the AMX kernels since PR #4505); TRON_K_VNNI absent
# for the base and ON for the target. The grep for the Note "Row-major blocks under hardware attention" in kv_cache.hpp
# runs for the target only (main has 0 occurrences). The worktree must be clean before the build (a dirty tree gives a
# "-dirty" version). No local commit is made: the build head must equal the commit.
# Same "make deb" recipe as before: outside nix, uv 0.9.5 + ghcup on PATH, 48 jobs pinned to socket 1 (cpus
# 72-143,216-287 = our half of the machine; Bill's half is socket 0). Package checks: the TRON_AMX_DISABLE literal,
# AMX tile instructions, vnni strings (reported). Not while the nightly's perf phase runs, not next to another build.
# Writes only under /var/tmp/jhan: the worktree $WT and the output directory $OUT. Outputs per arm, under $OUT:
#   base:   base.deb (plus a copy nightly.deb: the file name campaign W's dut.sh expects for the base arm), rinzler.base,
#           manifest-base.json, build-base.status = running|ok|failed, make-deb-base.log, test-deb-package-contents-base.log
#   target: target.deb, rinzler.target, manifest.json, build.status = running|ok|failed, make-deb.log,
#           test-deb-package-contents.log
# plus, for both, the deb under its original tron_<version>_amd64.deb name. The manifest carries "arm", "version" (the
# Version field, `dpkg-deb -f <deb> Version`), the deb and rinzler sha256 values and the options per arm: campaign W's
# EXPECTED_BASE and EXPECTED_BASE_SHA are the base manifest's "version" and "rinzler_sha256".
#
# usage (the chain's step deb, and by hand):
#   ARM=base   bash ~/workspace/intel-AMX/exec/pr4ci-20261012/build-deb.sh <MAIN_COMMIT>
#   ARM=target bash ~/workspace/intel-AMX/exec/pr4ci-20261012/build-deb.sh <COMMIT>
#   (COMMIT=<sha> in the environment also works; logs to stdout; 16 min 38 s measured 2026-10-08, up to 40 min)
set -u
ARM=${ARM:-}
case $ARM in base|target) ;; *) echo "usage: ARM=base|target bash build-deb.sh COMMIT (ARM is '${ARM:-unset}', want base or target)"; exit 2;; esac
COMMIT=${1:-${COMMIT:-}}; [ -n "$COMMIT" ] || { echo "usage: ARM=base|target bash build-deb.sh COMMIT"; exit 2; }
REPO=/home/jhan/workspace/tron          # the NFS repo that owns the /var/tmp/jhan worktrees; COMMIT must be in it (fetch fallback below)
WT=/var/tmp/jhan/tron-pr4ci-$ARM
OUT=/var/tmp/jhan/pr4ci-20261012
BRANCH=jhan-pr4ci-$ARM
SOCKET1=72-143,216-287
case $ARM in
  base)   DEB_OUT=base.deb;   RZ_OUT=rinzler.base;   MANIFEST=manifest-base.json; STATUS=build-base.status; MAKELOG=make-deb-base.log; PKGLOG=test-deb-package-contents-base.log; WANT_VNNI=absent;;
  target) DEB_OUT=target.deb; RZ_OUT=rinzler.target; MANIFEST=manifest.json;      STATUS=build.status;      MAKELOG=make-deb.log;      PKGLOG=test-deb-package-contents.log;      WANT_VNNI=ON;;
esac
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo failed >"$OUT/$STATUS"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/$STATUS"
say "start ARM=$ARM COMMIT=$COMMIT worktree=$WT branch=$BRANCH outputs=$OUT/{$DEB_OUT,$RZ_OUT,$MANIFEST,$STATUS,$MAKELOG}"
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
# the target must carry PR-4's Note in kv_cache.hpp (NFS attribute-cache trap: a stale read would build the wrong tree); main has 0 occurrences
if [ "$ARM" = target ]; then
  grep -q "Row-major blocks under hardware attention" "$WT/h/tron/models/kv_cache.hpp" || die "'Row-major blocks under hardware attention' not in $WT/h/tron/models/kv_cache.hpp (PR-4's change is missing, or the NFS attribute cache is stale)"
else
  say "base arm: the kv_cache.hpp Note check is skipped (main has 0 occurrences)"
fi
# deb preset CHECK (no edit): TRON_AMX_DISPATCH ON for both arms; TRON_K_VNNI absent for the base, ON for the target
python3 - "$WT/CMakePresets.json" "$WANT_VNNI" <<'PY' || die "preset check (ARM=$ARM wants TRON_K_VNNI $WANT_VNNI in the deb preset)"
import json,sys
p=json.load(open(sys.argv[1])); want=sys.argv[2]
d=[c for c in p['configurePresets'] if c['name']=='deb'][0].get('cacheVariables',{})
print("deb preset cacheVariables:", json.dumps(d))
assert d.get('TRON_AMX_DISPATCH')=='ON', f"TRON_AMX_DISPATCH is {d.get('TRON_AMX_DISPATCH')!r} in the deb preset, want ON"
if want=='absent':
    assert 'TRON_K_VNNI' not in d, f"TRON_K_VNNI is {d.get('TRON_K_VNNI')!r} in the deb preset; the base must not carry it"
else:
    assert d.get('TRON_K_VNNI')=='ON', f"TRON_K_VNNI is {d.get('TRON_K_VNNI')!r} in the deb preset, want ON for the target"
print(f"preset check ok: TRON_AMX_DISPATCH ON, TRON_K_VNNI {want}")
PY
HEAD_SHA=$(git -C "$WT" rev-parse HEAD)
[ "$HEAD_SHA" = "$FULL" ] || die "build head $HEAD_SHA is not the commit $FULL (this fork makes no local commit)"
say "build head $HEAD_SHA"; git -C "$WT" log --oneline -3
[ "$(git -C "$WT" status --porcelain | grep -vc '^??' )" = 0 ] || { git -C "$WT" status --short | head; die "worktree not clean (the deb version would carry -dirty)"; }
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/$MAKELOG)"
t0=$(date +%s)
( cd "$WT" && taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/$MAKELOG" 2>&1 || { tail -40 "$OUT/$MAKELOG"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
grep -n "TRON_AMX_DISPATCH\|TRON_K_VNNI" "$OUT/$MAKELOG" | head -5
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/$DEB_OUT"; cp "$DEB" "$OUT/"
[ "$ARM" = base ] && { cp "$DEB" "$OUT/nightly.deb"; say "base deb also copied to $OUT/nightly.deb (the base-arm file name of campaign W)"; }
( cd "$WT" && taskset -c "$SOCKET1" make test-deb-package-contents ) >"$OUT/$PKGLOG" 2>&1 && say "test-deb-package-contents ok" || say "WARNING test-deb-package-contents rc=$? (see $OUT/$PKGLOG)"
# package checks: the AMX kill-switch literal and AMX tile instructions must be present; vnni strings are reported
dpkg-deb --fsys-tarfile "$OUT/$DEB_OUT" | tar -xO ./opt/positron/bin/rinzler >"$OUT/$RZ_OUT" || die "extract rinzler"
AMX_STR=$(strings "$OUT/$RZ_OUT" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$OUT/$RZ_OUT" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
VNNI_STR=$(strings "$OUT/$RZ_OUT" | grep -c -i 'vnni')
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN strings matching vnni=$VNNI_STR"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
VERSION=$(dpkg-deb -f "$OUT/$DEB_OUT" Version) || die "dpkg-deb -f $DEB_OUT Version"
say "deb Version field: $VERSION"
case $VERSION in *-dirty*) die "deb version '$VERSION' carries -dirty";; esac
case $VERSION in *"$BRANCH"*) ;; *) die "deb version '$VERSION' lacks the branch name $BRANCH (a detached build? the campaign tells our packages from nightlies by it)";; esac
python3 - "$OUT/$MANIFEST" "$ARM" "$COMMIT" "$FULL" "$HEAD_SHA" "$(basename "$DEB")" "$VERSION" "$(sha256sum "$OUT/$DEB_OUT" | cut -d' ' -f1)" "$(sha256sum "$OUT/$RZ_OUT" | cut -d' ' -f1)" "$AMX_STR" "$AMX_INSN" "$VNNI_STR" "$WT" "$BRANCH" "$DEB_OUT" "$RZ_OUT" <<'PY'
import json,sys,datetime
p,arm,commit,full,head,deb,version,sha,rz,a,b,c,wt,br,debout,rzout=sys.argv[1:17]
opts={"TRON_AMX_DISPATCH":"ON"} if arm=="base" else {"TRON_AMX_DISPATCH":"ON","TRON_K_VNNI":"ON"}
note={"base":"main at the commit, on the local branch jhan-pr4ci-base (version marker only; no local commit); the deb preset must not carry TRON_K_VNNI",
      "target":"PR-4 at the commit, on the local branch jhan-pr4ci-target (version marker only; no local commit); the deb preset carries TRON_K_VNNI ON itself"}[arm]
json.dump({"built":datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),"arm":arm,"commit":commit,"commit_sha":full,"head_sha":head,
 "deb":deb,"version":version,"deb_file":debout,"rinzler_file":rzout,"deb_sha256":sha,"rinzler_sha256":rz,
 "checks":{"TRON_AMX_DISABLE_literal":int(a),"amx_tile_insns":int(b),"vnni_strings":int(c)},
 "options":opts,"worktree":wt,"branch":br,"note":note},open(p,'w'),indent=1)
PY
cat "$OUT/$MANIFEST"; echo ok >"$OUT/$STATUS"; say "DONE ARM=$ARM $OUT/$DEB_OUT version $VERSION (status $OUT/$STATUS = ok)"
