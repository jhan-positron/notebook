#!/bin/bash
export LC_ALL=C PAGER=cat
sec() { printf '\n=== %s ===\n' "$1"; }
B=~/positron
sec churn_r1_job_log; head -70 $B/runs/churn-r1/job.log 2>&1 | cut -c1-300
sec churn_r1_log_txt; cat $B/runs/churn-r1/log.txt 2>&1 | cut -c1-300
sec rejudge_summary
python3 - <<'PY'
import json
d=json.load(open('/home/positron-perf/positron/check/r1/latency.rejudge.json'))
print("top-level keys:", list(d.keys()))
for k in ('mode','problems','registration','requests','schema','verdict','result','summary','gated','isolation'):
    if k in d: print(k, "=", json.dumps(d[k])[:900])
t=d.get('targets',{})
print("targets:", list(t.keys()))
for name,v in t.items():
    print(f"  {name}: gated={v.get('gated')} excluded={v.get('excluded')} findings={json.dumps(v.get('findings'))[:300]} infra={json.dumps(v.get('infra'))[:200]}")
PY
sec record_latency_dir; ls -la $B/runs/churn-r1/record/latency 2>&1 | head -20; ls -la $B/runs/churn-r1/record/churn 2>&1 | head -12
for f in $(ls $B/runs/churn-r1/record/latency/*.json $B/runs/churn-r1/record/latency/*.txt $B/runs/churn-r1/record/latency/*.log 2>/dev/null | head -3); do echo "## $f"; head -c 1200 "$f"; echo; done
sec fixture_dense_log; cat $B/check/r1/fixture-dense.log 2>&1 | cut -c1-300
sec hiccup_c_header; head -40 $B/runs/hiccup.c | cut -c1-200
sec isol_py_header; head -45 $B/runs/isol.py | cut -c1-200
sec lag_scripts; head -20 $B/runs/lag3.py | cut -c1-200; echo ...; head -12 $B/runs/samples.py | cut -c1-200
sec freq_files; for f in $B/runs/hiccup/freq.*.txt $B/runs/logits-bench/freq.*.txt; do echo "$f: $(cat $f)"; done
sec isol_before_summary
python3 - <<'PY'
import json
d=json.load(open('/home/positron-perf/positron/runs/churn-r1/isol.before.json'))
print("keys:", list(d.keys())[:40])
for k,v in d.items():
    s=json.dumps(v); print(f"{k}: {s[:260]}")
PY
sec git_state; git -C $B/src/phoenix-int remote -v 2>&1 | head -2; git -C $B/src/phoenix-int log -1 --format='%h %cd %an %s' --date=iso 2>&1 | cut -c1-200; git -C $B/src/phoenix-int status --porcelain 2>&1 | wc -l
sec run_scheduled_gate; ls $B/src/phoenix-int/tools/ci/ 2>&1 | head -30; grep -nE 'churn|latency|isolcpus|nohz|taskset|sched_setaffinity|pin|SCHED_FIFO|chrt|mlock' $B/src/phoenix-int/tools/ci/run_scheduled_gate.sh 2>&1 | head -30 | cut -c1-220
sec churn_py_pinning; f=$(find $B/src/phoenix-int -name 'churn.py' | head -1); echo "$f"; grep -nE 'affinity|taskset|pass thread|pass_thread|127|isol|nohz|SCHED_|chrt|mlock|governor' "$f" 2>&1 | head -30 | cut -c1-220
sec latency_docs; ls $B/src/phoenix-int/docs | head -40; grep -rlE 'isolcpus|nohz_full' $B/src/phoenix-int/docs $B/src/phoenix-int/tools 2>/dev/null | head -10
sec end; date -u; echo DONE
