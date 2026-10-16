export const meta = {
  name: 'pr4901-explain-review',
  description: 'Review PR4901-explain.html from four lenses and refute the technical findings before fixes are applied',
  phases: [
    { title: 'Review', detail: 'plain English, technical accuracy, completeness, rendering' },
    { title: 'Refute', detail: 'one refuter per technical or completeness finding' },
  ],
}

const PAGE = '/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR4901-explain.html'
const W = '/home/jhan/workspace/ai-runs/tron-split-pr4'
const COMMON = [
  'CONTEXT. The page ' + PAGE + ' answers twelve code questions of jhan (the PR author) about PR #4901 of positron-ai/tron, plus a thirteenth request to abstract the prompts and suggest a skill. The questions are in /home/jhan/tmp/PR4901-questions.txt. The verified answers the page was written from are in /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-split-4424/e6f04fce-1790-4fc0-8220-267a113c6ec1/scratchpad/answers.md (one block per question, with the refuter verdicts under it; the ANSWER text is the corrected final answer).',
  'The worktree ' + W + ' is on branch jhan-vnnik-4-tail-block at head 175b1837b9. Its index holds change set A (ordered edits) and its working tree holds A plus B (proposals). THE WORKTREE IS READ-ONLY FOR YOU: never edit, add, reset, checkout, stash or commit in it. Line numbers on the page refer to the head commit 175b1837b9 BEFORE any edit unless the page says otherwise; read those with "git -C ' + W + ' show 175b1837b9:<path>" piped through sed -n, not from the working tree. The patches of the two change sets are /home/jhan/workspace/intel-AMX/exec/pr4-20261012/review-20261015/A-ordered.patch and B-proposals.patch.',
  'Environment quirk: a cd in a Bash call prints an ls listing through a hook; use absolute paths and never cd. Do not modify the page; report findings only. Your final text is data: return only the structured output.',
].join('\n')

const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['error', 'warning', 'nit'] },
      location: { type: 'string', description: 'section heading and an exact quote of the page text (copy it character for character so an Edit can find it)' },
      problem: { type: 'string' },
      fix: { type: 'string', description: 'the exact replacement text, or the action to take' },
      evidence: { type: 'string', description: 'file:line or command output that shows the problem' },
    }, required: ['severity', 'location', 'problem', 'fix'] } },
    summary: { type: 'string' },
  },
  required: ['findings', 'summary'],
}

const LENSES = [
  { key: 'plain-english', prompt: 'Lens: the plain-english skill in Check mode, applied to the page text (read the HTML, judge the prose, ignore the code blocks and the pre diagrams). Walk every rule: terms defined at first use (names from the code count; the Words used here list covers a term for the whole page), one claim per sentence, numbers with units and a meaning clause, citations after the sentence, a Short version of at most three sentences at the top, no idioms or metaphors, bullets for multi-point paragraphs, short sentences without semicolons. Report every violation with the exact phrase and a corrected phrase. Do not invent violations; report zero if there are none. Keep the corrections faithful to the page\'s facts.' },
  { key: 'technical', prompt: 'Lens: technical accuracy. For every factual claim on the page that names a file:line, a count, a measurement or a language rule, check it against answers.md (the final ANSWER text and the verdicts) and, where the claim is about the tree, against "git show 175b1837b9:<path>". Flag any claim that the answers do not support, any line number that does not point at what the page says, any number that differs from the measured one, and any statement that goes beyond what was measured (an inference stated as fact). Also check the two change-set descriptions against the patches: the counts of files, insertions and deletions, and which questions each set covers. Check that the quoted code blocks on the page match the tree or the patches. Sample at least 40 distinct claims across all twelve questions and list which you checked.' },
  { key: 'completeness', prompt: 'Lens: completeness and honesty against the asker\'s file /home/jhan/tmp/PR4901-questions.txt. For each of the thirteen items in that file, state whether the page answers the literal question or carries out the literal instruction, and whether anything was carried out that the file did not ask for without being labelled a proposal. Check the page\'s statements about the state of the branch and of the files against reality: "git -C ' + W + ' status --short", "git -C ' + W + ' diff --cached --stat" (should be change set A only) and "git -C ' + W + ' diff --stat" (should be B only); the existence and content of the patches and msg files in exec/pr4-20261012/review-20261015/; the skill file /home/jhan/.claude/skills/cpp-coding-guide/SKILL.md (does it hold the three bullets the page quotes and the new example block?); the draft skill /home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424/PR4901-explain/simplify-cpp-comments/SKILL.md (does it hold the eight rules the page summarizes, in that order, with the words the page uses?). Flag any claim the page makes that is not true of the actual state, and any instruction of the asker that was neither done nor explicitly deferred with a reason.' },
  { key: 'rendering', prompt: 'Lens: rendering. Parse the HTML with python3 -I and html.parser (or lxml if present): report unbalanced tags, unescaped < > & inside text, duplicate ids, and any pre line longer than 100 characters (horizontal scroll on phones). Confirm the page is a single light theme (color-scheme light, white background), the body has a 16px side gutter, and no element forces a width over the viewport. Check that every <code> in headings renders (no raw entities). Check that the table columns are readable: no cell longer than about 600 characters. Report what you found; do not restyle the page.' },
]

const REFUTE = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    corrected_fix: { type: 'string', description: 'if the finding stands but its fix is wrong, the right fix' },
  },
  required: ['refuted', 'reason'],
}

const results = await pipeline(
  LENSES,
  l => agent([COMMON, '', 'YOU ARE A REVIEWER. ' + l.prompt].join('\n'), { label: 'review:' + l.key, phase: 'Review', schema: FINDINGS }),
  async (r, l) => {
    if (!r) return { lens: l.key, findings: [], summary: 'no result' }
    if (l.key === 'plain-english' || l.key === 'rendering') return { lens: l.key, ...r }
    const judged = await parallel(r.findings.map(f => () =>
      agent([COMMON, '', 'YOU ARE A REFUTER. A reviewer (lens: ' + l.key + ') reported this finding about the page. Check it against the tree at 175b1837b9, answers.md, the patches and the actual file state. Refute it if the page is right as written or if the finding is not supported; confirm it if the page is wrong. If the finding stands but its proposed fix is itself wrong, give the corrected fix.', '', 'FINDING:', JSON.stringify(f, null, 1)].join('\n'),
        { label: 'refute:' + l.key, phase: 'Refute', schema: REFUTE }).then(v => ({ ...f, verdict: v }))))
    return { lens: l.key, summary: r.summary, findings: judged.filter(Boolean) }
  },
)
const out = results.filter(Boolean)
for (const r of out) log(r.lens + ': ' + r.findings.length + ' findings' + (r.findings[0] && r.findings[0].verdict ? ', ' + r.findings.filter(f => f.verdict && !f.verdict.refuted).length + ' confirmed' : ''))
return out