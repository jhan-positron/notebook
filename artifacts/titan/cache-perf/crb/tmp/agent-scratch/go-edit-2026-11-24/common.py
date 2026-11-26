"""Shared paths and texts of the three checks in this folder (edit of go.sh line 20, 2026-11-24).

CRB is the Arm reference server on which the benchmark runs. Nothing in this folder logs in to CRB.
The marker file is /tmp/positron-perf.RUNNING on CRB. Another user of CRB creates it during a performance test,
and the run scripts stop when it exists.
"""
import hashlib
import os

E = os.path.dirname(os.path.abspath(__file__))
C = os.path.normpath(os.path.join(E, '..', '..', '..'))                 # the folder crb
S = os.path.join(C, 'tmp', 'agent-scratch', 'w120-7200-2026-11-17')     # run folder of the rerun of 2026-11-17
ASRUN = os.path.join(E, 'go.sh.as-run-2026-11-17')                      # copy of go.sh from before the edit
RUN_SH = os.path.join(C, 'new-test-kernel', 'manual-run', 'run.sh')     # the start command that the user saved
# Record of the Claude Code session of 2026-11-17. It lies outside the project folder.
RECORD17 = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl'
MARKER = '/tmp/positron-perf.RUNNING'
OLD = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"\n'
NEW = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"\n'


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def read(path):
    return open(path, 'rb').read().decode()


def listed(name):
    """The sha256 that S/local.sha lists for one file name."""
    hits = [l.split()[0] for l in read(os.path.join(S, 'local.sha')).splitlines() if l.split()[1:] == [name]]
    assert len(hits) == 1, 'local.sha: %d lines for %s' % (len(hits), name)
    return hits[0]


def line20_is_new(text):
    """True when line 20 of a go.sh text is the line of 2026-11-24 and no other line holds it."""
    return text.count(NEW) == 1 and text.split('\n')[19] + '\n' == NEW


class Report:
    def __init__(self):
        self.ok = True

    def line(self, good, text):
        self.ok &= bool(good)
        print(('PASS ' if good else 'FAIL ') + text)

    def end(self):
        print('ALL PASS' if self.ok else 'SOME FAILED')
        raise SystemExit(0 if self.ok else 1)
