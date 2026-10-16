#!/usr/bin/env bash
# Fixture test of the pr4-20261012 chain's exit handler (chain-finish.sh) with local stubs, never against the live
# machine (PR4-handoff.md step 6, edit 15 and edit 19; fork of exec/pr3-20261012/cleanup-test.sh). Six runs of a stub
# chain that sources chain-finish.sh:
#   1. normal completion after serving-down            -> serving-up logged before the marker release
#   2. `exit 1` after the serving-down line             -> the same
#   3. SIGTERM (to the process group) during a long step -> the same, and the long step is cut short
#   4. the lease stub says busy                          -> serving left alone, the marker still released
#   5. MARKER_CREATED=1 with the hand-off marker file present -> the file is gone after finish()
#   6. MARKER_CREATED=0 with a pre-existing hand-off marker file -> the file is still there after finish()
# Stubs: dut.sh and bill-share.sh are scripts that log their arguments; ci_lease_busy reads a flag file; rinzler_active
# says the units are down (the chain took serving down). Output: cleanup-test.log next to this script.
set -u
D=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d /tmp/pr4-cleanup-test.XXXXXX)
LOGF=$D/cleanup-test.log
: >"$LOGF"
cat >"$T/dut.sh" <<'EOF'
#!/usr/bin/env bash
echo "STUB dut.sh $*"
EOF
cat >"$T/bill-share.sh" <<'EOF'
#!/usr/bin/env bash
echo "STUB bill-share.sh $*"
EOF
chmod +x "$T/dut.sh" "$T/bill-share.sh"
cat >"$T/stub-chain.sh" <<EOF
#!/usr/bin/env bash
set -u
MODE=\${1:?mode}
DUT=$T/dut.sh
BILL_SHARE=$T/bill-share.sh
NAME=pr4-cleanup-test
HUGEPAGES_DIR=$T/hp
OUR_RT_RE='^(/nonexistent/runtron\.cleanuptest) '
ts() { date -u +%FT%TZ; }
machine() { echo "stub-machine lease=\$(ci_lease_busy 600 && echo busy || echo free)"; }
ci_lease_busy() { [ -e "$T/lease-busy" ]; }
rinzler_active() { return 1; }
MARKER_TAKEN=0
SERVING_DOWN_BY_US=0
MARKER=$T/handoff.marker
MARKER_CREATED=0
source $D/chain-finish.sh
trap 'finish term; exit 143' TERM
trap 'finish exit' EXIT
echo "\$(ts) stub chain \$MODE pid \$\$ pgid \$(ps -o pgid= -p \$\$ | tr -d ' ')"
case \$MODE in
  hm1) touch "\$MARKER" && MARKER_CREATED=1; echo "\$(ts) STUB hand-off marker created" ;;
  hm0) touch "\$MARKER"; echo "\$(ts) STUB hand-off marker pre-existing, not created by this run" ;;
esac
echo "\$(ts) STUB bill-share take"; MARKER_TAKEN=1
SERVING_DOWN_BY_US=1; echo "\$(ts) STUB serving-down"
case \$MODE in
  normal|hm1|hm0) echo "\$(ts) work done"; echo ok >"$T/chain.done" ;;
  exit1) echo "\$(ts) a step failed"; exit 1 ;;
  term) echo "\$(ts) long step begins (sleep 300)"; sleep 300; echo "\$(ts) long step ended normally (WRONG)" ;;
  busy) echo "\$(ts) work done"; echo ok >"$T/chain.done" ;;
esac
echo "\$(ts) stub chain \$MODE: normal end"
EOF
chmod +x "$T/stub-chain.sh"
mkdir -p "$T/hp"
check() {  # check <name> <logfile> <expect serving-up: yes|no> [<expect hand-off marker file after: present|absent>]
  local name=$1 f=$2 want=$3 hm=${4:-} up rel ok=yes
  up=$(grep -n 'STUB dut.sh serving-up' "$f" | head -1 | cut -d: -f1); rel=$(grep -n 'STUB bill-share.sh release' "$f" | head -1 | cut -d: -f1)
  if [ "$want" = yes ]; then [ -n "$up" ] && [ -n "$rel" ] && [ "$up" -lt "$rel" ] || ok=no; else [ -z "$up" ] && [ -n "$rel" ] || ok=no; fi
  grep -q 'finish: begin' "$f" || ok=no
  [ "$(grep -c 'finish: begin' "$f")" = 1 ] || ok=no   # the handler ran exactly once
  local hm_state=n/a
  if [ -n "$hm" ]; then
    hm_state=$([ -e "$T/handoff.marker" ] && echo present || echo absent)
    [ "$hm_state" = "$hm" ] || ok=no
  fi
  echo "RUN $name: serving-up line=${up:-none} release line=${rel:-none} expected serving-up=$want hand-off marker after=$hm_state (expected ${hm:-n/a}) -> $([ $ok = yes ] && echo PASS || echo FAIL)"
}
{
  echo "=== cleanup-test $(date -u +%FT%TZ) in $T ==="
  rm -f "$T/lease-busy" "$T/chain.done" "$T/handoff.marker"
  echo "--- run 1: normal completion ---"; bash "$T/stub-chain.sh" normal >"$T/run1.log" 2>&1; echo "rc=$?"; cat "$T/run1.log"; check 1 "$T/run1.log" yes
  echo "--- run 2: exit 1 after serving-down ---"; bash "$T/stub-chain.sh" exit1 >"$T/run2.log" 2>&1; echo "rc=$?"; cat "$T/run2.log"; check 2 "$T/run2.log" yes
  echo "--- run 3: SIGTERM to the process group during the long step ---"
  setsid bash "$T/stub-chain.sh" term >"$T/run3.log" 2>&1 &
  p=$!; sleep 3; kill -- -"$p"; wait "$p"; echo "rc=$? (143 expected)"; cat "$T/run3.log"; check 3 "$T/run3.log" yes
  grep -q 'WRONG' "$T/run3.log" && echo "RUN 3: the long step was NOT cut short -> FAIL"
  echo "--- run 4: the lease stub says busy ---"; touch "$T/lease-busy"; bash "$T/stub-chain.sh" busy >"$T/run4.log" 2>&1; echo "rc=$?"; cat "$T/run4.log"; check 4 "$T/run4.log" no
  rm -f "$T/lease-busy"
  echo "--- run 5: the hand-off marker created by this run (MARKER_CREATED=1) ---"; rm -f "$T/handoff.marker"; bash "$T/stub-chain.sh" hm1 >"$T/run5.log" 2>&1; echo "rc=$?"; cat "$T/run5.log"; check 5 "$T/run5.log" yes absent
  echo "--- run 6: a pre-existing hand-off marker (MARKER_CREATED=0) ---"; rm -f "$T/handoff.marker"; bash "$T/stub-chain.sh" hm0 >"$T/run6.log" 2>&1; echo "rc=$?"; cat "$T/run6.log"; check 6 "$T/run6.log" yes present
  rm -f "$T/handoff.marker"
  echo "=== verdict: $(grep -c ' -> PASS' "$LOGF" 2>/dev/null) PASS lines so far (6 expected; see RUN lines) ==="
} | tee -a "$LOGF"
n=$(grep -c ' -> PASS$' "$LOGF"); bad=$(grep -c 'FAIL' "$LOGF")
echo "cleanup-test: $n of 6 runs PASS, $bad FAIL lines" | tee -a "$LOGF"
rm -rf "$T"
[ "$n" = 6 ] && [ "$bad" = 0 ]
