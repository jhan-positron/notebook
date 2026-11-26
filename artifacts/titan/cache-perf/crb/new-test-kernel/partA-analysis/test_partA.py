#!/usr/bin/env python3
"""test_partA.py [--keep DIR]

Builds synthetic Part A result folders in the format of run_partA.sh and bandwidth.c --per-thread,
runs analyze_partA.py and make_partA_html.py on them, and checks the computed values.
All rates in these folders are invented. They are test input, not measurements.

Two data sets:
  set 1 "clean":  split and uniform thread distributions, a killed block that a later folder repeats,
                  a skipped A3, a level change inside one A5 process, a second A5 process that waited.
  set 2 "mixed":  thread distributions between the two limits, so that q does not fall into two groups.
                  A3 is present. A6 is missing.
With --keep DIR the folders, the two json files and the two pages stay in DIR.
"""
import os, sys, json, shutil, tempfile, re
sys.dont_write_bytecode = True
BANNER = 'SYNTHETIC TEST DATA. Every rate on this page is invented by test_partA.py. It is not a measurement.'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_partA as A
import make_partA_html as H

MIB = 1 << 20
HEAD = 'kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps'


def cpulist(a, b):
    return list(range(a)) + list(range(64, 64 + b))


def cpustr(a, b):
    return ','.join(x for x in ([f'0-{a-1}'] if a else []) + ([f'64-{64+b-1}'] if b else []))


def jit(i, amp):
    return ((i * 37) % 11 - 5) * amp / 5.0


def split(m0, m1, amp=0.0):
    return lambda i, cpu, rep: (m0 if cpu < 64 else m1) + jit(i + rep, amp)


def flat(v, amp=0.0):
    return lambda i, cpu, rep: v + jit(i + rep, amp)


class Folder:
    def __init__(self, root, name, steps, skipped_a3=False, a7=False):
        self.d = os.path.join(root, name); os.makedirs(self.d)
        self.n = 0
        with open(os.path.join(self.d, 'env.txt'), 'w') as f:
            f.write(f'## host=ubuntu utc=2026-01-01T00:00:00Z loadavg=0.08 0.10 0.09 1/1400 5321 logins=1 steps={steps}\n'
                    '## thp=[always] madvise never defrag=always defer defer+madvise [madvise] never\n'
                    '## uptime=1000.00 MemFree: 500000000 kB MemAvailable: 510000000 kB \n'
                    '## busiest processes (pcpu user comm):\n%CPU USER     COMMAND\n 0.3 root     kworker\n 0.1 jhan     sshd\n'
                    '## sha256:\naaaa  bw_old\nbbbb  bw_new\ncccc  run_partA.sh\n## vmstat thp:\nthp_fault_alloc 10\n')
            if skipped_a3:
                f.write('A3 skipped: MemAvailable is 61 GiB, below 70 GiB\n')
            f.write('## end utc=2026-01-01T00:30:00Z loadavg=30.10 20.00 9.00 1/1400 9999\n')
        open(os.path.join(self.d, 'stderr.txt'), 'w').close()
        if a7:
            open(os.path.join(self.d, 'A7-sve.txt'), 'w').write('## sve_default_vector_length (bytes):\n16\n')
            open(os.path.join(self.d, 'A7-perf-list.txt'), 'w').write('  cycles\n  instructions\n')
            open(os.path.join(self.d, 'A7-pmu-devices.txt'), 'w').write('armv8_pmuv3_0\n')
            open(os.path.join(self.d, 'A7-core-events.txt'), 'w').write('== /sys/bus/event_source/devices/armv8_pmuv3_0 type=10\n/sys/x/events/l1d_cache_refill:event=0x03\n')

    def block(self, step, tag, binary, cpus, nbytes, min_ms, kernels, reps, fn, passes, args, waited=0, load='0.50 0.40 0.30 1/1400',
              thp='madvise', kill_after=None, fail=False, foreign=None):
        """kernels: list of kernel names. fn(kernel) -> f(i, cpu, rep) -> rate. passes(kernel, rep) -> passes per thread."""
        self.n += 1
        utc = f'00:{self.n // 60:02d}:{self.n % 60:02d}'
        with open(os.path.join(self.d, 'launches.txt'), 'a') as f:
            f.write(f'== {step}.csv {tag} utc {utc} loadavg {load} logins 1\n%CPU USER     COMMAND\n')
            f.write(foreign or ' 0.3 root     kworker/3:1\n 0.2 root     systemd\n 0.1 jhan     sshd\n 0.0 root     rcu_sched\n 0.0 root     ksoftirqd\n')
        out = [f'-- step {step} tag {tag} binary {binary} waited_s {waited} loadavg {load} logins 1 utc {utc} args {args}',
               f'# bandwidth: GB = 1e9 bytes; aggregate_GBps = sum(bytes) / max(per-thread elapsed_s); copy counts read+write bytes; '
               f'threads={len(cpus)} bytes_per_thread={nbytes} min_ms={min_ms} thp={thp}', HEAD]
        n = len(cpus)
        for k in kernels:
            f = fn(k); best = 0; lines = []
            for rep in range(reps):
                r = [round(f(i, c, rep), 2) for i, c in enumerate(cpus)]
                agg = round(sum(r) * (0.99 if n > 1 else 1), 2); best = max(best, agg)
                total = int(passes(k, rep) * n * nbytes * (2 if 'copy' in k else 1))
                lines.append(f'{k},{n},{nbytes},{rep},{total},{min_ms/1000*1.1:.4f},{agg:.2f},{min(r):.2f},{max(r):.2f},{sum(r)/n:.2f}')
            lines.append(f'{k},{n},{nbytes},best,,,{best:.2f},,,')
            if '--per-thread' in args:
                for i, c in enumerate(cpus):
                    for rep in range(reps):
                        lines.append(f'thread,{i},{c},{k},{rep},{f(i, c, rep):.2f}')
            out += lines
        if kill_after is not None:
            out = out[:kill_after] + [out[kill_after][:7], f'-- killed tag {tag} status 4 utc {utc}']      # one cut line, as after a kill
        if fail:
            out = out[:3] + [f'-- failed tag {tag} exit 1']
        with open(os.path.join(self.d, f'{step}.csv'), 'a') as f:
            f.write('\n'.join(out) + '\n')


def all_args(a, b, kernel, reps, ms):
    return f'--threads {a+b} --cpus {cpustr(a, b)} --bytes 256M --per-thread --kernel {kernel} --reps {reps} --min-ms {ms}'


K6 = ['read_old', 'read_new', 'asmread', 'write_old', 'write_new', 'asmwrite']


def ker(k): return {'read_old': 'read', 'read_new': 'read', 'write_old': 'write', 'write_new': 'write'}.get(k, k)
def binof(k): return 'bw_old' if k in ('read_old', 'write_old') else 'bw_new'


def long_steps(F, rates, a2_kill=True, a3=None, a4=None, load2='31.20 12.00 5.00 2/1500'):
    """rates: kernel name -> rate function. Writes A1, A2, optionally A3, and A4 into folder F."""
    cp = cpulist(64, 56)
    for rnd in (1, 2):
        for k in (K6 if rnd == 1 else K6[::-1]):
            F.block('A1', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, 500, [ker(k)], 3, lambda _k, k=k: rates[k], lambda _k, rep: 5,
                    all_args(64, 56, ker(k), 3, 500), load='0.50 0.40 0.30 1/1400' if (rnd, k) == (1, 'read_old') else load2,
                    waited=0 if (rnd, k) == (1, 'read_old') else 4,
                    foreign=' 99.0 other    busy_job\n 0.3 root     kworker/3:1\n 0.2 root     systemd\n 0.1 jhan     sshd\n 0.0 root     rcu_sched\n' if (rnd, k) == (2, 'asmread') else None)
    for rnd in (1, 2):
        for k in (K6 if rnd == 1 else K6[::-1]):
            ms = 6000 if 'read' in k else 15000
            # round 2 runs in the reversed order, so read_old-r2 is the last launch of A2: it is the killed one
            if a2_kill and (rnd, k) == (2, 'read_old'):
                F.block('A2', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, ms, [ker(k)], 3, lambda _k, k=k: rates[k], lambda _k, rep: 60,
                        all_args(64, 56, ker(k), 3, ms), load=load2, kill_after=5)
                continue
            # read_new round 1 repetition 2 gets 48 passes: it must be marked
            F.block('A2', f'{k}-r{rnd}', binof(k), cp, 256 * MIB, ms, [ker(k)], 3, lambda _k, k=k: rates[k],
                    lambda _k, rep, k=k, rnd=rnd: 48 if (k, rnd, rep) == ('read_new', 1, 2) else 60, all_args(64, 56, ker(k), 3, ms), load=load2)
    if a3:
        for ms in (500, 6000):
            for i in (1, 2, 3):
                F.block('A3', f'onebuf-ms{ms}-{i}', 'bw_old', cp, 256 * MIB, ms, ['read'], 3, lambda _k: a3['one'], lambda _k, rep: 60,
                        all_args(64, 56, 'read', 3, ms), load=load2)
                F.block('A3', f'twobuf-ms{ms}-{i}', 'bw_old', cp, 256 * MIB, ms, ['read', 'write', 'copy'], 3,
                        lambda k: a3['two'] if k == 'read' else flat(1.2, 0.02), lambda k, rep: 40 if k == 'copy' else 60, all_args(64, 56, 'all', 3, ms), load=load2)
    for a, b in ((64, 0), (64, 16), (64, 32), (64, 40), (64, 48), (64, 52), (64, 56), (32, 32), (40, 40), (48, 48), (56, 56)):
        for k in ('read_old', 'asmread'):
            F.block('A4', f'{k}-{a}+{b}', binof(k), cpulist(a, b), 256 * MIB, 6000, [ker(k)], 2, lambda _k, k=k, a=a, b=b: a4(k, a, b),
                    lambda _k, rep: 70, f'--threads {a+b} --cpus {cpustr(a, b)} --bytes 256M --per-thread --kernel {ker(k)} --reps 2 --min-ms 6000', load=load2)


def a5_args(cpu): return f'--threads 1 --cpus {cpu} --bytes 8M --kernel asmread --reps 30 --min-ms 300'


def build_set1(root):
    # folder 1: A7 A5 A6
    F = Folder(root, 'partA-20260101T000000Z', 'A7 A5 A6', a7=True)
    one = lambda v: (lambda _k: (lambda i, cpu, rep: v(rep)))
    F.block('A5', 'cpu2-proc1', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5 + 0.1 * (r % 3)), lambda k, r: 2500, a5_args(2))
    F.block('A5', 'cpu2-proc2', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.6 + 0.1 * (r % 2)), lambda k, r: 2500, a5_args(2), waited=2)
    # CPU 41: low for intervals 0-11, 69.8 (changing) at interval 12, high from interval 13
    F.block('A5', 'cpu41-proc1', 'bw_new', [41], 8 * MIB, 300, ['asmread'], 30,
            one(lambda r: 67.9 if r < 12 else 69.8 if r == 12 else 71.2), lambda k, r: 2500, a5_args(41))
    F.block('A5', 'cpu41-proc2', 'bw_new', [41], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 71.0 + 0.1 * (r % 2)), lambda k, r: 2500, a5_args(41))
    for i in range(1, 9):
        a = '--threads 1 --cpus 2 --bytes 8M --kernel asmread --reps 3 --min-ms 500'
        F.block('A6', f'thp-{i}', 'bw_new', [2], 8 * MIB, 500, ['asmread'], 3, one(lambda r, i=i: 67.0 + 0.1 * i + 0.05 * r), lambda k, r: 4000, a)
        F.block('A6', f'nothp-{i}', 'bw_new', [2], 8 * MIB, 500, ['asmread'], 3, one(lambda r, i=i: 52.0 + 0.1 * i + 0.05 * r), lambda k, r: 3000,
                a + ' --no-thp', thp='nohugepage')
    # folder 2: A1 A2 A3 A4. A3 is skipped. The last A2 launch (read_old-r2) is killed.
    rates = dict(read_old=split(5.0, 2.5), read_new=flat(2.4), asmread=flat(2.3, 0.05),
                 write_old=split(1.5, 0.9, 0.02), write_new=flat(1.05, 0.02), asmwrite=split(1.5, 0.9, 0.02))
    def a4(k, a, b):
        if a != 64: return flat(3.4, 0.05)                    # a+a counts: uniform
        lim = 48 if k == 'read_old' else 32                    # split up to this count of mesh-1 threads
        return split(5.2, 2.6, 0.05) if 0 < b <= lim else flat(5.3 if b == 0 else 2.5, 0.05)
    F = Folder(root, 'partA-20260101T001000Z', 'A1 A2 A3 A4', skipped_a3=True)
    long_steps(F, rates, a4=a4)
    # the kill ended the script, so A4 of this folder would not exist: remove it, and write it in folder 3
    os.remove(os.path.join(F.d, 'A4.csv'))
    # folder 3: the repeated A2 launch, and A4
    F3 = Folder(root, 'partA-20260101T020000Z', 'A2 A4')
    F3.block('A2', 'read_old-r2', 'bw_old', cpulist(64, 56), 256 * MIB, 6000, ['read'], 3, lambda _k: rates['read_old'], lambda k, r: 60,
             all_args(64, 56, 'read', 3, 6000))
    tmp = Folder(root, 'tmp-a4', 'A4'); long_steps(tmp, rates, a2_kill=False, a4=a4)
    shutil.copy(os.path.join(tmp.d, 'A4.csv'), os.path.join(F3.d, 'A4.csv')); shutil.rmtree(tmp.d)
    return [os.path.join(root, n) for n in ('partA-20260101T000000Z', 'partA-20260101T001000Z', 'partA-20260101T020000Z')]


def build_set2(root):
    """Thread distributions between the limits: q of the write kernels is about 0.72 to 0.80, read_old 0.60."""
    rates = dict(read_old=split(4.0, 2.4, 0.03), read_new=split(2.6, 2.0, 0.03), asmread=flat(2.3, 0.05),
                 write_old=split(1.4, 1.0, 0.03), write_new=split(1.3, 1.1, 0.03), asmwrite=split(1.4, 0.95, 0.03))
    def a4(k, a, b):
        return split(4.0, 4.0 - 0.02 * b, 0.03)
    F = Folder(root, 'partA-20260102T000000Z', 'A1 A2 A3 A4 A5')
    long_steps(F, rates, a2_kill=False, a3=dict(one=split(5.0, 2.5), two=flat(3.0, 0.2)), a4=a4)
    one = lambda v: (lambda _k: (lambda i, cpu, rep: v(rep)))
    F.block('A5', 'cpu2-proc1', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5), lambda k, r: 2500, a5_args(2))
    F.block('A5', 'cpu2-proc2', 'bw_new', [2], 8 * MIB, 300, ['asmread'], 30, one(lambda r: 67.5), lambda k, r: 2500, a5_args(2), fail=True)
    return [F.d]


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol


def check_set1(s):
    c = s['counts']
    assert s['steps_missing'] == ['A3'], s['steps_missing']
    assert s['env'][1]['skipped'] == ['A3 skipped: MemAvailable is 61 GiB, below 70 GiB']
    # killed and repeated
    assert c['killed'] == 1 and c['failed'] == 0 and c['repeated_tags'] == 1, c
    assert c['blocks_found'] == 4 + 16 + 12 + 12 + 1 + 22 and c['blocks_not_used'] == 1, c
    nu = s['not_used'][0]
    assert (nu['step'], nu['tag'], nu['folder'], nu['replaced']) == ('A2', 'read_old-r2', 'partA-20260101T001000Z', True), nu
    assert 'killed' in nu['reason']
    used = [b for b in s['blocks'] if (b['step'], b['tag']) == ('A2', 'read_old-r2')]
    assert len(used) == 1 and used[0]['folder'] == 'partA-20260101T020000Z'
    # passes: A1 has 5 per thread (all marked), A2 has 60, one repetition has 48
    a1 = s['A1']['read_old']
    assert all(near(r['passes_per_thread'], 5) and r['below_50_passes'] for r in a1['reps'])
    low_a2 = [x for x in s['passes']['below_50'] if x['step'] == 'A2']
    assert [(x['tag'], x['rep']) for x in low_a2] == [('read_new-r1', 2)] and near(low_a2[0]['passes_per_thread'], 48), low_a2
    assert s['passes']['n_below_50'] == 36 + 1
    # split distribution without jitter: 64 threads at 5.00 GB/s on mesh 0, 56 threads at 2.50 GB/s on mesh 1
    r = a1['reps'][0]
    assert r['mesh0'] == dict(n=64, sum=320.0, median=5.0) and r['mesh1'] == dict(n=56, sum=140.0, median=2.5), (r['mesh0'], r['mesh1'])
    assert near(r['q'], 0.5) and r['label_rule'] == 'split' and r['label'] == 'split'
    fh = r['fastest_half']
    assert fh['n_half'] == 60 and fh['mesh0'] == [60, 60] and fh['mesh1'] == [0, 0], fh
    # uniform distribution without jitter: every thread at 2.40 GB/s. The fastest half is then not defined by the rates.
    r = s['A1']['read_new']['reps'][0]
    assert near(r['q'], 1.0) and r['label'] == 'uniform'
    assert r['fastest_half']['mesh0'] == [4, 60] and r['fastest_half']['mesh1'] == [0, 56] and r['fastest_half']['tied_at_cut'] == 120
    assert near(r['mesh0']['sum'], 153.6) and near(r['mesh1']['sum'], 134.4)
    # percentile, nearest rank: 10 values 1..10 -> value number 1 and number 9
    assert A.pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 10) == 1 and A.pct([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9
    assert A.pct(list(range(1, 121)), 10) == 12 and A.pct(list(range(1, 121)), 90) == 108
    # q falls into two groups, labels are used
    d = s['q']['decision']
    assert d['two_groups'] and d['limits_fit'] and d['labels_usable'], d
    assert d['n_between'] == 0 and d['lower_max'] < 0.65 and d['upper_min'] > 0.85
    assert d['n'] == 36 + 36 + 44, d['n']
    # A1 against A2 for the write kernel with a split: mesh 0 is the fast mesh
    w = s['A1']['write_old']
    assert w['mesh0_median']['median'] > w['mesh1_median']['median'] and w['labels'] == ['split']
    assert set(s['A1_A2']['kernels']) == set(K6)
    assert near(s['A1_A2']['kernels']['read_new']['change_GBps'], 0.0) and s['A1_A2']['kernels']['read_new']['ranges_overlap']
    # A4: old read changes between 64+48 and 64+52, asm read between 64+32 and 64+40; a+a never changes
    k = s['A4']['kernels']
    assert k['read_old']['series']['64+b']['bracket'] == ['64+48', '64+52'], k['read_old']['series']['64+b']
    assert k['asmread']['series']['64+b']['bracket'] == ['64+32', '64+40']
    assert len(k['read_old']['series']['64+b']['changes']) == 2      # 64+0 is uniform: that change is listed, and is not the bracket
    assert k['read_old']['series']['a+a']['bracket'] is None and 'no change' in k['read_old']['series']['a+a']['note']
    assert s['A4']['bracket_compare']['64+b'] == 'different'
    assert k['read_old']['counts']['64+48']['label'] == 'split' and k['read_old']['counts']['64+52']['label'] == 'uniform'
    # A5
    p = {x['tag']: x for x in s['A5']['processes']}
    assert p['cpu41-proc1']['changes'] == [dict(at_interval=13, from_level='low', to_level='high')], p['cpu41-proc1']['changes']
    assert (p['cpu41-proc1']['n_low'], p['cpu41-proc1']['n_changing'], p['cpu41-proc1']['n_high']) == (12, 1, 17)
    assert p['cpu2-proc1']['changes'] == [] and p['cpu2-proc1']['n_low'] == 30
    assert p['cpu41-proc2']['first_level'] == 'high'
    pr = {x['cpu']: x for x in s['A5']['pairs']}
    assert pr[2]['second_not_at_once'] and pr[2]['second_waited_s'] == 2 and not pr[41]['second_not_at_once']
    # A6: process medians 67.15 .. 67.85 with pages of 2 MiB allowed, 52.15 .. 52.85 without
    a6 = s['A6']
    assert a6['thp']['process_medians']['n'] == 8 and a6['nothp']['process_medians']['n'] == 8
    assert near(a6['thp']['process_medians']['median'], 67.5, 1e-6) and near(a6['nothp']['process_medians']['median'], 52.5, 1e-6)
    assert near(a6['nothp_minus_thp_GBps'], -15.0, 1e-6) and not a6['process_ranges_overlap']
    assert all(x['thp_line_ok'] for x in a6['processes'])
    # load
    L = s['load']
    assert L['A1']['launches'] == 12 and L['A1']['load1']['min'] == 0.5 and L['A1']['load1']['max'] == 31.2
    assert L['A1']['n_waited'] == 11 and L['A1']['waited_s']['max'] == 4
    assert L['A1']['busiest'][0] == dict(user='other', comm='busy_job', max_pcpu=99.0), L['A1']['busiest'][0]
    assert s['env'][0]['a7']['A7-sve.txt']['sve_vector_length_bytes'] == '16'


def check_set1_a4_first_count(s):
    # with 64+0 uniform the 64+b series would have two changes. The generator gives 64+0 a flat rate, so check what was computed.
    k = s['A4']['kernels']['read_old']
    assert k['counts']['64+0']['label'] == 'uniform'


def check_set2(s):
    d = s['q']['decision']
    assert not d['labels_usable'], d
    assert d['reason']
    # WHY: the handoff compares only the read rows of A3. The 36 write and copy repetitions of the 6 processes with
    # --kernel all must not take part in the test that switches the labels on or off for all of Part A.
    # 36 (A1) + 36 (A2) + 44 (A4) + 18 (A3 one buffer, read) + 18 (A3 two buffers, read) = 152; before this rule 188.
    assert d['n'] == 152 and len(s['q']['rows']) == 152, d['n']
    assert len(s['q']['rows_left_out']) == 36 and {x['kernel'] for x in s['q']['rows_left_out']} == {'write', 'copy'}
    assert all(x['step'] != 'A3' or x['kernel'] == 'read' for x in s['q']['rows'])
    # no label is set anywhere, the rule labels stay available
    assert all(r['label'] is None for k in s['A1'].values() for r in k['reps'])
    assert any(r['label_rule'] == 'between' for k in s['A1'].values() for r in k['reps'])
    assert s['A1']['read_old']['labels'] is None
    for k in s['A4']['kernels'].values():
        for ser in k['series'].values():
            assert ser['bracket'] is None and ser['note'] == 'labels not available'
    # A3 is present: 4 groups of 3 processes, read rows only (3 repetitions per process, not 9)
    g = s['A3']['groups']
    assert sorted(g) == ['onebuf-ms500', 'onebuf-ms6000', 'twobuf-ms500', 'twobuf-ms6000']
    assert all(len(x['processes']) == 3 and all(len(p['reps']) == 3 for p in x['processes']) for x in g.values())
    assert g['twobuf-ms6000']['processes'][0]['other_kernels'] == ['copy', 'write']
    assert near(g['onebuf-ms6000']['q']['median'], 0.5) and g['twobuf-ms6000']['q']['median'] > 0.8
    assert not s['A3']['compare']['6000']['q_ranges_overlap'] and s['A3']['compare']['6000']['same_label'] is None
    # copy rows of --kernel all: 60 passes, not 120
    # 36 repetitions of A1 (5 passes), 1 of A2 (48 passes), and the 18 copy repetitions of A3 (40 passes).
    # A copy repetition counts read plus written bytes: without the division by 2 it would show 80 passes and not be marked.
    assert s['passes']['n_below_50'] == 36 + 1 + 18, s['passes']['n_below_50']
    cp = [x for x in s['passes']['below_50'] if x['kernel'] == 'copy']
    assert len(cp) == 18 and all(near(x['passes_per_thread'], 40) for x in cp)
    # the failed A5 process is not used and listed
    assert s['counts']['failed'] == 1 and [x['tag'] for x in s['not_used']] == ['cpu2-proc2']
    assert s['A5']['pairs'][0]['have_both'] is False
    assert s['steps_missing'] == ['A6', 'A7'], s['steps_missing']


def check_two_groups():
    f = A.two_groups
    assert f([0.5, 0.52, 0.55, 0.9, 0.95, 0.97])['labels_usable']
    assert not f([0.9, 0.92, 0.95, 0.97, 0.99])['two_groups']                  # one group
    assert not f([0.5, 0.6, 0.7, 0.8, 0.9, 0.95])['two_groups']                # spread evenly
    r = f([0.30, 0.32, 0.5, 0.52, 0.55])                                        # two groups, both below 0.65
    assert r['two_groups'] and not r['limits_fit'] and not r['labels_usable']
    assert not f([0.5, 0.9, 0.95, 0.97])['two_groups']                         # one value alone is not a group
    assert not f([0.5, 0.9])['labels_usable']


def check_units():
    # WHY: a median of 6 rates printed with 2 decimals can lie in the middle of two printed values (0.995). Printed as 0.99 next to
    # 0.98 and a difference of 0.02 the three numbers of one sentence do not agree. Such a value keeps its third decimal.
    assert H.fx(0.995) == '0.995' and H.fx(0.015) == '0.015' and H.fx(0.98) == '0.98' and H.fx(2.6149999999) == '2.615'
    assert H.fx(0.6053) == '0.61' and H.fs(-8.335) == '-8.335' and H.fs(4.85) == '+4.85' and H.fx(-0.001) == '0.00'
    # WHY (plan rule 5): a level limit that lies inside a dense run of rates must not be used to label them.
    # 30 rates that rise without a step from 68.5 to 69.5 GB/s: the limit 69 has rates 0.03 GB/s apart on its two sides.
    c = A.limit_check([68.5 + i * 1.0 / 29 for i in range(30)])
    assert not c['labels_usable'] and not c['limits'][0]['separates'] and c['limits'][1]['separates'] and c['limits'][1]['empty_range'] is None
    # two levels with an empty range of 1.9 GB/s around 69 and of 1.4 GB/s around 70.5: both limits separate
    c = A.limit_check([67.3, 67.4, 67.5, 69.4, 70.8, 70.9, 71.0])
    assert c['labels_usable'] and c['limits'][0]['n_below'] == 3 and near(c['limits'][0]['empty_range'], 1.9, 1e-9)
    # a CPU whose labels are not usable gets no level change, even if its labels go from low to changing
    a5 = dict(processes=[dict(cpu=41, rates_GBps=[68.9, 68.95, 69.0, 69.05, 69.1], changes=[dict(at_interval=2, from_level='low', to_level='high')])])
    lv = A.level_check(a5, dict(processes=[]))
    assert a5['processes'][0]['labels_usable'] is False and a5['processes'][0]['changes'] == [] and a5['processes'][0]['n_below_low_limit'] == 2
    assert not lv['cpus']['41']['labels_usable']
    # WHY (handoff B.8): Part C takes the PMU type and the event codes from A7-core-events.txt. A missing event must stay empty, not be guessed.
    pm = A.parse_core_events(['== /sys/bus/event_source/devices/armv8_pmuv3_0 type=11', '/sys/d/armv8_pmuv3_0/events/cpu_cycles:event=0x0011',
                              '/sys/d/armv8_pmuv3_0/events/ll_cache_miss_rd:event=0x0037', '/sys/d/armv8_pmuv3_0/events/l3d_cache_refill:event=0x002a'])
    assert len(pm) == 1 and pm[0]['name'] == 'armv8_pmuv3_0' and pm[0]['type'] == '11' and pm[0]['n_events'] == 3
    b8 = {x['event']: x for x in pm[0]['b8']}
    assert b8['cycles']['code'] == '0x0011' and b8['cycles']['line'] == 2 and b8['instructions']['code'] is None and b8['last-level read misses']['code'] == '0x0037'
    assert [x['name'] for x in pm[0]['b8_other']] == ['l3d_cache_refill']


def check_set1_more(s, h):
    # the A7 file of set 1 lists one PMU of type 10 with one of the five events
    pm = s['env'][0]['a7']['A7-core-events.txt']['pmu_list'][0]
    assert pm['type'] == '10' and [x['code'] for x in pm['b8']] == [None, None, '0x03', None, None]
    assert 'Consequence for Part C' in h and 'type number for <code>perf_event_open</code> is 10' in h and h.count('the file has no event of this name') == 4
    # A1 against A2: the rates of set 1 do not depend on the interval, so no long total lies outside the short range,
    # and the reading for the order of B7 and B8 is "the totals stayed" (choice C11)
    k = s['A1_A2']['kernels']['read_new']
    assert k['n_long'] == 6 and k['n_long_outside_short'] == 0
    assert s['A1_A2']['order_reading'] == dict(changed=False, difference_smaller_with_long=False)
    assert 'Consequence for the order of B7 and B8' in h and 'the totals stayed' in h
    # WHY: "no other load" may be said only if no reading speaks against it. Set 1 has 1 logged-in user, launches that waited,
    # and a process of another user at 99 % of a CPU.
    lc = s['load_check']
    assert lc['no_other_load_seen'] is False and lc['logins_max'] == 1 and lc['n_waited'] > 0 and lc['own_user'] is None
    assert lc['busiest_other'][0] == dict(pcpu=99.0, user='other', comm='busy_job')
    assert 'No reading of this run shows load from another user' not in h
    # the header line and launches.txt hold one reading each of the runnable tasks; the generator writes the same value into both.
    # The 22 A4 blocks of folder 3 were copied in without their launches.txt entries, so they have no second reading.
    assert lc['n_runnable_differ'] == 0 and lc['n_with_launches_txt'] == lc['n_launches'] - 22
    # the level limits separate the rates of both CPUs of set 1, so the level change of CPU 41 is given
    assert all(c['labels_usable'] for c in s['level_check']['cpus'].values()) and sorted(s['level_check']['cpus']) == ['2', '41']
    assert 'first high interval was number 13' in h
    # labels usable: the brackets of A4 are the thread counts for B8
    assert 'Consequence for B8' in h and 'the pattern changed between 64+48 and 64+52 threads. B8 refines' in h


def check_set2_more(s, h):
    # WHY (handoff B.9, row B8): without labels A4 gives no pair of counts. The page must say so as "Insufficient data", not stay silent.
    assert 'Part A gives no thread counts for B8' in h and re.search(r'Insufficient data\.</b> Part A gives no thread counts for B8', h)
    g = s['q']['groups']
    # old read at 64+56 threads: 12 repetitions of A1 and A2, 18 + 18 read repetitions of A3, 2 of A4
    assert g['read_old']['n'] == 6 + 6 + 36 + 2 and g['load_only_read']['n'] == 12 + 12 + 2, (g['read_old']['n'], g['load_only_read']['n'])
    assert sum(x['n'] for x in g['below_split']) == s['q']['decision']['n_split']
    assert sum(x['n'] for x in g['between']) == s['q']['decision']['n_between']
    # the count of the fastest half is given for each repetition, not as one merged range
    assert 'per repetition' in h and h.count(' of 60</td>') > 0
    # A7 is missing in set 2: no codes for Part C
    assert 'insufficient data for the counter codes of Part C (A7)' in h


def check_page(html, s):
    low = html.lower()
    for w in ('rejected', 'confirmed'):
        assert w not in low, f'the page must not use the word "{w}"'
    assert '<script' not in low and 'http://' not in low.replace('http://www.w3.org', '') and 'https://' not in low, 'external reference or script in the page'
    assert 'Short version' in html and 'Words used here' in html and 'References' in html and 'observed in screening' in low
    assert 'prefers-color-scheme' not in low
    for step in s['steps_missing']:
        assert re.search(r'Insufficient data[^<]*' + step, html), f'no "Insufficient data" for {step}'
    sv = re.search(r'<b>Short version\.</b>(.*?)</p>', html, re.S).group(1)
    n = len(re.findall(r'[.!?](?:\s|$)', re.sub(r'<[^>]+>', '', sv).strip()))
    assert n <= 3, f'Short version has {n} sentences'


def main():
    keep = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else None
    root = keep or tempfile.mkdtemp(prefix='partA-test-')
    if keep:
        shutil.rmtree(root, ignore_errors=True); os.makedirs(root)
    try:
        check_two_groups(); check_units()
        f1 = build_set1(os.path.join(root, 'set1')); s1 = A.analyse(f1)
        json.dump(s1, open(os.path.join(root, 'set1', 'partA-summary.json'), 'w'), indent=1)
        s1 = json.load(open(os.path.join(root, 'set1', 'partA-summary.json')))     # the page reads the json, so test that path
        check_set1(s1); check_set1_a4_first_count(s1)
        h1 = H.build(s1, BANNER); open(os.path.join(root, 'set1', 'partA-result.html'), 'w').write(h1); check_page(h1, s1); check_set1_more(s1, h1)
        f2 = build_set2(os.path.join(root, 'set2')); s2 = A.analyse(f2)
        json.dump(s2, open(os.path.join(root, 'set2', 'partA-summary.json'), 'w'), indent=1)
        s2 = json.load(open(os.path.join(root, 'set2', 'partA-summary.json')))
        check_set2(s2)
        h2 = H.build(s2, BANNER); open(os.path.join(root, 'set2', 'partA-result.html'), 'w').write(h2); check_page(h2, s2); check_set2_more(s2, h2)
        assert 'do not fall into two groups' in h2 or 'does not fall into two groups' in h2
        # an empty folder must give a page that says what is missing, not an error
        e = os.path.join(root, 'set3', 'partA-20260103T000000Z'); os.makedirs(e)
        s3 = json.loads(json.dumps(A.analyse([e]))); h3 = H.build(s3, BANNER); check_page(h3, s3)
        open(os.path.join(root, 'set3', 'partA-result.html'), 'w').write(h3)
        print('all tests passed' + (f'; files kept in {root}' if keep else ''))
    finally:
        if not keep:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    main()
