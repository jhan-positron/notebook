#!/usr/bin/env bash
# vnnik4-models-20260915: handoff section 5, item 3 (run the other generated models once)
# plus one FPGA-attention check. Runs on OUR half of delphi-3bda (tp2 placement of
# vnnik2-20260915/campaign.sh: cards 90/93, socket 1), after verify.sh, with the same
# guards. Arms: base = runtron.p0perf13 (PR #3879, row-major K); new = runtron.vnnik4
# (the cleaned-up VNNIed-K head). For each cell a greedy smoke (1 user, prompt 1024,
# 128 tokens, temperature 0, pay-for-determinism, tokens saved) and one 8-user cell
# (prompt 1024, 256 tokens; TTFT + TPS lines kept).
#   fpga    ingested-qwen-3-4b-instruct-2507-tp2, USE_HW_ATTN unset (FPGA attention, the
#           nightly's default): the K rows reach the FPGA through page::get_k_row.
#   gptoss  ingested-gpt-oss-120b-tp2 (head 64: the VNNI layout is off, save_k_helper
#           returns at once): nothing may hang and the tokens must equal base's.
#   llama   ingested-llama-3.1-8b-tp2 (head 128, kv_mul 4, 32 layers): striped store on.
#   qwen30b ingested-qwen-3-30b-a3b-instruct-2507-tp2 (head 128, kv_mul 8): VNNI layout
#           on, AMX dense kernel not eligible (kv_mul != 4), so every page goes through
#           k_vnni::qk_group<8>.
# CPU attention (USE_HW_ATTN=0) in the three model cells. Never edit while running.
# Usage (on delphi-3bda): models.sh     [CELLS="fpga gptoss llama qwen30b"] [DO_RT=1]
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
export NAME=vnnik4-models-20260915 WT=/var/tmp/jhan/tron-vnnik4 SUFFIX=vnnik4
VNNIK2_FUNCTIONS_ONLY=1 source "$EXEC/vnnik2-20260915/campaign.sh"
CELLS=${CELLS:-"fpga gptoss llama qwen30b"}
DO_RT=${DO_RT:-1}
QWEN30=ingested-qwen-3-30b-a3b-instruct-2507-tp2
GPTOSS=ingested-gpt-oss-120b-tp2
LLAMA=ingested-llama-3.1-8b-tp2
cell_model() { case $1 in fpga) echo "$QWEN2" ;; gptoss) echo "$GPTOSS" ;; llama) echo "$LLAMA" ;; qwen30b) echo "$QWEN30" ;; esac; }
cell_hw() { case $1 in fpga) echo unset ;; *) echo 0 ;; esac; }   # USE_HW_ATTN
arm_bin2() { case $1 in base) echo "$RT_BASE" ;; new) echo "$RT_NEW" ;; esac; }

run_cell() {  # $1 cell  $2 arm  $3 kind (smoke|rt)
  local cell=$1 arm=$2 kind=$3 model bin hw out rc attempt stops=0 hwenv res tmo args
  model=$(cell_model "$cell"); bin=$(arm_bin2 "$arm"); hw=$(cell_hw "$cell")
  out=$RES/${kind}/${cell}__${arm}
  if [ "$kind" = smoke ]; then
    [ -s "$out.tokens" ] && { echo "$(ts) $kind $cell $arm already done"; return 0; }
    args="--prompt-length 1024 -l 128 -u 1 --temperature 0 --pay-for-determinism -s 1 --output-token-file $out.tokens"; tmo=900
  else
    grep -q "average tok/s" "$out.log" 2>/dev/null && { echo "$(ts) $kind $cell $arm already done"; return 0; }
    args="--prompt-length 1024 -l 256 -u 8"; tmo=1500
  fi
  if [ "$hw" = unset ]; then hwenv="-u USE_HW_ATTN"; else hwenv="USE_HW_ATTN=0"; fi
  attempt=$(ls "$out".attempt* 2>/dev/null | wc -l)
  while :; do
    attempt=$((attempt + 1))
    wait_clear; take_guard
    status "$kind $cell arm=$arm attempt=$attempt"
    echo "### $kind cell=$cell model=$model arm=$arm bin=$bin USE_HW_ATTN=$hw attempt=$attempt $args $(ts) $(machine_line)" >>"$RES/results.txt"
    rm -f "$RES/rt.STOPPED"; watch_run "$RES/rt.STOPPED" & WPID=$!
    (cd "$(dirname "$(dirname "$bin")")" && { [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-; } && env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE $hwenv TRON_LOG_LEVEL=info \
        timeout "$tmo" "$bin" stream-generate-text -m "$model" $(placement 2) --hugepage_file /dev/hugepages/amx-vnnik -o $args) >"$out.attempt$attempt" 2>&1
    rc=$?
    stop_watcher; campaign_guard_release; remove_our_slice_files
    res=$(grep -E "Version:|HW attention|Parsing the prompt took|average tok/s|Generated|error|Error|abort|Assert" "$out.attempt$attempt" 2>/dev/null | cut -c1-220 | head -20)
    if [ -e "$RES/rt.STOPPED" ] || [ $rc -eq 143 ] || [ $rc -eq 137 ]; then
      echo "RUN-STOPPED rc=$rc $(cat "$RES/rt.STOPPED" 2>/dev/null)" >>"$RES/results.txt"
      stops=$((stops + 1)); [ $stops -ge 3 ] && { echo "RUN-GIVEN-UP" >>"$RES/results.txt"; return 1; }
      sleep 120; continue
    fi
    cp "$out.attempt$attempt" "$out.log"
    { echo "rc=$rc"; echo "$res"; } >>"$RES/results.txt"
    if [ $rc -ne 0 ]; then echo "RUN-FAILED rc=$rc (full output: $out.attempt$attempt)" >>"$RES/results.txt"; return 1; fi
    [ "$kind" = smoke ] && [ ! -s "$out.tokens" ] && { echo "SMOKE-NO-TOKENS" >>"$RES/results.txt"; return 1; }
    return 0
  done
}

exec >>"$LOG" 2>&1
mkdir -p "$RES/smoke" "$RES/rt"
rm -f "$MARKER"
trap '[ -e "$MARKER" ] || finish aborted' EXIT
echo "=== $NAME started $(ts) pid $$ CELLS=[$CELLS] DO_RT=$DO_RT ==="
[ -x "$RT_NEW" ] && [ -x "$RT_BASE" ] || { echo "$(ts) binary missing: $RT_NEW / $RT_BASE"; finish no-binary; exit 1; }
TIP=$(git -C "$WT" rev-parse HEAD)
{ echo "# $NAME: extra generated models + FPGA attention; new tip $TIP (runtron.$SUFFIX); base 544ca05c7a (runtron.p0perf13); host $(hostname); $(ts)"
  echo "# placement tp2: $(placement 2)"; sha256sum "$RT_BASE" "$RT_NEW"; } >>"$RES/results.txt"
fails=0
for cell in $CELLS; do
  for arm in base new; do run_cell "$cell" "$arm" smoke || fails=$((fails + 1)); done
done
python3 - "$RES/smoke" <<'PY' >>"$RES/results.txt" 2>&1
import os, re, sys
d = sys.argv[1]
def toks(p):
    if not os.path.exists(p): return None
    lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
    return [int(x) for x in re.findall(r"-?\d+", lines[0])] if lines else None
print("# smoke token comparison (base vs new, 1 user greedy, 128 tokens)")
for cell in sorted({f.split("__")[0] for f in os.listdir(d) if f.endswith(".tokens")}):
    a, b = toks(f"{d}/{cell}__base.tokens"), toks(f"{d}/{cell}__new.tokens")
    if a is None or b is None: print(f"{cell}: missing tokens (base={a is not None}, new={b is not None})"); continue
    n = min(len(a), len(b)); first = next((i for i in range(n) if a[i] != b[i]), None)
    print(f"{cell}: identical for {n} tokens" if first is None else f"{cell}: first difference at generated token {first} of {n}; agreeing prefix {first}")
PY
if [ "$DO_RT" = 1 ]; then
  for cell in $CELLS; do
    for arm in base new; do run_cell "$cell" "$arm" rt || fails=$((fails + 1)); done
  done
fi
grep -E "^### rt|Parsing the prompt took|average tok/s" "$RES/results.txt" | sed -E 's/.*(cell=[a-z0-9]+).*(arm=[a-z]+).*/\1 \2/; s/.*(Parsing the prompt took [0-9.]+ s).*/  \1/; s/.*(average tok\/s[^]]*).*/  \1/' | tail -40 >"$RES/summary.txt"
remove_our_slice_files
echo "$([ $fails -eq 0 ] && echo ok || echo "ok-with-$fails-failed-runs")" >"$MARKER"
status "finished: $(cat "$MARKER")"
echo "=== $NAME finished $(ts): $(cat "$MARKER") ==="
