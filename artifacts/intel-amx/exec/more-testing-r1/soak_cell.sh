#!/usr/bin/env bash
# Soak cell: one rinzler (mirror arm, tp2) serving two AMX-eligible models,
# scripts/soak.py traffic for MINUTES minutes with NUM_USERS users.
# usage: soak_cell.sh ARM MINUTES USERS [TAG]
set -u
ARM=$1 MINUTES=$2 USERS=$3 TAG=${4:-}
H=~/workspace/intel-AMX/exec/more-testing-r1
RES=~/workspace/intel-AMX/exec/results/more-testing-r1
ST=~/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
PORT=13100
MODELS=(llama-3.1-8b-instruct-good-tp2 ingested-qwen-3-4b-instruct-2507-tp2)
CELL=$RES/soak${TAG:+__$TAG}
mkdir -p "$CELL/work"
source "$H/rz.sh"
export HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false
export OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080
echo running >"$CELL/STATUS"
echo "{\"arm\": \"$ARM\", \"models\": [\"${MODELS[0]}\", \"${MODELS[1]}\"], \"minutes\": $MINUTES, \"users\": $USERS, \"started\": \"$(date -u +%FT%TZ)\"}" >"$CELL/meta.json"
cleanup() { rz_stop; }
trap cleanup EXIT
if ! rz_start "$ARM" "$PORT" 2 "$CELL/rinzler.log" "${MODELS[@]}"; then echo start-failed >"$CELL/STATUS"; exit 1; fi
# SSH_USER/SSH_PASS: the DUT monitor logs into the DUT over ssh; we use
# jhan's key (an empty password is never sent before public-key auth).
( cd "$CELL/work" && env PYTHONPATH="$H/talos_stub:$ST" NUM_USERS="$USERS" MAX_DURATION="$MINUTES" SSH_USER=jhan SSH_PASS= \
    timeout $(( MINUTES * 60 + 1500 )) "$PY" -m scripts.soak >"$CELL/soak.log" 2>&1 )
rc=$?; echo "soak rc=$rc"
rz_stop
trap - EXIT
python3 - "$CELL/meta.json" "$rc" <<'PY'
import json, sys, datetime
p, rc = sys.argv[1:3]; d = json.load(open(p)); d["ended"] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'); d["rc"] = int(rc); json.dump(d, open(p, 'w'), indent=1)
PY
echo done >"$CELL/STATUS"
