#!/usr/bin/env bash
# bill-share.sh: the delphi-3bda sharing protocol agreed with Bill (Slack DM, 2026-09-15).
#
# Words used here: "first half" = instance 0 of 2 of the machine (tron's --instance 0,2), the
# half Bill uses; "second half" = instance 1 of 2, where jhan's harness always runs;
# "marker" = the file /bill-has-instance-0,2 on delphi-3bda.
#
# Rules:
#   marker present -> Bill's agent may use the first half.
#   marker absent  -> the whole machine is ours; Bill's agent stays off the first half.
#   Our second-half campaigns run either way; they never look at the marker.
#   "take" happens only on jhan's word, never from a campaign script.
#   "take" refuses while Bill is active, so jhan can ask him first. Activity is judged by
#   lib-guard.sh other_user_active restricted to the user bill (CPU time over a 10 s window
#   or a tron/build process of his; an idle shell does not count).
#   After our whole-machine work ends, WE re-create the marker with "release".
#
# Run on delphi-3bda (the marker and Bill's processes are there), for example:
#   ssh delphi-3bda bash ~/workspace/intel-AMX/exec/bill-share.sh status
# Commands: status | take | release. Every line is also appended to exec/logs/bill-share.log.
# Exit codes: 0 done, 1 sudo/file error, 2 take refused because Bill is active, 64 usage.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
MARKER=${BILL_MARKER:-/bill-has-instance-0,2}   # BILL_MARKER is a test hook only
LOG=${BILL_SHARE_LOG:-$EXEC/logs/bill-share.log}
source "$EXEC/lib-guard.sh"
ts() { date -u +%FT%TZ; }
say() { echo "$(ts) $(hostname) $*" | tee -a "$LOG"; }
bill_active() { GUARD_OTHER_USERS=bill GUARD_EXCLUDE_USERS="jhan nobody positron packer" other_user_active; }

case ${1:-status} in
  status)
    if [ -e "$MARKER" ]; then say "marker present: Bill may use the first half (instance 0,2)"
    else say "marker absent: the whole machine is ours"; fi
    if bill_active; then say "Bill is ACTIVE now (see the GUARD other-user line above)"
    else say "Bill is idle now"; fi
    ;;
  take)
    [ -e "$MARKER" ] || { say "take: marker already absent; the whole machine is ours"; exit 0; }
    if bill_active; then
      say "take REFUSED: Bill is active; marker left in place. Ask Bill before taking the machine."
      exit 2
    fi
    sudo -n rm -f "$MARKER" || { say "take FAILED: sudo -n rm $MARKER returned nonzero"; exit 1; }
    [ -e "$MARKER" ] && { say "take FAILED: $MARKER still exists"; exit 1; }
    say "take: removed $MARKER; the whole machine is ours, Bill's agent stays off the first half"
    ;;
  release)
    if [ -e "$MARKER" ]; then say "release: marker already present; Bill may use the first half"; exit 0; fi
    { sudo -n touch "$MARKER" && sudo -n chmod 644 "$MARKER"; } || { say "release FAILED: could not create $MARKER"; exit 1; }
    say "release: created $MARKER; Bill may use the first half again"
    ;;
  *)
    echo "usage: bill-share.sh status|take|release" >&2; exit 64
    ;;
esac
