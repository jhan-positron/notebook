#!/usr/bin/env python3
"""scen.py NAME... - run failure scenarios of the copy of manual-run.sh against the folder that plays CRB.
Nothing here contacts a machine. One scenario runs at a time."""
import glob, os, re, shutil, signal, subprocess, sys, time
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = '/home/jhan/workspace/ai-proj/arm-crb'

def procs(crb):
    out = subprocess.run(['pgrep', '-af', crb + '/home'], capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if 'pgrep' not in l]

def short(text, d):
    return text.replace(d + '/crb', '<CRB>').replace(d, '<HERE>').replace(S, '<S>')

class Run:
    def __init__(self, name, sigint='255'):
        self.name, self.d = name, os.path.join(S, 'run', name)
        shutil.rmtree(self.d, ignore_errors=True); os.makedirs(self.d)
        self.crb = self.d + '/crb'
        subprocess.run([S + '/tools/mkcrb.sh', self.crb], check=True)
        shutil.copy(S + '/sim/manual-run.sh', self.d + '/manual-run.sh')
        os.symlink(REPO + '/code', self.d + '/code')
        self.env = dict(os.environ, SIMCRB=self.crb, FAKESSH_SIGINT=sigint, TMPDIR=S + '/tmp')
        self.res = self.crb + '/home/cache-perf/results'
    def ctl(self, name, value=''):
        open(self.crb + '/ctl/' + name, 'w').write(str(value))
    def start(self, args=('-y',), stdin=None):
        def pre():
            signal.signal(signal.SIGINT, signal.SIG_DFL); signal.signal(signal.SIGTERM, signal.SIG_DFL); os.setsid()
        self.t0 = time.time()
        self.p = subprocess.Popen(['bash', self.d + '/manual-run.sh', *args], stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                  stdout=open(self.d + '/console.txt', 'w'), stderr=subprocess.STDOUT, env=self.env, preexec_fn=pre, cwd=self.d)
        if stdin is not None:
            self.p.stdin.write(stdin.encode()); self.p.stdin.close()
    def wait_for(self, pattern, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            if glob.glob(os.path.join(self.res, pattern)): return True
            time.sleep(0.05)
        raise SystemExit('timeout waiting for ' + pattern)
    def finish(self, timeout=120, tail=14, note=''):
        rc = self.p.wait(timeout=timeout)
        took = time.time() - self.t0
        left = procs(self.crb)
        con = short(open(self.d + '/console.txt').read(), self.d)
        lines = [re.sub(r'(processes per user:).*', r'\1 ...', l)[:230] for l in con.splitlines()]
        print('=' * 100); print('SCENARIO %s %s' % (self.name, note))
        print('exit status of manual-run.sh: %d   (%.1f s)' % (rc, took))
        print('--- last %d console lines (stdout and stderr together):' % tail)
        for l in lines[-tail:]: print('  | ' + l)
        lg = self.crb + '/logins.log'
        print('--- logins on the stand-in CRB:')
        for l in (open(lg).read().splitlines() if os.path.exists(lg) else ['(none)']): print('  ' + l[:120])
        sl = self.crb + '/sudo.log'
        print('--- root commands: ' + (open(sl).read().strip().replace('\n', ' ; ') if os.path.exists(sl) else '(none)'))
        print('--- processes left on the stand-in CRB right after the exit: %d' % len(left))
        for l in left[:6]: print('  ' + short(l, self.d)[:150])
        dests = glob.glob(self.d + '/tests/*')
        for dd in dests: print('--- local result folder %s: %s' % (short(dd, self.d), ' '.join(sorted(os.listdir(dd)))[:400]))
        print('--- temp file left: ' + str([f for f in glob.glob(S + '/tmp/tmp.*') if os.path.getmtime(f) >= self.t0 - 1 and os.path.getsize(f) >= 0][:3]))
        self.rc, self.left, self.console = rc, left, con
        return rc
    def cleanup(self):
        for l in procs(self.crb):
            try: os.kill(int(l.split()[0]), signal.SIGKILL)
            except Exception: pass
    def settle(self, timeout=60):
        end = time.time() + timeout
        while procs(self.crb) and time.time() < end: time.sleep(0.2)
        return not procs(self.crb)

def happy():
    r = Run('happy'); r.start(); r.finish(tail=40)
    print('--- taskset calls on the stand-in CRB (CPU lists): ' + subprocess.run('sort %s/taskset.log | uniq -c | tr "\\n" ";"' % r.crb, shell=True, capture_output=True, text=True).stdout)
def answer(name, text, args=()):
    r = Run(name); r.start(args=args, stdin=text); r.finish(tail=4)
def marker_at_login(k):
    r = Run('marker_at_login_%d' % k); r.ctl('marker-at-login', k); r.start(); r.finish(tail=9); r.cleanup()
def marker_mid(name, key, val, load=None, wait=None):
    r = Run(name); r.ctl('bwx-seconds', 0.5)
    if key: r.ctl(key, val)
    if load: open(r.crb + '/proc/loadavg', 'w').write(load)
    r.start()
    if wait:
        r.wait_for(wait); time.sleep(0.5); open(r.crb + '/positron-perf.RUNNING', 'w').close()
    r.finish(tail=13); r.settle(5); print('--- processes left 5 s later: %d' % len(procs(r.crb))); r.cleanup()
def simple(name, prep, tail=9, **kw):
    r = Run(name); prep(r); r.start(); r.finish(tail=tail); r.cleanup(); return r

SC = {
 'happy': happy,
 'answer_n': lambda: answer('answer_n', 'n\n'),
 'answer_eof': lambda: answer('answer_eof', ''),
 'answer_Y': lambda: answer('answer_Y', 'Y\n'),
 'answer_y': lambda: answer('answer_y', 'y\n'),
 'usage': lambda: answer('usage', '', args=('-x',)),
 **{'marker_at_login_%d' % k: (lambda k=k: marker_at_login(k)) for k in range(1, 6)},
 'marker_mid_ra': lambda: marker_mid('marker_mid_ra', 'marker-at-bw', 30),
 'marker_mid_rx': lambda: marker_mid('marker_mid_rx', 'marker-at-bwx', 2),
 'marker_mid_go2_wait': lambda: marker_mid('marker_mid_go2_wait', None, None, load='5.00 5.00 5.00 1/900 12345\n', wait='go2-T72-*.log'),
 'marker_mid_go2_rx': lambda: marker_mid('marker_mid_go2_rx', 'marker-at-bwx', 8),
 'sha_mismatch': lambda: simple('sha_mismatch', lambda r: open(r.crb + '/home/cache-perf/w120-7200-20261117/ra.sh', 'a').write('# changed\n')),
 'ten_modules': lambda: simple('ten_modules', lambda r: (r.ctl('sudo-mode', 'ok10'), open(r.crb + '/proc/meminfo', 'w').write('MemTotal:       329494004 kB\n'))),
 'sudo_password': lambda: simple('sudo_password', lambda r: r.ctl('sudo-mode', 'password')),
 'no_connection': lambda: simple('no_connection', lambda r: r.ctl('refuse-at-login', 'all')),
 'no_connection_at_copy': lambda: simple('no_connection_at_copy', lambda r: r.ctl('refuse-at-login', 3)),
 'no_connection_at_go2': lambda: simple('no_connection_at_go2', lambda r: r.ctl('refuse-at-login', 4), tail=5),
 'driver_fails_go': lambda: simple('driver_fails_go', lambda r: r.ctl('bwx-fail-at', 3), tail=12),
 'driver_fails_go2': lambda: simple('driver_fails_go2', lambda r: r.ctl('bwx-fail-at', 8), tail=10),
 'remote_tar_fails': lambda: simple('remote_tar_fails', lambda r: r.ctl('tar-fail')),
}
if __name__ == '__main__':
    for n in sys.argv[1:]: SC[n]()
