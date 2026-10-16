export const meta = {
  name: 'pr-diagram-pages-qa',
  description: 'Check the four built walk-through pages (prose flow, plain English, every PR-head citation) and fix the specs in place',
  phases: [
    { title: 'Check', detail: 'reader lens and citation lens per page' },
    { title: 'Fix', detail: 'one fixer per page edits the spec JSON' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/05daa18d-ed3c-4a33-8e24-e3eab00ce2ea/scratchpad'
const PRS = [
  { ordinal: 1, number: 4868, branch: 'jhan-vnnik-1-layout', base: 'main', head: '82d05e94be', title: 'Add the VNNI K layout and its readers' },
  { ordinal: 2, number: 4887, branch: 'jhan-vnnik-2-amx', base: 'jhan-vnnik-1-layout', head: '0ee8671d35', title: 'Use VNNI K layout in AMX attention' },
  { ordinal: 3, number: 4898, branch: 'jhan-vnnik-3-shared-save', base: 'jhan-vnnik-2-amx', head: 'dfafd13dce', title: 'Save K in 16-token blocks, shared with idle worker threads' },
  { ordinal: 4, number: 4901, branch: 'jhan-vnnik-4-tail-block', base: 'jhan-vnnik-3-shared-save', head: '175b1837b9', title: 'Keep short K writes row-major; enable VNNI K in the deb preset' },
]

const CTX = (p) => `
CONTEXT. jhan will walk reviewer Ben through the four PRs that split tron PR 4424 (VNNI K: the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save). One HTML page per PR copies the base diagrams of the three PR 4424 source pages and adds prose: a Short version, Words used here, "What this PR adds", a walk-through order, a "why" paragraph plus four status boxes per diagram (In this PR / Already there / Lands in a later PR / Not in the stack in this form), a list of the source pages' code-change sections that land in the PR, and gaps.

The stack: PR-1 #4868 jhan-vnnik-1-layout (base main, head 82d05e94be); PR-2 #4887 jhan-vnnik-2-amx (base PR-1, head 0ee8671d35); PR-3 #4898 jhan-vnnik-3-shared-save (base PR-2, head dfafd13dce); PR-4 #4901 jhan-vnnik-4-tail-block (base PR-3, head 175b1837b9).

This page: PR-${p.ordinal} #${p.number} "${p.title}", branch ${p.branch}, base ${p.base}, head ${p.head}.
  Rendered page as text (the copied figures are elided as [FIGURE: ...]): ${S}/out/diagrams-PR${p.ordinal}-${p.number}.txt
  Built HTML (do not cat; grep if you need a detail): ${S}/out/diagrams-PR${p.ordinal}-${p.number}.html
  The spec the page is built from: ${S}/spec/pr${p.ordinal}-${p.number}.json  (sections: pr, short_version[], words[{term,definition}], what_lands[{concept,kind,where,diagrams,note}], diagrams[{id,role,why,in_this_pr[],already_there[{what,from}],not_yet[{what,lands_in}],never[],evidence[]}], change_sections[{id,source,status,note}], walkthrough[{diagram,say}], gaps[])
  Words entries the page prose never uses (mechanical check): ${S}/out/unused-words-${p.number}.txt
  PR body: ${S}/pr/body-${p.number}.md; PR diff: ${S}/pr/diff-${p.number}.patch; the other diffs: ${S}/pr/diff-4868.patch, diff-4887.patch, diff-4898.patch, diff-4901.patch
  Source-page extracts: ${S}/blocks/diagrams.txt (the 16 diagrams: title, intro, caption, boxes), ${S}/src/changes.txt (the 29 change sections)
  Code at any PR head: git -C /home/jhan/workspace/tron show origin/<branch>:<path> | grep -n ...   (read-only; never modify /home/jhan/workspace/tron or anything under /home/jhan/workspace/ai-runs)

Prose rules (plain-english skill in your CLAUDE.md): define every code name, acronym and metric at first use or in Words; one claim per sentence; short sentences; no idioms; numbers carry units; "VNNI-packed" for the storage sense; "PR" not "pull request"; "prompt 1024" never "ctx 1024"; the Short version has at most three sentences a newcomer can follow.
`

const FINDINGS = {
  type: 'object',
  required: ['lens', 'summary', 'corrections'],
  properties: {
    lens: { type: 'string' },
    summary: { type: 'string', description: 'one paragraph: what was checked, how many items, overall state' },
    corrections: { type: 'array', items: { type: 'object', required: ['where', 'problem', 'fix', 'evidence', 'severity'], properties: { where: { type: 'string', description: 'spec path, e.g. diagrams[k_vnni-b2].in_this_pr[1] or words[term=AMX] or walkthrough[3].say' }, problem: { type: 'string' }, fix: { type: 'string', description: 'the exact replacement text, or "delete"' }, evidence: { type: 'string' }, severity: { type: 'string', enum: ['must', 'should', 'nit'] } } } },
  },
}

const FIXED = {
  type: 'object',
  required: ['applied', 'rejected', 'spec_valid'],
  properties: {
    applied: { type: 'array', items: { type: 'string' } },
    rejected: { type: 'array', items: { type: 'string' } },
    spec_valid: { type: 'boolean', description: 'true when the spec file still parses and keeps 16 diagrams, 29 change sections, 2-3 short_version sentences' },
  },
}

const readerPrompt = (p) => `${CTX(p)}

LENS: reader. Read ${S}/out/diagrams-PR${p.ordinal}-${p.number}.txt from top to bottom as Ben would, in one pass. Then check, and report every problem as a correction addressed to the spec:
1. Flow: does the Short version say what the PR does, which data models and algorithms the page introduces, and which diagrams carry them, in at most three sentences a newcomer can follow? Does the walk-through visit the core diagrams in an order that introduces a data model before the algorithm that uses it, and does every "say" step name boxes that exist on that diagram (check against ${S}/blocks/diagrams.txt) and PR-head lines?
2. Consistency: do the status boxes of different diagrams agree with each other and with the change-section table (for example, the same element must not land in PR-3 under one diagram and in PR-4 under another)? Does "What this PR adds" agree with the status boxes?
3. Plain English on every sentence of the new prose (not the copied figures): undefined code names, acronyms or metrics at first use; two claims in one sentence; idioms; numbers without units; "ctx"; "pull request"; storage-sense "packed" without "VNNI-".
4. Words: every entry in ${S}/out/unused-words-${p.number}.txt is a candidate for deletion (confirm it is unused, or point at the use the mechanical check missed); every definition must be one or two sentences; terms that are only PR 4424 diagram vocabulary and never appear in this page's prose go.
5. Rendering oddities visible in the text: a code name split by the <code> wrapper, a diagram reference like "k_vnni-b1" in running prose where "K_VNNI-B1" reads better, a sentence that repeats the same fact as the one before it.
Report corrections with the exact replacement text. Severity must = wrong or misleading; should = rule violation; nit = taste.`

const citePrompt = (p) => `${CTX(p)}

LENS: citations. Extract EVERY file:line citation in the new prose of ${S}/out/diagrams-PR${p.ordinal}-${p.number}.txt that cites the head of THIS PR (everything outside the [FIGURE] placeholders; the page says the prose cites head ${p.head}; a citation that names another PR's head or PR 4424 head 9d5c7a389b is checked against that head instead). For each one, run git -C /home/jhan/workspace/tron show origin/${p.branch}:<file> | sed -n '<start>,<end>p' (or the branch the citation names) and confirm the cited lines hold the thing the sentence claims (the declaration, the call, the comment, the test case). Also confirm each "from main" claim by checking the name exists in origin/main (git -C /home/jhan/workspace/tron show origin/main:<file> | grep -n <name>), and each "lands in PR-n" claim by grepping the added lines of ${S}/pr/diff-<that number>.patch. Report every citation that is off by any amount, points at the wrong thing, or cannot be verified, with the correct lines as the fix. Count what you checked in the summary (citations checked, wrong, unverifiable). Be exhaustive: check all of them, not a sample.`

const fixPrompt = (p, findings) => `${CTX(p)}

You are the fixer for this page. Two checkers reported corrections (below). Apply every correction whose evidence you can confirm (open the cited lines or files when in doubt) by editing the spec file ${S}/spec/pr${p.ordinal}-${p.number}.json IN PLACE with a small Python script or the Edit tool. Reject a correction only with evidence that refutes it. Keep the schema exactly: pr fields unchanged; short_version 2-3 strings; words[{term,definition}] sorted does not matter; what_lands kind in {data model, algorithm, protocol, policy, build and test}; 16 diagrams with the same ids, role in {core, context, not involved}, order core then context then not involved; 29 change_sections with status in {full, partial, none}; walkthrough[{diagram,say}] where diagram is a diagram id or "none"; gaps[]. After editing, run python3 -I -c "import json; d=json.load(open('${S}/spec/pr${p.ordinal}-${p.number}.json')); assert len(d['diagrams'])==16 and len(d['change_sections'])==29 and 2<=len(d['short_version'])<=3; print('ok')" and report the result in spec_valid.

CORRECTIONS:
${JSON.stringify(findings, null, 1)}

Return the lists of applied and rejected corrections through the StructuredOutput tool.`

phase('Check')
const out = await pipeline(
  PRS,
  async (p) => {
    const f = await parallel([
      () => agent(readerPrompt(p), { label: `reader:PR-${p.ordinal}`, phase: 'Check', schema: FINDINGS }),
      () => agent(citePrompt(p), { label: `cite:PR-${p.ordinal}`, phase: 'Check', schema: FINDINGS }),
    ])
    return f.filter(Boolean)
  },
  async (findings, p) => {
    const n = findings.reduce((a, f) => a + f.corrections.length, 0)
    log(`PR-${p.ordinal}: ${findings.length} checkers, ${n} corrections`)
    const fixed = n ? await agent(fixPrompt(p, findings), { label: `fix:PR-${p.ordinal}`, phase: 'Fix', schema: FIXED }) : { applied: [], rejected: [], spec_valid: true }
    return { pr: p, findings, fixed }
  }
)
return out.filter(Boolean)