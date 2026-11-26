#!/usr/bin/env bash
# Is SIGINT ignored in a command that a script starts in the background? Read bit 2 of the SigIgn mask of the child.
show() { sleep 0.2; python3 -c "
import sys
for l in open('/proc/%s/status' % sys.argv[2]):
    if l.startswith('SigIgn'):
        v = int(l.split()[1], 16); print('   %-52s SIGINT %s' % (sys.argv[1] + ':', 'IGNORED' if v & 2 else 'not ignored'))
" "$1" "$2"; }
sleep 3 & show "plain background command" $!
( exec sleep 3 ) & show "background subshell that execs" $!
( exec env --default-signal=INT sleep 3 ) & show "the same with env --default-signal=INT" $!
f() { ( cd / && exec sleep 3 ) & show "in a function: background subshell, cd, exec" $!; }; f
kill $(jobs -p) 2>/dev/null; wait 2>/dev/null
