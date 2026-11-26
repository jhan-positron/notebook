# Third version of the corrections of the list generator, the agent briefing and three hand-written companions.
# Each file is first restored from the backup (state before the edit of go.sh line 20).
import shutil, sys
G = sys.argv[1]
C = '/home/jhan/workspace/titan/cache-perf/crb'
T = C + '/tmp/agent-scratch/code-data-list-2026-11-21'
S = C + '/tmp/agent-scratch/w120-7200-2026-11-17'
E = C + '/tmp/agent-scratch/go-edit-2026-11-24'
NOW = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl'
def patch(path, pairs):
    shutil.copyfile(G + '/backup/' + path[len(C) + 1:], path)
    t = open(path).read()
    for old, new in pairs:
        assert t.count(old) == 1, (path.split('/')[-1], old[:70], t.count(old))
        t = t.replace(old, new)
    open(path, 'w').write(t)
    print('patched', path[len(C) + 1:], len(pairs))

# ------------------------------------------------------------------ make_list.py
GUARD = r'''

def check_two_texts_go():
    """The two texts of go.sh: stop when a tested statement of the open point "Two texts of go.sh" no longer holds.

    Tested: the text of line 20, both sha256 values, the file local.sha, go2.sh against go2.sha, the lines of the two
    session records, the lines of the notes about Jeremy, the place of check 20 in build_facts.py and in facts.json,
    and the stored output of the two tests of [Ref9]. Not tested: the copy on CRB. The tests of [Ref9] are not run here.
    """
    import hashlib
    sha = lambda b: hashlib.sha256(b).hexdigest()
    src = open(MAN['go']['path'], 'rb').read().decode()
    if src.split('\n')[19] != GO_NEW_LINE20 or src.count(GO_NEW_LINE20) != 1:
        die('go.sh: line 20 is not the line of the edit of 2026-11-24')
    raw = open(MAN['local_sha']['path'], 'rb').read()
    if sha(raw) != LOCAL_SHA_SHA256:
        die('local.sha is not the list of 2026-11-17 any more')
    listed = [l.split()[0] for l in raw.decode().splitlines() if l.split()[1:] == ['go.sh']]
    old = sha(src.replace(GO_NEW_LINE20, GO_OLD_LINE20).encode())
    if listed != [old] or not old.startswith('75bc50b0') or not sha(src.encode()).startswith('d68cf6c0'):
        die('go.sh: with the old line 20 put back the sha256 is %s, local.sha lists %s' % (old, listed))
    # session record of 2026-11-17: line 295 wrote go.sh (the text that local.sha lists), line 310 shows the test on CRB
    rec = open(RECORD).read().split('\n')
    cmd = [c['input']['command'] for c in json.loads(rec[294])['message']['content'] if c.get('type') == 'tool_use'][0]
    m = re.search(r"cat > go\.sh <<'EOF'\n(.*?\n)EOF\n", cmd, re.S)
    if not m or sha(m.group(1).encode()) != old:
        die('line 295 of the session record of 2026-11-17 does not hold the go.sh text that local.sha lists')
    if 'go.sh: OK' not in rec[309]:
        die('line 310 of the session record of 2026-11-17 does not hold "go.sh: OK"')
    # session record of the edit: line 2153 is the instruction of the user, line 2245 is the edit
    rec = open(RECORD24).read().split('\n')
    ask, edit = json.loads(rec[2152]), json.loads(rec[2244])
    said = ask['message']['content'] if ask.get('type') == 'user' else ''
    if not (isinstance(said, str) and said.startswith('`%s` in go.sh changes to `%s`' % (GO_OLD_LINE20, GO_NEW_LINE20))):
        die('line 2153 of the session record of the edit does not hold the instruction of the user')
    calls = [c['input'] for c in edit['message']['content'] if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Edit']
    if [(c['file_path'], c['old_string'], c['new_string']) for c in calls] != [(MAN['go']['path'], GO_OLD_LINE20, GO_NEW_LINE20)]:
        die('line 2245 of the session record of the edit does not hold the edit of go.sh line 20')
    # go2.sh was not edited: it has the sha256 of go2.sha, and lines 16 and 25 hold the old message
    g2 = open(os.path.join(S, 'go2.sha')).read().split()
    if g2[1:] != ['go2.sh'] or sha(open(MAN['go2']['path'], 'rb').read()) != g2[0] or not g2[0].startswith('38edfa54'):
        die('go2.sh does not have the sha256 that go2.sha lists')
    need(MAN['go2']['path'], 16, 'fail "RUNNING file present"')
    need(MAN['go2']['path'], 25, 'fail "RUNNING file present"')
    # the notes about Jeremy [Ref8]
    notes = os.path.join(C, 'jeremy-plan-constraints-2026-10-30.md')
    need(notes, 12, 'a reserved whole-host window in which Jeremy runs measurements')
    need(notes, 13, '`/tmp/positron-perf.RUNNING`, present for the whole block')
    # check 20 of the facts sheet is the check with the key sha-local (build_facts.py lines 772 to 780)
    bf = MAN['build_facts']['path']
    need(bf, 773, "for f in ('local.sha', 'go2.sha'):")
    need(bf, 777, "bad = [n for n, h in listed.items() if fd.sha256(os.path.join(S, n)) != h]")
    need(bf, 778, "chk('sha-local'")
    if [c['key'] for c in json.load(open(os.path.join(S, 'facts.json')))['meta']['checks']].index('sha-local') + 1 != 20:
        die('facts.json: the check sha-local is not check 20')
    # the kept tests of the edit [Ref9]: the scripts, the copy of the older text, and the stored output of two tests
    for name in ('common.py', 'check_line20.py', 'check_facts_build.py'):
        if not os.path.isfile(os.path.join(GOEDIT, name)):
            die('go-edit-2026-11-24/%s is missing' % name)
    if sha(open(os.path.join(GOEDIT, 'go.sh.as-run-2026-11-17'), 'rb').read()) != old:
        die('go-edit-2026-11-24/go.sh.as-run-2026-11-17 does not have the sha256 that local.sha lists')
    wanted = {'check_line20.out': ['PASS with the old line 20 put back in memory, the text of the local go.sh has the listed sha256'],
              'check_facts_build.out': ['PASS run 1 ends with status 1 and the stop message', 'PASS run 1 changes nothing in the copied run folder',
                                        'PASS run 2 ends with status 0 and prints "checks: 27, failed: 0"']}
    for name, lines in wanted.items():
        out = open(os.path.join(GOEDIT, name)).read().strip().split('\n')
        if out[-1] != 'ALL PASS' or any(l.startswith('FAIL') for l in out) or not all(any(l.startswith(w) for l in out) for w in lines):
            die('go-edit-2026-11-24/%s: the stored output of the test is not a pass' % name)
'''
POINT = ("    '**Two texts of `go.sh`: they differ in the message of line 20 only.** The run of 2026-11-17 used the text with the sha256 value `75bc50b0...`. "
         "This value is the `go.sh` entry of `local.sha`. The session record of 2026-11-17 shows that `sha256sum -c local.sha` printed `OK` for `go.sh` on CRB before the start [Ref3]. "
         "Line 295 of the record holds the last command that wrote `go.sh` before the copy to CRB. The script text in that command has the same sha256 value [Ref3]. "
         "On 2026-11-24 the message of line 20 was changed on the instruction of the user. `RUNNING file present` became `RUNNING file present, Jeremy or someone else is using CRB` [Ref7]. "
         "Jeremy is another user of CRB [Ref8]. The local `go.sh` now has the sha256 value `d68cf6c0...`. With this edit reversed, the local text has the value `75bc50b0...` again [Ref9]. "
         "`local.sha` was not changed. So `sha256sum -c local.sha` in the local folder now prints `go.sh: FAILED`. "
         "Check 20 of `build_facts.py` makes the same comparison (line 778, key `sha-local`). So a new run of `build_facts.py` fails check 20. It then stops and writes no file. With the edit reversed it passes [Ref9]. "
         "The edit was made in the local file only. `go2.sh` was not edited. It keeps the old message in lines 16 and 25.',\n")
patch(T + '/make_list.py', [
    ("# The comment edit of 2026-11-13 18:32:07 UTC (line 1000 of RECORD13): BW_OLD_COMMENT became BW_NEW_COMMENT.\n",
     "RECORD24 = '" + NOW + "'\n"
     "GOEDIT = os.path.join(C, 'tmp', 'agent-scratch', 'go-edit-2026-11-24')\n"
     "# The message edit of 2026-11-24 (line 2245 of RECORD24, instruction of the user in line 2153; file time of go.sh 20:35:43 UTC):\n"
     "# line 20 of go.sh, GO_OLD_LINE20 became GO_NEW_LINE20. LOCAL_SHA_SHA256 is the sha256 of the unchanged file local.sha.\n"
     "GO_OLD_LINE20 = '[ -e /tmp/positron-perf.RUNNING ] && fail \"RUNNING file present\"'\n"
     "GO_NEW_LINE20 = '[ -e /tmp/positron-perf.RUNNING ] && fail \"RUNNING file present, Jeremy or someone else is using CRB\"'\n"
     "LOCAL_SHA_SHA256 = 'dce73e4e22dd068e78806142d3a0a1b4bb54eaf4ba5e5b7012fdb0d6a9c2ab26'\n"
     "# The comment edit of 2026-11-13 18:32:07 UTC (line 1000 of RECORD13): BW_OLD_COMMENT became BW_NEW_COMMENT.\n"),
    ("        die('the session record of 2026-11-13 does not hold the comment edit')\n",
     "        die('the session record of 2026-11-13 does not hold the comment edit')\n" + GUARD),
    ("    check_two_texts()\n", "    check_two_texts()\n    check_two_texts_go()\n"),
    ("Two files lie outside `crb`: the session records [Ref3] and [Ref6].')", "Three files lie outside `crb`: the session records [Ref3], [Ref6] and [Ref7].')"),
    ("This list uses two of them [Ref3] [Ref6].", "This list uses three of them [Ref3] [Ref6] [Ref7]."),
    ("    need(MAN['ra']['path'], 16, 'sha256sum -c')\n",
     "    need(MAN['ra']['path'], 16, 'sha256sum -c')\n"
     "    w('   - The local `go.sh` is not the copied text any more. The message of its line 20 was changed on 2026-11-24 (section 7). In the local folder, `sha256sum -c local.sha` now prints `go.sh: FAILED`.')\n"),
    ("    w('- ' + code('go'))\n",
     "    w('- ' + code('go'))\n"
     "    w('  - The local file and its companion show the text of 2026-11-24. It differs from the text that ran in the message of line 20 only (section 7).')\n"),
    ("    w('  - ' + code('local_sha', 'local.sha'))\n",
     "    w('  - ' + code('local_sha', 'local.sha'))\n"
     "    w('    - The `go.sh` entry is the sha256 value of the text that ran. The local `go.sh` has another value since 2026-11-24 (section 7).')\n"),
    ("    '**The binaries are not local.** `bw_old`, `bw_new` and `bwx12` are in no local folder.", POINT + "    '**The binaries are not local.** `bw_old`, `bw_new` and `bwx12` are in no local folder."),
    ("Lines 309, 313, 339, 353, 365 and 377 hold the commands of section 3.1.' % RECORD,",
     "Lines 309, 313, 339, 353, 365 and 377 hold the commands of section 3.1. Line 310 holds the output of the copy command, with `go.sh: OK`. Line 295 holds the last command that wrote `go.sh` before the copy.' % RECORD,"),
])
t = open(T + '/make_list.py').read()
tail = "The file lies outside the project folder.' % RECORD13,\n"
assert t.count(tail) == 1
t = t.replace(tail, tail +
    "    '[Ref7] `%s`, lines 2153 and 2245: record of the Claude Code session in which line 20 of `go.sh` was changed. The session began on 2026-11-22. Line 2153 holds the instruction of the user (2026-11-24, 20:27:54 UTC). Line 2245 holds the edit. The file lies outside the project folder.' % RECORD24,\n"
    "    '[Ref8] `jeremy-plan-constraints-2026-10-30.md`, lines 12 and 13: notes of 2026-10-30 about the tests of Jeremy on CRB. The file `/tmp/positron-perf.RUNNING` is present for the whole of each time window that is reserved for these tests.',\n"
    "    '[Ref9] `tmp/agent-scratch/go-edit-2026-11-24`: tests of 2026-11-24 for the edit of `go.sh` line 20, with their output in the files that end with `.out`. `check_line20.py` puts the old line back in a copy of the text of `go.sh` and compares the sha256 value. It does not change `go.sh`. `check_facts_build.py` runs `build_facts.py` in a copy of the run folder, with the edited text and with the old line. `go.sh.as-run-2026-11-17` is a copy of `go.sh` from before the edit.',\n")
open(T + '/make_list.py', 'w').write(t)

# ------------------------------------------------------------------ BRIEF.md
shutil.copyfile(G + '/backup/tmp/agent-scratch/code-data-list-2026-11-21/BRIEF.md', T + '/BRIEF.md')
b = open(T + '/BRIEF.md').read()
assert '8. Two texts of go.sh' not in b and b.rstrip().split('\n')[-1].startswith('   - Line 365: the start of go2.sh.')
b = b.rstrip('\n') + '\n' + (
    '8. Two texts of go.sh. Line 20 of the local `S/go.sh` was edited on 2026-11-24, after the rerun, on the instruction of the user. '
    '`fail "RUNNING file present"` became `fail "RUNNING file present, Jeremy or someone else is using CRB"`. '
    'Jeremy is another user of CRB: `' + C + '/jeremy-plan-constraints-2026-10-30.md`, lines 12 and 13. '
    'No other line changed. The file still has 48 lines. '
    'The rerun ran the older text. Its sha256 is `75bc50b0...`. This value is the go.sh entry of `S/local.sha`. '
    'It is also the sha256 of the script text in line 295 of the session record of point 1. That line holds the last command that wrote go.sh before the copy to CRB. '
    'The local text has the sha256 `d68cf6c0...`. With the old line 20 put back, the local text has `75bc50b0...` again. '
    '`S/local.sha` was not changed. So `sha256sum -c local.sha` in `S` prints `go.sh: FAILED`. '
    'A new run of `build_facts.py` fails check 20 (key `sha-local`: the sha256 of the local run files against `local.sha` and `go2.sha`). It then stops at line 1461 of `facts_text4.py`, before it writes a file. '
    'Do not write `S/local.sha` or `S/go2.sha` again. They are the records of the two launches. FACTS.md prints the file time of `local.sha` in decision (h). '
    '`S/go2.sh` was not edited. It keeps the older message in lines 16 and 25. The edit was made in the local file only. '
    'The tests of the edit and a copy of the older go.sh are in `' + E + '`. '
    'The record of the Claude Code session of the edit holds the instruction (line 2153, 2026-11-24 20:27:54 UTC) and the edit (line 2245): `' + NOW + '`. That session began on 2026-11-22 (UTC). The record lies outside the project folder.\n')
open(T + '/BRIEF.md', 'w').write(b); print('patched BRIEF.md (point 8 added)')

# ------------------------------------------------------------------ hand-written companions
TESTREF = ('`' + E + '/check_facts_build.py` and its output `check_facts_build.out` in the same folder: the test of 2026-11-24 that ran `build_facts.py` in a copy of `S`. '
           'With the edited `go.sh` the build ended with status 1 and wrote no file. With the old line 20 put back it ended with status 0 and printed `checks: 27, failed: 0`.')
f = S + '/FACTS.md.md'
patch(f, [
    ('The script `build_facts.py` wrote every measured rate from the raw result files, and a new run of the script overwrites the file.',
     'The script `build_facts.py` wrote every measured rate from the raw result files, and a new run of the script overwrites the file only when all 27 integrity checks pass.'),
    ('- **Size:** 1118 lines, 185615 bytes.\n',
     '- **Size:** 1118 lines, 185615 bytes.\n'
     '- **A new build stops since 2026-11-24:** line 20 of `S/go.sh` was edited on that day (the text of one message). Check 20 (line 232 of the sheet) compares the sha256 (a checksum) of 6 local files with the lists `S/local.sha` and `S/go2.sha`. The 6 files are go.sh, go2.sh, ra.sh and the three spec files. '
     'So check 20 fails for `go.sh` in a new build. `facts_text4.py` then stops the build before a file is written [Ref1] [Ref6]. A test of 2026-11-24 ran the build in a copy of the folder `S` [Ref10]. '
     'With the edited `go.sh` the build ended with status 1 and wrote no file. With the old line 20 put back the build passed. '
     'Its `FACTS.md` and its `facts.json` then equal the stored files after the folder path of the copy is replaced by the real path. '
     'The file list of the sheet names `S/go.sh` in line 962 and `S/local.sha` in line 968. `S/local.sha` holds the sha256 of the text that ran. It does not hold the sha256 of the present `go.sh`.\n'),
    ('27 numbered checks of the result files. All 27 say "pass". A sheet with a failed check is not written: `facts_text4.py` stops the build when one check failed [Ref6]. |',
     '27 numbered checks of the result files. All 27 say "pass" in the stored sheet. A sheet with a failed check is not written: `facts_text4.py` stops the build when one check failed [Ref6]. '
     'Checks 19, 20 and 26 (lines 231, 232 and 238) read `S/go.sh` as it was at the build. Check 20 fails in a new build since 2026-11-24 (see "What this file is"). |'),
])
t = open(f).read(); assert t.rstrip('\n').split('\n')[-1].startswith('- [Ref9] ')
open(f, 'w').write(t.rstrip('\n') + '\n- [Ref10] ' + TESTREF + '\n')
f = S + '/facts.json.md'
patch(f, [
    ('All 27 have `ok` = true. A file with a failed check is not written.', 'All 27 have `ok` = true in the stored file. A file with a failed check is not written.'),
    ('This happens before `build_facts.py` writes `facts.json` and FACTS.md [Ref2]. Section 1.4 of FACTS.md prints the same 27 checks. |',
     'This happens before `build_facts.py` writes `facts.json` and FACTS.md [Ref2]. Since 2026-11-24 a new build gives the check `sha-local` (check 20) `ok` = false. Line 20 of `S/go.sh` was edited on that day. '
     'So `go.sh` no longer has the sha256 that the list `S/local.sha` holds for it. A new build then writes no file [Ref21]. Section 1.4 of FACTS.md prints the same 27 checks. |'),
])
t = open(f).read(); assert t.rstrip('\n').split('\n')[-1].startswith('- [Ref20] ')
open(f, 'w').write(t.rstrip('\n') + '\n- [Ref21] ' + TESTREF + '\n')
patch(C + '/new-test-kernel/whole-chip-rerun-7200.html.md', [
    ('| References | 1140 to 1143 | 76 entries, numbered Ref1 to Ref76 in the list of the page. Each entry is a file path and a note on what the file holds |',
     '| References | 1140 to 1143 | 76 entries, numbered Ref1 to Ref76 in the list of the page. Each entry is a file path and a note on what the file holds. '
     'Ref2 of the page names `S/go.sh`. Line 20 of that file was edited on 2026-11-24, after the page was built. The edit changed the text of one message. The page `go.sh.md` in `S` (the explanation of go.sh) gives the record of the edit |'),
])
