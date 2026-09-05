#!/usr/bin/env bash
# One cell = one model x one arm: start rinzler, run functional -> perf ->
# (optional) MMLU Pro with the systems_test code, stop rinzler.
# usage: run_cell.sh MODEL ARM TP RUN_MMLU(0|1) [TAG]   (TAG = suffix for a repeat cell, e.g. rep2)
set -u
MODEL=$1 ARM=$2 TP=$3 RUN_MMLU=$4 TAG=${5:-}
H=~/workspace/intel-AMX/exec/more-testing-r1
RES=~/workspace/intel-AMX/exec/results/more-testing-r1
ST=~/workspace/ai-runs/systems_test
PY=/var/tmp/jhan/st-venv/bin/python
PORT=13100
CELL=$RES/cells/${MODEL}__${ARM}${TAG:+__$TAG}
mkdir -p "$CELL/work"
ln -sfn "$ST/golden_responses" "$CELL/work/golden_responses"
ln -sfn "$ST/wordlist.txt" "$CELL/work/wordlist.txt"
source "$H/rz.sh"
export HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false
export OPENAI_HOST=http://delphi-3bda:$PORT/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080
echo running >"$CELL/STATUS"
python3 - "$CELL/meta.json" "$MODEL" "$ARM" "$TP" "$RUN_MMLU" <<'PY'
import json, sys, subprocess, datetime, os
p, model, arm, tp, mmlu = sys.argv[1:6]
tron = os.path.expanduser('~/workspace/tron-amx')
binf = f"{tron}/gen/rinzler.{'mirror' if arm == 'mirror' else 'canon'}"
sha = subprocess.run(['sha256sum', binf], capture_output=True, text=True).stdout.split()[0]
head = subprocess.run(['git', '-C', tron, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
json.dump({"model": model, "arm": arm, "tp": int(tp), "run_mmlu": mmlu == '1', "binary": os.path.basename(binf), "binary_sha256": sha,
           "tron_head": head, "started": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), "port": 13100,
           "env": {"USE_HW_ATTN": "0", "TRON_AMX_DISABLE": "1" if arm == 'off' else "(unset)", "TRON_USE_SPECULATION": "0"},
           "phases": {}}, open(p, 'w'), indent=1)
PY
phase_stamp() {  # $1 phase $2 rc $3 seconds
  python3 - "$CELL/meta.json" "$1" "$2" "$3" <<'PY'
import json, sys
p, ph, rc, secs = sys.argv[1:5]
d = json.load(open(p)); d["phases"][ph] = {"rc": int(rc), "seconds": int(secs)}; json.dump(d, open(p, 'w'), indent=1)
PY
}
cleanup() { rz_stop; }
trap cleanup EXIT

t0=$(date +%s)
if ! rz_start "$ARM" "$PORT" "$TP" "$CELL/rinzler.log" "$MODEL"; then
  phase_stamp start 1 $(( $(date +%s) - t0 )); echo start-failed >"$CELL/STATUS"; exit 1
fi
phase_stamp start 0 $(( $(date +%s) - t0 ))

# functional: system_ci's invocation (pytest on functional_tests/) against
# the one model the server lists. The two auth-rejection tests check the
# platformd proxy's token handling (401/403); there is no proxy in front of
# our rinzler, so they are deselected exactly as system_ci deselects them for
# every model group after the first (scripts/system_ci.py:331-365).
t0=$(date +%s)
( cd "$CELL/work" && env PYTHONPATH="$ST" timeout 2400 "$PY" -m pytest "$ST/functional_tests" -q -p no:cacheprovider \
    --deselect "$ST/functional_tests/test_api.py::test_auth_reject_no_token" \
    --deselect "$ST/functional_tests/test_api.py::test_auth_reject_bad_token" \
    --junitxml="$CELL/functional.xml" >"$CELL/functional.log" 2>&1 )
rc=$?; phase_stamp functional $rc $(( $(date +%s) - t0 )); echo "functional rc=$rc"

# perf: scripts/perf.py's config for this model through testlib.tps.benchmark_tps
t0=$(date +%s)
( cd "$CELL/work" && env PYTHONPATH="$H/talos_stub:$ST" timeout 3000 "$PY" "$H/st_perf.py" --model "$MODEL" --out "$CELL/perf.json" >"$CELL/perf.log" 2>&1 )
rc=$?; phase_stamp perf $rc $(( $(date +%s) - t0 )); echo "perf rc=$rc"

# MMLU Pro: detached runner, chat style, coverage 10 (CI's setting). Request
# timeout raised from CI's 60 s to 180 s because one engine serves all 8
# parallel questions here (CI spreads them over 2-4 engines).
if [ "$RUN_MMLU" = 1 ]; then
  t0=$(date +%s)
  ( cd "$CELL/work" && rm -rf eval_results mmlu_output && env PYTHONPATH="$ST" SKIP_PROVISION=1 MMLU_MODEL="$MODEL" MMLU_COVERAGE=10 \
      MMLU_REQUEST_TIMEOUT_SECONDS=180 timeout 6000 "$PY" -c "from scripts.mmlu_cli import main_chat; main_chat()" >"$CELL/mmlu.log" 2>&1 )
  rc=$?; phase_stamp mmlu $rc $(( $(date +%s) - t0 )); echo "mmlu rc=$rc"
  rm -rf "$CELL/eval_results"; mv "$CELL/work/eval_results" "$CELL/eval_results" 2>/dev/null
  rm -rf "$CELL/mmlu_output"; mv "$CELL/work/mmlu_output" "$CELL/mmlu_output" 2>/dev/null
fi
rz_stop
trap - EXIT
grep -E "HW attention|K mirror|AMX|amx" "$CELL/rinzler.log" | head -20 >"$CELL/rinzler-amx-lines.txt"
python3 - "$CELL/meta.json" <<'PY'
import json, sys, datetime
p = sys.argv[1]; d = json.load(open(p)); d["ended"] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'); json.dump(d, open(p, 'w'), indent=1)
PY
echo done >"$CELL/STATUS"
