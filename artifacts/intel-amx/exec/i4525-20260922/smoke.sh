#!/usr/bin/env bash
# i4525-20260922 greedy smoke (runs ON delphi-3bda, our half): one user, temperature 0, --pay-for-determinism, fixed seed,
# PROMPT prompt tokens, LEN generated tokens, tokens written with --output-token-file; then the token rows are compared.
# Issue #4525 changes only how the KV cache is accessed (typed tensors), not the numbers, so the head binary must produce
# the same tokens as the main binary; head vs head2 is the A/A control; headoff = head with TRON_AMX_DISABLE=1.
# Reuses the guard, watcher, placement and cleanup functions of campaign.sh (I4525_FUNCTIONS_ONLY=1).
# Usage: NAME=... RT_BASE=... RT_HEAD=... [SMOKE_ARMS="base head head2 baseoff headoff"] [MODEL=ingested-qwen-3-4b-instruct-2507-tp2]
#        [TP=2] [PROMPT=1024] [LEN=128] [ATTN=cpu|fpga] [ARM_ENV_headoff=TRON_AMX_DISABLE=1] bash smoke.sh
# Outputs: exec/results/$NAME/smoke/<attn>-p<prompt>/{<arm>.tokens,<arm>.log,smoke.txt,smoke.done}.
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=${NAME:-i4525-20260922}
export CELLS_ALL=${CELLS_ALL:-"smoke|${MODEL:-ingested-qwen-3-4b-instruct-2507-tp2}|${TP:-2}|1|${PROMPT:-1024}"}
I4525_FUNCTIONS_ONLY=1; source "$EXEC/i4525-20260922/campaign.sh"   # returns after the function definitions
unset I4525_FUNCTIONS_ONLY
SMOKE_ARMS=${SMOKE_ARMS:-"base head head2 baseoff headoff"}
MODEL=${MODEL:-ingested-qwen-3-4b-instruct-2507-tp2}; TP=${TP:-2}; PROMPT=${PROMPT:-1024}; LEN=${LEN:-128}; ATTN=${ATTN:-cpu}
SM=$RES/smoke/${ATTN}-p${PROMPT}; mkdir -p "$SM"
exec >>"$LOG" 2>&1
rm -f "$SM/smoke.done"
echo "=== $NAME smoke started $(ts) pid $$ arms=[$SMOKE_ARMS] model=$MODEL tp=$TP prompt=$PROMPT len=$LEN attn=$ATTN ==="
TIP_BASE=$(git -C "$(dirname "$(dirname "$RT_BASE")")" rev-parse --short HEAD 2>/dev/null || echo "?")
TIP_HEAD=$(git -C "$(dirname "$(dirname "$RT_HEAD")")" rev-parse --short HEAD 2>/dev/null || echo "?")
if [ "$ATTN" = fpga ]; then hwenv="-u USE_HW_ATTN"; else hwenv="USE_HW_ATTN=0"; fi
trap 'stop_watcher; kill_ours; remove_our_slice_files; campaign_guard_release 2>/dev/null' EXIT
for arm in $SMOKE_ARMS; do
  base_arm=${arm%2}; bin=$(arm_bin "$base_arm") || { echo "$(ts) unknown smoke arm $arm"; continue; }
  envv=$(arm_env "$base_arm"); out=$SM/$arm; stops=0
  [ -x "$bin" ] || { echo "SMOKE-FAILED arm=$arm: $bin missing" >>"$SM/smoke.txt"; continue; }
  while :; do
    [ -s "$out.tokens" ] && { echo "$(ts) smoke $arm already done"; break; }
    wait_clear || { echo "$(ts) deadline while waiting"; break; }
    take_guard || { echo "$(ts) deadline while waiting for the guard"; break; }
    status "smoke $arm"
    echo "### smoke arm=$arm bin=$bin env=[${envv}] tip=$(arm_tip "$base_arm") model=$MODEL tp=$TP attn=$ATTN prompt=$PROMPT len=$LEN users=1 temperature=0 pay-for-determinism seed=1 $(ts) $(machine_line)" >>"$SM/smoke.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv $envv TRON_LOG_LEVEL=info \
        timeout -k 30 900 "$bin" stream-generate-text -m "$MODEL" $(placement "$TP") --hugepage_file "$HPFILE" -o \
        --prompt-length "$PROMPT" -l "$LEN" -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    echo "smoke $arm rc=$rc $(grep -E 'Version:|HW attention|average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-300)" >>"$SM/smoke.txt"
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
      echo "SMOKE-STOPPED arm=$arm rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)" >>"$SM/smoke.txt"
      rm -f "$out.tokens"; stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "SMOKE-GIVEN-UP arm=$arm" >>"$SM/smoke.txt"; break; }
      sleep 120; continue
    fi
    [ $rc -eq 0 ] && [ -s "$out.tokens" ] || echo "SMOKE-FAILED arm=$arm rc=$rc (see $out.log)" >>"$SM/smoke.txt"
    break
  done
done
python3 - "$SM" "$SMOKE_ARMS" <<'PY' >>"$SM/smoke.txt" 2>&1
import os, re, sys
d, arms = sys.argv[1], sys.argv[2].split()
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if os.path.exists(p):
        lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
        if lines: rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
pairs = [("head", "head2"), ("head", "base"), ("headoff", "baseoff"), ("headoff", "head"), ("baseoff", "base")]
verdict = "ok"
wanted = [p for p in pairs if p[0] in arms and p[1] in arms]   # only pairs whose arms this run asked for
for a, b in wanted:
    if a not in rows or b not in rows:
        print(f"{a} vs {b}: missing"); verdict = "incomplete"; continue
    ra, rb = rows[a], rows[b]; n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    if first is None: print(f"{a} vs {b}: identical for {n} tokens (lengths {len(ra)} / {len(rb)})")
    else:
        print(f"{a} vs {b}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens")
        if (a, b) in (("head", "head2"), ("head", "base"), ("headoff", "baseoff")): verdict = "differs"
print("SMOKE-VERDICT", verdict if (wanted and len(rows) >= 2) else "incomplete")
PY
tail -8 "$SM/smoke.txt"
last=$(grep -o 'SMOKE-VERDICT.*' "$SM/smoke.txt" | tail -1)   # the LAST verdict line only (smoke.txt is appended to across reruns)
[ "$last" = "SMOKE-VERDICT ok" ] && echo ok >"$SM/smoke.done" || echo "${last:-SMOKE-VERDICT missing}" >"$SM/smoke.done"
echo "=== $NAME smoke finished $(ts): $(cat "$SM/smoke.done") ==="
