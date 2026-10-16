#!/usr/bin/env bash
# For jhan to run by hand (the auto-mode classifier refused the executor the gate change): accept the PR-4 chain's end
# verdict of 2026-10-13 00:17 UTC for campaign W and relaunch W. Why: the verdict "failed host=failed
# smoke=SMOKE-VERDICT differs/VALIDATE ok/ok/SMOKE-VERDICT differs/VALIDATE ok E=ok/ok bench=ok" differs from the known
# host-suite form only in the two smoke fields (the must-match pairs new:base at CPU p1024 and new:head at FPGA p1024,
# the token-identity finding recorded in split-status.md "PR-4 Step 6, run 2: the smokes"); every binary ran (rc 0, 256
# tokens), the cells and the bench passed, the host suite shows the known exception only. W compares the two Debian
# packages and does not depend on those pairs. Without this change campaign.sh's gate (line 460-463) aborts W tomorrow
# after the lease wait, before any machine change.
# What it does: (1) edits the gate of exec/pr4ci-20261012/campaign.sh so that the exact text in CHAIN_DONE_ACCEPT is
# also accepted (the knob is already declared at line 109; an empty knob changes nothing); (2) bash -n; (3) stops the
# sleeping W (pid 1098150; it has taken nothing: W_TOOK_MACHINE=0, W_TOOK_MARKER=0; its signal path releases only its
# own flock); (4) relaunches W with CHAIN_DONE_ACCEPT set to tonight's verdict and the same knobs as the 22:36 UTC launch.
# Run from claude-box before 2026-10-13 13:00 UTC:   ! bash ~/workspace/intel-AMX/exec/pr4ci-20261012/accept-verdict-and-relaunch.sh
set -u
H=/home/jhan/workspace/intel-AMX/exec/pr4ci-20261012
V='failed host=failed smoke=SMOKE-VERDICT differs/VALIDATE ok/ok/SMOKE-VERDICT differs/VALIDATE ok E=ok/ok bench=ok'
[ "$(ssh -o BatchMode=yes delphi-3bda cat /home/jhan/workspace/intel-AMX/exec/results/pr4-20261012/chain.done)" = "$V" ] || { echo "chain.done on 3bda is not the expected text; stop"; exit 1; }
python3 - "$H/campaign.sh" <<'PY' || exit 1
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = """  ok*|"failed host=failed smoke=ok/ok/ok E=ok/ok bench="*) status "chain end verdict '$v': W may run";;
  *) abort_early "the chain's end verdict is '$v': not ok and not the known host-suite exception" 5;;
esac
"""
new = """  ok*|"failed host=failed smoke=ok/ok/ok E=ok/ok bench="*) status "chain end verdict '$v': W may run";;
  *) if [ -n "$CHAIN_DONE_ACCEPT" ] && [ "$v" = "$CHAIN_DONE_ACCEPT" ]; then
       status "chain end verdict '$v' accepted by CHAIN_DONE_ACCEPT (jhan's decision of 2026-10-13): W may run"
     else
       abort_early "the chain's end verdict is '$v': not ok and not the known host-suite exception" 5
     fi;;
esac
"""
if s.count(new) == 1: print("gate already edited"); sys.exit(0)
assert s.count(old) == 1, "gate text not found exactly once"
p.write_text(s.replace(old, new)); print("gate edited")
PY
bash -n "$H/campaign.sh" || { echo "campaign.sh syntax error after the edit"; exit 1; }
grep -q '^CHAIN_DONE_ACCEPT=' "$H/campaign.sh" || { echo "the knob line is missing"; exit 1; }
pid=$(pgrep -f "^bash $H/campaign[.]sh" | head -1)
if [ -n "$pid" ]; then
  st=$(cat /home/jhan/workspace/intel-AMX/exec/results/pr4ci-20261012/.status 2>/dev/null)
  case $st in *"waiting: NOT_BEFORE"*|*"waiting: CI lease"*|*"waiting for the hand-off marker"*|*"pre-check marker"*) ;; *) echo "W (pid $pid) is not in a harmless wait (status: $st); not stopping it"; exit 1;; esac
  kill -TERM "$pid"; sleep 5; pgrep -f "^bash $H/campaign[.]sh" >/dev/null && { echo "W still running after TERM; stop"; exit 1; }
  echo "stopped the sleeping W (pid $pid)"
fi
cd /home/jhan/workspace/intel-AMX && CHAIN_DONE_ACCEPT="$V" EXPECTED_BASE=2026.10.12-72308ec9-jhan-pr4ci-base EXPECTED_BASE_SHA=5bc911725bf1688d5e83fc9674c97517c5482e7f26faa9872177d247ca423596 NEED_FLOOR_S=1800 NOT_BEFORE=2026-10-13T13:00:00Z DEADLINE_START=2026-10-13T19:00:00Z PASS_DEADLINE=2026-10-14T00:30:00Z DRIVER_END_BY=2026-10-14T02:05:00Z bash "$H/launch.sh"
