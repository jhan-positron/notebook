#!/usr/bin/env python3
"""data_companions.py - writes the companion "<data file>.md" next to each result file of the 7200 MT/s rerun.

One companion = a part that this script computes from the data file itself (short version, file facts,
a table of what the file holds, the first lines copied from the file) + the explanation of the file type
(rows and columns) from types/<type>.md, which is the same text for every file of that type.

Every number in the computed part comes from the data file through the parsers of stat_k120.py and stat_bwx.py.
Usage: python3 data_companions.py [--check]     --check: build in memory, write nothing
Python 3 standard library only.
"""
import glob
import hashlib
import os
import statistics
import sys

sys.dont_write_bytecode = True
T = os.path.dirname(os.path.abspath(__file__))
C = os.path.normpath(os.path.join(T, '..', '..', '..'))
R = os.path.join(C, 'results')
S = os.path.join(C, 'tmp', 'agent-scratch', 'w120-7200-2026-11-17')
sys.path.insert(0, S)
import stat_bwx    # noqa: E402  the parser of the bwx csv files that the analysis uses
import stat_k120   # noqa: E402  the parser of threads120.csv that the analysis uses

WRITTEN = []


def die(msg):
    sys.exit('data_companions.py: ERROR: ' + msg)


def one(pattern):
    hits = sorted(glob.glob(pattern))
    if len(hits) != 1:
        die('%d matches for %s' % (len(hits), pattern))
    return hits[0]


def read_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines, hashlib.sha256(raw).hexdigest(), len(raw)


def type_text(name):
    path = os.path.join(os.environ.get('TYPES_DIR', os.path.join(T, 'types')), name + '.md')
    if not os.path.isfile(path):
        die('missing type explanation ' + path)
    with open(path) as f:
        lines = f.read().strip().split('\n')
    # The companion has its own title and its own "Short version". The type text keeps its short part under another heading.
    while lines and (not lines[0].strip() or lines[0].startswith('# ')):
        lines.pop(0)
    for i, l in enumerate(lines):
        if l.startswith('```'):
            break
        if l.strip() == '## Short version':
            lines[i] = '## The file type in short'
            break
    text = '\n'.join(lines)
    if '## ' not in text:
        die(path + ' has no section heading')
    return text


def fence(lines, numbers):
    """Lines of the data file as a fenced block, each with its line number. The fence is longer than any run of backticks."""
    width = len(str(max(numbers))) if numbers else 1
    body = ['%s  %s' % (str(n).rjust(width), l) if l != '' else str(n).rjust(width) for n, l in zip(numbers, lines)]
    longest = max([len(m) for l in body for m in __import__('re').findall(r'`+', l)] + [2])
    f = '`' * (longest + 1)
    return [f + 'text'] + body + [f]


def facts_list(path, nlines, nbytes, sha, written_by, step):
    rel = os.path.relpath(path, C)
    return ['- File: `%s` in this folder (`crb/%s`).' % (os.path.basename(path), os.path.dirname(rel)),
            '- Size: %d lines, %d bytes. sha256 when this page was built: `%s`.' % (nlines, nbytes, sha),
            '- Written by: %s' % written_by,
            '- Step of the run: %s' % step]


def emit(path, title, short, facts, sections, typename):
    out = ['# `%s` explained: %s' % (os.path.basename(path), title), '', '## Short version', '']
    out += short + ['']
    out += ['## This file', ''] + facts + ['']
    for head, body in sections:
        out += ['## ' + head, ''] + body + ['']
    out += ['The sections below explain the file type. The same text stands in the companion of every file of this type.', '']
    out.append(type_text(typename))
    out.append('')
    text = '\n'.join(out)
    dest = path + '.md'
    if os.environ.get('OUT_DIR'):          # test mode: write into one folder, with the path in the name
        with open(os.path.join(os.environ['OUT_DIR'], os.path.relpath(dest, C).replace('/', '__')), 'w') as f:
            f.write(text)
    elif '--check' not in sys.argv:
        with open(dest, 'w') as f:
            f.write(text)
    WRITTEN.append((dest, len(text)))


def f2(x):
    return '%.2f' % x


def rng(vals):
    return '%s to %s GB/s' % (f2(min(vals)), f2(max(vals)))


# ----------------------------------------------------------------------------- the steps of the rerun

STEPS = [  # tag, kind, label
    ('T72A1', 'A', 'part A, session 1'), ('T72A2', 'A', 'part A, session 2'), ('T72A3', 'A', 'part A, session 3'),
    ('T72L1', 'L', 'part L, session 1'), ('T72L2', 'L', 'part L, session 2'), ('T72L3', 'L', 'part L, session 3'),
    ('T72C1', 'C', 'part C, session 1 (spec file cfwd.spec)'), ('T72C2', 'C', 'part C, session 2 (spec file crev.spec)'),
    ('T72C3', 'C', 'part C, session 3 (spec file cfwd.spec)'),
    ('T72C4', 'C', 'part C, the extra process after session 3 (spec file crev.spec)'),
    ('T72I1', 'I', 'control I, run 1 (started by go2.sh from an idle machine)'),
    ('T72I2', 'I', 'control I, run 2 (started by go2.sh from an idle machine)'),
]
RERUN = 'the whole-chip rerun at 7200 MT/s of 2026-11-17'

A_LABEL = {('bw_old', 'read'): 'old read kernel', ('bw_new', 'read'): 'new read kernel'}
B_LABEL = {'oldread': 'old read kernel', 'read': 'new read kernel',
           'asmread': 'asmread (hand-written load-only loop)',
           'read_nop96': 'test loop', 'read_nop256': 'test loop', 'read_1pl': 'test loop'}


def a_label(binary, kernel):
    if (binary, kernel) in A_LABEL:
        return A_LABEL[(binary, kernel)]
    if kernel == 'asmread':
        return 'asmread (hand-written load-only loop)'
    return 'not a read kernel'


# ----------------------------------------------------------------------------- part A: threads120.csv

def header_lines(lines):
    return [i for i, l in enumerate(lines, 1) if l.startswith('-- binary ')]


def threads120(folder, title, step, short_intro, written_by, extra_notes=()):
    path = os.path.join(folder, 'threads120.csv')
    lines, sha, nbytes = read_lines(path)
    procs = stat_k120.load(folder)
    heads = header_lines(lines)
    if len(heads) != len(procs):
        die('%s: %d header lines, %d processes' % (path, len(heads), len(procs)))
    rows = ['| Process | Header line | Binary | Kernel | Which kernel | Round | Load | Start (UTC) | Interval rates, GB/s |',
            '|---|---|---|---|---|---|---|---|---|']
    for i, (p, ln) in enumerate(zip(procs, heads), 1):
        rows.append('| %d | %d | `%s` | `%s` | %s | %d | %.2f | %s | %s |' % (
            i, ln, p['binary'], p['kernel'], a_label(p['binary'], p['kernel']), p['round'], p['load'], p['utc'] or '-',
            ', '.join(f2(iv[0]) for iv in p['iv'])))
    old = [iv[0] for p in procs if (p['binary'], p['kernel']) == ('bw_old', 'read') for iv in p['iv']]
    new = [iv[0] for p in procs if (p['binary'], p['kernel']) == ('bw_new', 'read') for iv in p['iv']]
    nint = sorted({len(p['iv']) for p in procs})
    short = [short_intro + ' It holds %d processes, each with %s timed intervals at %s threads.'
             % (len(procs), ' or '.join(str(x) for x in nint), ' or '.join(sorted({l.split(' threads ')[1].split()[0] for l in lines if l.startswith('-- binary ')})))]
    if old:
        short.append('The old read kernel (binary `bw_old`, kernel `read`) gave %s over its %d intervals (column `aggregate_GBps`, GB = 1e9 bytes).' % (rng(old), len(old)))
    if new:
        short.append('The new read kernel (binary `bw_new`, kernel `read`) gave %s over its %d intervals.' % (rng(new), len(new)))
    notes = ['- One row of the table is one process: one start of a benchmark binary with one kernel.',
             '- "Header line" is the line number of the `-- binary` line of the process in this file. The interval rows of the process follow it.',
             '- "Load" is the 1-minute load average that the script read directly before it started the process.',
             '- "Interval rates" are the values of the column `aggregate_GBps` of the interval rows (rep 0, 1, 2), in file order.',
             '- This table was computed from the file with the parser of `stat_k120.py`.'] + list(extra_notes)
    first = lines[:heads[1] - 1] if len(heads) > 1 else lines[:8]
    head = 'The first process of the file (copied from the file by a script)'
    if len(first) > 12:
        head = 'The first 12 lines of the file (copied from the file by a script; the first process has %d lines)' % len(first)
        first = first[:12]
    emit(path, title, short, facts_list(path, len(lines), nbytes, sha, written_by, step),
         [('What this file holds', rows + [''] + notes),
          (head, fence(first, list(range(1, len(first) + 1))))],
         'partA-threads120')


def probe(folder, title, step):
    path = os.path.join(folder, 'probe.txt')
    lines, sha, nbytes = read_lines(path)
    short = ['This file is the machine record of %s of %s.' % (title, RERUN),
             'The script `ra.sh` wrote it: the state of the machine before the first process, the sha256 values of the two binaries, and the load after the last process.']
    emit(path, title, short,
         facts_list(path, len(lines), nbytes, sha, '`ra.sh` (the script of part A), before the first process and after the last one.', step),
         [('The whole file (copied from the file by a script)', fence(lines, list(range(1, len(lines) + 1))))],
         'partA-probe')


# ----------------------------------------------------------------------------- bwx12 csv

def bwx_csv(folder, tag, title, step):
    csvs = sorted(glob.glob(os.path.join(folder, '*.csv')))
    if len(csvs) != 1:
        die('%s: %d csv files' % (folder, len(csvs)))
    path = csvs[0]
    lines, sha, nbytes = read_lines(path)
    rows_iv = stat_bwx.interval_rows(folder)
    kinds = {}
    first_of = {}
    for i, l in enumerate(lines, 1):
        if l.startswith('# page_read'):
            k = '# page_read'
        elif l.startswith('#'):
            k = '# header'
        else:
            k = l.split(',', 1)[0]
        kinds[k] = kinds.get(k, 0) + 1
        first_of.setdefault(k, i)
    i_line = {}
    for i, l in enumerate(lines, 1):
        p = l.split(',')
        if p[0] == 'I':
            i_line[(int(p[1]), int(p[2]), p[3])] = i
    table = ['| Round | Position | Kernel | Which kernel | Line of the I row | Thread rows | Sum over the thread rows, GB/s | `aggregate_GBps` of the I row, GB/s | Thread rows with a flag |',
             '|---|---|---|---|---|---|---|---|---|']
    for r in rows_iv:
        key = (r['round'], r['pos'], r['kernel'])
        table.append('| %d | %d | `%s` | %s | %s | %d | %s | %s | %d |' % (
            r['round'], r['pos'], r['kernel'], B_LABEL.get(r['kernel'], '-'), i_line.get(key, '-'), r['threads'],
            f2(r['total']), '-' if r['I_agg'] is None else f2(r['I_agg']), r['flagged']))
    seq = []
    for r in rows_iv:
        if r['round'] == rows_iv[0]['round']:
            seq.append(r['kernel'])
    rounds = sorted({r['round'] for r in rows_iv})
    short = ['This file is the output of one process of the runner `bwx12` at 120 threads: %s of %s.' % (title, RERUN),
             'The process timed the kernel sequence %s, %d times (%d intervals).' % (', '.join('`%s`' % k for k in seq), len(rounds), len(rows_iv))]
    parts = []
    for k, name in (('oldread', 'the old read kernel (`oldread`)'), ('read', 'the new read kernel (`read`)'), ('asmread', '`asmread` (a hand-written load-only loop)')):
        v = [r['total'] for r in rows_iv if r['kernel'] == k]
        if v:
            parts.append('%s gave %s' % (name, ' and '.join(f2(x) for x in v) if len(v) <= 3 else rng(v)))
    short.append('Summed over the 120 thread rows of each interval, in GB/s (GB = 1e9 bytes): ' + ', '.join(parts) + '.')
    notes = ['- One row of the table is one timed interval: one kernel, timed once, on all threads.',
             '- "Sum over the thread rows" is the sum over the T rows of the interval of bytes / elapsed_s / 1e9. This is the rate that the analysis of the rerun uses.',
             '- "`aggregate_GBps` of the I row" is the rate that `bwx12` itself printed for the interval.',
             '- "Thread rows with a flag" counts the T rows whose last field is not `-`.',
             '- This table was computed from the file with the parser of `stat_bwx.py`.',
             '- Lines of each kind in this file: ' + ', '.join('%d `%s`' % (kinds[k], k) for k in sorted(kinds)) + '.']
    heads = [i for i, l in enumerate(lines, 1) if l.startswith('#') and not l.startswith('# page_read')]
    sample_no = list(heads)
    for k in ('P', 'T', 'I', 'C', '# page_read'):
        if k in first_of:
            sample_no.append(first_of[k])
    sample_no = sorted(set(sample_no))
    sample = fence([lines[i - 1] for i in sample_no], sample_no)
    emit(path, title, short,
         facts_list(path, len(lines), nbytes, sha, 'the runner `bwx12` (its standard output). The script `rx.sh` started it and named the file after the tag `%s` of the spec file.' % os.path.basename(path)[:-4], step),
         [('What this file holds', table + [''] + notes),
          ('The header lines and the first row of each kind (copied from the file by a script)',
           ['The number at the left is the line number in the file.', ''] + sample)],
         'bwx12-csv')
    return path


def small_file(path, title, step, typename, written_by, what):
    lines, sha, nbytes = read_lines(path)
    short = ['This file is %s of %s of %s.' % (what, title, RERUN)]
    if nbytes == 0:
        short.append('The file is empty (0 bytes).')
        sections = [('The whole file', ['The file has no line.'])]
    else:
        sections = [('The whole file (copied from the file by a script)', fence(lines, list(range(1, len(lines) + 1))))]
    emit(path, title, short, facts_list(path, len(lines), nbytes, sha, written_by, step), sections, typename)


def main():
    for tag, kind, label in STEPS:
        step = '%s, folder tag `%s`.' % (label, tag)
        if kind == 'A':
            folder = one(os.path.join(R, 'k120-%s-*' % tag))
            threads120(folder, label, step,
                       'This file holds the results of %s of %s.' % (label, RERUN),
                       '`ra.sh` (one `-- binary` line per process) and the binaries `bw_old` and `bw_new` (all other lines).')
            probe(folder, label, step)
        else:
            folder = one(os.path.join(R, 'w120-%s-*' % tag))
            bwx_csv(folder, tag, label, step)
            small_file(os.path.join(folder, 'env.txt'), label, step, 'rx-env',
                       '`rx.sh` (the runner script), once, before it started the process.', 'the machine record')
            small_file(os.path.join(folder, 'launches.txt'), label, step, 'rx-launches',
                       '`rx.sh` (the runner script): one line before the process started and one line after it ended.', 'the launch record')
            small_file(os.path.join(folder, 'stderr.txt'), label, step, 'rx-stderr',
                       '`rx.sh` (the runner script) sent the error output of `bwx12` to this file.', 'the error output of `bwx12`')
    base = [('partA-A1', 'row A-2 of the baseline list: the 12 processes of `results/partA-20261113T205055Z/A1.csv`',
             'the `sed` command in `baselines-and-rules.txt`. It rewrote the header line of each process of the original file and changed no other line.',
             []),
            ('partA-A3-onebuf500', 'row A-3 of the baseline list: the three `onebuf-ms500` processes of `results/partA-20261113T205055Z/A3.csv`',
             'the `awk` and `sed` commands in `baselines-and-rules.txt`. `awk` kept 3 of the 12 processes of the original file. `sed` rewrote their header lines.',
             ['- In this copy the column "Round" holds the repeat number (1 to 3) of the tag `onebuf-ms500-1` to `-3`. It is not a round of a script.'])]
    for sub, what, by, extra in base:
        folder = os.path.join(S, 'base8000', sub)
        threads120(folder, '8000 MT/s baseline copy, ' + sub,
                   'Not a step of the rerun. A converted copy of 8000 MT/s data of 2026-11-13 (%s).' % what,
                   'This file is a converted copy of 8000 MT/s results of 2026-11-13, made for the comparison with the rerun: %s.' % what,
                   by, extra)
    for dest, size in WRITTEN:
        print('%s %s (%d bytes)' % ('checked' if '--check' in sys.argv else 'wrote', dest, size))
    print(len(WRITTEN), 'companions')


if __name__ == '__main__':
    main()
