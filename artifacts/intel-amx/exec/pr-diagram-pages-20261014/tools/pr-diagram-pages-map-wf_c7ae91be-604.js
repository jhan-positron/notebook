export const meta = {
  name: 'pr-diagram-pages-map',
  description: 'Map the PR 4424 base diagrams and code-change sections onto the four split PRs, verify adversarially, revise',
  phases: [
    { title: 'Map', detail: 'one mapper per PR writes the page spec' },
    { title: 'Verify', detail: 'three lenses per spec try to refute it' },
    { title: 'Revise', detail: 'one reviser per PR folds the grounded corrections in' },
  ],
}

const S = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/05daa18d-ed3c-4a33-8e24-e3eab00ce2ea/scratchpad'
const PRS = [
  { ordinal: 1, number: 4868, branch: 'jhan-vnnik-1-layout', base: 'main', head: '82d05e94be', title: 'Add the VNNI K layout and its readers' },
  { ordinal: 2, number: 4887, branch: 'jhan-vnnik-2-amx', base: 'jhan-vnnik-1-layout', head: '0ee8671d35', title: 'Use VNNI K layout in AMX attention' },
  { ordinal: 3, number: 4898, branch: 'jhan-vnnik-3-shared-save', base: 'jhan-vnnik-2-amx', head: 'dfafd13dce', title: 'Save K in 16-token blocks, shared with idle worker threads' },
  { ordinal: 4, number: 4901, branch: 'jhan-vnnik-4-tail-block', base: 'jhan-vnnik-3-shared-save', head: '175b1837b9', title: 'Keep short K writes row-major; enable VNNI K in the deb preset' },
]
const DIAGRAM_IDS = ['k_vnni-b1','k_vnni-b1a','k_vnni-b2','k_vnni-b3','k_vnni-b4','k_vnni-b5','kv_cache-b1','kv_cache-b2','kv_cache-b3','kv_cache-b4','kv_cache-b5','model-b1','model-b2','model-b3','model-b4','model-b5']
const CHANGE_IDS = ['C0','C1','C2','C3','C4','C5','C6','C7','C8','C9','C10','K0','K1','K2','K3','K4','K5','K6','K7','K8','K9','M0','M1','M2','M3','M4','M5','M6','M7']

const CTX = `
CONTEXT (read this first; all paths are absolute).

jhan will walk reviewer Ben through the four PRs that split tron PR 4424 (VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save). jhan will use the base diagrams of three existing pages (one per source file of PR 4424) to introduce the data models and the main algorithms. We are building one HTML page per split PR that copies the base diagrams that matter for that PR and says, for each diagram, what of it lands in that PR, what was already there from an earlier PR of the stack, and what lands only in a later PR. You produce the page's content as structured data; a Python builder copies the SVG diagrams verbatim, so never reproduce SVG.

The stack (each PR's base is the previous PR's branch):
  PR-1 #4868 jhan-vnnik-1-layout (base main, head 82d05e94be): the typed VNNI K layout (owner, views, index map), the per-row store, the AVX-512 reader (kernels/k_vnni.hpp qk_group), the FPGA staging gather, tests, the CI lane. No AMX instruction.
  PR-2 #4887 jhan-vnnik-2-amx (base PR-1, head 0ee8671d35): the AMX kernel qk_vnni_128x4 that reads the VNNI plane as its B operand; removes PR-1's temporary dense-path gate.
  PR-3 #4898 jhan-vnnik-3-shared-save (base PR-2, head dfafd13dce): the 16-token block store (store_block, transpose_16x16_epi32, page::set_k_block), save_k work units shared with the idle main helpers (window protocol, worker_ix / n_workers, Note [Shared block save], join watchdog), the Haskell call sites.
  PR-4 #4901 jhan-vnnik-4-tail-block (base PR-3, head 175b1837b9): the saved-row and converted-block bits, the row-major tail block, the forward-end conversion (pending list), the hardware-attention policy, the dense gate and the dotter for tail rows, the deb preset.

Inputs:
  ${S}/blocks/diagrams.txt   : the 16 base diagrams of the source pages as text: id, title, intro, caption, and the list of boxes with the code name and the line that defines each (lines cite PR 4424 head 9d5c7a389b).
  ${S}/src/changes.txt       : the 29 code-change sections of the source pages (C0-C10 kv_cache.hpp, K0-K9 tensor/k_vnni.hpp, M0-M7 model.hpp): heading, lead text, cross-reference row (which base diagram each updates).
  ${S}/blocks/hits.txt       : mechanical hit matrix: for each diagram box identifier, how many times it occurs in origin/main and in the ADDED lines of each PR's diff. Use it as a first signal, then confirm in the diffs.
  ${S}/src/kv_cache.txt, ${S}/src/k_vnni.txt, ${S}/src/model.txt : the full text of the three source pages (SVGs elided), including their Short version and Words used here lists. Read the Words lists when you write definitions.
  ${S}/pr/body-<number>.md, ${S}/pr/diff-<number>.patch, ${S}/pr/files-<number>.txt, ${S}/pr/commits-<number>.txt : the live PR body (written under the PR-description skill; its Words used here list is the vocabulary jhan uses), the PR diff against its base, the changed files, the commits.
  ${S}/pr/split-plan-3.1.md  : the split plan's description of the four PRs and the U2.1 note on the masked partial-block path that PR-3 carries and PR-4 deletes.
  Source code at any PR head: git -C /home/jhan/workspace/tron show origin/<branch>:<path>  (for example: git -C /home/jhan/workspace/tron show origin/jhan-vnnik-1-layout:h/tron/tensor/k_vnni.hpp | grep -n store_row). Do not modify anything under /home/jhan/workspace/tron or /home/jhan/workspace/ai-runs (the PR-4 worktree holds uncommitted edits; never touch it). Read-only git commands only.
  Source pages themselves (read only if you need more than the text extracts): /home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424/diagramming-code-changes-{kv_cache,k_vnni,model}.hpp.html (1 MB each; grep, do not cat).

Rules for every sentence you write (they go on the page unchanged):
  - Plain English per the plain-english skill rules in your CLAUDE.md: one claim per sentence, short sentences, no idioms, define every code name, acronym and metric at first use on the page or list it in words; numbers carry units.
  - Use the PR-description vocabulary: "VNNI-packed" for the storage sense of packed; "query pack" keeps "pack"; "PR", not "pull request"; "prompt 1024", never "ctx".
  - Cite the PR head as file:line (lines at the PR head, found with git show ... | grep -n), not PR 4424 lines, whenever you cite code of a split PR. When you quote a diagram's line, say it is a PR 4424 line.
  - Ground every "in this PR" / "already there" / "lands later" claim in the diff of the PR named (added lines, removed lines) or in the file at that PR head. Never infer from the split plan alone; the plan is a guide to where to look.
  - Say "Insufficient data" rather than guess.
`

const SPEC = {
  type: 'object',
  required: ['pr', 'short_version', 'words', 'what_lands', 'diagrams', 'change_sections', 'walkthrough', 'gaps'],
  properties: {
    pr: { type: 'object', required: ['number', 'ordinal', 'title', 'branch', 'base', 'head', 'files', 'added', 'removed'], properties: { number: { type: 'integer' }, ordinal: { type: 'integer' }, title: { type: 'string' }, branch: { type: 'string' }, base: { type: 'string' }, head: { type: 'string' }, files: { type: 'integer' }, added: { type: 'integer' }, removed: { type: 'integer' } } },
    short_version: { type: 'array', minItems: 2, maxItems: 3, items: { type: 'string' }, description: 'At most three sentences a newcomer can follow: what the PR does, which data models and algorithms the page introduces, and which diagrams carry them.' },
    words: { type: 'array', items: { type: 'object', required: ['term', 'definition'], properties: { term: { type: 'string' }, definition: { type: 'string' } } }, description: 'Only the terms this page uses (in the short version, the notes, the walkthrough), each defined in one or two sentences, reusing the source pages and the PR body definitions. Alphabetical. Include the project terms the CLAUDE.md of intel-AMX lists when they appear.' },
    what_lands: { type: 'array', minItems: 3, items: { type: 'object', required: ['concept', 'kind', 'where', 'diagrams', 'note'], properties: { concept: { type: 'string' }, kind: { type: 'string', enum: ['data model', 'algorithm', 'protocol', 'policy', 'build and test'] }, where: { type: 'string', description: 'file:line ranges at the PR head' }, diagrams: { type: 'array', items: { type: 'string' } }, note: { type: 'string', description: 'one or two sentences: what it is and what it is for' } } }, description: 'The data models, algorithms, protocols and policies this PR adds, in the order to present them.' },
    diagrams: { type: 'array', minItems: 16, maxItems: 16, items: { type: 'object', required: ['id', 'role', 'why', 'in_this_pr', 'already_there', 'not_yet', 'never', 'evidence'], properties: { id: { type: 'string' }, role: { type: 'string', enum: ['core', 'context', 'not involved'] }, why: { type: 'string', description: 'one or two sentences: why this diagram is (or is not) part of the walk-through of this PR' }, in_this_pr: { type: 'array', items: { type: 'string' }, description: 'elements of the diagram (boxes, arrows, steps) that this PR adds or changes, each with a PR-head file:line' }, already_there: { type: 'array', items: { type: 'object', required: ['what', 'from'], properties: { what: { type: 'string' }, from: { type: 'string', description: 'main, or PR-n (#number)' } } } }, not_yet: { type: 'array', items: { type: 'object', required: ['what', 'lands_in'], properties: { what: { type: 'string' }, lands_in: { type: 'string', description: 'PR-n (#number)' } } } }, never: { type: 'array', items: { type: 'string' }, description: 'elements the diagram draws that no PR of the stack adds in that form (for example a name that differs at the PR heads); usually empty' }, evidence: { type: 'array', items: { type: 'string' }, description: 'diff hunks or PR-head file:line that ground the classification' } } }, description: 'All 16 base diagrams, in the order the page should show them: core first, then context, then not involved.' },
    change_sections: { type: 'array', minItems: 29, maxItems: 29, items: { type: 'object', required: ['id', 'source', 'status', 'note'], properties: { id: { type: 'string' }, source: { type: 'string', enum: ['kv_cache', 'k_vnni', 'model'] }, status: { type: 'string', enum: ['full', 'partial', 'none'] }, note: { type: 'string', description: 'one sentence: what of this change section lands in this PR, or which PR it lands in' } } }, description: 'All 29 code-change sections of the source pages (C0-C10, K0-K9, M0-M7).' },
    walkthrough: { type: 'array', minItems: 3, items: { type: 'object', required: ['diagram', 'say'], properties: { diagram: { type: 'string', description: 'a diagram id, or "none" for a step without a diagram' }, say: { type: 'string', description: 'two to four sentences jhan can say at this step, naming the boxes of the diagram to point at and the PR-head lines to open' } } }, description: 'The order of the talk with Ben.' },
    gaps: { type: 'array', items: { type: 'string' }, description: 'what this PR contains that no base diagram draws (for example the AMX kernel itself), one sentence each' },
  },
}

const REVIEW = {
  type: 'object',
  required: ['lens', 'verdict', 'corrections'],
  properties: {
    lens: { type: 'string' },
    verdict: { type: 'string', description: 'one paragraph: what you checked, how, and the overall state' },
    corrections: { type: 'array', items: { type: 'object', required: ['where', 'problem', 'fix', 'evidence', 'severity'], properties: { where: { type: 'string', description: 'JSON path in the spec, e.g. diagrams[kv_cache-b1].not_yet[0] or short_version[1]' }, problem: { type: 'string' }, fix: { type: 'string', description: 'the exact replacement text or the exact change' }, evidence: { type: 'string', description: 'the diff hunk, the PR-head file:line, or the source-page passage that proves it' }, severity: { type: 'string', enum: ['must', 'should', 'nit'] } } } },
  },
}

const REVISED = {
  type: 'object',
  required: ['spec', 'applied', 'rejected'],
  properties: {
    spec: SPEC,
    applied: { type: 'array', items: { type: 'string' }, description: 'one line per correction applied: where + what' },
    rejected: { type: 'array', items: { type: 'string' }, description: 'one line per correction not applied, with the evidence that refutes it' },
  },
}

const LENSES = [
  { key: 'diff-grounding', prompt: (p) => `LENS: diff grounding. For EVERY diagram entry and EVERY change_sections entry of the spec, try to refute the classification (role, in_this_pr, already_there, not_yet, never, status) against the four PR diffs (${S}/pr/diff-4868.patch, diff-4887.patch, diff-4898.patch, diff-4901.patch) and the files at the PR heads (git -C /home/jhan/workspace/tron show origin/<branch>:<path>). Check every file:line citation the spec makes at the PR head ${p.head} (origin/${p.branch}): the line must hold the thing claimed. A claim that something lands in PR-n must be visible in PR-n's added lines; a claim that something is already there must be visible at the base of this PR; a claim that something lands later must be absent at this PR's head and present in the later PR's added lines. Report every wrong or unprovable claim as a correction with the proving hunk or line. Default to reporting when uncertain.` },
  { key: 'completeness', prompt: (p) => `LENS: completeness and ordering. (1) Is any base diagram marked "not involved" although this PR adds or changes something the diagram draws (use ${S}/blocks/hits.txt and ${S}/blocks/diagrams.txt, and the PR diff)? (2) Is any diagram marked core or context although nothing of it is in this PR's diff? (3) Does what_lands name every data model, algorithm, protocol or policy this PR adds (compare with the PR body ${S}/pr/body-${p.number}.md, sections "How to review" and "Words used here", and with the change sections of ${S}/src/changes.txt that the spec marks full or partial)? (4) Is every change section (C0-C10, K0-K9, M0-M7) present exactly once with a status that matches the diff? (5) Does the walkthrough visit every core diagram, in an order that introduces a data model before the algorithm that uses it? (6) Are the gaps real gaps (things the PR adds that no diagram draws)? Report each omission or wrong inclusion as a correction with evidence.` },
  { key: 'prose-and-facts', prompt: (p) => `LENS: prose and facts. Check every sentence of short_version, words, what_lands[*].note, diagrams[*].why, walkthrough[*].say and gaps against the plain-english rules of your CLAUDE.md (define every code name, acronym and metric at first use or in words; one claim per sentence; short sentences; no idioms; numbers with units; "VNNI-packed" for the storage sense; "PR" not "pull request"; "prompt N" never "ctx N"). Check every number and every name against the PR body ${S}/pr/body-${p.number}.md and the source pages (${S}/src/*.txt). Check that every term in words is used on the page and that every code name, acronym and metric used on the page is in words or defined inline. Check that short_version has at most three sentences a newcomer can follow. Report each violation as a correction with the exact replacement text.` },
]

function mapPrompt(p) {
  return `${CTX}

YOUR TASK: write the page spec for PR-${p.ordinal} #${p.number} "${p.title}" (branch ${p.branch}, base ${p.base}, head ${p.head}).

Steps:
1. Read ${S}/pr/body-${p.number}.md, ${S}/pr/files-${p.number}.txt, ${S}/pr/commits-${p.number}.txt, ${S}/pr/split-plan-3.1.md, ${S}/blocks/diagrams.txt, ${S}/src/changes.txt, ${S}/blocks/hits.txt. Read the diff ${S}/pr/diff-${p.number}.patch in full (it is the ground truth for this PR). Skim the other three diffs for the names you need to place in earlier or later PRs.
2. For each of the 16 base diagrams (ids: ${DIAGRAM_IDS.join(', ')}), decide its role for this PR: core (the PR adds or changes a main element the diagram draws, and jhan should show it), context (the diagram helps to place this PR, but the PR changes little of it), or not involved. For every diagram, list in_this_pr (with PR-head file:line), already_there (from main or an earlier PR), not_yet (which later PR), never. Use the box list of the diagram as the checklist: every box must land in exactly one of the four lists or be unchanged main code (put unchanged main code in already_there with from: "main").
3. For each of the 29 change sections (${CHANGE_IDS.join(', ')}), set status full / partial / none for this PR with a one-sentence note. The cross-reference rows in changes.txt name the PR 4424 commits; the split PRs were rebuilt from the final tree, so decide by content (the identifiers and the hunks), not by commit hash.
4. Write what_lands: the data models, algorithms, protocols and policies this PR adds, in the order to present them, with PR-head file:line and the diagrams that draw them.
5. Write the walkthrough for the talk with Ben: the order of diagrams and what to say at each (two to four sentences, naming boxes and PR-head lines).
6. Write short_version (at most three sentences) and words (every term used on the page, defined; reuse the definitions of the PR body and the source pages). Write gaps.
7. Count files, added and removed lines of the PR from the diff (git-style: added = lines starting with + but not +++; removed likewise) and put them in pr.files, pr.added, pr.removed.

Return the spec through the StructuredOutput tool. Order the diagrams array core first, then context, then not involved. Every diagram id and change id must appear exactly once.`
}

phase('Map')
const results = await pipeline(
  PRS,
  (p) => agent(mapPrompt(p), { label: `map:PR-${p.ordinal}`, phase: 'Map', schema: SPEC }),
  async (spec, p) => {
    if (!spec) return null
    const specText = JSON.stringify(spec, null, 1)
    const reviews = await parallel(LENSES.map((L) => () =>
      agent(`${CTX}

You are an adversarial verifier of the page spec for PR-${p.ordinal} #${p.number} "${p.title}" (branch ${p.branch}, base ${p.base}, head ${p.head}). The spec was written by another agent. Your job is to REFUTE what is wrong, not to confirm. Default to reporting a correction when you cannot prove a claim.

${L.prompt(p)}

THE SPEC:
${specText}

Return your review through the StructuredOutput tool with lens = "${L.key}".`, { label: `verify:${L.key}:PR-${p.ordinal}`, phase: 'Verify', schema: REVIEW })
    ))
    return { spec, reviews: reviews.filter(Boolean) }
  },
  async (r, p) => {
    if (!r) return null
    const { spec, reviews } = r
    const nCorr = reviews.reduce((n, v) => n + v.corrections.length, 0)
    log(`PR-${p.ordinal}: ${reviews.length} reviews, ${nCorr} corrections`)
    const revised = await agent(`${CTX}

You revise the page spec for PR-${p.ordinal} #${p.number} "${p.title}" (branch ${p.branch}, base ${p.base}, head ${p.head}). Three verifiers reviewed it. Apply every correction whose evidence you can confirm in the diffs (${S}/pr/diff-*.patch) or at the PR heads (git show origin/<branch>:<path>). Reject a correction only when you can cite evidence that refutes it; list rejections with that evidence. Where two verifiers disagree, check the code and pick the grounded one. Keep the schema: 16 diagrams (each id once; core first, then context, then not involved), 29 change sections (each id once), short_version at most three sentences, words only for terms the page uses. Re-read every sentence you touch against the plain-English rules.

THE SPEC:
${JSON.stringify(spec, null, 1)}

THE REVIEWS:
${JSON.stringify(reviews, null, 1)}

Return the revised spec, the list of applied corrections and the list of rejected corrections through the StructuredOutput tool.`, { label: `revise:PR-${p.ordinal}`, phase: 'Revise', schema: REVISED })
    return { pr: p, spec_v1: spec, reviews, revised }
  }
)

const out = results.filter(Boolean)
log(`done: ${out.length} of 4 PR specs`)
return out