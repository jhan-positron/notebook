#!/usr/bin/env bash
# Launch the issue4500 campaign on delphi-3bda (nohup, detached). It waits by itself for: the CI lease,
# every rinzler@N unit inactive, and 256 free 1 GiB hugepages. It never touches other people's
# processes. To free our half the OPERATOR runs, on delphi-3bda, the recipe the l8bload campaign
# used today (only when the rinzler journal shows no request for 10 min):
#   sudo -n journalctl -u 'rinzler@*' --since '-10 min' --no-pager | grep -v '#EVT#' | grep -icE 'Parsing the prompt|response tokens|chat/completions|Request [0-9]+\]'   # must print 0
#   curl -s -m 60 -X POST http://localhost:8080/api/inference/down
#   sleep 20; systemctl is-active rinzler@0 rinzler@1 rinzler@2 rinzler@3
#   sudo -n rm -f /dev/hugepages/slice-*-of-8       # positron's slice files stay allocated until unlinked
#   grep HugePages_Free /proc/meminfo                # must be 512 (the campaign needs >= 256)
# The ci-runner-stop timer (02:45 UTC) brings production serving back up by itself for the nightly;
# to restore it earlier: curl -s -m 60 -X POST http://localhost:8080/api/inference/up
set -u
C=/home/jhan/workspace/intel-AMX/exec/issue4500-20260918
want=$(md5sum "$C/campaign.sh" | cut -c1-32)
have=$(ssh delphi-3bda "md5sum $C/campaign.sh | cut -c1-32")
[ "$want" = "$have" ] || { echo "NFS attribute cache: 3bda sees a different campaign.sh ($have vs $want); wait a minute and retry"; exit 1; }
ssh delphi-3bda "nohup env BLOCKS='${BLOCKS:-m1 m2 m3 m4 m1b}' REPS=${REPS:-3} REPS_B=${REPS_B:-2} bash $C/campaign.sh >/dev/null 2>&1 &"
sleep 3
ssh delphi-3bda "pgrep -fa 'issue4500-20260918/campaign[.]sh' | head -3; cat /home/jhan/workspace/intel-AMX/exec/logs/issue4500-20260918.status 2>/dev/null"
