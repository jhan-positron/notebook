#!/usr/bin/env bash
# Detached launcher for campaign W of PR-4 (pr4ci-20261012) on the client host (forked 2026-10-12 from
# exec/pr4424ci-20261009/launch.sh, itself from exec/q4b-fpga-20260921/launch.sh).
# It syncs nothing: it VALIDATES (syntax, compile, the DUT sees the same files over NFS, the two deb builds and the saved
# base deb exist on the DUT with the expected version and rinzler sha, the chain's our-half verdict all.done = ok (the
# fork's gate), platformd 0.11, the check mode ran after the last driver edit, no peer campaign, knob sanity) and then
# starts campaign.sh detached with setsid + nohup. Bill's marker is taken by campaign.sh itself right before its
# preflight (after the NOT_BEFORE, lease, hand-off marker, chain.done gate, runtron and flock waits).
# usage: EXPECTED_BASE=<base deb Version> EXPECTED_BASE_SHA=<its rinzler sha256> [NEED_FLOOR_S=1800] [NOT_BEFORE=...]
#        [DEADLINE_START=...] [PASS_DEADLINE=...] [DRIVER_END_BY=...] [PASSES="base target target base"] [PASS_TAGS="..."]
#        [FULL_CONFIGS=<json>] [SW8K=0|1] [DRIVER_TIMEOUT=s] [SW8K_TIMEOUT=s] [AMX_PROBE=1|0] bash launch.sh
# Scope (jhan, 2026-10-12): FULL_CONFIGS defaults to $H/subset3.json (three configs: llama-3.1-8b tp2 at 8u/1024 and
# 32u/4096, gpt-oss-120b tp4 at 8u/1024) and SW8K defaults to 0 (no sw8k cell): four tags base-pass1 target-pass1
# target-pass2 base-pass2. NEED_FLOOR_S is the floor of campaign.sh's need rule (default 6600 s; pass 1800 for this scope).
# EXPECTED_BASE and EXPECTED_BASE_SHA are REQUIRED (no default; the values are in $OUT/manifest-base.json on the DUT).
# Every knob is inherited by campaign.sh through the environment (see its header). Prints the pid and the log path.
set -u
H=/home/jhan/workspace/intel-AMX/exec/pr4ci-20261012
RESD=/home/jhan/workspace/intel-AMX/exec/results/pr4ci-20261012
LOG=/home/jhan/workspace/intel-AMX/exec/logs/pr4ci-20261012.log
ST=/home/jhan/workspace/ai-runs/systems_test
OUT=/var/tmp/jhan/pr4ci-20261012
CHAIN_RES=/home/jhan/workspace/intel-AMX/exec/results/pr4-20261012   # the PR-4 chain's results folder (all.done, chain.done)
SSH="ssh -o BatchMode=yes -o ConnectTimeout=20 delphi-3bda"
mkdir -p "$(dirname "$LOG")"
if pgrep -f "^bash $H/campaign[.]sh" >/dev/null; then echo "campaign.sh already running: $(pgrep -af "^bash $H/campaign[.]sh")"; exit 1; fi
for f in dut.sh st_ci_perf.py talos_stub/talos.py sw8k.json campaign.sh summarize.py ../lib-guard.sh ../bill-share.sh; do
  want=$(md5sum "$H/$f" | cut -c1-32); have=$($SSH "md5sum $H/$f 2>/dev/null | cut -c1-32")
  [ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different $f ($have vs $want); wait a minute and retry"; exit 1; }
done
"$ST/.venv/bin/python" -m py_compile "$H/st_ci_perf.py" "$H/summarize.py" "$H/configs.py" || { echo "a python file does not compile"; exit 1; }
bash -n "$H/campaign.sh" && bash -n "$H/dut.sh" && bash -n "$H/build-deb.sh" || { echo "a bash file has a syntax error"; exit 1; }
FULL_CONFIGS=${FULL_CONFIGS-$H/subset3.json}; export FULL_CONFIGS   # unset = the three-config scope; "" = the harness's own list; campaign.sh reads the same variable
[ -z "$FULL_CONFIGS" ] || [ -s "$FULL_CONFIGS" ] || { echo "FULL_CONFIGS=$FULL_CONFIGS is not a readable file"; exit 1; }
[ -z "$FULL_CONFIGS" ] || "$ST/.venv/bin/python" -c 'import json,sys; l=json.load(open(sys.argv[1])); assert isinstance(l, list) and l, "not a non-empty list"; print("FULL_CONFIGS cells:", [(c["model"], c["nominal_users"], c["prompt_length"]) for c in l])' "$FULL_CONFIGS" || { echo "FULL_CONFIGS=$FULL_CONFIGS does not parse as a configs list"; exit 1; }
CHK=$RESD/check-mode/perf.json
[ -f "$CHK" ] && [ ! "$H/st_ci_perf.py" -nt "$CHK" ] || { echo "st_ci_perf.py is newer than the last CI_MIMIC_CHECK=1 run ($CHK); re-run the check mode first (see README)"; exit 1; }
[ "$(git -C "$ST" rev-parse --short HEAD 2>/dev/null)" = "$(git -C "$ST" rev-parse --short origin/main 2>/dev/null)" ] || echo "NOTE: the harness checkout $ST is not at origin/main (HEAD $(git -C "$ST" rev-parse --short HEAD), origin/main $(git -C "$ST" rev-parse --short origin/main)); the driver follows the checkout"
[ -z "$(git -C "$ST" status --short -- scripts testlib 2>/dev/null)" ] || { echo "the harness checkout has local changes under scripts/ or testlib/ (fidelity with the nightly needs a clean checkout):"; git -C "$ST" status --short -- scripts testlib; exit 1; }
$SSH "dpkg-query -W -f='\${Version}' platformd" | grep -q '^0\.11' || { echo "platformd on 3bda is not 0.11.x (the harness's explicit provisioning path is what this campaign was checked against)"; exit 1; }
st=$($SSH "cat $OUT/build.status 2>/dev/null"); [ "$st" = ok ] || { echo "target build status on 3bda is '$st', not ok (the chain's step deb runs ARM=target build-deb.sh COMMIT on delphi-3bda)"; exit 1; }
$SSH "test -s $OUT/target.deb && test -s $OUT/rinzler.target && test -s $OUT/manifest.json" || { echo "target.deb, rinzler.target or manifest.json missing in $OUT on 3bda"; exit 1; }
bst=$($SSH "cat $OUT/build-base.status 2>/dev/null"); [ "$bst" = ok ] || { echo "base build status on 3bda is '$bst', not ok (the chain's step deb runs ARM=base build-deb.sh MAIN_COMMIT on delphi-3bda)"; exit 1; }
# the base arm's identity is REQUIRED (no default in this fork): the Version field and the rinzler sha256 of base.deb ($OUT/manifest-base.json)
[ -n "${EXPECTED_BASE:-}" ] && [ -n "${EXPECTED_BASE_SHA:-}" ] || { echo "EXPECTED_BASE and EXPECTED_BASE_SHA must both be set (the base deb's Version field and its rinzler sha256, from $OUT/manifest-base.json on 3bda); there is no default"; exit 1; }
nv=$($SSH "dpkg-deb -f $OUT/nightly.deb Version 2>/dev/null"); [ "$nv" = "$EXPECTED_BASE" ] || { echo "saved nightly.deb (base arm) on 3bda has version '$nv', expected EXPECTED_BASE=$EXPECTED_BASE"; exit 1; }
bsha=$($SSH "sha256sum $OUT/rinzler.base 2>/dev/null | cut -d' ' -f1"); [ "$bsha" = "$EXPECTED_BASE_SHA" ] || { echo "rinzler.base on 3bda has sha256 '$bsha', expected EXPECTED_BASE_SHA=$EXPECTED_BASE_SHA"; exit 1; }
# the chain's our-half verdict (the fork's gate): read on 3bda, where the chain wrote it (claude-box's NFS attribute cache could serve a stale copy)
[ "$(timeout 60 $SSH "cat $CHAIN_RES/all.done 2>/dev/null")" = ok ] || { echo "the chain's our-half verdict ($CHAIN_RES/all.done on 3bda) is not ok: not launching W"; exit 1; }
# peer gate: no runtron/rinzler process of ours may run on the DUT
if $SSH "pgrep -u jhan -f '[r]inzler --model|[r]untron[. ]' >/dev/null"; then echo "peer processes (runtron/rinzler) run on the DUT as jhan; not launching"; $SSH "pgrep -u jhan -af '[r]inzler --model|[r]untron[. ]'"; exit 1; fi
# knob sanity: every date knob must parse, the deadlines must be ordered, a launch far ahead of its window needs NOT_BEFORE
for v in NOT_BEFORE DEADLINE_START PASS_DEADLINE DRIVER_END_BY; do
  [ -z "${!v:-}" ] && continue
  date -u -d "${!v}" +%s >/dev/null 2>&1 || { echo "knob $v='${!v}' is not a date that 'date -u -d' accepts (use 2026-10-09T13:00:00Z)"; exit 1; }
done
NB=${NOT_BEFORE:-2026-10-13T13:05:00Z}; DS=${DEADLINE_START:-2026-10-14T01:35:00Z}; PD=${PASS_DEADLINE:-2026-10-14T01:40:00Z}; DE=${DRIVER_END_BY:-2026-10-14T02:05:00Z}   # option (a) defaults; campaign.sh carries the same
[ "$(date -u -d "$DS" +%s)" -lt "$(date -u -d "$PD" +%s)" ] && [ "$(date -u -d "$PD" +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "deadline order wrong: need DEADLINE_START ($DS) < PASS_DEADLINE ($PD) < DRIVER_END_BY ($DE)"; exit 1; }
[ "$(date -u -d "$NB" +%s)" -lt "$(date -u -d "$DS" +%s)" ] || { echo "NOT_BEFORE ($NB) must be before DEADLINE_START ($DS)"; exit 1; }
[ "$(date -u +%s)" -lt "$(date -u -d "$DE" +%s)" ] || { echo "DRIVER_END_BY ($DE) is already past"; exit 1; }
setsid nohup bash "$H/campaign.sh" >>"$LOG" 2>&1 </dev/null &
echo "launched pid $! log $LOG (knobs: NOT_BEFORE=$NB DEADLINE_START=$DS PASS_DEADLINE=$PD DRIVER_END_BY=$DE EXPECTED_BASE=$EXPECTED_BASE FULL_CONFIGS=${FULL_CONFIGS:-harness-list} SW8K=${SW8K:-0} NEED_FLOOR_S=${NEED_FLOOR_S:-6600} PASSES=${PASSES:-default} PASS_TAGS=${PASS_TAGS:-none} DRIVER_TIMEOUT=${DRIVER_TIMEOUT:-default} SW8K_TIMEOUT=${SW8K_TIMEOUT:-default})"
