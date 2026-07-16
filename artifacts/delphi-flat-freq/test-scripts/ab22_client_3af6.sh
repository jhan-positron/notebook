#!/bin/bash
# ab22_client_3af6.sh — talos load-client daemon for the 2x2 second row.
# Watches /scratch/jhan/ab22/REQ_* markers (written by the 3bda
# orchestrator over NFS), runs benchmark_tps with nightly-parity params,
# writes results/<name>.json and DONE_<name>. Exits on ALL_DONE.
set -u
AB=/scratch/jhan/ab22
cd /scratch/jhan/p43/talos
export PYTHONPATH=/tmp/jhan-systest:/tmp/jhan-talos TOKENIZERS_PARALLELISM=false
export OPENAI_HOST=http://192.168.1.4/v1 OPENAI_TOKEN=dummy
export MODEL=ingested-gpt-oss-120b-tp4 TOKENIZER_MODEL=openai/gpt-oss-120b
export N_USERS=8 N_ROUNDS=10 PROMPT_LENGTH=1024 GENERATE_LENGTH=1536
export START_CAPTURE=896 END_CAPTURE=1024
log(){ echo "$(date -u '+%F %T') [client] $*" >> "$AB/journal.log"; }
log "client daemon armed (pid $$)"
END=$(( $(date +%s) + 12*3600 ))
while [ "$(date +%s)" -lt "$END" ]; do
  [ -f "$AB/ALL_DONE" ] && log "ALL_DONE seen — exiting" && exit 0
  REQ=$(ls "$AB"/REQ_* 2>/dev/null | head -1)
  if [ -n "$REQ" ]; then
    NAME=$(basename "$REQ" | sed "s/^REQ_//")
    SEED=$(grep -oE "[0-9]+" "$REQ" | head -1)
    rm -f "$REQ"
    log "running $NAME seed_offset=$SEED"
    SEED_OFFSET=$SEED TALOS_SESSION=$(./venv/bin/python -c "import uuid; print(uuid.uuid1())") \
    timeout 900 ./venv/bin/python -c "
import statistics as st, json
from testlib.tps import benchmark_tps, Config
r = benchmark_tps(Config(), raise_for_goal=False)
tt=r.ttfts; pt=r.prompt_tokens
pf=[p/(t/1000.0) for p,t in zip(pt,tt)]
out={'name':'$NAME','n':len(tt),'ttft_ms':round(st.mean(tt)),'prefill':round(st.mean(pf),1),
     'decode':round(st.mean(r.tpss),2),'cached':round(st.mean(r.cached_tokens),1),
     'ptok':round(st.mean(pt))}
print(json.dumps(out))
open('$AB/results/$NAME.json','w').write(json.dumps(out))
" >> "$AB/journal.log" 2>&1
    touch "$AB/DONE_$NAME"
    log "$NAME finished"
  fi
  sleep 10
done
log "client daemon 12h safety timeout — exiting"
