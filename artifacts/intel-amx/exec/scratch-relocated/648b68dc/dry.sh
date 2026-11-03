#!/usr/bin/env bash
# Dry run of exec/glimext-20261018 in a stub sandbox (bash-local-expansion-trap memory): paths rewritten, runtron/build/guard/dut stubbed.
set -u
S=${S:?}; SB=$S/sandbox; SRC=/home/jhan/workspace/intel-AMX/exec
rm -rf "$SB"; mkdir -p "$SB/exec/glimext-20261018" "$SB/exec/logs" "$SB/exec/results" "$SB/exec/q4b-fpga-20260921" "$SB/exec/sync4424-20261002" "$SB/exec/dd" "$SB/exec/glimmer-20261016" "$SB/vt" "$SB/hp"
REW="s#/home/jhan/workspace/intel-AMX/exec#$SB/exec#g; s#/var/tmp/jhan#$SB/vt#g; s#/dev/hugepages#$SB/hp#g; s#awk '/^HugePages_Free/{print \$2}' /proc/meminfo#echo 512#g"
for f in chain.sh chain2.sh campaign.sh smoke.sh smoke2.sh margin.sh tests.sh gen_report.py; do sed "$REW" "$SRC/glimext-20261018/$f" >"$SB/exec/glimext-20261018/$f"; done
# the git rev-parse checks against the real shas cannot hold in the sandbox
sed -i -E 's/\[ "\$\(git -C [^ ]+ rev-parse HEAD 2>\/dev\/null\)" = "\$(BASE_SHA|HEAD_SHA|SHA)" \]/true/' "$SB/exec/glimext-20261018/chain.sh" "$SB/exec/glimext-20261018/chain2.sh" "$SB/exec/glimext-20261018/tests.sh"
cp "$SRC/sync4424-20261002/summarize.py" "$SB/exec/sync4424-20261002/"; cp "$SRC/dd/"*.py "$SB/exec/dd/"; cp "$SRC/glimmer-20261016/gen_compare.py" "$SB/exec/glimmer-20261016/"
cat >"$SB/exec/lib-guard.sh" <<EOG
ci_lease_busy() { return 1; }
other_user_active() { return 1; }
blackout_active() { return 1; }
campaign_guard_acquire() { return 0; }
campaign_guard_release() { return 0; }
rinzler_active() { [ -e "$SB/serving" ]; }
rinzler_takeover_if_idle() { rm -f "$SB/serving"; GUARD_TAKEOVER_LAST=\$(date +%s); echo "\$(date -u +%FT%TZ) STUB takeover"; return 0; }
EOG
cat >"$SB/exec/q4b-fpga-20260921/dut.sh" <<EOG
#!/usr/bin/env bash
case \$1 in serving-up) touch "$SB/serving"; echo "STUB serving-up";; serving-down) rm -f "$SB/serving"; echo "STUB serving-down";; esac
EOG
touch "$SB/serving"   # production serving active at the start: the first run must take it over
# stub build.sh: creates the worktree with stub binaries and the marker
cat >"$SB/exec/glimext-20261018/build.sh" <<EOG
#!/usr/bin/env bash
set -u
TAG=\${TAG:?}; SHA=\${SHA:?}; KSYM_RE=\${KSYM_RE:?}; KSYM_N=\${KSYM_N:?}
RES=$SB/exec/results/glimext-20261018; WT=$SB/vt/tron-\$TAG; mkdir -p "\$RES" "\$WT/gen" "\$WT/stats"
exec >>$SB/exec/logs/glimext-20261018-build-\$TAG.log 2>&1
rm -f "\$RES/build-\$TAG.done"; echo "=== STUB build \$TAG started \$(date -u +%FT%TZ) sha=\$SHA ksym=[\$KSYM_RE] n=\$KSYM_N ==="
sleep 2
sed "s/__TAG__/\$TAG/g; s/__SHA__/\$SHA/g" "$S/runtron-stub.sh" >"\$WT/gen/runtron.\$TAG"; chmod +x "\$WT/gen/runtron.\$TAG"; cp "\$WT/gen/runtron.\$TAG" "\$WT/gen/runtron"
for t in t_amx_numerics t_amx_dispatch_dtype t_llama_unit; do printf '#!/usr/bin/env bash\n[ "\${TRON_AMX_DISABLE:-}" = 1 ] && echo "WARN: AMX unavailable on this host"\necho "All tests passed (10 assertions in 2 test cases)"\n' >"\$WT/gen/\$t"; chmod +x "\$WT/gen/\$t"; done
{ echo "tag \$TAG worktree \$WT"; echo "tip \$SHA (stub)"; echo "compiler: stub clang"; echo "version: stub"; echo "checks: tdpbf16ps=1 TRON_ATTN_STATS=1 kernel_symbols=\$KSYM_N (need \$KSYM_N)"; } >"\$RES/build-\$TAG.txt"
echo ok >"\$RES/build-\$TAG.done"; echo "=== STUB build \$TAG finished ok ==="
EOG
REAL_LOG=$SRC/results/glimmer-20261016/rt/l8b-tp2-8u-p1024-cpu__cpu__amxon__rep1.log
grep '^\[attn-stats\]' "$REAL_LOG" >"$S/attn-stats-sample.txt"
cat >"$S/runtron-stub.sh" <<'EOG'
#!/usr/bin/env bash
# stub runtron (__TAG__): prints the log lines the parsers need, writes tokens / intermediates files
TAG=__TAG__; SHA=__SHA__
model=; out=; inter=; forced=; len=256; users=1; prompt=1024
while [ $# -gt 0 ]; do case $1 in -m) model=$2; shift;; --output-token-file) out=$2; shift;; --intermediates-file) inter=$2; shift;; --force-feed-text-token-file) forced=$2; shift;; -l) len=$2; shift;; -u) users=$2; shift;; --prompt-length) prompt=$2; shift;; --version) echo "Version: 2026.10.18-stub hash: $SHA"; exit 0;; esac; shift; done
sleep 1
echo "[info ] Version: 2026.10.18-${SHA:0:8} hash: $SHA"
if [ "${USE_HW_ATTN:-unset}" = 0 ]; then echo "[info ] HW attention disabled for model '$model': USE_HW_ATTN=0"; else echo "[info ] HW attention enabled for model '$model' (hw_slots 13)"; fi
base=100; [ "$TAG" = g16h ] && [ -z "${TRON_AMX_DISABLE:-}" ] && base=104
for u in $(seq 1 "$users"); do
  echo "Parsing the prompt took $(awk -v p=$prompt 'BEGIN{printf "%.3f", p/830.0}') s at 830.0 tokens/s"
  echo "Generating $((len - 3)) response tokens with $((prompt + len)) context took 2.1 s at $(awk -v b=$base -v r=$RANDOM 'BEGIN{printf "%.2f", b + (r % 100) / 100.0}') average tok/s"
done
cat "__ATTN__"
if [ -n "$out" ]; then
  if [ -n "$forced" ]; then cp "$forced" "$out"
  else
    flip=0; case $model in *Glimmer*) [ "$TAG" = g16h ] && [ -z "${TRON_AMX_DISABLE:-}" ] && flip=1;; esac
    { for i in $(seq 0 $((len - 1))); do v=$((1000 + i)); [ $flip = 1 ] && [ $i -ge 40 ] && v=$((2000 + i)); printf '%d ' $v; done; echo; } >"$out"
  fi
fi
if [ -n "$inter" ]; then
  python3 - "$inter" "$prompt" "$len" "$TAG" <<'PY'
import sys, random
p, P, L, tag = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
random.seed(1)
with open(p, "w") as f:
  for k in range(L):
    N = P - 1 + k
    v = [round(random.uniform(-2, 10), 4) for _ in range(32)]
    if tag == "g16h": v[3] += 0.01
    f.write("  Logits of token %d (32): %s\n" % (N, " ".join("%12.6f" % x for x in v)))
    top = sorted(range(32), key=lambda i: -v[i])[:5]
    f.write("  Top-k Logits of token %d (5): %s\n" % (N, " ".join("%12.6f" % v[i] for i in top)))
    f.write("  Top-k Token IDs for Logits of token %d (5): %s\n" % (N, " ".join(str(i) for i in top)))
PY
fi
exit 0
EOG
sed -i "s#__ATTN__#$S/attn-stats-sample.txt#" "$S/runtron-stub.sh"
cd "$SB" || exit 1
export S
echo "sandbox at $SB; running chain with REPS=2 (stubs)"
( cd "$SB" && env REPS=2 E_NOT_AFTER=2026-12-31T00:00:00Z bash "$SB/exec/glimext-20261018/${CHAIN:-chain.sh}" )
echo "chain rc=$?"
echo "--- markers:"; for f in build-g16b.done build-g16h.done tests.done identity.done margin.done chain.done; do printf "%s=%s " $f "$(cat $SB/exec/results/glimext-20261018/$f 2>/dev/null)"; done; echo; echo "campaign.done=$(cat $SB/exec/logs/glimext-20261018.done 2>/dev/null)"
echo "--- serving at end: $([ -e $SB/serving ] && echo up || echo DOWN); taken-down marker: $([ -e $SB/exec/results/glimext-20261018/serving-taken-down.marker ] && echo present || echo absent)"
echo "--- rt runs: $(ls $SB/exec/results/glimext-20261018/rt/*.log 2>/dev/null | grep -vc attempt) logs; smoke cells: $(ls -d $SB/exec/results/glimext-20261018/smoke/* 2>/dev/null | wc -l)"
echo "--- chain log tail:"; tail -25 "$SB/exec/logs/glimext-20261018-chain.log" | cut -c1-220
