#!/usr/bin/env bash
# i4500fix-20260928 greedy smoke (runs ON delphi-3bda, our half): runtron token rows of the fix binary against the
# PR #4424 head binary, one user, temperature 0, --pay-for-determinism, seed 1, 128 generated tokens, qwen-3-4b tp2,
# with CPU attention (USE_HW_ATTN=0) and with FPGA attention (variable unset), at prompt 1024 (every prefill block
# full) and prompt 1000 (a row-major tail block left by the prefill). Arms: vnni = /var/tmp/jhan/tron-tilec/gen/runtron
# (30c4ac82cb, AMX + VNNI K, built 2026-09-17), fix = the runtron of build step A, fix2 = fix again (the A/A control).
# The fix changes the fp32 add order of the tail-block scores (row-major dotter instead of qk_group), so fix vs vnni
# may differ at a bf16 tie; fix vs fix2 must be identical. Recipe of exec/i4525-20260922/smoke.sh.
# Outputs: exec/results/i4500fix-20260928/smoke/<attn>-p<prompt>/{<arm>.tokens,<arm>.log}, smoke/smoke.txt, smoke/smoke.done
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
C=$EXEC/i4500fix-20260928
RES=$EXEC/results/i4500fix-20260928
SM=$RES/smoke
RT_VNNI=${RT_VNNI:-/var/tmp/jhan/tron-tilec/gen/runtron}
RT_FIX=${RT_FIX:-/var/tmp/jhan/tron-i4500/gen/runtron}
MODEL=${MODEL:-ingested-qwen-3-4b-instruct-2507-tp2}; LEN=${LEN:-128}
SMOKE_ARMS=${SMOKE_ARMS:-"vnni fix fix2"}; ATTNS=${ATTNS:-"cpu fpga"}; PROMPTS=${PROMPTS:-"1024 1000"}
HPFILE=/dev/hugepages/amx-i4500fix-smoke
OUR_RT_RE='runtron .*--hugepage_file /dev/hugepages/amx-i4500fix-smoke'
export GUARD_RUNTRON_USER=jhan
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
source "$EXEC/lib-guard.sh"
source "$C/lib.sh"
mkdir -p "$SM"
exec >>"$RES/smoke.log" 2>&1
rm -f "$SM/smoke.done"; : >"$SM/smoke.txt"; gaveup=0
echo "=== i4500fix smoke started $(ts) pid $$ arms=[$SMOKE_ARMS] attn=[$ATTNS] prompts=[$PROMPTS] model=$MODEL len=$LEN ==="
placement2="--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128"
arm_bin() { case $1 in vnni) echo "$RT_VNNI" ;; fix|fix2) echo "$RT_FIX" ;; *) return 1 ;; esac; }
kill_ours() { pkill -TERM -u jhan -f "$OUR_RT_RE" 2>/dev/null; return 0; }
trap 'stop_watcher; kill_ours; remove_our_hugepage_files "$HPFILE"; campaign_guard_release 2>/dev/null' EXIT
for arm in $SMOKE_ARMS; do bin=$(arm_bin "$arm") || continue; [ -x "$bin" ] || { echo "SMOKE-FAILED arm=$arm: $bin missing" >>"$SM/smoke.txt"; }; done
for attn in $ATTNS; do
  for prompt in $PROMPTS; do
    d=$SM/$attn-p$prompt; mkdir -p "$d"
    if [ "$attn" = fpga ]; then hwenv="-u USE_HW_ATTN"; else hwenv="USE_HW_ATTN=0"; fi
    for arm in $SMOKE_ARMS; do
      bin=$(arm_bin "$arm") || continue; [ -x "$bin" ] || continue
      out=$d/$arm; stops=0
      while :; do
      [ -s "$out.tokens" ] && { echo "$(ts) smoke $attn p$prompt $arm already done"; break; }
      wait_clear || { echo "$(ts) blocked while waiting; smoke gives up"; gaveup=1; break 4; }
      take_guard || { echo "$(ts) guard refused; smoke gives up"; gaveup=1; break 4; }
      status "smoke $attn p$prompt $arm"
      echo "### arm=$arm bin=$bin attn=$attn prompt=$prompt len=$LEN users=1 temperature=0 pay-for-determinism seed=1 $(ts) $(machine_line)" >>"$SM/smoke.txt"
      rm -f "$RES/smoke.STOPPED"; watch_run "$RES/smoke.STOPPED" "$OUR_RT_RE" "$HPFILE" & WPID=$!
      (cd "$(dirname "$(dirname "$bin")")" && { [ -z "${CAMPAIGN_LOCK_FD:-}" ] || exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv TRON_LOG_LEVEL=info \
          timeout -k 30 900 "$bin" stream-generate-text -m "$MODEL" $placement2 --hugepage_file "$HPFILE" -o \
          --prompt-length "$prompt" -l "$LEN" -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file "$out.tokens") >"$out.log" 2>&1
      rc=$?
      stop_watcher; campaign_guard_release; remove_our_hugepage_files "$HPFILE"
      echo "smoke $attn p$prompt $arm rc=$rc $(grep -E 'Version:|HW attention|average tok/s|Parsing the prompt took' "$out.log" | tr '\n' ' ' | cut -c1-300)" >>"$SM/smoke.txt"
      if [ -e "$RES/smoke.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ] || [ $rc -eq 124 ]; then
        echo "SMOKE-STOPPED arm=$arm rc=$rc $(cat "$RES/smoke.STOPPED" 2>/dev/null)" >>"$SM/smoke.txt"; rm -f "$out.tokens"
        stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "SMOKE-GIVEN-UP arm=$arm attn=$attn prompt=$prompt" >>"$SM/smoke.txt"; gaveup=1; break; }
        sleep 120; continue
      fi
      [ $rc -eq 0 ] && [ -s "$out.tokens" ] || { echo "SMOKE-FAILED arm=$arm attn=$attn prompt=$prompt rc=$rc (see $out.log)" >>"$SM/smoke.txt"; gaveup=1; }
      break
      done
    done
  done
done
python3 - "$SM" "$ATTNS" "$PROMPTS" "$SMOKE_ARMS" <<'PY' >>"$SM/smoke.txt" 2>&1
import os, re, sys
sm, attns, prompts, arms = sys.argv[1], sys.argv[2].split(), sys.argv[3].split(), sys.argv[4].split()
for attn in attns:
    for prompt in prompts:
        d = os.path.join(sm, f"{attn}-p{prompt}"); rows = {}
        for a in arms:
            p = os.path.join(d, a + ".tokens")
            if os.path.exists(p):
                lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
                if lines: rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
        print(f"== {attn} p{prompt}: token rows", {a: len(r) for a, r in rows.items()})
        def cmp(a, b):
            if a not in rows or b not in rows: return f"{a} vs {b}: missing"
            x, y = rows[a], rows[b]; n = min(len(x), len(y))
            first = next((i for i in range(n) if x[i] != y[i]), None)
            diff = sum(1 for i in range(n) if x[i] != y[i])
            return f"{a} vs {b}: " + ("IDENTICAL" if first is None and len(x) == len(y) else f"first difference at token {first}, {diff} of {n} differ")
        print(cmp("fix", "fix2")); print(cmp("fix", "vnni"))
PY
missing=0; for attn in $ATTNS; do for prompt in $PROMPTS; do for arm in $SMOKE_ARMS; do [ -s "$SM/$attn-p$prompt/$arm.tokens" ] || missing=$((missing + 1)); done; done; done
if [ $missing -eq 0 ] && [ $gaveup -eq 0 ]; then echo done >"$SM/smoke.done"; else echo "incomplete ($missing token rows missing, gaveup=$gaveup)" >"$SM/smoke.done"; fi
status "smoke finished: $(cat "$SM/smoke.done")"
echo "=== i4500fix smoke finished $(ts) ==="
