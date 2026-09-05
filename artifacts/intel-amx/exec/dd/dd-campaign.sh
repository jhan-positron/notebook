#!/usr/bin/env bash
# Token-30 root cause campaign (intel-AMX/definitive-decode/debug-plan.html), v2 after review.
# Runs detached on delphi-3bda:
#   Stage B  build three variants of the debug worktree (canonical, mirror, PV-truncation);
#            light profile (nice/taskset -j6) while CI holds the DUT or rinzler serves
#   Stage A  wait for the CI lease, rinzler idle policy, campaign guard
#   Stage C  R1a/R1b/R2 (free-running), R1c (prompt ids), R3a/R3b (A/A values), R3c (add-order
#            control: different core count, no AMX), R4 (forced ON), R4x/R3x (256 steps, logits
#            only), R7 (kernel tests per variant), R6 (mirror), R5 (truncation)
# Debug code lives ONLY in ~/workspace/ai-runs/tron-dd (branch jhan-dd-debug), never on jhan-amx-p0.
set -u
EXEC=~/workspace/intel-AMX/exec
DD=$EXEC/dd
RES=$EXEC/results/dd
D=/var/tmp/jhan/dd                     # local NVMe: big intermediates logs
LOG=$EXEC/logs/dd-campaign.log
MARKER=$EXEC/logs/dd-campaign.done
WT=~/workspace/ai-runs/tron-dd
SRC=~/workspace/tron-amx               # traces to reuse (git-ignored, 15 MB)
mkdir -p "$RES" "$D" "$EXEC/logs"
exec >>"$LOG" 2>&1
rm -f "$MARKER"
echo "=== dd-campaign v2 queued $(date -u +%FT%TZ) pid $$ ==="
stamp() { date -u +%FT%TZ; }
source "$EXEC/lib-guard.sh"
fail() { echo "$1" >"$MARKER"; echo "FAIL: $1 $(stamp)"; exit 1; }

# ---------------------------------------------------------------- Stage B: build (light profile while busy)
cd "$WT" || fail no-worktree
echo "--- stage B: build $(git log -1 --format='%h %s') $(stamp)"
if [ ! -d ingest/traces ]; then
  cp -r "$SRC/ingest/traces" ingest/   # plain cp: fresh mtimes newer than the checkout, so no torch export re-runs
  echo "copied ingest/traces from tron-amx ($(ls ingest/traces | wc -l) dirs)"
fi
if ci_lease_busy || rinzler_active; then J="-j6"; PIN="nice -n19 taskset -c 23,24,36,167,168,180"; PROFILE=light; else J="-j96"; PIN="nice -n10"; PROFILE=full; fi
echo "build profile: $PROFILE ($J)"
CFG='cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS='
build() {  # build <suffix> <cmake flags...>
  local suffix=$1; shift
  local t0=$(date +%s)
  $PIN nix develop --command bash -c "$CFG $* >/dev/null && cmake --build gen --target runtron t_amx_numerics t_amx_dispatch_dtype t_amx_logit_ab $J 2>&1 | grep -E 'error|FAILED' | head -20; exit \${PIPESTATUS[0]}" \
    || fail "build-$suffix-failed"
  cp gen/runtron "gen/runtron.$suffix"; cp gen/t_amx_numerics "gen/t_amx_numerics.$suffix"
  echo "built $suffix in $(( $(date +%s) - t0 )) s $(stamp)"
}
build canon  -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_PV_TRUNC=OFF
build mirror -DTRON_AMX_K_MIRROR=ON  -DTRON_AMX_PV_TRUNC=OFF
build trunc  -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_PV_TRUNC=ON
$PIN nix develop --command bash -c "$CFG -DTRON_AMX_K_MIRROR=OFF -DTRON_AMX_PV_TRUNC=OFF >/dev/null"   # leave the cache canonical
{
  echo "# build record $(stamp) profile=$PROFILE"; git -C "$WT" log -1 --format='%H %s'
  for b in canon mirror trunc; do
    echo "runtron.$b: $(sha256sum gen/runtron.$b | cut -c1-16)  symbols(qk_canonical,qk_mirror,weights_times_v)=$(nm -C gen/runtron.$b | grep -c -e qk_canonical_128x4 -e qk_mirror_128x4 -e weights_times_v_128x4)  qwen-tp2-in-model-table=$(./gen/runtron.$b --list-models 2>/dev/null | grep -cx ingested-qwen-3-4b-instruct-2507-tp2)"
  done
  echo "final cache:"; grep -E "^(TRON_AMX_DISPATCH|TRON_AMX_K_MIRROR|TRON_AMX_PV_TRUNC|CMAKE_BUILD_TYPE|BUILD_INGEST_MODELS)" gen/CMakeCache.txt
} | tee "$RES/build-record.txt"
grep -q "qwen-tp2-in-model-table=1" "$RES/build-record.txt" || echo "WARNING: --list-models gate did not report the qwen tp2 slug (flag may not exist); continuing"
echo "--- builds done $(stamp)"

# ---------------------------------------------------------------- Stage A: window
echo "--- stage A: wait for CI release $(stamp)"
wait_for_ci_release 36000 || fail ci-never-released
echo "lease free $(stamp)"
quiet=0
for _ in $(seq 1 36); do
  if ! rinzler_active; then quiet=1; break; fi
  traffic=$(sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager 2>/dev/null | grep -icE 'session|request|prompt|generat|token') || true
  conns=$(sudo -n ss -Htn state established '( sport = :13000 or sport = :13001 or sport = :13002 or sport = :13003 )' 2>/dev/null | awk '$4 !~ /^127\.0\.0\.1:/' | wc -l) || true
  if [ "${traffic:-0}" -eq 0 ] && [ "${conns:-0}" -eq 0 ]; then
    echo "rinzlers idle (journal=$traffic conns=$conns) -> rinzler policy stop $(stamp)"
    sudo -n systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3 && sleep 5
    fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null || { rm -f /dev/hugepages/slice-*-of-8; echo "orphaned hugepage slices removed"; }
    quiet=1; break
  fi
  echo "serving in use (journal=$traffic conns=$conns), waiting $(stamp)"; sleep 600
done
[ "$quiet" = 1 ] || fail never-quiet
campaign_guard_acquire || fail guard-refused
trap 'campaign_guard_release; fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null || rm -f /dev/hugepages/slice-*-of-8' EXIT
echo "--- guard acquired $(stamp)"

# ---------------------------------------------------------------- Stage C: runs
export USE_HW_ATTN=0
CORES_A="151-152,24-29,48-53,153-154,30-35,54-59"          # t1-quick set (26 app cores)
CORES_B="151-152,24-29,48-53,153-154,30-35,54-57"          # R3c: two fewer cores -> different attention plan, no AMX
SYS="--instance 0,4 --devices 10:00.0,13:00.0 --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/dd --nr_hugepages 128 -o --temperature 0 --pay-for-determinism"
PROMPT_ARGS="-u 1 --prompt-length 2048"                  # switched to --text-token-file after R1c if the ids reproduce r1a
FILT_FULL='Logits|Top-k|Attn out|WO|WQ roped|WK roped|WV'  # attention in/out per layer + logits; drops WFF* (see plan)
FILT_LOGITS='Logits|Top-k'
run() {  # run <name> <binary> <off|on> <cores> <filter|-> <timeout> <extra args...>
  local name=$1 bin=$2 arm=$3 cores=$4 filt=$5 to=$6; shift 6
  if ci_took_dut; then echo "CI-TOOK-DUT before $name $(stamp)"; return 2; fi
  local envs=(USE_HW_ATTN=0)
  [ "$arm" = off ] && envs+=(TRON_AMX_DISABLE=1)
  [ "$filt" != "-" ] && envs+=("TRON_INTERMEDIATES_FILTER=$filt")
  local t0=$(date +%s)
  echo "### $name arm=$arm bin=$bin cores=$cores filter=$filt $(stamp)"
  env -u TRON_AMX_DISABLE -u TRON_INTERMEDIATES_FILTER "${envs[@]}" timeout "$to" "$bin" stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 \
      --app-cores "$cores" $SYS $PROMPT_ARGS "$@" >"$D/$name.log" 2>&1
  local rc=$?
  grep -E "Enqueueing prompt|HW attention (disabled|enabled) for model|HW-attention not available|AMX-DEBUG|KV cache footprint|average tok/s|Loaded forced|Generating [0-9]+ response tokens" "$D/$name.log" | sed "s/^/  [$name] /"
  echo "  [$name] rc=$rc wall=$(( $(date +%s) - t0 ))s $(stamp)"
  if [ $rc -ne 0 ] || ! grep -q "Generating [0-9]* response tokens" "$D/$name.log"; then echo "  [$name] INCOMPLETE"; return 1; fi
  return 0
}
tok() { python3 "$DD/dd_tokens.py" "$@"; }
div() { python3 "$DD/dd_first_divergence.py" "$@"; }

{
echo "# token-30 root cause campaign v2, $(stamp)"
cat "$RES/build-record.txt"

echo "## Phase 1: reproduce + A/A tokens (R1a, R1b, R2), -l 256"
run r1a gen/runtron.canon off "$CORES_A" - 1800 -l 256 --output-token-file "$D/r1a.tok" || fail r1a-incomplete
run r1b gen/runtron.canon off "$CORES_A" - 1800 -l 256 --output-token-file "$D/r1b.tok" || fail r1b-incomplete
run r2  gen/runtron.canon on  "$CORES_A" - 1800 -l 256 --output-token-file "$D/r2.tok"  || fail r2-incomplete
echo "A/A tokens (r1a vs r1b):";  tok "$D/r1a.tok" "$D/r1b.tok" --json "$RES/r1a-vs-r1b.json" | grep -E '"identical"|first_diff|n_diff'
echo "cross-day OFF (r1a vs 2026-08-18 off1, green chunks both sides):"; tok "$D/r1a.log" "$EXEC/results/slot1/t1-quick/off1-2048.log" --json "$RES/r1a-vs-archived-off1.json" | grep -E '"identical"|first_diff|n_diff'
echo "OFF vs ON (r1a vs r2):";    tok "$D/r1a.tok" "$D/r2.tok" --json "$RES/r1a-vs-r2.json" | grep -E '"identical"|first_diff|n_diff|at_first_diff'
grep -q '"identical": true' "$RES/r1a-vs-r1b.json" || fail aa-tokens-differ
FF=$(python3 -c "import json;d=json.load(open('$RES/r1a-vs-r2.json'));print(d['first_diff_pos_1based'] or 0)")
NPROMPT=$(grep -oP 'Enqueueing prompt 1/1 consisting of \K[0-9]+' "$D/r1a.log" | head -1)
echo "first free-running flip: $FF (0 = none in 256); prompt tokens enqueued: $NPROMPT"
if [ "$FF" -gt 0 ]; then L=$(( FF + 8 )); [ $L -lt 64 ] && L=64; [ $L -gt 256 ] && L=256; else L=256; fi
echo "L (forced/intermediates length) = $L"
cp "$D"/r1a.tok "$D"/r1b.tok "$D"/r2.tok "$RES/" 2>/dev/null

echo "## Phase 1c: prompt ids (HF tokenizer, add_special_tokens=False, clipped to 2048) reproduce r1a?"
nix develop --command python3 bin/tokenize_py -n "$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/* | head -1)" -f /scratch/prompts/md_ch1.txt > "$D/md_ch1.ids.json" 2>"$D/tokenize.err" \
  && python3 -c "import json;ids=json.load(open('$D/md_ch1.ids.json'));print('HF ids for md_ch1:',len(ids));open('$D/prompt.ids','w').write(' '.join(map(str,ids[:2048]))+'\n')" \
  || echo "tokenize_py failed: $(tail -2 "$D/tokenize.err")"
if [ -s "$D/prompt.ids" ]; then
  PROMPT_ARGS="--text-token-file $D/prompt.ids"
  run r1c gen/runtron.canon off "$CORES_A" - 1800 -l 256 --output-token-file "$D/r1c.tok" || echo "r1c incomplete"
  echo "prompt ids reproduce r1a (r1c vs r1a):"; tok "$D/r1c.tok" "$D/r1a.tok" --json "$RES/r1c-vs-r1a.json" | grep -E '"identical"|first_diff|n_diff'
  if grep -q '"identical": true' "$RES/r1c-vs-r1a.json"; then echo "USING --text-token-file $D/prompt.ids for all later runs (ids shared with HF by construction)"; cp "$D/prompt.ids" "$RES/"; else echo "ids do NOT reproduce r1a -> keeping -u 1 for later runs"; PROMPT_ARGS="-u 1 --prompt-length 2048"; fi
fi

echo "## Phase 2: logits + activations, -l $L, filter '$FILT_FULL'"
df -h /var/tmp | tail -1
run r3a gen/runtron.canon off "$CORES_A" "$FILT_FULL" 7200 -l "$L" --output-token-file "$D/r3a.tok" --intermediates-file "$D/r3a.txt" || fail r3a-incomplete
ls -la "$D/r3a.txt"; du -h "$D/r3a.txt"; wc -l "$D/r3a.txt"
run r3b gen/runtron.canon off "$CORES_A" "$FILT_FULL" 7200 -l "$L" --output-token-file "$D/r3b.tok" --intermediates-file "$D/r3b.txt" || fail r3b-incomplete
echo "A/A tokens (r3a vs r3b):"; tok "$D/r3a.tok" "$D/r3b.tok" --json "$RES/r3a-vs-r3b.json" | grep -E '"identical"|first_diff'
echo "prefix check (r3a first $L ids vs r1a):"; python3 -c "
a=open('$D/r1a.tok').read().split(); b=open('$D/r3a.tok').read().split(); import json
r={'identical_prefix': a[:len(b)]==b, 'len_r3a': len(b)}; print(json.dumps(r)); json.dump(r, open('$RES/r3a-prefix.json','w'))"
echo "A/A values (r3b vs r3a), threshold 0:"; div --off "$D/r3a.txt" --on "$D/r3b.txt" --out "$RES/layers-aa.json" 2>"$D/layers-aa.err" | head -3
AA_OVER=$(python3 -c "import json;s=json.load(open('$RES/layers-aa.json'))['summary'];print(s['n_over_threshold']+s['n_missing_in_off']+s['n_missing_in_on'])")
echo "A/A differing+missing keys: $AA_OVER (0 expected)"
run r3c gen/runtron.canon off "$CORES_B" "$FILT_FULL" 7200 -l "$L" --output-token-file "$D/r3c.tok" --intermediates-file "$D/r3c.txt" || echo "r3c incomplete"
echo "add-order control (r3c vs r3a: different core count, no AMX):"; tok "$D/r3c.tok" "$D/r3a.tok" --json "$RES/r3c-vs-r3a-tokens.json" | grep -E '"identical"|first_diff|n_diff'
div --off "$D/r3a.txt" --on "$D/r3c.txt" --out "$RES/layers-r3c.json" 2>"$D/layers-r3c.err" | tee "$RES/layers-r3c.txt" | head -14
cp "$D/r3a.tok" "$D/forced.tok"; NF=$(wc -w <"$D/forced.tok"); echo "forced ids: $NF (row from r3a)"
run r4 gen/runtron.canon on "$CORES_A" "$FILT_FULL" 7200 -l "$NF" --force-feed-text-token-file "$D/forced.tok" --output-token-file "$D/r4.tok" --intermediates-file "$D/r4.txt" || fail r4-incomplete
echo "forced replay check (r4.tok == forced.tok):"; tok "$D/r4.tok" "$D/forced.tok" | grep -E '"identical"'
python3 "$DD/dd_logits_step.py" --off "$D/r3a.txt" --on "$D/r4.txt" --forced "$D/forced.tok" --out "$RES/steps-r4.json" --mark "${FF:-30}" | tee "$RES/steps-r4.txt"
echo "flip consistency (R4's own top-1 at the free-running flip step == r2 token there):"; python3 -c "
import json; ff=$FF; s=json.load(open('$RES/steps-r4.json'))['steps']; r2=open('$D/r2.tok').read().split()
row=next((r for r in s if r.get('step')==ff), None); ok=(row is not None and ff>0 and str(row['on_top1'])==r2[ff-1]); out={'ff':ff,'on_top1':row['on_top1'] if row else None,'r2_token':r2[ff-1] if ff>0 else None,'match':ok}
print(json.dumps(out)); json.dump(out, open('$RES/flip-match.json','w'))"
div --off "$D/r3a.txt" --on "$D/r4.txt" --out "$RES/layers-r4.json" --csv "$D/layers-r4.csv" 2>"$D/layers-r4.err" | tee "$RES/layers-r4.txt" | head -16
echo "## Phase 2x: forced ON over all 256 r1a ids, logits only (more flips for the near-tie statistics)"
run r3x gen/runtron.canon off "$CORES_A" "$FILT_LOGITS" 7200 -l 256 --output-token-file "$D/r3x.tok" --intermediates-file "$D/r3x.txt" || echo "r3x incomplete"
run r4x gen/runtron.canon on "$CORES_A" "$FILT_LOGITS" 7200 -l 256 --force-feed-text-token-file "$D/r1a.tok" --output-token-file "$D/r4x.tok" --intermediates-file "$D/r4x.txt" || echo "r4x incomplete"
python3 "$DD/dd_logits_step.py" --off "$D/r3x.txt" --on "$D/r4x.txt" --forced "$D/r1a.tok" --out "$RES/steps-r4x.json" --mark "${FF:-30}" | tee "$RES/steps-r4x.txt" | head -20

echo "## Phase 3 (decision-free): R7 kernel tests per variant, R6 mirror, R5 truncation"
for v in canon mirror trunc; do
  echo "### R7 t_amx_numerics.$v"; ( env -u TRON_AMX_DISABLE -u SYSTEM_CONFIG nix develop --command ./gen/t_amx_numerics.$v -s 2>&1 | grep -E "All tests passed|FAILED|failed|assertions|skipped|nothing to test|WARN" | tail -6 ) | tee "$RES/r7-$v.txt"
done
echo "### R7 t_amx_dispatch_dtype (dispatch-gate test, CPU fakes)"; ( env -u TRON_AMX_DISABLE -u SYSTEM_CONFIG nix develop --command ./gen/t_amx_dispatch_dtype 2>&1 | tail -3 ) | tee "$RES/r7-dtype.txt"
run r6 gen/runtron.mirror on "$CORES_A" "$FILT_FULL" 7200 -l "$NF" --force-feed-text-token-file "$D/forced.tok" --output-token-file "$D/r6.tok" --intermediates-file "$D/r6.txt" || echo "r6 incomplete"
grep -o "KV cache footprint.*" "$D/r6.log" | head -2 | tee "$RES/r6-footprint.txt"
echo "mirror canary: r6 vs r4 (0 expected) and r6 vs r3a (nonzero expected unless the arena was absent)"
div --off "$D/r4.txt"  --on "$D/r6.txt" --out "$RES/layers-r6-vs-r4.json"  2>/dev/null | head -2
div --off "$D/r3a.txt" --on "$D/r6.txt" --out "$RES/layers-r6-vs-r3a.json" 2>/dev/null | head -2
run r5 gen/runtron.trunc on "$CORES_A" "$FILT_FULL" 7200 -l "$NF" --force-feed-text-token-file "$D/forced.tok" --output-token-file "$D/r5.tok" --intermediates-file "$D/r5.txt" || echo "r5 incomplete"
python3 "$DD/dd_logits_step.py" --off "$D/r3a.txt" --on "$D/r5.txt" --forced "$D/forced.tok" --out "$RES/steps-r5.json" --mark "${FF:-30}" | tee "$RES/steps-r5.txt" | head -20
div --off "$D/r3a.txt" --on "$D/r5.txt" --out "$RES/layers-r5.json" 2>"$D/layers-r5.err" | tee "$RES/layers-r5.txt" | head -16
div --off "$D/r4.txt"  --on "$D/r5.txt" --out "$RES/layers-r5-vs-r4.json" 2>/dev/null | head -2   # rounding-mode-only difference (same add order)
cp "$D"/r3a.tok "$D"/r4.tok "$D"/r5.tok "$D"/r6.tok "$D"/forced.tok "$D"/r4x.tok "$RES/" 2>/dev/null
echo "# done $(stamp)"
} >"$RES/campaign.txt" 2>&1

echo ok >"$MARKER"
echo "=== dd-campaign done $(stamp) ==="
