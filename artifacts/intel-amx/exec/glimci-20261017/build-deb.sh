#!/usr/bin/env bash
# glimci-20261017: build the Debian package (deb) of branch jhan-amx-kvmul16 ON delphi-3bda, outside nix, the way
# exec/ci-mimic-20260918/build-target.sh built its target deb (make deb with the deb preset; the preset already
# carries TRON_AMX_DISPATCH=ON on this branch). The package is what the CI-config campaign installs for its
# amxon / amxoff arms. Output: /var/tmp/jhan/glimci-20261017/{target.deb, rinzler.target, manifest.json,
# build.status (running|ok|failed), make-deb.log}.
# Usage (on 3bda, detached): setsid nohup bash build-deb.sh 5061623a346ba5e8d22a6de8b3ab4cc058023214 >/var/tmp/jhan/glimci-20261017/build.log 2>&1 &
set -u
SHA=${1:?full commit sha of the branch head}
WT=/var/tmp/jhan/tron-g16            # the 3bda-local worktree of the branch (built by exec/glimmer-20261016/build.sh)
OUT=/var/tmp/jhan/glimci-20261017
SOCKET1=72-143,216-287               # our half of the machine
say() { echo "$(date -u +%FT%TZ) $*"; }
die() { say "FAILED: $*"; echo "failed: $*" >"$OUT/build.status"; exit 1; }
mkdir -p "$OUT"; echo running >"$OUT/build.status"
say "start SHA=$SHA"
[ -d "$WT" ] || die "worktree $WT missing"
HEAD=$(git -C "$WT" rev-parse HEAD) || die "git rev-parse"
[ "$HEAD" = "$SHA" ] || die "worktree head $HEAD is not $SHA"
[ -z "$(git -C "$WT" status --short)" ] || die "worktree not clean: $(git -C "$WT" status --short | head -3 | tr '\n' ' ')"
python3 - "$WT/CMakePresets.json" <<'PY' || die "deb preset lacks TRON_AMX_DISPATCH=ON"
import json,sys
p=json.load(open(sys.argv[1])); d=[c for c in p['configurePresets'] if c['name']=='deb'][0]['cacheVariables']
assert d.get('TRON_AMX_DISPATCH')=='ON', d
print("deb preset cacheVariables:", json.dumps(d))
PY
[ -e "$WT/ingest/traces/ingested-meta-models-Muse-Glimmer-30B/torch-export.stamp" ] || die "no Glimmer trace stamp"
export PATH=/tools/uv/0.9.5:$HOME/.ghcup/bin:$PATH
say "make deb (log $OUT/make-deb.log)"
t0=$(date +%s)
( cd "$WT" && nice -n 10 taskset -c "$SOCKET1" make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb ) >"$OUT/make-deb.log" 2>&1 || { tail -40 "$OUT/make-deb.log"; die "make deb"; }
say "make deb done in $(( $(date +%s) - t0 )) s"
grep -n "TRON_AMX_DISPATCH" "$OUT/make-deb.log" | head -3
DEB=$(ls -t "$WT"/gen-deb/tron_*_amd64.deb | head -1); [ -n "$DEB" ] || die "no deb produced"
cp "$DEB" "$OUT/target.deb" || die "copy deb"
dpkg-deb --fsys-tarfile "$OUT/target.deb" | tar -xO ./opt/positron/bin/rinzler >"$OUT/rinzler.target" || die "extract rinzler"
chmod +x "$OUT/rinzler.target"
AMX_STR=$(strings "$OUT/rinzler.target" | grep -c -x TRON_AMX_DISABLE)
AMX_INSN=$(objdump -d --no-show-raw-insn "$OUT/rinzler.target" | grep -c -E '\b(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)\b')
SYM16=$(nm -C "$OUT/rinzler.target" 2>/dev/null | grep -c -E 'amx_attn_h128g4::(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)<16ul?>')
SYM4=$(nm -C "$OUT/rinzler.target" 2>/dev/null | grep -c -E 'amx_attn_h128g4::(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)<4ul?>')
GLM=$(strings "$OUT/rinzler.target" | grep -c -x 'ingested-meta-models--Muse-Glimmer-30B-tp4')
say "package checks: TRON_AMX_DISABLE literal=$AMX_STR AMX tile insns=$AMX_INSN kernel symbols <16>=$SYM16 <4>=$SYM4 Glimmer tp4 model string=$GLM"
[ "$AMX_STR" -ge 1 ] && [ "$AMX_INSN" -ge 50 ] || die "AMX not compiled into the package"
[ "$GLM" -ge 1 ] || die "Glimmer tp4 model not in the package"
SHA256=$(sha256sum "$OUT/target.deb" | cut -d' ' -f1); RZSHA=$(sha256sum "$OUT/rinzler.target" | cut -d' ' -f1)
VER=$(dpkg-deb -f "$OUT/target.deb" Version)
python3 - "$OUT/manifest.json" "$SHA" "$(basename "$DEB")" "$VER" "$SHA256" "$RZSHA" "$AMX_STR" "$AMX_INSN" "$SYM16" "$SYM4" <<'PY'
import json,sys,datetime
p,sha,deb,ver,s256,rz,a,b,c,d=sys.argv[1:11]
json.dump({"branch":"jhan-amx-kvmul16","head":sha,"deb":deb,"version":ver,"deb_sha256":s256,"rinzler_sha256":rz,
           "amx_disable_literal":int(a),"amx_tile_insns":int(b),"kernel_symbols_16":int(c),"kernel_symbols_4":int(d),
           "built_utc":datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
           "make":"make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb (deb preset, outside nix, socket 1)"},open(p,"w"),indent=1)
PY
say "deb $(basename "$DEB") version $VER sha256 $SHA256; rinzler sha256 $RZSHA"
echo ok >"$OUT/build.status"
say "done"
