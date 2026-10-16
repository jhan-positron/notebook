set -u
trace() { printf '%s\n' "$*" >>"$TRACE_FILE"; }
say() { trace "$*"; }
status() { trace "$*"; }
ts() { echo 100000; }
now_s() { echo 0; }
in_list() { return 1; }
restart_engines() { trace restart_engines; return 0; }
run_pass() { trace "retry $1 succeeded"; LAST_COMPLETED=14; LAST_RUN_S=100; return 0; }
rm() { :; }
mv() { :; }
fails=0 incomplete= known_failed= stop_reason= problems=
DRIVER_END_BY=deadline zero_runs=0 need=6600 LAST_FAILED_CONFIGS=cell
RES=/tmp/local-fixture kind=full tmo=9000 cfg= IDLE_MIN_SWITCH=1
PASS_S=0 SW8K_S=0 DRIVER_KILLED=0
for tag in base-pass1; do
  rc=1
  [ $rc -eq 0 ] && continue
  fails=$((fails+1))
  if [ $rc -eq 124 ]; then status "$tag: the driver ran past its timeout (rc 124); no repeat, completed configs stay in perf.json raw records"; incomplete="$incomplete $tag"; continue; fi
  if [ $(( $(ts "$DRIVER_END_BY") - $(now_s) )) -lt "$need" ]; then stop_reason="no time for a repeat of $tag before DRIVER_END_BY"; incomplete="$incomplete $tag"; break; fi
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken"; incomplete="$incomplete $tag"; break; fi
  # restart the engines and repeat the run once, unless every failed cell is a known systematic failure (failed twice before)
  systematic=1
  if [ -z "$LAST_FAILED_CONFIGS" ]; then systematic=0; else for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$known_failed" || systematic=0; done; fi
  if [ $systematic = 1 ]; then status "$tag: the failed cells ($LAST_FAILED_CONFIGS) are known systematic failures; not repeating"; incomplete="$incomplete $tag"; continue; fi
  status "$tag: repeating the run once after an engine restart"
  # the first attempt's results directory is kept as <tag>-failed1 (an older copy of that name is removed; both names are
  # guarded with :? so an empty variable can never widen the removal)
  rm -rf "${RES:?}/${tag:?}-failed1"; mv "$RES/$tag" "$RES/$tag-failed1"
  first_failed=$LAST_FAILED_CONFIGS
  restart_engines "$IDLE_MIN_SWITCH" || say "WARNING: engine restart before the repeat failed"
  run_pass "$tag" "$cfg" "$tmo"; rc=$?
  if [ "$kind" = sw8k ]; then [ "$LAST_RUN_S" -gt "$SW8K_S" ] && SW8K_S=$LAST_RUN_S; else [ "$LAST_RUN_S" -gt "$PASS_S" ] && PASS_S=$LAST_RUN_S; fi
  if [ "$DRIVER_KILLED" = 1 ]; then stop_reason="driver killed by signal (rc $rc) during the repeat of $tag: operator stop"; break; fi
  if [ $rc -eq 9 ]; then stop_reason="CI lease became busy during the repeat of $tag (driver rc 9; stop safely)"; incomplete="$incomplete $tag"; break; fi
  if [ "$LAST_COMPLETED" -eq 0 ]; then zero_runs=$((zero_runs+1)); else zero_runs=0; fi
  if [ $rc -eq 0 ]; then say "$tag: repeat ok"; continue; fi
  if [ $rc -eq 8 ]; then stop_reason="engine environment wrong for the attention mode after provisioning in both runs of $tag (driver rc 8; stop safely)"; incomplete="$incomplete $tag"; break; fi
  status "$tag: failed twice (rc $rc); continuing with the next pass (gap reported)"; incomplete="$incomplete $tag"
  for c in $LAST_FAILED_CONFIGS; do in_list "$c" "$first_failed" && known_failed="$known_failed $c"; done   # systematic = failed in both runs
  if [ $zero_runs -ge 2 ]; then stop_reason="two consecutive driver runs completed 0 configs: the driver or the DUT is broken"; break; fi
done
if [ $fails -eq 0 ] && [ -z "$problems" ] && [ -z "$stop_reason" ]; then
 trace '.done'
else
 trace ".done-with-failures: fails=$fails incomplete=$incomplete stop_reason=$stop_reason problems=$problems"
fi
