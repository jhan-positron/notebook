export const meta = {
  name: 'go-sh-edit-impact-sweep',
  description: 'Read-only sweep: find every statement in the list, the companions, their inputs and the tools that the edit of go.sh line 20 makes false or stale',
  phases: [{ title: 'Sweep', detail: '8 read-only agents, each with a different search angle' }],
}

const G = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771/scratchpad/goedit'
const BRIEF = G + '/BRIEF-sweep.md'
const SP = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771/scratchpad'
const MEM = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory'

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string', description: 'absolute path of the file that holds the statement' },
          line: { type: 'integer' },
          quote: { type: 'string', description: 'exact quote, at most 300 characters' },
          input_file: { type: 'string', description: 'for a generated companion: the input file (and line) that holds the same sentence; empty when the file is itself the input' },
          category: { type: 'string', enum: ['false-now', 'needs-note', 'tool-break', 'other'] },
          reason: { type: 'string' },
          proposed: { type: 'string', description: 'proposed replacement text, or empty' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'quote', 'category', 'reason', 'confidence'],
      },
    },
    files_read_in_full: { type: 'array', items: { type: 'string' } },
    files_searched_only: { type: 'array', items: { type: 'string' } },
    not_checked: { type: 'string', description: 'what inside the scope was not checked, and why' },
  },
  required: ['findings', 'files_read_in_full', 'files_searched_only', 'not_checked'],
}

const HEAD = 'First read the brief ' + BRIEF + ' in full. It defines the folders C, S, T, LIST, G, the edit, the task, the report format and the hard rules (read-only, no ssh, no generators, no benchmark scripts, no cd). Your label is "@L@" (your scratch folder is ' + G + '/agents/@L@/). Then work on this scope:\n\n'

const SCOPES = [
  { label: 'id-keyword', scope:
    'Angle: KEYWORD sweep for statements about the identity and the checksum of go.sh.\n' +
    'Search ALL of these: every companion .md that LIST links to (take the link targets from LIST), LIST itself, every file in T/ann and T/types, T/BRIEF.md, and the text constants of T/make_list.py and T/data_companions.py.\n' +
    'Search terms (use grep -n -i, and think of more): local.sha, "sha256sum -c", 75bc50b0, "script that ran", "the script that", unchanged, "not changed", identical, "same content", "same text", "equal to the list", "check 20", "still has", "copy on CRB", "copied", "local copy", "local go.sh", "run files", "five files", "5 files", "6 local run files", "file time" near go.sh.\n' +
    'For every hit read the whole sentence and its neighbours and decide whether the edit makes it false, stale or misleading.' },
  { label: 'msg-keyword', scope:
    'Angle: KEYWORD sweep for statements about the message of go.sh line 20 and about the meaning of the marker file /tmp/positron-perf.RUNNING.\n' +
    'Search ALL of these: every companion .md that LIST links to (take the link targets from LIST), LIST itself, every file in T/ann and T/types, T/BRIEF.md, and the text constants of T/make_list.py and T/data_companions.py.\n' +
    'Search terms (use grep -n -i, and think of more): RUNNING, marker, "who creates", "do not say", "does not say", "stands for", Jeremy, "another user", "other user", "FAILED", "line 20", "fail(", "`fail`", "stops the run with", "message".\n' +
    'Pay special attention to sentences that speak about "the scripts" as a group (for example that the scripts do not say who creates the marker file or what it means): after the edit the message of go.sh says "Jeremy or someone else is using CRB".\n' +
    'For every hit read the whole sentence and its neighbours and decide whether the edit makes it false, stale or misleading.' },
  { label: 'read-go', scope:
    'Angle: FULL READ, sentence by sentence, of the documents about go.sh itself and about its log.\n' +
    'Read in full: S/go.sh (new text), G/backup/tmp/agent-scratch/w120-7200-2026-11-17/go.sh (old text), S/go.sh.md, T/ann/go.overview.json, T/ann/go.c01.json, the companion of the go.sh log (the file go-T72-20261117T221209Z.log.md under C/results) with its inputs T/ann/go_log.overview.json and T/ann/go_log.c01.json.\n' +
    'For EVERY sentence ask: does its truth depend on the text of line 20, on the checksum of go.sh, on the file time of go.sh, or on the claim that the local go.sh is the script that ran on 2026-11-17? Report each one that the edit touches. Also report every place that quotes line 20 or its message.' },
  { label: 'read-S', scope:
    'Angle: FULL READ of the other companions in the run folder S.\n' +
    'Read in full: S/local.sha.md and the type text that generates it (find it in T/types and T/data_companions.py), S/go2.sh.md, S/go2.sha.md, S/ra.sh.md, S/like.spec.md, S/cfwd.spec.md, S/crev.spec.md, S/baselines-and-rules.txt.md, S/FACTS.md.md, S/facts.json.md, and the inputs of the generated ones (T/ann/go2*.json, T/ann/ra*.json, the spec keys, see T/manifest.json).\n' +
    'For the large Python companions (S/build_facts.py.md, S/facts_data.py.md, S/facts_text.py.md, S/facts_text4.py.md, S/make_report.py.md, S/test_make_report.py.md, S/stat_bwx.py.md, S/stat_k120.py.md) read every passage that mentions go.sh, local.sha, go2.sha, sha256, "check 20", "check 26", "sha-local", the marker file or "RUNNING" (use grep -n to find them, then read the passages in full), and their inputs in T/ann.\n' +
    'Also read S/FACTS.md lines that mention go.sh, local.sha or the marker file: FACTS.md is a built record of 2026-11-17 and is not rebuilt, so report where a reader could now be misled (category needs-note) and say which companion should carry the note.' },
  { label: 'read-list', scope:
    'Angle: FULL READ of the list and of the tool texts.\n' +
    'Read in full: LIST (about 1024 lines), C/new-test-kernel/whole-chip-rerun-7200.html.md, T/BRIEF.md, every file in T/types, and every text constant of T/make_list.py (the strings that it writes into LIST) and of T/data_companions.py.\n' +
    'For EVERY sentence ask whether the edit of go.sh line 20 makes it false, stale or misleading: statements about go.sh, about local.sha, about the copy to CRB, about which text ran, about the marker file, about what the scripts say or do not say, about sha256 checks, about the start command.\n' +
    'Also check the list for statements about "two texts" of other files (bandwidth.c) and report whether the list must now say the same kind of thing about go.sh, and where (name the section and the function of make_list.py that writes it).' },
  { label: 'read-rest', scope:
    'Angle: the companions OUTSIDE the run folder S and outside C/new-test-kernel.\n' +
    'Take from LIST every linked companion .md that lies in another folder (C/tmp/agent-scratch/w120-2026-11-15, C/tmp/agent-scratch/kernels-2026-11-13, C/tmp/agent-scratch/bwx12-2026-11-15, C/bench, C/results/..., and any other). For each one: grep -n -i for go.sh, local.sha, RUNNING, marker, "who creates", "do not say", sha256, "script that ran", then read every hit passage in full. Read rx.sh.md, run_kernels.sh.md and build12.sh.md in full (they describe marker tests of other scripts and may compare them with go.sh).\n' +
    'Also search their inputs in T/ann (all keys except go, go_log, go2, go2_log, go2_sha, ra and the spec keys, which other agents read) and T/prior/*.json.\n' +
    'Report every sentence that the edit makes false, stale or misleading, and every sentence that groups go.sh with other scripts in a claim about the marker file.' },
  { label: 'tooling', scope:
    'Angle: CODE analysis of the generators, checks and tests. Read code, do not run the generators.\n' +
    'Read: T/make_list.py, T/companion_tool.py, T/data_companions.py, T/manifest.json, and in S: build_facts.py, facts_data.py, facts_text.py, facts_text4.py, make_report.py, test_make_report.py, stat_bwx.py, stat_k120.py. Also list any other script under C that opens S/go.sh or S/local.sha (grep -rIn "go.sh\\|local.sha" over C/tmp/agent-scratch/code-data-list-2026-11-21 and S, *.py and *.sh only).\n' +
    'Find every code path that reads the content, a line, the sha256 or the file time of S/go.sh, or that reads S/local.sha. For each one say exactly what happens now: passes unchanged, fails (quote the message and say whether files are written before the failure), or writes different text (which file, which sentence).\n' +
    'Known so far: build_facts.py check "sha-local" (about lines 772 to 780) compares the local run files with local.sha and go2.sha, and at the end build_facts.py writes FACTS.md and facts.json BEFORE it exits with status 1 on a failed check. Confirm or correct this, and find all other cases (for example make_list.py need(...) anchors on go.sh lines 21, 22, 23; build_facts.py check 26 that reads the text of go.sh; companion_tool.py checks that compare the left column with the source or that pin a sha256 or a line count; any check on annotation text such as quoted source text inside T/ann/go.c01.json).\n' +
    'Also say what the smallest safe way is to keep the record checkable that the run of 2026-11-17 used the old text (the list already does this for bandwidth.c in make_list.py function check_two_texts: it reverses a later edit and compares the sha256 with a record). Do not write the code into the tool files; describe it.' },
  { label: 'critic', scope:
    'Angle: COMPLETENESS critic. Other agents sweep the companions, the list, the annotation inputs and the generator code. You look for everything ELSE that depends on go.sh.\n' +
    'Check at least: (1) the memory notes ' + MEM + '/crb-whole-chip-rerun-7200-2026-11-17.md, ' + MEM + '/crb-go-sh-remove-boot-id-todo.md, ' + MEM + '/crb-whole-chip-code-data-list-2026-11-21.md and ' + MEM + '/MEMORY.md: which sentences are now false or need an addition (for example "Do not edit go.sh itself (it must equal local.sha)"). (2) The start command that the user was given and its local test: ' + SP + '/startcmd/direct/cmd.txt and ' + SP + '/startcmd/direct/test.py (the command runs on CRB, where go.sh and local.sha are still the old files; the test copies S/go.sh and S/local.sha into a fake home): say what the test would do now and what the command would do on CRB in three cases: CRB copy unchanged; only the new go.sh copied to CRB; new go.sh and a new checksum list copied. Do not run the test. (3) The static records S/FACTS.md, S/facts.json and C/new-test-kernel/whole-chip-rerun-7200.html: grep for go.sh, local.sha, sha256, RUNNING and report sentences that a reader could now misread. (4) S/go2.sh: it holds the same old message in lines 16 and 25; say whether any document states that go.sh and go2.sh have the same checks or the same messages. (5) The truth of the NEW message itself: it says "Jeremy or someone else is using CRB". Collect what the local records say about who creates /tmp/positron-perf.RUNNING and what it means (grep the folder C for "positron-perf.RUNNING" in .md, .txt and .py files, and S/facts_text.py near line 642) and say whether the message agrees with the records. (6) Any other file under C/tmp/agent-scratch or C/new-test-kernel that quotes go.sh line 20 or names the sha256 75bc50b0 (grep -rIl), for example review or check outputs: say for each whether it is a dated record (leave it) or a living document (fix it).\n' +
    'Report in the same format. Use category "other" for consequences that are not a sentence in a file, and put the file that should carry the fix in "file".' },
]

phase('Sweep')
const results = await parallel(SCOPES.map(s => () =>
  agent(HEAD.replace(/@L@/g, s.label) + s.scope, { label: 'sweep:' + s.label, phase: 'Sweep', schema: SCHEMA })
    .then(r => ({ label: s.label, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
const missing = SCOPES.map(s => s.label).filter(l => !ok.some(r => r.label === l))
log('agents returned: ' + ok.length + ' of ' + SCOPES.length + (missing.length ? ' (missing: ' + missing.join(', ') + ')' : ''))
const total = ok.reduce((n, r) => n + r.result.findings.length, 0)
log('findings in total (before dedup): ' + total)
return { missing, results: ok }
