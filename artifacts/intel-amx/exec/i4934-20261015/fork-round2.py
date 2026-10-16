#!/usr/bin/env python3
"""fork-round2.py: the round-2 copies of the chain drivers (fresh result names, the rotated arm order), by exact-text
replacement with a count check per edit. Round 2 measures the final head after the page-struct change; the round-1
records stay untouched. Creates probe-r2.sh, identity-r2.sh, mutate-r2.sh, chain-r2.sh, launch-chain2.sh."""
import os, sys
D = os.path.dirname(os.path.abspath(__file__))
HEAD = ("# i4934-20261015 round 2 (2026-10-15): copy of {src} with fresh result names, so the final head's records do not reuse\n"
        "# round 1's (campaign-fix.sh skips a cell whose log holds 'average tok/s', smoke-fix.sh an arm with a .tokens file).\n"
        "# Made by fork-round2.py; only the replacements listed there differ. Original header follows.\n")
def fork(src, dst, edits, extra_head=True):
    s = open(os.path.join(D, src)).read()
    for old, new, n in edits:
        c = s.count(old)
        assert c == n, f"{src}: '{old[:50]}' occurs {c} times, expected {n}"
        s = s.replace(old, new)
    if extra_head:
        s = s.replace('#!/usr/bin/env bash\n', '#!/usr/bin/env bash\n' + HEAD.format(src=src), 1)
    open(os.path.join(D, dst), 'w').write(s); print(f"{dst} written")
fork('probe-fix.sh', 'probe-r2.sh', [
    ('export NAME=i4934-20261015\n', 'export NAME=i4934-r2\n', 1),
    ('i4934-E-cpu', 'i4934-E2-cpu', 4),
    ('i4934-E-fpga', 'i4934-E2-fpga', 4),
    ('bash "$D/campaign-fix.sh"', 'bash "$D/campaign-rot.sh"', 2),
])
fork('identity-fix.sh', 'identity-r2.sh', [
    ('export NAME=i4934-identity\n', 'export NAME=i4934-identity2\n', 1),
])
fork('mutate-fix.sh', 'mutate-r2.sh', [
    ('export NAME=i4934-mutate\n', 'export NAME=i4934-mutate2\n', 1),
])
fork('chain-fix.sh', 'chain-r2.sh', [
    ('LOG=/home/jhan/workspace/intel-AMX/exec/logs/i4934-chain.log', 'LOG=/home/jhan/workspace/intel-AMX/exec/logs/i4934-chain2.log', 1),
    ('bash "$D/probe-fix.sh"; echo "$(ts) probe-fix.sh rc=$? probe.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-20261015/probe.done',
     'bash "$D/probe-r2.sh"; echo "$(ts) probe-r2.sh rc=$? probe.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-r2/probe.done', 1),
    ('bash "$D/identity-fix.sh"; echo "$(ts) identity-fix.sh rc=$? identity.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-identity/identity.done',
     'bash "$D/identity-r2.sh"; echo "$(ts) identity-r2.sh rc=$? identity.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-identity2/identity.done', 1),
    ('bash "$D/mutate-fix.sh"; echo "$(ts) mutate-fix.sh rc=$? mutate.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-mutate/mutate.done',
     'bash "$D/mutate-r2.sh"; echo "$(ts) mutate-r2.sh rc=$? mutate.done=$(cat /home/jhan/workspace/intel-AMX/exec/results/i4934-mutate2/mutate.done', 1),
])
fork('launch-chain.sh', 'launch-chain2.sh', [
    ('for f in probe-fix.sh identity-fix.sh mutate-fix.sh chain-fix.sh; do', 'for f in probe-r2.sh identity-r2.sh mutate-r2.sh chain-r2.sh campaign-rot.sh; do', 1),
    ("grep -c 'local out=' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/probe-fix.sh", "grep -c 'local out=' /home/jhan/workspace/intel-AMX/exec/i4934-20261015/probe-r2.sh", 1),
    ("pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/(probe|identity|mutate|chain)-fix\\\\.sh' | wc -l", "pgrep -f '^bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/(probe|identity|mutate|chain)-(fix|r2)\\\\.sh' | wc -l", 1),
    ('echo "$vis" | sed -n 3,7p | grep -q syntax', 'echo "$vis" | sed -n 3,8p | grep -q syntax', 1),
    ('[ "$(echo "$vis" | sed -n 8p)" = 1 ]', '[ "$(echo "$vis" | sed -n 9p)" = 1 ]', 1),
    ('bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/chain-fix.sh >/dev/null', 'bash /home/jhan/workspace/intel-AMX/exec/i4934-20261015/chain-r2.sh >/dev/null', 1),
    ('# Launch chain-fix.sh detached', '# Launch chain-r2.sh (round 2) detached', 1),
])
