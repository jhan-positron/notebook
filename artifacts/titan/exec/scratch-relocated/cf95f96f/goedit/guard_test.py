# Failure modes of the guard check_two_texts_go of make_list.py.
# For each state ONE of the files that the guard reads is replaced by a changed copy (the guard is pointed at the copy).
# The real files are never changed.
import os, shutil, sys
sys.dont_write_bytecode = True
C = '/home/jhan/workspace/titan/cache-perf/crb'
T = C + '/tmp/agent-scratch/code-data-list-2026-11-21'; E = C + '/tmp/agent-scratch/go-edit-2026-11-24'
sys.path.insert(0, T)
import make_list as ml
W = sys.argv[1] + '/guardtest'
real = dict(go=ml.MAN['go']['path'], local_sha=ml.MAN['local_sha']['path'], go2=ml.MAN['go2']['path'], goedit=ml.GOEDIT)
def point(which, path):
    if which == 'goedit': ml.GOEDIT = path
    else: ml.MAN[which]['path'] = path
def state(tag, which, name, mutate, expect):
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    if which == 'goedit':
        shutil.copytree(E, W + '/e'); os.chmod(W + '/e/go.sh.as-run-2026-11-17', 0o644); target, newpath = W + '/e/' + name, W + '/e'
    else:
        shutil.copy2(real[which], W + '/' + name); target, newpath = W + '/' + name, W + '/' + name
    data = open(target, 'rb').read(); open(target, 'wb').write(mutate(data))
    if tag.startswith('p '): os.remove(target)
    point(which, newpath)
    try:
        ml.check_two_texts_go(); res = 'passed'
    except SystemExit as e:
        res = 'stopped: ' + str(e)[len('make_list.py: ERROR: '):]
    finally:
        point(which, real[which])
    good = res.startswith('stopped: ' + expect)
    print(('PASS ' if good else 'FAIL ') + '%-40s %s' % (tag, res[:100]))
    return good
def setline(n, text):
    def f(b):
        l = b.decode().split('\n'); l[n - 1] = text(l[n - 1]); return '\n'.join(l).encode()
    return f
NEW_GO_ENTRY = b'd68cf6c0468abeb658765b950b9bd86b34ff9556070efcd954824f6e936da2bd  go.sh\n'
ok = True
for tag, which, name, mut, expect in [
    ('b other line of go.sh changed', 'go', 'go.sh', setline(30, lambda s: s + ' '), 'go.sh: with the old line 20 put back the sha256 is'),
    ('c go.sh with the old line 20', 'go', 'go.sh', setline(20, lambda s: ml.GO_OLD_LINE20), 'go.sh: line 20 is not the line of the edit'),
    ('g go.sh with CR LF line ends', 'go', 'go.sh', lambda b: b.replace(b'\n', b'\r\n'), 'go.sh: line 20 is not the line of the edit'),
    ('i one more line at the end of go.sh', 'go', 'go.sh', lambda b: b + b'\n', 'go.sh: with the old line 20 put back the sha256 is'),
    ('d go.sh entry of local.sha changed', 'local_sha', 'local.sha', lambda b: b.replace(b'75bc50b0', b'75bc50b1'), 'local.sha is not the list of 2026-11-17'),
    ('e ra.sh entry of local.sha changed', 'local_sha', 'local.sha', lambda b: b.replace(b'6d67715e', b'6d67715f'), 'local.sha is not the list of 2026-11-17'),
    ('f second go.sh line in local.sha', 'local_sha', 'local.sha', lambda b: NEW_GO_ENTRY + b, 'local.sha is not the list of 2026-11-17'),
    ('h go2.sh line 16 with the new message', 'go2', 'go2.sh', setline(16, lambda s: ml.GO_NEW_LINE20), 'go2.sh does not have the sha256 that go2.sha lists'),
    ('m go2.sh line 25 with the new message', 'go2', 'go2.sh', setline(25, lambda s: s.replace('"RUNNING file present"', '"RUNNING file present, Jeremy or someone else is using CRB"')), 'go2.sh does not have the sha256 that go2.sha lists'),
    ('j kept copy of the older text changed', 'goedit', 'go.sh.as-run-2026-11-17', lambda b: b + b'#\n', 'go-edit-2026-11-24/go.sh.as-run-2026-11-17 does not have'),
    ('k stored test output holds a FAIL', 'goedit', 'check_facts_build.out', lambda b: b.replace(b'PASS run 1 ends', b'FAIL run 1 ends'), 'go-edit-2026-11-24/check_facts_build.out: the stored output'),
    ('l stored test output not complete', 'goedit', 'check_line20.out', lambda b: b.replace(b'ALL PASS', b''), 'go-edit-2026-11-24/check_line20.out: the stored output'),
    ('n go2.sh line 12 turned into a comment', 'go2', 'go2.sh', setline(12, lambda s: '#' + s), 'go2.sh does not have the sha256 that go2.sha lists'),
    ('o stored output lacks the run 2 line', 'goedit', 'check_facts_build.out', lambda b: b.replace(b'PASS run 2 ends with status 0', b'note run 2 ends with status 0'), 'go-edit-2026-11-24/check_facts_build.out: the stored output'),
    ('p a test script is missing', 'goedit', 'check_line20.py', lambda b: b, 'go-edit-2026-11-24/check_line20.py is missing'),
]: ok &= state(tag, which, name, mut, expect)
try:
    ml.check_two_texts_go(); print('PASS real files                                passed')
except SystemExit as e:
    ok = False; print('FAIL real files stopped:', e)
shutil.rmtree(W, ignore_errors=True)
print('ALL PASS' if ok else 'SOME FAILED')
