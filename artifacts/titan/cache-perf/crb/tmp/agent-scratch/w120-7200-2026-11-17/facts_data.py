#!/usr/bin/env python3
"""facts_data.py - parsers and the data model for the facts sheet of the 7200 MT/s rerun (2026-11-17).

Used by build_facts.py. It reads raw result files and writes nothing.

R = results folder, S = scratch folder of this task (both derived from the location of this file).
GB = 1e9 bytes everywhere.

Two kinds of rate exist in the raw files, and this module never mixes them:
- part A (binaries bw_old, bw_new of bandwidth.c): the column aggregate_GBps of the csv
  (the binary computes it as sum(bytes) / max(per-thread elapsed_s)).
- bwx runners (bwx12, bwx11, bwx): sum over the T rows (threads) of bytes / elapsed_s / 1e9,
  the method of stat_bwx.py.
"""
import datetime as dt
import glob
import hashlib
import os
import re
import statistics
import sys

sys.dont_write_bytecode = True

S = os.path.dirname(os.path.abspath(__file__))
CRB = os.path.normpath(os.path.join(S, '..', '..', '..'))
R = os.path.join(CRB, 'results')
W15 = os.path.join(CRB, 'tmp', 'agent-scratch', 'w120-2026-11-15')
K13 = os.path.join(CRB, 'tmp', 'agent-scratch', 'kernels-2026-11-13')
DIMM_REPORT = os.path.normpath(os.path.join(CRB, '..', '..', '..', 'machines', 'arm-crb', 'DIMM-flaky-report.md'))

sys.path.insert(0, S)
import stat_bwx    # noqa: E402  (existing tool, used as a cross-check)
import stat_k120   # noqa: E402  (existing tool, used as a cross-check)

OPENED = []  # every file that a reader of this module opened, in order (for the file list of the facts sheet)


def _open(path, mode='r'):
    path = os.path.abspath(path)
    if path not in OPENED:
        OPENED.append(path)
    return open(path, mode)


def rel(path):
    """Path as written in the facts sheet: R/... or S/..."""
    path = os.path.abspath(path)
    for name, root in (('R', R), ('S', S)):
        if path.startswith(root + os.sep):
            return name + '/' + os.path.relpath(path, root)
    return path


def sha256(path):
    h = hashlib.sha256()
    with _open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def folder_date(folder):
    """Date and time in a folder name such as k120-T72A1-20261117T221209Z."""
    m = re.search(r'(\d{8})T(\d{6})Z', os.path.basename(folder))
    return dt.datetime.strptime(m[1] + m[2], '%Y%m%d%H%M%S')


def clock(folder, hms):
    """HH:MM:SS of a run file -> datetime, with the date of the folder name (next day if earlier)."""
    base = folder_date(folder)
    t = dt.datetime.combine(base.date(), dt.datetime.strptime(hms, '%H:%M:%S').time())
    if t < base - dt.timedelta(seconds=1):
        t += dt.timedelta(days=1)
    return t


# ----------------------------------------------------------------------------- logs and state files

STATE = re.compile(r'^== (.+?) utc (\S+) boot (\S+) MemTotal: (\d+) kB load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) '
                   r'users (\d+) marker (\S+) processes per user:\s*(.*)$')


def read_log(path):
    """State lines and the other '== ' lines of a go.sh or go2.sh log."""
    out = dict(path=path, states=[], other={}, lines=[], alldone=False, failed=[])
    with _open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            out['lines'].append(line)
            m = STATE.match(line)
            if m:
                users = {}
                for part in m[13].split(';'):
                    part = part.strip()
                    if part:
                        n, name = part.split()
                        users[name] = int(n)
                out['states'].append(dict(
                    label=m[1], utc=dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%SZ'), boot=m[3], memtotal_kB=int(m[4]),
                    load1=float(m[5]), load5=float(m[6]), load15=float(m[7]), runnable=int(m[8]), tasks=int(m[9]),
                    logins=int(m[11]), marker=m[12], procs=users, line=ln, file=path))
            elif line.startswith('== cmdline '):
                out['other']['cmdline'] = (line[len('== cmdline '):], ln)
            elif line.startswith('== governors'):
                out['other']['governors'] = (line[3:], ln)
            elif line.startswith('== thp '):
                out['other']['thp'] = (line[3:], ln)
            elif line.startswith('== affinity'):
                out['other']['affinity'] = (line[3:], ln)
            elif line == 'ALLDONE':
                out['alldone'] = True
            elif line.startswith('FAILED'):
                out['failed'].append(line)
    return out


def read_probe(path):
    """probe.txt of ra.sh (part A)."""
    txt = _open(path).read()
    m1 = re.search(r'## host=\S+ utc=(\S+) load_before=(\S+) (\S+) (\S+) logins=(\d+) name=(\S+)', txt)
    m2 = re.search(r'## boot_id=(\S+) MemTotal: (\d+) kB runnable=(\d+)', txt)
    m3 = re.search(r'## kernel=(\S+) thp=(.*)', txt)
    m4 = re.search(r'## load_after=(\S+) (\S+) (\S+) utc=(\S+) MemTotal: (\d+) kB', txt)
    shas = dict((os.path.basename(n), h) for h, n in re.findall(r'^([0-9a-f]{64})  (\S+)$', txt, re.M))
    pcpu = [float(x) for x in re.findall(r'^\s*(\d+\.\d+) \S+\s+\S+', txt, re.M)]
    T = lambda s: dt.datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
    return dict(path=path, utc=T(m1[1]), load_before=(float(m1[2]), float(m1[3]), float(m1[4])), logins=int(m1[5]),
                name=m1[6], boot=m2[1], memtotal_kB=int(m2[2]), runnable=int(m2[3]), kernel=m3[1], thp=m3[2].strip(),
                load_after=(float(m4[1]), float(m4[2]), float(m4[3])), utc_after=T(m4[4]), memtotal_after_kB=int(m4[5]),
                sha=shas, pcpu_max=max(pcpu) if pcpu else None)


LAUNCH = re.compile(r'^launch (\S+) utc (\S+) load (\S+) (\S+) (\S+) (\d+)/(\d+) (\d+) users (\d+) args (.*)$')
RC = re.compile(r'^rc (\S+) (\S+) utc (\S+)$')


def read_launches(folder):
    """launches.txt of rx.sh: one dict per launch, with its rc line."""
    out = []
    with _open(os.path.join(folder, 'launches.txt')) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            m = LAUNCH.match(line)
            if m:
                out.append(dict(tag=m[1], utc=clock(folder, m[2]), load1=float(m[3]), load5=float(m[4]),
                                load15=float(m[5]), runnable=int(m[6]), tasks=int(m[7]), logins=int(m[9]), args=m[10],
                                rc=None, rc_utc=None, line=ln))
                continue
            m = RC.match(line)
            if m:
                for la in out:
                    if la['tag'] == m[2] and la['rc'] is None:
                        la['rc'] = m[1]
                        la['rc_utc'] = clock(folder, m[3])
                        break
    return out


def read_env(folder):
    """env.txt of rx.sh."""
    lines = _open(os.path.join(folder, 'env.txt')).read().splitlines()
    m = None
    for l in lines:
        m = re.match(r'binary (\S+) ([0-9a-f]{64})', l) or m
    pcpu = [float(x) for x in re.findall(r'^\S+\s+(\d+(?:\.\d+)?) \S+', '\n'.join(lines[3:]), re.M)]
    # the process list of `ps -eo user,pcpu,comm --sort=-pcpu | head -6`: (user, %CPU, command, line number)
    top = [(t[1], float(t[2]), t[3], ln) for ln, t in ((ln, re.match(r'^(\S+)\s+(\d+(?:\.\d+)?) (\S+)', l))
                                                      for ln, l in enumerate(lines, 1) if ln > 3) if t]
    start = dt.datetime.strptime(lines[0], '%a %b %d %I:%M:%S %p UTC %Y')
    return dict(start=start, kernel=lines[1], loadavg=lines[2], binary=m[1] if m else None, sha=m[2] if m else None,
                pcpu_max=max(pcpu) if pcpu else None, top=top, n_lines=len(lines))


def read_error_records(path):
    """Hardware error records of a saved journal. One record = one line
    'Hardware error from APEI Generic Hardware Error Source'. Returns line, time, record number, severity."""
    out, by_id = [], {}
    with _open(path) as f:
        for ln, l in enumerate(f, 1):
            m = re.match(r'(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: (.*)$', l.rstrip('\n'))
            if not m:
                continue
            if m[3].startswith('Hardware error from APEI'):
                rec = dict(line=ln, utc=dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S'), id=int(m[2]), severity=None)
                out.append(rec)
                by_id[int(m[2])] = rec
            s = re.match(r'event severity: (\S+)', m[3])
            if s and int(m[2]) in by_id and by_id[int(m[2])]['severity'] is None:
                by_id[int(m[2])]['severity'] = s[1]
    return out


def step_headers(path):
    """Every '-- step' line of a run_partA.sh csv: line, tag, binary, kernel, launch time."""
    out = []
    folder = os.path.dirname(path)
    with _open(path) as f:
        for ln, l in enumerate(f, 1):
            m = HDR_STEP.match(l.rstrip('\n'))
            if m:
                out.append(dict(line=ln, tag=m[2], binary=m[3], kernel=re.search(r'--kernel (\S+)', m[12])[1],
                                utc=clock(folder, m[11]), args=m[12], load1=float(m[5]), step=m[1]))
    return out


def read_try6():
    """R/dimm7200-20261117/try6.txt: the record of 12 modules at 7200 MT/s in the boot of the rerun."""
    path = os.path.join(R, 'dimm7200-20261117', 'try6.txt')
    lines = _open(path).read().splitlines()
    out = dict(path=path, utc=dt.datetime.strptime(lines[0], '%Y-%m-%dT%H:%M:%SZ'), boot=lines[1].strip(),
               utc_line=1, boot_line=2, n_lines=len(lines))
    for ln, l in enumerate(lines, 1):
        m = re.match(r'MemTotal:\s+(\d+) kB', l)
        if m:
            out['memtotal_kB'], out['memtotal_line'] = int(m[1]), ln
        m = re.search(r'This system has (\d+) DIMM sockets', l)
        if m:
            out['dimm_sockets'], out['dimm_line'] = int(m[1]), ln
        m = re.match(r'\s*(\d+)\s+Configured Memory Speed: (\d+) MT/s', l)
        if m:
            out['speed_count'], out['speed_MTps'], out['speed_line'] = int(m[1]), int(m[2]), ln
        m = re.match(r'hwerr=(\d+)', l)
        if m:
            out['hwerr'], out['hwerr_line'] = int(m[1]), ln
    # gaps.txt and boots.txt number the boots of the journal; row 0 must be the boot of try6.txt
    boots = os.path.join(R, 'dimm7200-20261117', 'boots.txt')
    row0 = [(ln, l.split()) for ln, l in enumerate(_open(boots), 1) if l.split()[:1] == ['0']]
    if len(row0) != 1 or row0[0][1][1] != out['boot'].replace('-', ''):
        sys.exit('boots.txt: row 0 is not the boot of try6.txt')
    out['boots_path'], out['boots_line'] = boots, row0[0][0]
    f = row0[0][1]              # 0 <boot id> Tue 2026-11-17 20:02:21 UTC Tue 2026-11-17 20:06:19 UTC
    if len(f) != 10 or f[5] != 'UTC' or f[9] != 'UTC':
        sys.exit('boots.txt: row 0 has another form than expected')
    out['boots_first'] = dt.datetime.strptime(f[3] + ' ' + f[4], '%Y-%m-%d %H:%M:%S')
    out['boots_last'] = dt.datetime.strptime(f[7] + ' ' + f[8], '%Y-%m-%d %H:%M:%S')
    # first kernel log line of this boot (gaps.txt, row "0 first=...")
    gaps = os.path.join(R, 'dimm7200-20261117', 'gaps.txt')
    for ln, l in enumerate(_open(gaps), 1):
        m = re.match(r'0 first=(\S+)\+00:00 last=(\S+)\+00:00 dimm=has (\d+) DIMM hwerr=(\d+) ', l)
        if m:
            out['first_log_utc'] = dt.datetime.strptime(m[1], '%Y-%m-%dT%H:%M:%S')
            out['last_log_utc'] = dt.datetime.strptime(m[2], '%Y-%m-%dT%H:%M:%S')
            out['gaps_dimm'], out['gaps_hwerr'] = int(m[3]), int(m[4])
            out['gaps_path'], out['gaps_line'] = gaps, ln
            continue
        # lines after row 0: output of `uptime` and of the process list, taken when gaps.txt was written
        m = re.match(r'\s*(\d\d:\d\d:\d\d) up ', l)
        if m and 'first_log_utc' in out:
            out['gaps_uptime_utc'] = dt.datetime.combine(out['first_log_utc'].date(),
                                                         dt.datetime.strptime(m[1], '%H:%M:%S').time())
            out['gaps_uptime_line'] = ln
        m = re.match(r'(\S+)\s+(\d+\.\d+) (\S+)$', l.rstrip())
        if m and 'gaps_uptime_utc' in out:
            out.setdefault('gaps_top', []).append((m[1], float(m[2]), m[3], ln))
    return out


# ----------------------------------------------------------------------------- part A files (bandwidth.c)

HDR_STEP = re.compile(r'-- step (\S+) tag (\S+) binary (\S+) waited_s (\S+) loadavg (\S+) (\S+) (\S+) (\d+)/(\d+) '
                      r'logins (\d+) utc (\S+) args (.*)$')


def read_k120(path, only_tags=None):
    """Processes of a bandwidth.c csv. Header lines are '-- binary ...' (run_kernels.sh, ra.sh)
    or '-- step ...' (run_partA.sh). Returns the processes in file order."""
    procs, cur = [], None
    with _open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            m = stat_k120.HDR.match(line)
            if m:
                cur = dict(file=path, hdr_line=ln, binary=m[1], kernel=m[2], round=int(m[6]), load1=float(m[7]),
                           utc=m[8], tag=None, args=None, iv=[], hdr_threads=m[3], hdr_cpus=m[4], hdr_bytes=m[5])
                procs.append(cur)
                continue
            m = HDR_STEP.match(line)
            if m:
                k = re.search(r'--kernel (\S+)', m[12])[1]
                rd = re.search(r'-r?(\d+)$', m[2])
                cur = dict(file=path, hdr_line=ln, binary=m[3], kernel=k, round=int(rd[1]), load1=float(m[5]),
                           utc=m[11], tag=m[2], args=m[12], iv=[])
                if only_tags is None or only_tags(m[2]):
                    procs.append(cur)
                else:
                    cur['skip'] = True
                continue
            if cur is not None and line.startswith('# bandwidth:'):
                # header line that the binary prints: it says how the copy kernels count their bytes
                cur['copy_note'] = 'copy counts read+write bytes' in line
                cur['bw_hdr'] = line.split('; ')[-1]       # threads=... bytes_per_thread=... min_ms=... thp=...
                continue
            p = line.split(',')
            if cur is not None and p[0] == 'thread' and len(p) == 6:
                # row of the option --per-thread: thread,index,cpu,kernel,rep,GBps
                cur.setdefault('thr', {}).setdefault(int(p[4]), []).append(float(p[5]))
                continue
            if cur is not None and len(p) > 9 and p[3].isdigit():
                if p[0] != cur['kernel'] and cur['kernel'] != 'all':
                    sys.exit(f'{path}:{ln}: interval line does not belong to the header line before it')
                cur['iv'].append(dict(rep=int(p[3]), total_bytes=int(p[4]), elapsed_s=float(p[5]), agg=float(p[6]),
                                      tmin=float(p[7]), tmax=float(p[8]), tavg=float(p[9]),
                                      passes=int(p[4]) // int(p[2]), threads=int(p[1]), line=ln, kernel=p[0]))
    return procs


# ----------------------------------------------------------------------------- bwx csv files

def _new_section(path, step=None, line=None):
    return dict(file=path, step=step, step_line=line, hdr={}, T={}, Tl={}, I={}, P=[], C=0)


def read_bwx(path):
    """Sections of a bwx csv. A file of rx.sh has one section. A file of run_bwx.sh (B7, C3, B5)
    has one section per '-- step' line."""
    secs, cur = [], None
    with _open(path) as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip('\n')
            if line.startswith('-- step'):
                m = HDR_STEP.match(line)
                cur = _new_section(path, dict(step=m[1], tag=m[2], binary=m[3], load1=float(m[5]), load5=float(m[6]),
                                              load15=float(m[7]), runnable=int(m[8]), logins=int(m[10]), utc=m[11],
                                              args=m[12]), ln)
                secs.append(cur)
                continue
            if cur is None:
                cur = _new_section(path)
                secs.append(cur)
            if line.startswith('#'):
                if line.startswith('# bandwidth:') or line.startswith('# bwx:'):
                    for key in ('min_ms', 'thp', 'seq', 'rounds', 'stop', 'start', 'two_buffers', 'count'):
                        m = re.search(r'\b%s=([^\s;]+)' % key, line)
                        if m and key not in cur['hdr']:
                            cur['hdr'][key] = m[1]
                continue
            p = line.split(',')
            if p[0] == 'T':
                if len(p) != 13:
                    sys.exit(f'{path}:{ln}: a T row with {len(p)} fields, 13 expected')
                # cpu, bytes, elapsed_s, flags, t_start_s, t_end_s (seconds since the process start)
                cur['T'].setdefault((int(p[1]), int(p[2]), p[3]), []).append(
                    (int(p[5]), int(p[6]), float(p[7]), p[-1], float(p[9]), float(p[10])))
                tl = cur['Tl'].setdefault((int(p[1]), int(p[2]), p[3]), [ln, ln])
                tl[1] = ln
            elif p[0] == 'I':
                cur['I'][(int(p[1]), int(p[2]), p[3])] = dict(threads=int(p[5]), total_bytes=int(p[6]),
                                                             max_elapsed_s=float(p[7]), agg=float(p[8]), line=ln)
            elif p[0] == 'P':
                cur['P'].append(tuple([int(p[1]), int(p[2]), int(p[3]), p[4]] + [int(x) for x in p[5:11]]))
            elif p[0] == 'C':
                cur['C'] += 1
    return secs


def bwx_intervals(sec):
    """One dict per interval (round, pos, kernel) of a section, in file order."""
    seq = sec['hdr'].get('seq', '').split(',')
    out = []
    for (rnd, pos, kernel), tl in sec['T'].items():
        rate = lambda t: t[1] / t[2] / 1e9
        m0 = [rate(t) for t in tl if t[0] < 64]
        m1 = [rate(t) for t in tl if t[0] >= 64]
        cpus = [t[0] for t in tl]
        i = sec['I'].get((rnd, pos, kernel))
        if pos > 0:
            before = seq[pos - 1]
        elif rnd > 0:
            before = seq[-1]
        else:
            before = None
        assert seq[pos] == kernel, (sec['file'], rnd, pos, kernel, seq)
        out.append(dict(round=rnd, pos=pos, kernel=kernel, kernel_before=before, threads=len(tl),
                        total=sum(m0) + sum(m1), mesh0=sum(m0), mesh1=sum(m1), n0=len(m0), n1=len(m1),
                        m0_min=min(m0) if m0 else None, m0_max=max(m0) if m0 else None,
                        m1_min=min(m1) if m1 else None, m1_max=max(m1) if m1 else None,
                        is_64_56=(len(m0) == 64 and len(m1) == 56 and max(cpus) <= 119 and len(set(cpus)) == 120),
                        flagged=sum(t[3] != '-' for t in tl), flags=sorted(set(t[3] for t in tl)),
                        I_agg=i['agg'] if i else None, line=i['line'] if i else None,
                        max_elapsed_s=i['max_elapsed_s'] if i else None,
                        t_start=min(t[4] for t in tl), t_end=max(t[5] for t in tl),
                        T_first=sec['Tl'][(rnd, pos, kernel)][0], T_last=sec['Tl'][(rnd, pos, kernel)][1]))
    return out


# ----------------------------------------------------------------------------- the data sets

RERUN_A = [('T72A1', 1), ('T72A2', 2), ('T72A3', 3)]
RERUN_L = [('T72L1', 1), ('T72L2', 2), ('T72L3', 3)]
RERUN_C = [('T72C1', 1, 'cfwd'), ('T72C2', 2, 'crev'), ('T72C3', 3, 'cfwd'), ('T72C4', None, 'crev')]
RERUN_I = [('T72I1', 1), ('T72I2', 2)]

SHA_NAMES = {  # short names of the binaries, by sha256 prefix, as the result files record them
    'e8fc0205': 'bw_old', 'fd7c14df': 'bw_new', 'cd58e564': 'bwx12', 'f1215f9e': 'bwx11', '5b702073': 'bwx'}


def find(prefix):
    """The one result folder whose name starts with prefix."""
    hits = sorted(glob.glob(os.path.join(R, prefix + '-2026*')))
    if len(hits) != 1:
        sys.exit(f'expected one folder for {prefix}, found {hits}')
    return hits[0]


def read_boot_table():
    """Boot history of the DIMM report (section 3): list of (boot number, Linux start, modules),
    and the time until which the memory speed setting was 8000 MT/s."""
    path = DIMM_REPORT
    boots, until = [], None
    for ln, line in enumerate(_open(path), 1):
        m = re.match(r'\| (-?\d+) \| (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) \| \**(\d+)\** \|', line)
        if m:
            boots.append(dict(no=int(m[1]), start=dt.datetime.strptime(m[2], '%Y-%m-%d %H:%M'), modules=int(m[3]),
                              line=ln))
        m = re.match(r'\| Memory speed until (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) UTC \| (\d+) MT/s', line)
        if m:
            until = dict(utc=dt.datetime.strptime(m[1], '%Y-%m-%d %H:%M'), speed=int(m[2]), line=ln)
    return dict(path=path, boots=sorted(boots, key=lambda b: b['start']), until=until)


def base_record(**kw):
    """One flat interval record of facts.json. Every record has every key."""
    rec = dict(dataset=None, part=None, role=None, speed_MTps=None, modules=None, boot=None,
               folder=None, file=None, line=None, tag=None, session=None, process=None, proc_key=None, round=None,
               pos=None, interval=None, kernel=None, kernel_before=None, binary=None, binary_sha256=None, GBps=None,
               rate_kind=None, mesh0_GBps=None, mesh1_GBps=None, passes=None, per_thread_min_GBps=None,
               per_thread_max_GBps=None, per_thread_avg_GBps=None, threads=None, is_64_56=None, flagged=None,
               stop=None, start=None, min_ms=None, count=None, thp=None, load1_at_launch=None, launch_utc=None,
               gap_s=None, start_state=None)
    unknown = set(kw) - set(rec)
    assert not unknown, unknown
    rec.update(kw)
    return rec


KIND_A = 'aggregate_GBps column of the csv (sum of bytes / longest per-thread time)'
KIND_X = 'sum over the T rows (threads) of bytes / elapsed_s / 1e9'


# ----------------------------------------------------------------------------- selection and statistics

def sel(recs, **cond):
    """Records that match every condition. A condition value may be a value, a set, or a function."""
    out = []
    for r in recs:
        for k, v in cond.items():
            x = r[k]
            if callable(v):
                ok = v(x)
            elif isinstance(v, (set, frozenset, list, tuple)):
                ok = x in v
            else:
                ok = x == v
            if not ok:
                break
        else:
            out.append(r)
    return out


def rng(rs, key='GBps'):
    """min, max, median, number of intervals and number of processes of a list of records."""
    v = [r[key] for r in rs]
    if not v:
        return None
    return dict(lo=min(v), hi=max(v), med=statistics.median(v), n=len(v), procs=len({r['proc_key'] for r in rs}),
                sessions=len({r['session'] for r in rs if r['session'] is not None}),
                boots=len({r['boot'] for r in rs}))


def overlap(a, b):
    return a['lo'] <= b['hi'] and b['lo'] <= a['hi']


def gap(a, b):
    """Distance between the nearest ends of two ranges, GB/s. Positive: a is above b. Zero: they overlap."""
    if a['lo'] > b['hi']:
        return a['lo'] - b['hi']
    if a['hi'] < b['lo']:
        return a['hi'] - b['lo']
    return 0.0


def width_pct(a):
    return (a['hi'] - a['lo']) / a['lo'] * 100
