#!/usr/bin/env bash
# Historical check (codex C1): does the nearest preserved artifact, tron-amx/gen/runtron.inc1b
# (built 2026-08-19 00:22Z, sha 9e5df5dd), reproduce the archived 2026-08-18 token-30 flip with
# the archived t1-quick flags? Three runs: OFF, OFF, ON at ctx 2048, -l 256; compare green-chunk
# text against the archived logs and each other. Results: exec/results/dd/inc1b/.
set -u
EXEC=~/workspace/intel-AMX/exec; DD=$EXEC/dd; RES=$EXEC/results/dd/inc1b; D=/var/tmp/jhan/dd/inc1b
LOG=$EXEC/logs/dd-inc1b.log; MARKER=$EXEC/logs/dd-inc1b.done
mkdir -p "$RES" "$D"; exec >>"$LOG" 2>&1; rm -f "$MARKER"
stamp() { date -u +%FT%TZ; }
echo "=== inc1b check start $(stamp) ==="
source "$EXEC/lib-guard.sh"
if ci_lease_busy; then echo lease-busy >"$MARKER"; exit 1; fi
if rinzler_active; then echo rinzler-active >"$MARKER"; exit 1; fi
campaign_guard_acquire || { echo guard-refused >"$MARKER"; exit 1; }
trap 'campaign_guard_release; fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null || rm -f /dev/hugepages/slice-*-of-8' EXIT
cd ~/workspace/tron-amx
BIN=gen/runtron.inc1b
RT="$BIN stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2 --instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/dd --nr_hugepages 128 -o \
  --temperature 0 -s 42 --pay-for-determinism -u 1 --prompt-length 2048 -l 256"
{
echo "# inc1b historical check $(stamp)"; echo "binary: $(sha256sum $BIN)"; ls -la --time-style=long-iso $BIN
echo "qwen in model table: $(strings -n 8 $BIN | grep -c ingested-qwen-3-4b-instruct-2507)"
for arm in off1 off2 on1; do
  if ci_took_dut; then echo CI-TOOK-DUT; break; fi
  if [ $arm = on1 ]; then E="TRON_AMX_DISABLE=0"; else E="TRON_AMX_DISABLE=1"; fi
  echo "### $arm $(stamp)"; env USE_HW_ATTN=0 $E timeout 1800 $RT --output-token-file "$D/$arm.tok" >"$D/$arm.log" 2>&1; echo "  rc=$? $(stamp)"
  grep -E "Enqueueing prompt|HW attention" "$D/$arm.log" | head -2 | cut -c1-150
done
A=$EXEC/results/slot1/t1-quick
echo "## inc1b OFF vs OFF:";            python3 $DD/dd_tokens.py "$D/off1.log" "$D/off2.log" --json "$RES/off1-vs-off2.json" | grep -E '"identical"|first_diff|n_diff'
echo "## inc1b OFF vs archived OFF:";   python3 $DD/dd_tokens.py "$D/off1.log" "$A/off1-2048.log" --json "$RES/off1-vs-archived-off1.json" | grep -E '"identical"|first_diff|n_diff|at_first_diff'
echo "## inc1b ON vs archived ON:";     python3 $DD/dd_tokens.py "$D/on1.log" "$A/on1-2048.log" --json "$RES/on1-vs-archived-on1.json" | grep -E '"identical"|first_diff|n_diff|at_first_diff'
echo "## inc1b OFF vs inc1b ON:";       python3 $DD/dd_tokens.py "$D/off1.log" "$D/on1.log" --json "$RES/off1-vs-on1.json" | grep -E '"identical"|first_diff|n_diff|at_first_diff'
echo "## today's canonical debug build OFF (r1a) vs inc1b OFF:"; python3 $DD/dd_tokens.py /var/tmp/jhan/dd/r1a.log "$D/off1.log" --json "$RES/r1a-vs-inc1b-off1.json" | grep -E '"identical"|first_diff|n_diff'
cp "$D"/*.tok "$RES/" 2>/dev/null; echo "# done $(stamp)"
} >"$RES/inc1b.txt" 2>&1
echo ok >"$MARKER"; echo "=== inc1b check done $(stamp) ==="
