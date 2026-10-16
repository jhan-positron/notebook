#!/usr/bin/env bash
# Launch probe-fix.sh detached on delphi-3bda from claude-box (fork of exec/pr4-20261012/launch-probe.sh). The driver builds
# and unit-tests the fix on our half, then takes Bill's marker (bill-share.sh take) and production serving down for the cells:
# that whole-machine part runs on jhan's order (2026-10-15: "Work on Issue 4934 ... make sure ... should not lower perf").
# Before launching it checks that the commit and its new text are visible on 3bda through NFS (attribute-cache trap).
# Usage: COMMIT=<full sha> END_BY=<ISO UTC> [START_NOT_BEFORE=<ISO UTC>] [SKIP_OURHALF=1] [GREP_TEXT=block_token_mask] bash launch-fix.sh
set -u
COMMIT=${COMMIT:?}; START_NOT_BEFORE=${START_NOT_BEFORE:-}; SKIP_OURHALF=${SKIP_OURHALF:-0}
GREP_TEXT=${GREP_TEXT:-block_token_mask}
END_BY=${END_BY:?END_BY is required (ISO UTC, for example 2026-10-15T20:00:00Z)}
date -u -d "$END_BY" +%s >/dev/null 2>&1 || { echo "END_BY '$END_BY' is not a date that 'date -u -d' accepts"; exit 64; }
[ -z "$START_NOT_BEFORE" ] || date -u -d "$START_NOT_BEFORE" +%s >/dev/null 2>&1 || { echo "START_NOT_BEFORE '$START_NOT_BEFORE' is not a date"; exit 64; }
vis=$(ssh -n delphi-3bda "git -C /home/jhan/workspace/tron cat-file -e $COMMIT^{commit} 2>/dev/null && echo commit-ok || echo commit-missing; git -C /home/jhan/workspace/tron show $COMMIT:h/tron/models/self_attention.hpp 2>/dev/null | grep -c '$GREP_TEXT'")
echo "3bda visibility: $(echo "$vis" | tr '\n' ' ')"
echo "$vis" | grep -q '^commit-ok$' || { echo "the commit is not visible on 3bda yet: wait and retry"; exit 1; }
[ "$(echo "$vis" | tail -1)" -gt 0 ] || { echo "the new text '$GREP_TEXT' is not visible in the commit on 3bda yet: wait and retry"; exit 1; }
ssh -n delphi-3bda "COMMIT=$COMMIT START_NOT_BEFORE=$START_NOT_BEFORE END_BY=$END_BY SKIP_OURHALF=$SKIP_OURHALF setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/probe-fix.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
