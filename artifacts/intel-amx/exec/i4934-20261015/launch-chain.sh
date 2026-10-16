#!/usr/bin/env bash
# Launch chain-fix.sh detached on delphi-3bda from claude-box (fork of launch-fix.sh: the same NFS visibility check, then
# the chain of the three drivers instead of probe-fix.sh alone). The whole-machine steps inside run on jhan's order.
# Usage: COMMIT=<full sha> PROBE_END_BY=<ISO UTC> IDENTITY_END_BY=<ISO UTC> MUTATE_END_BY=<ISO UTC> [GREP_TEXT=block_token_mask] bash launch-chain.sh
set -u
COMMIT=${COMMIT:?}; GREP_TEXT=${GREP_TEXT:-block_token_mask}
for v in PROBE_END_BY IDENTITY_END_BY MUTATE_END_BY; do date -u -d "${!v:?$v is required (ISO UTC)}" +%s >/dev/null 2>&1 || { echo "$v '${!v}' is not a date"; exit 64; }; done
vis=$(ssh -n delphi-3bda "git -C /home/jhan/workspace/tron cat-file -e $COMMIT^{commit} 2>/dev/null && echo commit-ok || echo commit-missing; git -C /home/jhan/workspace/tron show $COMMIT:h/tron/models/self_attention.hpp 2>/dev/null | grep -c '$GREP_TEXT'; for f in probe-fix.sh identity-fix.sh mutate-fix.sh chain-fix.sh; do bash -n /home/jhan/workspace/intel-AMX/exec/i4934-20261015/\$f 2>/dev/null && echo \$f-ok || echo \$f-syntax; done; python3 -c 'import ast,sys; ast.parse(open(sys.argv[1]).read())' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/mutations.py 2>/dev/null && echo mutations.py-ok || echo mutations.py-syntax; grep -c 'local out=' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/probe-fix.sh; pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/(probe|identity|mutate|chain)-fix\\.sh' | wc -l")
echo "3bda visibility: $(echo "$vis" | tr '\n' ' ')"
echo "$vis" | grep -q '^commit-ok$' || { echo "the commit is not visible on 3bda yet: wait and retry"; exit 1; }
[ "$(echo "$vis" | sed -n 2p)" -gt 0 ] || { echo "the new text '$GREP_TEXT' is not visible in the commit on 3bda yet: wait and retry"; exit 1; }
echo "$vis" | sed -n 3,7p | grep -q syntax && { echo "a script has a syntax error on 3bda (see the visibility line)"; exit 1; }
[ "$(echo "$vis" | sed -n 8p)" = 1 ] || { echo "the fixed trace_one (local out=) is not visible on 3bda yet: wait and retry"; exit 1; }
[ "$(echo "$vis" | tail -1)" = 0 ] || { echo "a driver of this chain still runs on 3bda"; exit 1; }
ssh -n delphi-3bda "COMMIT=$COMMIT PROBE_END_BY=$PROBE_END_BY IDENTITY_END_BY=$IDENTITY_END_BY MUTATE_END_BY=$MUTATE_END_BY setsid nohup bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/chain-fix.sh >/dev/null 2>&1 </dev/null & echo launched pid \$!"
