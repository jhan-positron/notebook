# Third version of the corrections of the annotation inputs after the edit of go.sh line 20 (2026-11-24).
# It starts from the backup of each file (state before the edit) and applies every change with a check of the old text.
import json, shutil, sys
C = '/home/jhan/workspace/titan/cache-perf/crb'
T = C + '/tmp/agent-scratch/code-data-list-2026-11-21'
S = C + '/tmp/agent-scratch/w120-7200-2026-11-17'
E = C + '/tmp/agent-scratch/go-edit-2026-11-24'
G = sys.argv[1]
OLD_SHA = '75bc50b00b26438c00c425cff0ed8620352f7c668eec6dc2831d9ab009b198e3'
NEW_SHA = 'd68cf6c0468abeb658765b950b9bd86b34ff9556070efcd954824f6e936da2bd'
NOW = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl'
changed = []
def load(key):
    p = f'{T}/ann/{key}.json'
    shutil.copyfile(f'{G}/backup/tmp/agent-scratch/code-data-list-2026-11-21/ann/{key}.json', p)
    raw = open(p).read(); o = json.loads(raw)
    assert json.dumps(o, indent=1, ensure_ascii=True) + '\n' == raw, key
    return p, o
def save(p, o):
    open(p, 'w').write(json.dumps(o, indent=1, ensure_ascii=True) + '\n'); changed.append(p)
def swap(text, old, new):
    assert text.count(old) == 1, (old[:60], text.count(old))
    return text.replace(old, new)
def word(o, term):
    hits = [w for w in o['words'] if w['term'] == term]; assert len(hits) == 1, term
    return hits[0]
def ref(o, rid):
    hits = [r for r in o['refs'] if r['id'] == rid]; assert len(hits) == 1, rid
    return hits[0]
def note(o, start):
    hits = [i for i, n in enumerate(o['behavior_notes']) if n.startswith(start)]; assert len(hits) == 1, start
    return hits[0]
def seg(c, start):
    hits = [s for s in c['segments'] if s['start'] == start]; assert len(hits) == 1, start
    return hits[0]
def newref(o, n, path, what):
    assert [x['id'] for x in o['refs']][-1] == 'Ref%d' % (n - 1), [x['id'] for x in o['refs']][-1]
    o['refs'].append({'id': 'Ref%d' % n, 'path': path, 'what': what})
TESTS = ('tests of 2026-11-24 for the edit of line 20 of go.sh. The files that end with `.out` hold their output. `go.sh.as-run-2026-11-17` is a copy of go.sh from before the edit. '
         '`check_line20.py` reads the local go.sh and puts the old line back in a copy of the text in memory. It does not change the file. That text has the sha256 that `local.sha` lists for go.sh. '
         '`check_facts_build.py` runs `build_facts.py` in a copy of the run folder. With the edited go.sh the build ends with status 1 and writes no file. With the old line 20 it passes.')
JEREMY_HERE = 'Jeremy is another user of CRB. The page `go.sh.md` in this folder (the explanation of go.sh) names the notes that say this.'
JEREMY_THERE = 'Jeremy is another user of CRB. The page `go.sh.md` in the folder of go.sh (the explanation of go.sh) names the notes that say this.'

# ---------------------------------------------------------------- go.sh
p, c = load('go.c01'); s = seg(c, 20); assert s['end'] == 20
assert s['text'].startswith('Check of the marker file.') and 'stops the run with `RUNNING file present`.' in s['text']
s['text'] = ('Check of the marker file.\n'
             '- Test: does the file `/tmp/positron-perf.RUNNING` exist.\n'
             '- On failure (the file exists): `fail` stops the run with `RUNNING file present, Jeremy or someone else is using CRB`.\n'
             '- The words after the comma were added on 2026-11-24, after the rerun [Ref18]. The text that ran had the message `RUNNING file present`. The rerun did not print it. Its log shows `marker absent` in all 12 state lines [Ref1].\n'
             '- go.sh stops on the file only here. The function `state` (line 17) only reports the file as `present` or `absent`.\n'
             '- `ra.sh` tests it again before each process [Ref2]. `rx.sh` tests it before each process and once per second while a process runs [Ref3].\n'
             '- What the file stands for, by the message: Jeremy or someone else is using CRB. The word list says who Jeremy is. go.sh does not say who creates the file.')
save(p, c)

p, o = load('go.overview')
i = note(o, 'Is the local go.sh the script that ran:')
n = o['behavior_notes'][i]
n = swap(n, 'Is the local go.sh the script that ran: the log of go.sh', 'Is the local go.sh the script that ran: yes, except for the message of line 20. The next note gives the difference. The log of go.sh')
n = swap(n, 'The local go.sh still has the sha256 of `local.sha` (tested with `sha256sum -c` on 2026-11-21) [Ref16].',
         'On 2026-11-21 the local go.sh still had the sha256 that `local.sha` lists for it (tested with `sha256sum -c`) [Ref16].')
o['behavior_notes'][i] = n
o['behavior_notes'][i + 1:i + 1] = [
    'Two texts of go.sh: the local text differs from the text that ran in line 20 only. On 2026-11-24 the message of that line was changed on the instruction of the user of the AI agent [Ref18]. '
    'The old line was `[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"`. With the old line put back, the local go.sh has the sha256 that `local.sha` lists for it [Ref20]. '
    'The transcript of the rerun holds the last command that wrote go.sh before the copy to CRB. The script text in that command has the same sha256 [Ref15].',
    'Effect of the edit on two checks: `local.sha` was not changed. So `sha256sum -c local.sha` now prints `go.sh: FAILED` and `OK` for the 4 other files [Ref16]. '
    'The script `build_facts.py` builds the facts sheet of the rerun (the file `FACTS.md` in this folder). Its check 20 makes the same test as `sha256sum -c` [Ref19]. '
    'So a new run of `build_facts.py` fails this check. It then stops and writes no file. With the old line put back it passes [Ref20].',
    'The copy of go.sh on CRB: the edit was made in the local file only. Insufficient data: the present text of the copy on CRB. `sha256sum go.sh` on CRB would resolve it.']
w = word(o, 'Marker file')
assert w['def'] == 'the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. The scripts do not say who creates it. The facts sheet of the rerun says that another user creates it during a performance test [Ref10].'
w['def'] = ('the file `/tmp/positron-perf.RUNNING`. The scripts of this test stop when it exists. Since 2026-11-24 the message of go.sh line 20 says what the file stands for: Jeremy or someone else is using CRB. '
            'The messages of `ra.sh`, `rx.sh` and go2.sh do not say it. None of the scripts that test the file says who creates it. The facts sheet of the rerun says that another user creates it during a performance test [Ref10].')
o['words'].insert(o['words'].index(w) + 1, {'term': 'Jeremy', 'def': 'another user of CRB. A block is a time window in which the whole machine is reserved for the measurements of Jeremy. Notes of 2026-10-30 say that the marker file is present for the whole of each block [Ref17].'})
r = ref(o, 'Ref1'); assert r['what'].endswith('The last line is `ALLDONE`.')
r['what'] += ' All 12 state lines hold `marker absent`. No line starts with `FAILED`.'
r = ref(o, 'Ref15'); assert r['what'].endswith('Line 313 holds the start command, run at 22:12:08 UTC.')
r['what'] += (' Line 295 holds the last command that wrote go.sh in the local run folder before the copy (22:11:29 UTC). The script text in that command has 48 lines and 3628 bytes. '
              'Its sha256 is %s (computed on 2026-11-24). An earlier command (line 182, 21:44:21 UTC) wrote a first text of go.sh.' % OLD_SHA)
r = ref(o, 'Ref16'); assert r['what'].endswith('printed `OK` for the 5 files.')
r['what'] += (' On 2026-11-24, after the edit of line 20 of go.sh, the same command printed `go.sh: FAILED` and `OK` for the 4 other files. '
              'The edited go.sh has the sha256 %s.' % NEW_SHA)
newref(o, 17, C + '/jeremy-plan-constraints-2026-10-30.md',
       'notes of 2026-10-30 about the tests of Jeremy, another user of CRB. Line 12 defines a block: a reserved whole-host window in which Jeremy runs measurements. Line 13: the file `/tmp/positron-perf.RUNNING` is present for the whole block.')
newref(o, 18, NOW,
       'the transcript of the Claude Code session in which line 20 was changed, one JSON record per line. It lies outside the project folder. The session began on 2026-11-22 at 01:35 UTC (2026-11-21 by the clock of the agent\'s server). '
       'Line 2153 holds the instruction of the user of the AI agent with the old and the new line (2026-11-24, 20:27:54 UTC). Line 2245 holds the edit (sent at 20:35:42 UTC). The file time of go.sh is 20:35:43 UTC.')
newref(o, 19, S + '/build_facts.py',
       'the script that builds the facts sheet. Lines 772 to 780 compare the sha256 of the local run files with `local.sha` and `go2.sha` (check 20 of the facts sheet). '
       'The function `main` builds the text of the sheet in line 1037. It writes the files after that, in lines 1038 to 1041. The script `facts_text4.py` writes a part of that text. Its line 1461 stops the build when a check failed.')
newref(o, 20, E, TESTS)
save(p, o)

# ---------------------------------------------------------------- local.sha
p, o = load('local_sha.overview')
o['purpose'] = swap(o['purpose'], 'The file lists the sha256 checksums of five local run files of the rerun: go.sh, ra.sh, like.spec, cfwd.spec and crev.spec.',
                    'The file lists the sha256 checksums that five run files of the rerun had at launch (the start of the rerun on 2026-11-17): go.sh, ra.sh, like.spec, cfwd.spec and crev.spec.')
st = o['main_flow'][3]; assert st['step'].endswith('On 2026-11-21 all 5 files gave OK (run for this page).')
st['step'] += ' On 2026-11-24 it printed `go.sh: FAILED` and `OK` for the 4 other files. Line 20 of go.sh was edited on that day.'
st = o['main_flow'][4]
st['step'] = swap(st['step'], 'The result there is: pass, 6 files equal [Ref1] [Ref3].',
                  'The facts sheet in this folder was built before the edit of go.sh. It says: pass, 6 files equal [Ref1] [Ref3]. Since the edit a new run of build_facts.py fails this check. It then stops and writes no file [Ref8].')
i = note(o, '**What the list allows.**'); assert o['behavior_notes'][i].endswith('`sha256sum -c` and check 20 fail.')
o['behavior_notes'][i] += (' This is the case for go.sh since 2026-11-24. Line 20 of go.sh was edited on that day (the text of one message). local.sha was not changed. So line 1 still holds the checksum of the text that ran. '
                           'With the old line 20 put back, go.sh has this checksum again [Ref8]. The page `go.sh.md` in this folder (the explanation of go.sh) shows the old line.')
i = note(o, '**Local copies only.**'); assert o['behavior_notes'][i].endswith('So the list alone does not show what ran on CRB [Ref3].')
o['behavior_notes'][i] += ' Line 1 is the checksum that go.sh had at launch. Since 2026-11-24 it is not the checksum of the local go.sh.'
i = note(o, '**Evidence that CRB ran the same content.**')
o['behavior_notes'][i] = swap(o['behavior_notes'][i], '**Evidence that CRB ran the same content.**', '**Evidence that CRB ran the listed content.**') + ' For go.sh the listed content is the text that ran. The local go.sh differs from it in line 20 since 2026-11-24.'
i = note(o, '**Who wrote the file.**')
o['behavior_notes'].insert(i + 1, '**Do not write the list again.** The command of step 3 would replace the listed checksums with those of the present files. It would also change the file time of local.sha. Decision (h) of the facts sheet prints that file time [Ref2]. For a later copy of the edited go.sh to CRB, write the checksum list of the copied files under another name.')
r = ref(o, 'Ref1'); assert r['what'].endswith('The function `main` (lines 1033 to 1052) ends with status 1 when a check fails.')
r['what'] += ' It builds the text of the sheet in line 1037. It writes the files after that, in lines 1038 to 1041. The script `facts_text4.py` writes a part of that text. Its line 1461 stops the build when a check failed.'
r = ref(o, 'Ref2'); assert r['what'].endswith('require that it is later than the file time of the rules file.')
r['what'] += ' Lines 1174 to 1180 print this file time in decision (h).'
newref(o, 8, E, TESTS.replace('in a copy of the run folder', 'in a copy of this folder'))
save(p, o)
p, c = load('local_sha.c01'); s = seg(c, 1)
s['text'] = swap(s['text'], 'Checksum of `go.sh`, the driver script of the rerun.\n', 'Checksum that `go.sh`, the driver script of the rerun, had at launch.\n')
s['text'] = swap(s['text'], '- The facts sheet states that the 2 logs',
                 '- The local go.sh no longer has this checksum. Its line 20 was edited on 2026-11-24 (the text of one message). Its sha256 is now %s. With the old line 20 put back it has the listed value again [Ref8].\n- The facts sheet states that the 2 logs' % NEW_SHA)
save(p, c)

# ---------------------------------------------------------------- go2.sh, rx.sh, go2.sha, log of go.sh
MARK_OLD = 'The scripts do not say who creates it.'
p, o = load('go2.overview'); w = word(o, 'Marker file')
w['def'] = swap(w['def'], MARK_OLD, 'The messages of go2.sh, `ra.sh` and `rx.sh` do not say what the file stands for. None of the scripts that test the file says who creates it. Since 2026-11-24 the message in line 20 of go.sh says what the file stands for: Jeremy or someone else is using CRB. ' + JEREMY_HERE)
hits = [r for r in o['refs'] if r['what'].startswith('the driver script that ran before go2.sh in the rerun.')]; assert len(hits) == 1 and hits[0]['path'].endswith('/go.sh')
hits[0]['what'] += ' Line 20 of this local file was edited on 2026-11-24 (the text of one message). The lines named here are unchanged.'
save(p, o)
p, o = load('rx.overview'); w = word(o, 'Marker file')
w['def'] = swap(w['def'], MARK_OLD, 'The messages of rx.sh, `ra.sh` and go2.sh do not say what the file stands for. None of the scripts that test the file says who creates it. Since 2026-11-24 the message in line 20 of go.sh says what the file stands for: Jeremy or someone else is using CRB. ' + JEREMY_THERE)
i = note(o, 'Is the local rx.sh the script that ran in the rerun:')
o['behavior_notes'][i] = swap(o['behavior_notes'][i], 'It stops the run when the copy differs [Ref10].',
                              'It stops the run when the copy differs [Ref10]. Line 20 of the local go.sh was edited on 2026-11-24 (the text of one message). The lines of go.sh that hold this value and its test are the same as in the text that ran [Ref10].')
r = ref(o, 'Ref10'); assert 'Line 14 of go.sh' in r['what'] and 'RXSHA' in r['what']
r['what'] += ' Line 20 of the local go.sh was edited on 2026-11-24 (the text of one message). Lines 14 and 22 of go.sh are the same as in the text that ran. The page `go.sh.md` in the folder of go.sh (the explanation of go.sh) gives the proof.'
save(p, o)
p, o = load('go2_sha.overview')
hits = [s for s in o['main_flow'] if s['step'].startswith('build_facts.py reads this line together with the 5 lines of local.sha')]; assert len(hits) == 1
hits[0]['step'] = swap(hits[0]['step'], 'reports the test as check 20 of the facts sheet: pass, 6 files equal [Ref1] [Ref3].', 'reports the test as check 20 of the facts sheet. The facts sheet in this folder was built before line 20 of go.sh was edited on 2026-11-24. It says: pass, 6 files equal [Ref1] [Ref3].')
i = note(o, '**What the line allows.**'); assert o['behavior_notes'][i].endswith('`sha256sum -c` and check 20 fail.')
o['behavior_notes'][i] += ' Check 20 also tests the 5 files of local.sha. Since 2026-11-24 a new run of build_facts.py fails check 20 because of go.sh. Line 20 of go.sh was edited on that day. The page `go.sh.md` in this folder (the explanation of go.sh) gives the proof. `sha256sum -c go2.sha` still prints `go2.sh: OK` (tested on 2026-11-24).'
save(p, o)
p, o = load('go_log.overview'); r = ref(o, 'Ref1'); assert r['path'].endswith('/go.sh') and r['what'].endswith('print the other state lines and `ALLDONE`.')
r['what'] += ' Line 20 of the local file was edited on 2026-11-24 (the text of one message). The script that ran had the older line 20. The page `go.sh.md` in the folder of go.sh (the explanation of go.sh) gives the proof. The lines named here are unchanged.'
save(p, o)

# ---------------------------------------------------------------- analysis scripts
p, o = load('build_facts.overview')
o['purpose'] = swap(o['purpose'], 'and writes `S/facts.json` and `S/FACTS.md`.', 'and writes `S/facts.json` and `S/FACTS.md` when every check passes.')
i = note(o, '**The 27 checks, by key, in groups.**'); assert o['behavior_notes'][i].endswith('All 27 passed in the build of 2026-11-17 [Ref9].')
newref(o, 17, E, TESTS.replace('`check_facts_build.py` runs `build_facts.py` in a copy of the run folder.', '`check_facts_build.py` runs this script in a copy of `S`.'))
o['behavior_notes'][i] += (' Since 2026-11-24 a new build fails `sha-local` (check 20 of the facts sheet). Line 20 of go.sh was edited on that day. So go.sh no longer has the sha256 that `local.sha` lists for it. '
                           'The build then stops before it writes a file [Ref17].')
hits = [w for w in o['words'] if w['def'].endswith('Check `sha-local` tests the present local files against the two lists.')]; assert len(hits) == 1
hits[0]['def'] += ' Since 2026-11-24 it fails for go.sh.'
save(p, o)
p, c = load('build_facts.c02')
hits = [s for s in c['segments'] if s['text'].startswith('Check `sha-local`.')]; assert len(hits) == 1
hits[0]['text'] = swap(hits[0]['text'], 'It shows that the 6 files in `S` have not changed since the two lists were written. The row of lines 853 to 866 says what is known about the copies on CRB.',
    'A pass shows that the 6 files in `S` have not changed since the two lists were written. The row of lines 853 to 866 says what is known about the copies on CRB.\n'
    '- The stored sheet shows a pass. A new build fails since 2026-11-24. Line 20 of go.sh was edited on that day (the text of one message). So `bad` holds `go.sh`. With the old line 20 put back the check passes again [Ref17].')
hits = [s for s in c['segments'] if '`local_sha`: the sha256 values of the local rx.sh, go.sh and go2.sh.' in s['text']]; assert len(hits) == 1
hits[0]['text'] = swap(hits[0]['text'], '`local_sha`: the sha256 values of the local rx.sh, go.sh and go2.sh.',
    '`local_sha`: the sha256 values of the local rx.sh, go.sh and go2.sh. Since 2026-11-24 the value for go.sh is that of the edited file. It is not the value of the text that ran.')
save(p, c)
p, o = load('facts_text.overview')
hits = [w for w in o['words'] if w['def'] == 'a file in `S`. It holds the sha256 values of go.sh, ra.sh and the three spec files like.spec, cfwd.spec and crev.spec.']; assert len(hits) == 1
hits[0]['def'] = ('a file in `S`. It holds the sha256 values that go.sh, ra.sh and the three spec files like.spec, cfwd.spec and crev.spec had when the rerun started. '
                  'Line 20 of go.sh was edited on 2026-11-24. Since then go.sh no longer has the value that the file lists for it. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit.')
save(p, o)
p, o = load('facts_text4.overview')
w = word(o, 'Integrity check'); assert w['def'].endswith('Section 1.4 of the present sheet lists 27 checks, all with the result `pass` [Ref3] [Ref4].')
w['def'] += (' Since 2026-11-24 a new build stops at line 1461. Check 20 (key `sha-local`) fails then. It compares the sha256 of go.sh and of five other local scripts and spec files with the lists `local.sha` and `go2.sha`. '
             'Line 20 of go.sh was edited on 2026-11-24. So go.sh no longer has the sha256 that `local.sha` lists for it. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit.')
w = word(o, 'Present sheet, present values')
w['def'] = swap(w['def'], 'are examples of what the code prints with the present data [Ref4].', 'are examples of what the code printed with the present data [Ref4].')
save(p, o)
print('changed %d annotation files' % len(changed))
