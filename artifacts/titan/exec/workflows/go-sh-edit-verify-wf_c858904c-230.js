export const meta = {
  name: 'go-sh-edit-verify',
  description: 'Adversarial check of the corrections after the edit of go.sh line 20: every new sentence against evidence, regression, residual sweep, plain English, and the draft answer',
  phases: [{ title: 'Verify', detail: '8 agents, each with its own scope, all read-only' }],
}

const G = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771/scratchpad/goedit'
const BRIEF = G + '/BRIEF-verify.md'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          quote: { type: 'string', description: 'exact quote, at most 300 characters' },
          input_file: { type: 'string', description: 'for a generated companion: the input file that holds the sentence; else empty' },
          kind: { type: 'string', enum: ['false', 'unsupported', 'inconsistent', 'missed', 'regression', 'style'] },
          evidence: { type: 'string', description: 'what you ran or read, and what it showed' },
          proposed: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'quote', 'kind', 'evidence', 'severity'],
      },
    },
    checked_ok: {
      type: 'array',
      items: {
        type: 'object',
        properties: { claim: { type: 'string' }, evidence: { type: 'string' } },
        required: ['claim', 'evidence'],
      },
    },
    not_checked: { type: 'string' },
  },
  required: ['findings', 'checked_ok', 'not_checked'],
}

const HEAD = 'First read the brief ' + BRIEF + ' in full. It defines the folders C, S, T, LIST, G, MEM, what happened, the measured facts, the policy for notes, the report format and the hard rules. Your label is "@L@" (your scratch folder is ' + G + '/agents2/@L@/). Then do this:\n\n'

const SCOPES = [
  { label: 'claims-go', scope:
    'Scope: the companion of go.sh. Files: S/go.sh.md, its inputs T/ann/go.overview.json and T/ann/go.c01.json, and the diffs G/diffs/*go.sh.md.diff, *ann__go.overview.json.diff, *ann__go.c01.json.diff.\n' +
    'Take EVERY sentence that is new or changed (the "+" lines of the diffs) and split it into single claims. Try to refute each claim with evidence that you collect yourself: read S/go.sh, the log C/results/go-T72-20261117T221209Z.log, S/local.sha, the two session records (parse the JSON lines named in the brief), C/jeremy-plan-constraints-2026-10-30.md, S/ra.sh, C/tmp/agent-scratch/w120-2026-11-15/rx.sh, S/go2.sh, S/build_facts.py, S/facts_text4.py, S/FACTS.md. Compute checksums yourself. Rebuild the old text of go.sh in your scratch folder (put line 20 back) and hash it.\n' +
    'Also check: every [RefN] that a new sentence cites exists in the reference list of the page and holds what the sentence needs; the line numbers named (17, 20, 295, 309, 310, 313, 772 to 780, 1037, 1038 to 1041, 1461, 2153, 2245, 12, 13) are right; the times (20:27:54, 20:35:42, 22:11:29 UTC) are right; row 20 of the left column of S/go.sh.md equals line 20 of S/go.sh; the segment of line 20 has at most 6 bullets; the sentences that were NOT changed in the row of line 20 and in the notes are still true.\n' +
    'For the claim that a new run of build_facts.py stops and writes no file, and passes with the old line put back: do NOT run the sandbox script (another agent does). Verify it by reading the code path (S/build_facts.py function main and run_checks, S/facts_text.py function need, S/facts_text4.py line 1461).' },
  { label: 'claims-sha', scope:
    'Scope: the companions of the checksum lists and of the neighbour scripts. Files: S/local.sha.md, S/go2.sha.md, S/go2.sh.md, C/tmp/agent-scratch/w120-2026-11-15/rx.sh.md, C/results/go-T72-20261117T221209Z.log.md, their inputs T/ann/local_sha.overview.json, T/ann/local_sha.c01.json, T/ann/go2_sha.overview.json, T/ann/go2.overview.json, T/ann/rx.overview.json, T/ann/go_log.overview.json, and the matching files in G/diffs.\n' +
    'Take EVERY sentence that is new or changed (the "+" lines of the diffs), split it into single claims, and try to refute each claim with evidence that you collect yourself (run `sha256sum -c` read-only through Python with cwd=S, read the scripts, read S/FACTS.md lines 232, 238 and 288, read S/facts_text.py lines 380 to 390, read the session record line 309 and 310).\n' +
    'Check in particular: the new bullet "Do not write the list again" (is each of its two reasons true?); the renamed title "Evidence that CRB ran the listed content" (does any other file still point to the old title?); the statement that ra.sh, rx.sh and go2.sh give no meaning for the marker file and do not say who creates it (read every line of the three scripts that names the file, comments included); "Lines 14 and 22 of go.sh, which hold this value and its test, are unchanged"; "`sha256sum -c go2.sha` still prints `go2.sh: OK`"; every [RefN] cited by a new sentence.\n' +
    'Also read each of these five companions once in full and report any OTHER sentence in them that the edit of go.sh line 20 made false and that is still not corrected.' },
  { label: 'claims-facts', scope:
    'Scope: the companions of the analysis scripts and of the facts sheet. Files: S/build_facts.py.md, S/facts_text.py.md, S/facts_text4.py.md (generated; inputs T/ann/build_facts.overview.json, T/ann/build_facts.c02.json, T/ann/facts_text.overview.json, T/ann/facts_text4.overview.json), and the hand-written S/FACTS.md.md, S/facts.json.md, C/new-test-kernel/whole-chip-rerun-7200.html.md, with the matching files in G/diffs.\n' +
    'Take EVERY sentence that is new or changed (the "+" lines of the diffs), split it into single claims, and try to refute each claim.\n' +
    'You are the ONE agent that may run the sandbox test: `python3 ' + G + '/sandbox_facts.py ' + G + '` (it builds a mirror below G/sbx out of symlinks and a copy of S, runs the copy of build_facts.py twice, and writes only below G/sbx; it takes about one minute). Read the script first and confirm that it cannot write into S. Then run it once and compare its output with the claims "status 1, no file written" and "with the old line 20 put back the build passed and wrote a FACTS.md and a facts.json with the stored content". Check afterwards that S/FACTS.md and S/facts.json still have their sha256 from G/before.json and their old file times.\n' +
    'Check in particular: FACTS.md.md says the new build "stops since 2026-11-24" and cites [Ref1] and [Ref6] (do these two references hold the order of the steps and the stop line?); the Short version of FACTS.md.md still has at most three sentences; the table rows that were changed in FACTS.md.md, facts.json.md and the html companion are still valid Markdown table rows (same number of cells as their neighbours, no line break); "Ref9" and "Ref15" of the sheet are S/go.sh and S/local.sha (S/FACTS.md lines 962 and 968); "Ref2 of the page names S/go.sh" in the HTML report (line 1143) and the page was built before 2026-11-24; check 26 really reads go.sh; the bullet count of the changed segments of build_facts.c02.json stays within 6.' },
  { label: 'claims-list', scope:
    'Scope: the list and its generator. Files: LIST, T/make_list.py, T/BRIEF.md, and the diffs G/diffs/*whole-chip-test-code-data-list.md.diff, *make_list.py.diff, *BRIEF.md.diff.\n' +
    '1. Take EVERY new sentence of LIST (5 new lines) and of point 8 of T/BRIEF.md, split it into single claims, and try to refute each claim with evidence that you collect yourself.\n' +
    '2. Review the new code of T/make_list.py line by line (the constants RECORD24, GO_OLD_LINE20, GO_NEW_LINE20 and the function check_two_texts_go). Does it test what its messages say? Copy the function into your scratch folder as a stand-alone script with the paths it needs, and run it on COPIES in these states: (a) the present files: must pass; (b) go.sh with another line changed: must stop; (c) go.sh with line 20 put back to the old text: must stop (the list text would be wrong then); (d) local.sha with another go.sh entry: must stop; (e) go2.sh with the new message in line 16: must stop. Report each state where the behaviour is not the wanted one. Also look for a way in which the guard passes although the open point "Two texts of go.sh" of the list is false.\n' +
    '3. Run `python3 T/make_list.py --check` (it writes nothing) and report its output. Confirm that LIST on disk is what the generator would write now: the size and line count that --check prints must equal those of the file.\n' +
    '4. Check the placement and the Markdown of the 5 new lines in LIST: the indentation of the three sub-bullets fits their parent items, the references [Ref3] and [Ref7] exist in the reference section and hold what the text needs, "section 7" is the right section number, the reference list is in order Ref1 to Ref7. Check that no line of LIST outside the 5 new ones changed (diff against the backup).\n' +
    '5. Read sections 1, 3.1, 3.2, 4.7, 7 and 8 of LIST in full and report any sentence that the edit of go.sh made false and that is still not corrected.' },
  { label: 'regression', scope:
    'Scope: nothing changed that should not have changed.\n' +
    '1. Recompute the sha256 of all 268 files of G/before.json. Report the set of changed files. It must be exactly the 28 files of G/changed.json. Report every other difference.\n' +
    '2. Read all 28 diffs in G/diffs in full. For each hunk decide whether it is an intended correction for the edit of go.sh line 20 (text about go.sh, local.sha, check 20, the marker message, Jeremy, new references) or the mechanical effect of a rebuild (byte count, sha256 of the source, the left cell of row 20). Report every hunk that is neither. For the annotation inputs: confirm that each JSON file still loads, and that the generated companion holds the same new text as its input (the build was run after the last input change: compare file times, and search each new input sentence in the companion).\n' +
    '3. Run `python3 T/companion_tool.py verify-all` and report the number of lines that say "left column equals the source" (wanted: 33) and the exit status. Run check-overview on the 9 changed overview files and check-ann on the 3 changed chunk files (names in G/changed.json). Run `python3 T/make_list.py --check`.\n' +
    '4. Evidence files: confirm that S/local.sha, S/go2.sha, S/go2.sh, S/ra.sh, the three spec files, S/FACTS.md, S/facts.json, C/new-test-kernel/whole-chip-rerun-7200.html and C/new-test-kernel/manual-run/run.sh have the content of the backup (where a backup exists) and their old file times (`stat`), and that `diff` of the backup go.sh against S/go.sh shows exactly one changed line.\n' +
    '5. Links: every relative link of LIST must resolve to an existing file (162 links). Every companion that LIST links must exist and be non-empty.\n' +
    '6. The 44 data companions: confirm that all are byte-equal to the backup, although data_companions.py was run again.\n' +
    '7. Look for leftovers of the work in the deliverable folders: files named *.tmp, *.bak, *.orig, or new files in S, T, C/new-test-kernel and the result folders that are newer than 2026-11-24 12:00 local time and are not in G/changed.json. Report each one.' },
  { label: 'residual', scope:
    'Scope: a FRESH sweep of the final state. Forget the list of places that were corrected. Search the whole deliverable again for statements that are false NOW, given the edit of go.sh line 20.\n' +
    'Search all of: every companion .md that LIST links (take the link targets from LIST), LIST, every file in T/ann and T/types, T/BRIEF.md, the text constants of T/make_list.py and T/data_companions.py.\n' +
    'Angles (use grep -n -i, then read every hit sentence with its neighbours): (1) checksum and identity: local.sha, "sha256sum -c", 75bc50b0, d68cf6c0, "script that ran", "text that ran", unchanged, "not changed", "have not changed", identical, "same content", "equal to", "check 20", sha-local, "still has", "copy on CRB", "local copy", "local go.sh", "run files", "5 files", "6 files", "all 27", "27 checks", 3628, 3665; (2) message and marker: RUNNING, marker, "who creates", "do not say", "does not say", "give no meaning", "stands for", Jeremy, "another user", "line 20", "stops the run with"; (3) instructions to the reader whose result changed: "run `sha256sum", "run build_facts", "a new run", "rebuild", "overwrites".\n' +
    'Report as `missed` every sentence that is false now, or that tells the reader to do something and names a result that no longer comes out. Apply the policy of the brief: do not report a sentence that stays literally true and only mentions the topic in passing, but DO report it when you can show a concrete way in which a careful reader is led to a false belief about the present files; give that reading in the evidence field.\n' +
    'Report as `inconsistent` every pair of places that now state the same fact in a different way (for example one page says "build of 2026-11-17" and another "2026-11-18", or the old message is quoted differently, or a page says the copy on CRB was changed).\n' +
    'Also check the opposite error: a NEW sentence that claims too much (for example that states something about the present copy on CRB as a fact, or that says "the scripts" where only go.sh is meant).' },
  { label: 'english', scope:
    'Scope: language and format of the NEW text only. Take the "+" lines of all files in G/diffs (skip the diff of go.sh itself and the mechanical lines with byte counts and checksums), and the four memory notes MEM/crb-go-sh-remove-boot-id-todo.md, MEM/crb-whole-chip-rerun-7200-2026-11-17.md (lines 15 and 19), MEM/crb-whole-chip-code-data-list-2026-11-21.md (lines 19 and the bullet on go.sh), MEM/MEMORY.md (the line on go.sh).\n' +
    'Check every new sentence against the plain-English rules that you were given (no idioms or metaphors; one claim per sentence; short sentences; a term is defined at first use on its page: look at the word list of the page for "Jeremy", "block", "transcript", "sha256", "facts sheet", "check 20", "CRB", "marker file", "stored sheet", "launch"; numbers carry units; a citation follows a sentence). Check the rule of this user: no pronoun for a person whose pronouns are not stated (search the new text for he, his, him, she, her).\n' +
    'Check the format rules of T/BRIEF.md sections 4 and 5 for annotation text: `text` of a segment has 1 to 4 short sentences or up to 6 bullets; only the markup `code`, **bold** and "- " bullets; no tabs; `role` at most 14 words; notes of call_sequence at most 14 words.\n' +
    'Check consistency of wording across the pages: the same fact should be said with the same words. Collect, for each of these facts, every wording that the new text uses, and report real differences in meaning: the date of the edit; what was edited ("the text of one message", "the message of line 20", "line 20"); the old message and the new message (exact strings); "the text that ran" / "the text of the launch" / "the script that ran"; "stored sheet" / "sheet of 2026-11-17" / "build of 2026-11-17"; "a copy of the folder" / "a copy of the run folder" / "a copy of `S`" for the sandbox test.\n' +
    'Report each defect as `style` (or `inconsistent`), with a proposed replacement sentence. Do not report sentences that the diff did not add.' },
  { label: 'answer', scope:
    'Scope: the draft of the answer to the user and the memory notes.\n' +
    '1. Read ' + G + '/DRAFT-answer.md. It holds 17 claims, C1 to C17. Try to refute EACH claim with evidence that you collect yourself. For C4: rebuild the test in your scratch folder (a copy of S/go.sh in which every occurrence of /tmp/positron-perf.RUNNING is replaced by a path in your scratch folder, a fake HOME folder in your scratch folder with the sub-folder cache-perf/results; run the copy with bash once with the marker file present and once without; with the fake HOME the script cannot pass its line 22, so no benchmark can start). For C6 and C7 you are the ONE agent that may run `python3 ' + G + '/test_start.py <scratchpad> ' + '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17 ' + G + '` where <scratchpad> is the parent folder of G (read the script first: it runs the text of C/new-test-kernel/manual-run/run.sh without ssh, in fake home folders below G/run-start, with stand-in programs for sudo and dmidecode; confirm that the command text it tests is byte-equal to C/new-test-kernel/manual-run/run.sh). For C8 read run.sh. For C12 do not run the sandbox (another agent does); verify the code path. For C15 and C16 recompute.\n' +
    '2. Say for each claim whether it is true, false, or stated too strongly, and what the user would be misled about. Also say what is MISSING from the draft: a consequence of the edit that the user must know and that no claim covers.\n' +
    '3. Read the four memory notes MEM/crb-go-sh-remove-boot-id-todo.md, MEM/crb-whole-chip-rerun-7200-2026-11-17.md, MEM/crb-whole-chip-code-data-list-2026-11-21.md and MEM/MEMORY.md. Try to refute each sentence that speaks about go.sh, local.sha, run.sh, the copy on CRB, build_facts.py, make_list.py or the edit of 2026-11-24. Check that the notes do not contradict each other and that every file, function and line number they name exists.' },
]

phase('Verify')
const results = await parallel(SCOPES.map(s => () =>
  agent(HEAD.replace(/@L@/g, s.label) + s.scope, { label: 'verify:' + s.label, phase: 'Verify', schema: SCHEMA })
    .then(r => ({ label: s.label, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const missing = SCOPES.map(s => s.label).filter(l => !ok.some(r => r.label === l))
log('agents returned: ' + ok.length + ' of ' + SCOPES.length + (missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''))
log('findings: ' + ok.reduce((n, r) => n + r.result.findings.length, 0) + ', claims checked ok: ' + ok.reduce((n, r) => n + r.result.checked_ok.length, 0))
return { missing, results: ok }
