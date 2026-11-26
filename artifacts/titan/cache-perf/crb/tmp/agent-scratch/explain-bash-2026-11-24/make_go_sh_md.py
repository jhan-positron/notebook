#!/usr/bin/env python3
"""make_go_sh_md.py - writes go.sh.md: a short line-by-line explanation of go.sh (explain-bash skill).

The page is plain Markdown. It holds no HTML tag.
The side-by-side part is one Markdown table with one row per source line: line number, source line, explanation.
The source cells are copied from go.sh by this script. Each "|" of the source is written "\\|" there, because a plain "|"
would end the table cell.
Each explanation names a piece of text that its source line must hold. The build stops when a line changed.
Each fact that the page takes from another file is tested here before the page is written.
Before the page replaces go.sh.md, the script reads it back twice and compares every source cell with go.sh:
once with its own reader of the table rows, and once through pandoc (reader gfm). pandoc must also find no HTML in it.
Needs: Python 3 standard library, and the program pandoc.
"""
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys

C = '/home/jhan/workspace/titan/cache-perf/crb'
S = C + '/tmp/agent-scratch/w120-7200-2026-11-17'
E = C + '/tmp/agent-scratch/go-edit-2026-11-24'
X = C + '/tmp/agent-scratch/explain-bash-2026-11-24'
RX_DIR = C + '/tmp/agent-scratch/w120-2026-11-15'
LOG = C + '/results/go-T72-20261117T221209Z.log'
TRY6 = C + '/results/dimm7200-20261117/try6.txt'
INSPECT = C + '/inspection-record-2026-10-30.md'
NOTES = C + '/jeremy-plan-constraints-2026-10-30.md'
RECORD = ('/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/'
          '405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl')
OLD_PAGE = X + '/go.sh.md.before-explain-bash'
TABLE_HEAD = '| Line | Source | Explanation |'
TABLE_RULE = '|---:|---|---|'


def die(msg):
    sys.exit('make_go_sh_md.py: ERROR: ' + msg)


def need(cond, msg):
    if not cond:
        die('check failed: ' + msg)


def text_lines(path):
    with open(path) as f:
        return f.read().split('\n')


def source_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    need(b'\r' not in raw, path + ' has Unix line ends')
    lines = raw.decode('utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()          # the file ends with a line end
    return lines, hashlib.sha256(raw).hexdigest(), len(raw)


# ----------------------------------------------------------------------------- facts from other files

def check_facts(src):
    boot = src[15].split('=', 1)[1]
    rxsha = src[13].split('=', 1)[1]
    whole = '\n'.join(src)
    need('set -e' not in whole, 'go.sh holds no "set -e"')
    need([i for i, l in enumerate(src, 1) if 'baselines-and-rules' in l] == [8], 'only line 8 names baselines-and-rules.txt')
    need('rm ' not in whole, 'go.sh holds no rm command')
    need('taskset -c ' not in whole, 'go.sh sets no CPU list')
    need([i for i, l in enumerate(src, 1) if 'date' in l] == [17], 'go.sh reads the clock in line 17 only')

    log = text_lines(LOG)
    need(log[0].startswith('go.sh pid 4864 '), 'log line 1 holds the process id 4864')
    need(log[2].endswith('cpu0 scaling_cur_freq 2800000'), 'log line 3 ends with the frequency value 2800000')
    need(log[4].endswith('current affinity list: 0-119'), 'log line 5 holds the CPU list 0-119')
    need('boot ' + boot + ' MemTotal: 395392808 kB' in log[5], 'log line 6 holds the boot id and MemTotal')
    states = [l for l in log if l.startswith(('== start ', '== after ', '== end '))]
    need(len(states) == 12 and all('marker absent' in l and 'MemTotal: 395392808 kB' in l for l in states),
         '12 state lines, each with "marker absent" and the same MemTotal')
    need(not any(l.startswith('FAILED') for l in log), 'no FAILED line in the log')
    need([l for l in log if l][-1] == 'ALLDONE', 'the last line of the log is ALLDONE')

    ra = text_lines(S + '/ra.sh')
    need(ra[7] == 'set -euo pipefail', 'ra.sh line 8')
    need('exec taskset -c 0-119 "$0" "$@"' in ra[8], 'ra.sh line 9 restarts under taskset')
    need('--min-ms 500' in ra[41], 'ra.sh line 42 holds --min-ms 500')

    rx_raw = open(RX_DIR + '/rx.sh', 'rb').read()
    rx = rx_raw.decode().split('\n')
    need(hashlib.sha256(rx_raw).hexdigest() == rxsha, 'the local rx.sh has the sha256 of go.sh line 14')
    need('date -u +%Y%m%dT%H%M%SZ' in rx[8], 'rx.sh line 9 puts the time into the folder name')
    need(rx[16].startswith('  taskset -c 0-119 $BW $args'), 'rx.sh line 17 starts the binary under taskset')
    need('echo "rc $? $tag' in rx[19], 'rx.sh line 20 writes the rc line')

    seq = {'like': 'oldread,asmread,read_nop96,read_nop256,read_1pl', 'cfwd': 'oldread,read,asmread', 'crev': 'asmread,read,oldread'}
    spec = {}
    for k in seq:
        ls = [l for l in text_lines('%s/%s.spec' % (S, k)) if l]
        need(len(ls) == 1, k + '.spec holds one line')
        need('--stop common ' in ls[0] and '--min-ms 6000 ' in ls[0] and '--threads 120 --cpus 0-63,64-119 ' in ls[0], k + '.spec arguments')
        need('--seq %s ' % seq[k] in ls[0], k + '.spec kernel order')
        spec[k] = ls[0]
    need(text_lines(RX_DIR + '/r8.spec')[0] == spec['like'], 'r8.spec line 1 equals like.spec')

    t6 = text_lines(TRY6)
    need(t6[1] == boot, 'try6.txt line 2 holds the boot id of go.sh line 16')
    need(t6[6].split() == ['12', 'Configured', 'Memory', 'Speed:', '7200', 'MT/s'], 'try6.txt line 7: 12 modules at 7200 MT/s')

    need('`CPUAffinity=0-119`' in text_lines(INSPECT)[139], 'inspection record line 140')
    notes = text_lines(NOTES)
    need(notes[11].startswith('- block: a reserved whole-host window in which Jeremy runs measurements'), 'notes line 12')
    need(notes[12].startswith('- RUNNING file: `/tmp/positron-perf.RUNNING`, present for the whole block'), 'notes line 13')

    with open(RECORD) as f:
        for i, l in enumerate(f, 1):
            if i == 313:
                rec = l
                break
    cmds = []

    def walk(x):
        if isinstance(x, dict):
            if x.get('type') == 'tool_use':
                cmds.append(x['input'].get('command', ''))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(json.loads(rec))
    need(len(cmds) == 1, 'record line 313 holds one command')
    need('nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null & pid=$!' in cmds[0], 'record line 313: start command')
    need('L=~/cache-perf/results/go-T72-$(date -u +%Y%m%dT%H%M%SZ).log;' in cmds[0], 'record line 313: log file name')
    need('taskset' not in cmds[0], 'the start command holds no taskset')

    old_raw = open(E + '/go.sh.as-run-2026-11-17', 'rb').read()
    old = old_raw.decode().split('\n')
    if old[-1] == '':
        old.pop()
    need(len(old) == len(src) and [i for i in range(len(src)) if old[i] != src[i]] == [19], 'the text that ran differs in line 20 only')
    need(old[19] == '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"', 'old text of line 20')
    need(text_lines(S + '/local.sha')[0] == hashlib.sha256(old_raw).hexdigest() + '  go.sh', 'local.sha lists the sha256 of the text that ran')
    need(os.path.isfile(OLD_PAGE), 'the copy of the earlier page exists')
    for name in sorted(os.listdir(S)):
        if name.endswith('.sh'):
            t = open(os.path.join(S, name)).read()
            need('nohup' not in t and 'setsid' not in t, 'no script of the run folder holds the start command (%s)' % name)
    return '%.1f' % (395000000 * 1024 / 2 ** 30)   # the limit of line 27 in GiB


# ----------------------------------------------------------------------------- the page text

WORDS = [
    ('Rerun', 'the run of the whole-chip test on 2026-11-17, at a memory speed of 7200 MT/s. By line 8 of go.sh, it is compared with earlier results at 8000 MT/s.'),
    ('Whole-chip test', 'a memory benchmark with 120 threads on the CPUs 0 to 119.'),
    ('MT/s', 'million transfers per second, the unit of memory speed.'),
    ('Memory module', 'one DIMM, a plug-in memory board.'),
    ('bwx12', 'the benchmark binary of 2026-11-15 that parts L and C run.'),
    ('Process', 'one start of a benchmark binary.'),
    ('Session', 'one pass of go.sh through part A, part L and part C.'),
    ('Part A, part L, part C', 'the three steps of a session. Lines 3 to 5 of go.sh describe them.'),
    ('Spec file', 'a text file that `rx.sh` reads as its input. Its line has the form `tag|arguments of the binary` and gives one process.'),
    ('State line', 'a line that go.sh prints with the time, the boot id, MemTotal, the load, the logins, the marker file and the processes per user.'),
    ('Marker file', 'the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. By the message of line 20 it means that Jeremy or someone else is using CRB.'),
    ('Jeremy', 'another user of CRB. Notes of 2026-10-30 say that the marker file is present during each time window that is reserved for the measurements of Jeremy [Ref10].'),
    ('Boot id', 'a random identifier that Linux creates once per boot [Ref9]. Equal boot ids mean the same boot.'),
    ('MemTotal', 'the usable memory that Linux reports in the file `/proc/meminfo`, in kB.'),
    ('Load', 'the content of the file `/proc/loadavg`: three load averages, the number of runnable tasks and of all tasks, and the newest process id [Ref11].'),
    ('Governor', 'the Linux policy that sets the CPU frequency.'),
    ('Transparent huge pages (thp)', 'a Linux feature that can place a buffer on 2 MiB pages.'),
    ('sha256', 'a checksum. Two files with the same sha256 have the same content.'),
    ('Exit status (rc)', 'the number that a process returns when it ends. 0 means success.'),
    ('launches.txt', 'a file that `rx.sh` writes in its result folder. It holds one line `rc <exit status> <tag>` per process [Ref3].'),
    ('Process id', 'the number that Linux gives to a process. `$$` is the process id of the shell that runs the script.'),
    ('Process group', 'a set of processes that one signal can reach together. The group has the process id of its leader as its number.'),
    ('File descriptor', 'the number under which a process holds an open file.'),
    ('CPU list', 'the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.'),
    ('Start command', 'the command line that started go.sh on CRB in the rerun. No script of the run folder holds it. The saved record of the AI agent (Claude Code) that ran the rerun holds it [Ref5].'),
    ('UTC', 'Coordinated Universal Time.'),
]

FLOW = [
    ('Set `set -u`, the paths on CRB, the two expected sha256 values and the expected boot id', 'lines 9-16'),
    ('Define the helpers `state` (prints one state line) and `fail` (prints the reason and ends the run with exit status 1)', 'lines 17-18'),
    ('Print the process id of go.sh', 'line 19'),
    ('Run the checks: marker file, lock file, sha256 of `rx.sh` and of bwx12, presence of `ra.sh` and of the spec files, boot id, MemTotal. Each failed check calls `fail`', 'lines 20-27'),
    ('Define the helpers `rxok` (tests the `rc` line that `rx.sh` wrote) and `runx` (one call of `rx.sh`, then `rxok`, then a state line)', 'lines 28-34'),
    ('Print the Linux kernel command line, the governors, the huge page settings, the CPU list of the shell and the first state line', 'lines 35-39'),
    ('For the sessions 1, 2 and 3: run part A with `ra.sh`, then part L with `like.spec`, then part C with `cfwd.spec` (session 2: `crev.spec`). Print a state line after each step', 'lines 40-45'),
    ('Run one more part C process with `crev.spec`', 'line 46'),
    ('Print the last state line and `ALLDONE`', 'lines 47-48'),
]

BEHAVIOR = [
    'go.sh measures nothing itself. It reads the clock only for the time in a state line (line 17). It starts `ra.sh` and `rx.sh` and waits for them.',
    'A failed check stops the whole run with exit status 1 (helper `fail`, line 18). go.sh deletes nothing. So the result folders that were written before the failure stay on disk.',
    'The script has no `set -e`. A failed command stops the run only where the line calls `fail`. Lines 35 to 38 do not call it.',
    'The boot check (line 26) compares with one fixed boot id. So in every boot other than the boot of the rerun, go.sh stops at line 26 or at an earlier check [Ref1] [Ref9].',
    'CPU list: go.sh sets none. `ra.sh` restarts itself under `taskset -c 0-119` [Ref2]. `rx.sh` starts bwx12 under `taskset -c 0-119` [Ref3].',
    'Source of the CPU list that line 38 printed in the rerun (`0-119`) [Ref1]: the start command holds no `taskset` [Ref5]. A child process starts with the CPU list of its parent [Ref8]. So the shell of go.sh got the list from the process that started it. An inspection of CRB on 2026-10-30 found the systemd setting `CPUAffinity=0-119` [Ref6]. systemd is the first process of the system. The setting gives this list to systemd and to every process that descends from it.',
    'The start command of the rerun: `L=~/cache-perf/results/go-T72-$(date -u +%Y%m%dT%H%M%SZ).log; nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null &` [Ref5]. Its parts:\n'
    '  - `L=...`: the name of the log file, with the UTC time of the start. go.sh itself names no log file.\n'
    '  - `> $L 2>&1`: the standard output and the error output of go.sh go to the log file.\n'
    '  - `< /dev/null`: go.sh gets an empty input.\n'
    '  - `nohup`: go.sh ignores the hangup signal. This signal tells a program that its terminal or connection was closed [Ref7].\n'
    '  - `setsid`: go.sh becomes the leader of a new process group [Ref7]. So the `kill` command that line 19 prints reaches go.sh and its child processes.\n'
    '  - `&`: the command runs in the background. The shell that started it does not wait before its next command.',
    'Two texts of go.sh: this page shows the local text. It differs from the text that ran in the rerun in the message of line 20 only. The old line was `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"`. The message was changed on 2026-11-24 [Ref12].',
]


def rows(gib):
    """One entry per source line: (text that the source line must hold, explanation). An explanation is one line of
    Markdown without "|": a Markdown table row cannot hold a line break or a list."""
    return [
        ('#!/usr/bin/env bash',
         'Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user.'),
        ('# go.sh - whole-chip rerun at 7200 MT/s. Three sessions.',
         'Comment: the name of the script and the plan. The run has three sessions. Each session runs the parts A, L and C, one after the other.'),
        ('#   A: ra.sh',
         'Comment, part A: `ra.sh` repeats the 120-thread part of the test of 2026-11-13 with the same binaries. '
         '`whole-pass stop, 0.5 s` names the stop rule of these binaries and their minimum run time (`--min-ms 500` in `ra.sh`) [Ref2].'),
        ('#   L: rx.sh like.spec',
         'Comment, part L: `rx.sh` runs bwx12 with the spec file `like.spec`. '
         '`common stop, 6 s` stands for the arguments `--stop common --min-ms 6000` of the spec file [Ref4]. '
         'The one line of `like.spec` is equal to line 1 of the older spec file `r8.spec` [Ref4].'),
        ('#   C: rx.sh cfwd.spec or crev.spec',
         'Comment, part C: `rx.sh` runs bwx12 with `cfwd.spec` or `crev.spec`. '
         'One process times three read loops: the old C loop, the new C loop and the assembly loop (`--seq oldread,read,asmread` in `cfwd.spec`) [Ref4]. '
         '`crev.spec` holds the reverse order. Session 2 uses it.'),
        ('# After session 3 one more C process',
         'Comment: after session 3, one more part C process runs in reverse order. Part C then has 2 processes in forward order and 2 processes in reverse order.'),
        ('# No root. CPUs 0-119 only.',
         'Comment: the run needs no root rights and uses the CPUs 0 to 119 only. `ra.sh` and `rx.sh` stop when the marker file exists.'),
        ('# 8000 MT/s baselines',
         'Comment: the rerun is compared with earlier results at 8000 MT/s. The file `baselines-and-rules.txt` lists them. By the comment, the list was fixed before this run. go.sh never reads that file.'),
        ('set -u',
         'The script stops when it uses a variable that was never set. The script has no `set -e`. So a failed command alone does not stop it.'),
        ('D=$HOME/cache-perf/w120-7200-20261117',
         '`D`: the folder on CRB that holds `ra.sh` and the three spec files.'),
        ('RX=$HOME/cache-perf/w120-20261115/rx.sh',
         '`RX`: the path of the runner script `rx.sh`.'),
        ('BW=$HOME/cache-perf/bwx12-20261115/bwx12',
         '`BW`: the path of the binary bwx12.'),
        ('SHA=',
         '`SHA`: the sha256 that the file bwx12 must have. Line 23 tests it.'),
        ('RXSHA=',
         '`RXSHA`: the sha256 that `rx.sh` must have. Line 22 tests it.'),
        ('# The boot in which results/dimm7200-20261117/try6.txt recorded 12 modules at 7200 MT/s.',
         'Comment: the origin of the boot id in line 16. It is the boot in which the file `try6.txt` recorded 12 memory modules at 7200 MT/s [Ref1].'),
        ('BOOT=',
         '`BOOT`: the boot id that the running system must have. Line 26 tests it.'),
        ('state() {',
         'Defines the helper `state LABEL`. It prints one state line and stops nothing. '
         'The line holds `==`, the label, the UTC time (`date -u`), the boot id and the `MemTotal` line of `/proc/meminfo`. '
         'Then it holds the load, which is the content of `/proc/loadavg`. '
         'Then it holds the number of logins: `who` prints one line per login, and `wc -l` counts the lines. '
         'Then it holds `present` or `absent` for the marker file. '
         'The last part is the number of processes of each user: `ps -eo user=` prints the user of every process, and `sort` with `uniq -c` counts equal lines. '
         '`tr -s \' \'` reduces each run of spaces to one space. `tr \'\\n\' \';\'` joins the counts with `;`.'),
        ('fail() {',
         'Defines the helper `fail MESSAGE`. It prints `FAILED:` and the message. Then it prints a state line with the label `abort`. Then it ends go.sh with exit status 1.'),
        ('echo "go.sh pid $$',
         'Prints the process id of go.sh and a command that stops the run. '
         '`kill -TERM -- -PID` sends the termination signal to every process of the process group with that number. '
         'The command reaches go.sh and its child processes only when go.sh is the leader of its process group. '
         'go.sh does not make itself the leader. In the rerun the start command did it with `setsid` [Ref5].'),
        ('[ -e /tmp/positron-perf.RUNNING ] && fail',
         'Check of the marker file: when the file exists (`-e`), `fail` stops the run with this message. The words after the comma were added on 2026-11-24, after the rerun [Ref12].'),
        ('flock -n 9',
         'Lock against a second run. `exec 9> FILE` opens the lock file for writing as file descriptor 9 of the shell. It creates the file when it is missing. '
         '`flock -n 9` asks for an exclusive lock on that file and does not wait. When another process holds the lock, `fail` stops the run.'),
        ('echo "$RXSHA  $RX" | sha256sum -c -',
         'Checksum check of `rx.sh`. `echo` writes one line with the expected checksum and the path. '
         '`sha256sum -c -` reads that line, computes the sha256 of the file and compares the two values. `> /dev/null` discards its report. '
         'When the values differ or the file cannot be read, `fail` stops the run.'),
        ('echo "$SHA  $BW" | sha256sum -c -',
         'The same check for the binary bwx12, with the checksum of line 13.'),
        ('[ -x "$f" ]',
         'For `ra.sh` and for bwx12: when the file is missing or not executable (`-x`), `fail` stops the run.'),
        ('[ -s "$D/$f.spec" ]',
         'For `like.spec`, `cfwd.spec` and `crev.spec` in the folder `D`: when the file is missing or empty (`-s`), `fail` stops the run.'),
        ('= "$BOOT" ]',
         'Boot check: when the boot id of the running system differs from `BOOT` (line 16), `fail` stops the run. The check reads the boot id only. It does not read the memory speed or the number of modules.'),
        ('-ge 395000000 ]',
         'Memory size check. `awk` prints the second field of the `MemTotal` line of `/proc/meminfo`, a value in kB. '
         'When the value is below 395000000 kB (about %s GiB), `fail` stops the run. By the message, a lower value means: not 12 modules. '
         'In the rerun the value was 395392808 kB [Ref1].' % gib),
        ('# rx.sh ends with status 0 also when bwx12 failed',
         'Comment: the reason for line 29. `rx.sh` ends with status 0 also when bwx12 failed. It only writes a line `rc N tag` to the file `launches.txt`. Each spec file has one line. So exactly one line `rc 0` must be there.'),
        ('rxok() {',
         'Defines the helper `rxok NAME`. It tests the exit status that `rx.sh` recorded for the bwx12 process. '
         '`ls -d` lists the `launches.txt` files of all result folders `w120-NAME-<time>` in name order, and `tail -1` keeps the last one. '
         'The time in the folder name puts the newest folder last [Ref3]. `2>/dev/null` discards the error message of `ls` when no file matches. '
         'The helper succeeds only when three tests pass. Test 1: a file was found (`-n`). '
         'Test 2: the file holds exactly 1 line that starts with `rc` and a space. Test 3: it holds exactly 1 line that starts with `rc 0` and a space. '
         '`grep -c` counts the matching lines.'),
        ('runx() { # name spec',
         'Starts the definition of the helper `runx NAME SPEC`. It runs one step of part L or part C.'),
        ('bash "$RX" "$1" "$BW" "$SHA" < "$2"',
         'Runs `rx.sh` with `bash` and three arguments: NAME, the path of bwx12 and its expected sha256. The spec file is the input of `rx.sh` (`< "$2"`). '
         'go.sh waits until `rx.sh` has ended. On a non-zero exit status, `fail` stops the run and prints that status (`$?`).'),
        ('rxok "$1" || fail',
         'Calls `rxok` (line 29). When it does not succeed, `fail` stops the run. The message names two files of the result folder to read: `launches.txt` and `stderr.txt`.'),
        ('state "after $1"',
         'Prints a state line with the label `after NAME`.'),
        ('}',
         'Ends the definition of `runx`.'),
        ('echo "== cmdline',
         'Prints the command line of the running Linux kernel (file `/proc/cmdline`). This line and the next three lines only write to the log. None of them is a check.'),
        ('echo "== governors of CPUs 0-119',
         'Prints the governor of each of the CPUs 0 to 119, counted per governor name (`sort` with `uniq -c`). '
         'Then it prints the file `scaling_cur_freq` of CPU 0: the current frequency that Linux reports for that CPU, in kHz [Ref11].'),
        ('echo "== thp enabled',
         'Prints the two settings of transparent huge pages: the files `enabled` and `defrag`.'),
        ('echo "== affinity of this shell: $(taskset -cp $$)"',
         '`taskset -cp $$` prints the CPU list of this shell. go.sh does not set this list. In the rerun the log shows `0-119` [Ref1].'),
        ('state start',
         'Prints the first state line, with the label `start`.'),
        ('for s in 1 2 3; do',
         'Starts a loop over the sessions: `s` is 1, then 2, then 3.'),
        ('"$D/ra.sh" T72A$s || fail',
         'Part A: runs `ra.sh` with the name `T72A1`, `T72A2` or `T72A3` and waits for its end. On a non-zero exit status, `fail` stops the run and prints that status.'),
        ('state "after T72A$s"',
         'Prints a state line with the label `after T72A<s>`. Here `<s>` stands for the session number.'),
        ('runx T72L$s "$D/like.spec"',
         'Part L: `runx` (lines 30 to 34) runs one bwx12 process with `like.spec` and the name `T72L<s>`.'),
        ('if [ "$s" = 2 ]; then runx T72C$s "$D/crev.spec"; else runx T72C$s "$D/cfwd.spec"; fi',
         'Part C: one bwx12 process with the name `T72C<s>`. Session 2 uses `crev.spec` (reverse order). Sessions 1 and 3 use `cfwd.spec` (forward order).'),
        ('done',
         'Ends the loop.'),
        ('runx T72C4 "$D/crev.spec"',
         'One more part C process after session 3, with `crev.spec` and the name `T72C4`. No part A and no part L run between `T72C3` and `T72C4`.'),
        ('state end',
         'Prints the last state line, with the label `end`.'),
        ('echo ALLDONE',
         'Prints `ALLDONE`. The script reaches this line only when no check called `fail`.'),
    ]


REFS = [
    ('Ref1', [LOG, TRY6],
     'the log of go.sh in the rerun, and the record of the memory check. Log: line 5 holds the CPU list `0-119` of the shell. Line 6 holds the boot id of line 16 of go.sh. All 12 state lines hold `MemTotal: 395392808 kB` and `marker absent`. No line starts with `FAILED`. The last line is `ALLDONE`. `try6.txt`: line 2 holds the same boot id. Line 7 holds the count 12 for the text `Configured Memory Speed: 7200 MT/s`.'),
    ('Ref2', [S + '/ra.sh'],
     'part A script. `set -euo pipefail`: line 8. Restart under `taskset -c 0-119`: line 9. `--min-ms 500`: line 42.'),
    ('Ref3', [RX_DIR + '/rx.sh'],
     'runner script. The result folder name ends with the UTC start time: line 9. Start of the binary under `taskset -c 0-119`: line 17. The `rc` line: line 20. This copy has the sha256 of line 14 of go.sh.'),
    ('Ref4', [S + '/like.spec', S + '/cfwd.spec', S + '/crev.spec', RX_DIR + '/r8.spec'],
     'the three spec files and the older spec file. Each of the three holds one line with `--threads 120 --cpus 0-63,64-119`, `--stop common` and `--min-ms 6000`. `--seq` gives the loop order: `oldread,asmread,read_nop96,read_nop256,read_1pl` (like), `oldread,read,asmread` (cfwd), `asmread,read,oldread` (crev). Line 1 of `r8.spec` is equal to the line of `like.spec`.'),
    ('Ref5', [RECORD],
     'the saved record of the AI agent (Claude Code) that ran the rerun, one JSON record per line. It lies outside the project folder. Line 313 holds the command that the agent sent to CRB at 22:12:08 UTC on 2026-11-17. It holds the start command and no `taskset`.'),
    ('Ref6', [INSPECT],
     'inspection of CRB on 2026-10-30. Line 140: the file `/etc/systemd/system.conf.d/60-positron-cpuaffinity.conf` holds `CPUAffinity=0-119`, and process 1 and every process that descends from it have the CPU list 0-119.'),
    ('Ref7', [],
     'external source: Linux manual pages nohup(1), setsid(1) and setsid(2). `nohup` runs a command that ignores the hangup signal. `setsid` runs a program in a new Linux session. The process that creates the session becomes the leader of a new process group.'),
    ('Ref8', [],
     'external source: Linux manual page sched_setaffinity(2). A child process inherits the CPU affinity of its parent.'),
    ('Ref9', [],
     'external source: Linux manual page random(4), entry `/proc/sys/kernel/random/boot_id`. The value is generated once per boot.'),
    ('Ref10', [NOTES],
     'notes of 2026-10-30 about the tests of Jeremy. Line 12 defines a block: a reserved whole-host window in which Jeremy runs measurements. Line 13: the file `/tmp/positron-perf.RUNNING` is present for the whole block.'),
    ('Ref11', [],
     'external sources: Linux manual page proc(5), entry `/proc/loadavg` (meaning of the five fields). Linux kernel documentation "CPU Performance Scaling" (`admin-guide/pm/cpufreq`), entry `scaling_cur_freq` (the value is in kHz).'),
    ('Ref12', [E + '/go.sh.as-run-2026-11-17', S + '/local.sha'],
     'a copy of go.sh from before the edit of 2026-11-24, and the checksum list that was written when the files were copied to CRB on 2026-11-17. The copy differs from the local go.sh in line 20 only. The copy has the sha256 that line 1 of `local.sha` lists for go.sh.'),
    ('Ref13', [],
     'external source: GitHub Flavored Markdown Spec, section 4.10 "Tables (extension)". A `|` inside a table cell is written `\\|`, also inside a code span. The script that built this page read the page back with pandoc (reader `gfm`). Each source cell was equal to its line of go.sh.'),
]


# ----------------------------------------------------------------------------- Markdown table

def source_cell(n, line):
    """One source line as a code span of a table cell."""
    if line == '' or '`' in line or '\\|' in line or (line[0] == ' ' and line[-1] == ' '):
        die('line %d of go.sh needs a case that this script does not handle '
            '(empty line, backtick, backslash before "|", or a space at both ends)' % n)
    return '`' + line.replace('|', '\\|') + '`'


def read_table(md):
    """The rows of the table, read back from the page text: (line number, source line, explanation)."""
    lines = md.split('\n')
    need(lines.count(TABLE_HEAD) == 1, 'the page holds one table head')
    a = lines.index(TABLE_HEAD)
    need(lines[a + 1] == TABLE_RULE and lines[a - 1] == '', 'the table head is followed by its rule line')
    out = []
    for l in lines[a + 2:]:
        if not l.startswith('|'):
            need(l == '', 'a blank line ends the table')
            break
        cells = re.split(r'(?<!\\)\|', l)        # a "|" without a backslash before it separates two cells
        need(len(cells) == 5 and cells[0] == '' and cells[4] == '', 'a table row has three cells: ' + l[:60])
        num, code, text = (c[1:-1] for c in cells[1:4])
        need(len(code) > 2 and code[0] == '`' and code[-1] == '`' and '`' not in code[1:-1], 'the source cell is one code span: ' + l[:60])
        out.append((int(num), code[1:-1].replace('\\|', '|'), text))
    return out


def read_table_pandoc(path):
    """The same rows as pandoc reads them, and a test that pandoc finds no HTML in the page."""
    exe = shutil.which('pandoc')
    if not exe:
        die('the program pandoc was not found. The page was not written.')

    def run(fmt):
        return subprocess.run([exe, '-f', 'gfm', '-t', fmt, '--wrap=none', path], check=True,
                              stdout=subprocess.PIPE, universal_newlines=True).stdout
    ast = run('json')
    need('"RawBlock"' not in ast and '"RawInline"' not in ast, 'pandoc finds no HTML element in the page')
    need(ast.count('"t":"Table"') == 1, 'pandoc finds one table in the page')
    page = run('html')
    found = re.findall(r'<tr[^>]*>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*><code>(.*?)</code></td>\s*<td[^>]*>.*?</td>\s*</tr>', page, re.S)
    return [(int(n), html.unescape(c)) for n, c in found], subprocess.run([exe, '--version'], stdout=subprocess.PIPE,
                                                                             universal_newlines=True).stdout.split('\n')[0]


def no_html(md):
    """Outside code spans the page holds no "<" and no ">". All code spans of the page have one backtick at each end."""
    for n, l in enumerate(md.split('\n'), 1):
        rest = re.sub(r'`[^`]+`', '', l)
        need('`' not in rest, 'page line %d: every backtick belongs to a code span' % n)
        need('<' not in rest and '>' not in rest, 'page line %d holds "<" or ">" outside a code span' % n)


def main():
    path = S + '/go.sh'
    src, sha, nbytes = source_lines(path)
    gib = check_facts(src)
    table = rows(gib)
    if len(table) != len(src):
        die('%d explanations for %d source lines' % (len(table), len(src)))
    for i, (anchor, text) in enumerate(table, 1):
        if anchor not in src[i - 1]:
            die('line %d of go.sh does not hold %r: the explanation no longer fits' % (i, anchor))
        if not text.strip() or text != text.strip() or '\n' in text or '|' in text:
            die('line %d: the explanation must be one line of text without "|"' % i)
    used = '\n'.join([d for _, d in WORDS] + BEHAVIOR + [t for _, t in table]
                     + ['[Ref13]'])            # the head of the page cites Ref13
    for rid, _, _ in REFS:
        if '[%s]' % rid not in used:
            die('%s is never cited' % rid)
    for n in range(1, 40):
        if '[Ref%d]' % n in used and n > len(REFS):
            die('Ref%d is cited and not listed' % n)

    out = []
    w = out.append
    w('# `go.sh` explained, line by line')
    w('')
    w('- Source file: `go.sh` in this folder (Bash script, %d lines, %d bytes).' % (len(src), nbytes))
    w('- sha256 of the source when this page was built: `%s`.' % sha)
    w('- The column "Source" of the table below is a copy of the source, made by a script. The column "Line" holds the line numbers of the source.')
    w('- In the raw text of this page, each `|` of the source is written `\\|`. A plain `|` would end the table cell [Ref13]. A Markdown viewer shows `|`.')
    w('- A longer page stood here until 2026-11-24. A copy is kept: `%s`. The copy also holds the call sequence, a table of the functions and more notes on the rerun.' % OLD_PAGE)
    w('')
    w('## Short version: purpose')
    w('')
    w('go.sh is the top-level script of the whole-chip rerun of 2026-11-17 on CRB (the Arm reference server under test). '
      'It first checks that the machine and the files are the expected ones. '
      'Then it runs three sessions of part A (`ra.sh`), part L and part C (both through `rx.sh`), and one more part C process at the end.')
    w('')
    w('## Words used here')
    w('')
    for term, d in WORDS:
        w('- **%s**: %s' % (term, d))
    w('')
    w('## Main flow')
    w('')
    for i, (step, where) in enumerate(FLOW, 1):
        w('%d. %s (%s).' % (i, step, where))
    w('')
    w('## Behavior a reader must know')
    w('')
    for x in BEHAVIOR:
        w('- ' + x)
    w('')
    w('## Source and explanation, line by line')
    w('')
    w(TABLE_HEAD)
    w(TABLE_RULE)
    for i, (_, text) in enumerate(table, 1):
        w('| %d | %s | %s |' % (i, source_cell(i, src[i - 1]), text))
    w('')
    w('## References')
    w('')
    for rid, paths, what in REFS:
        for p in paths:
            if not os.path.isfile(p):
                die('%s: missing file %s' % (rid, p))
        p = ' ' + ', '.join('`%s`' % x for x in paths) + ':' if paths else ''
        w('- [%s]%s %s' % (rid, p, what))
    w('')
    md = '\n'.join(out)

    # Read the page back before it replaces go.sh.md.
    no_html(md)
    want = [(i, src[i - 1], table[i - 1][1]) for i in range(1, len(src) + 1)]
    need(read_table(md) == want, 'the rows read back from the page are the lines of go.sh and their explanations')
    tmp = X + '/go.sh.md.new'
    with open(tmp, 'w') as f:
        f.write(md)
    seen, version = read_table_pandoc(tmp)
    need(seen == [(n, code) for n, code, _ in want], 'pandoc reads every source cell as the line of go.sh')
    dest = path + '.md'
    shutil.copyfile(tmp, dest)
    os.remove(tmp)
    print('wrote %s: %d bytes, plain Markdown, %d table rows' % (dest, len(md.encode()), len(table)))
    print('checks passed: facts from the other files; no "<" or ">" outside code spans; own reader and %s (reader gfm) '
          'read all %d source cells equal to go.sh; pandoc finds no HTML element' % (version, len(seen)))


if __name__ == '__main__':
    main()
