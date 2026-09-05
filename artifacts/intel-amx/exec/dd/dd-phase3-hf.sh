#!/usr/bin/env bash
# Phase 3, interactive part (run on delphi-3bda AFTER dd-campaign.sh, inside the CI window):
#   dd-phase3-hf.sh r8    # HF fp32 logits for prompt + OFF continuation (arbiter); prompt ids come
#                         # from the campaign's own R1c id file ($D/prompt.ids) - tron and HF share ids
#   dd-phase3-hf.sh r9    # t_amx_logit_ab OFF/ON on prompt ids + 64 forced ids -> dd_bin_score
# R9 is a supplement only: t_amx_logit_ab feeds the prompt one token at a time through a default
# system config, so its attention plan differs from runtron's; its logits are bf16 like runtron's.
set -u
EXEC=~/workspace/intel-AMX/exec; DD=$EXEC/dd; RES=$EXEC/results/dd; D=/var/tmp/jhan/dd
WT=~/workspace/ai-runs/tron-dd
HF=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/* | head -1)
export USE_HW_ATTN=0
source "$EXEC/lib-guard.sh"
cd "$WT"
case "${1:-}" in
r8)
  # Text for HF = prompt text + decoded OFF continuation (30 steps). Tokenization must reproduce
  # prompt.ids + forced ids; the check below decides whether the arbiter is usable at step 30.
  [ -f "$D/prompt.ids" ] || { echo "no $D/prompt.ids (campaign R1c not done)"; exit 1; }
  NSTEP=${2:-30}
  python3 - "$D/prompt.ids" "$D/forced.tok" "$NSTEP" > "$D/r8-expected.ids" <<'PY'
import sys
p=[int(x) for x in open(sys.argv[1]).read().split()]; f=[int(x) for x in open(sys.argv[2]).read().split()][:int(sys.argv[3])]
print(' '.join(map(str,p+f)))
PY
  nix develop --command bash -c "
    python3 bin/tokenize_py -n '$HF' -d \"\$(python3 -c 'import json;print(json.dumps([int(x) for x in open(\"$D/r8-expected.ids\").read().split()]))')\" > '$D/r8-text.json' &&
    python3 -c 'import json;open(\"$D/r8-text.txt\",\"w\").write(json.loads(open(\"$D/r8-text.json\").read().strip()))' &&
    python3 bin/tokenize_py -n '$HF' -f '$D/r8-text.txt' > '$D/r8-retok.json'" || { echo tokenizer-step-failed; exit 1; }
  python3 - "$D/r8-expected.ids" "$D/r8-retok.json" <<'PY'
import json,sys
exp=[int(x) for x in open(sys.argv[1]).read().split()]; got=json.loads(open(sys.argv[2]).read().strip())
same=exp==got; print("round-trip ids identical:", same, "len", len(exp), len(got))
if not same:
    i=next((k for k in range(min(len(exp),len(got))) if exp[k]!=got[k]), min(len(exp),len(got))); print("first differing position", i)
PY
  mkdir -p "$D/hf"
  # HF forward with ALL layers; --max-tokens = exactly the expected length; no BOS (Qwen3 has none anyway).
  N=$(wc -w <"$D/r8-expected.ids")
  ./bin/extract_logits --model "$HF" --text-file "$D/r8-text.txt" --max-tokens "$N" --max-layers 36 --save-tokens \
      --scratch-dir "$D/hf" 2>&1 | tee "$RES/hf-r8.log" | tail -5
  TOK=$(grep -oP 'Saved tokens to: \K\S+' "$RES/hf-r8.log" | tail -1); LOG=$(grep -oP 'Saved logits to: \K\S+' "$RES/hf-r8.log" | tail -1)
  echo "HF tokens file: $TOK"; echo "HF logits file: $LOG"
  python3 - "$TOK" "$D/r8-expected.ids" <<'PY'
import struct,sys
b=open(sys.argv[1],'rb').read(); (n,)=struct.unpack('<Q',b[:8]); ids=list(struct.unpack(f'<{n}I',b[8:8+4*n]))
exp=[int(x) for x in open(sys.argv[2]).read().split()]
print("HF saved ids == expected:", ids==exp, n, len(exp))
PY
  echo "$LOG" > "$D/r8-logits.path"
  ;;
r9)
  [ -f "$D/prompt.ids" ] || { echo "no $D/prompt.ids"; exit 1; }
  python3 - "$D/prompt.ids" "$D/forced.tok" "$D/amx_tokens.bin" <<'PY'
import struct,sys
ids=[int(x) for x in open(sys.argv[1]).read().split()]
forced=[int(x) for x in open(sys.argv[2]).read().split()][:64]
assert len(forced)==64, f"need 64 forced ids, have {len(forced)}"
if 1 in forced: print("WARNING: token id 1 among forced ids; force_generate treats id 1 as a stop token -> shorter dump")
allids=ids+forced
open(sys.argv[3],'wb').write(struct.pack('<Q',len(allids))+struct.pack(f'<{len(allids)}I',*allids))
print("AMX_TOKENS:", len(allids), "= prompt", len(ids), "+ forced 64 -> force_generate prompt =", len(allids)-64)
PY
  campaign_guard_acquire || exit 1
  trap campaign_guard_release EXIT
  # test binaries take the system config from SYSTEM_CONFIG (same instance/cores/hugepages as runtron)
  export SYSTEM_CONFIG="--instance 0,4 --devices 10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/dd --nr_hugepages 128"
  for arm in off on; do
    if [ $arm = off ]; then E="TRON_AMX_DISABLE=1"; else E="TRON_AMX_DISABLE=0"; fi
    env $E AMX_LOGIT_OUT="$D/r9-$arm.bin" AMX_MODEL=ingested-qwen-3-4b-instruct-2507-tp2 AMX_TOKENS="$D/amx_tokens.bin" \
      timeout 2400 ./gen/t_amx_logit_ab >"$D/r9-$arm.log" 2>&1; echo "r9-$arm rc=$?"; grep -E "AMX-DEBUG|passed|failed" "$D/r9-$arm.log" | tail -3
  done
  python3 "$DD/dd_bin_score.py" "$D/r9-off.bin" "$D/r9-on.bin" --last 64 --out "$RES/r9-score.json" | tee "$RES/r9-score.txt"
  fuser -s /dev/hugepages/slice-*-of-8 2>/dev/null || rm -f /dev/hugepages/slice-*-of-8
  ;;
*) echo "usage: $0 r8 [nsteps] | r9"; exit 2;;
esac
