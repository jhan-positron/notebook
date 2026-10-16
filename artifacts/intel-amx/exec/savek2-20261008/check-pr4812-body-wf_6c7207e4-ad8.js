export const meta = {
  name: 'check-pr4812-body',
  description: 'Fact-check and plain-English-check the draft body of PR 4812 against the merged code',
  phases: [{ title: 'Check', detail: 'fact lens and English lens' }, { title: 'Verify', detail: 'two refuters per finding' }],
}
const CTX = `
READ-ONLY task: never edit files, never run state-changing git commands.
The draft body of PR 4812 is the file /tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-merge-4774-2-4424/350a38ed-e19c-400f-a674-ca4754d64af2/scratchpad/pr-body-v1.md.
The code it describes is the worktree /home/jhan/workspace/ai-runs/tron-vnnik-savek2 at HEAD 45e6bb266d (merge of f52d634c32 = PR 4774 onto 6b939d25d2 = branch jhan-amx-vnniK head; merge base 30c4ac82cb). PR diff: git diff 6b939d25d2 45e6bb266d.
The "Test" section's pending table is intentionally pending (a build is running); do not report that.
`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, quote: { type: 'string' }, problem: { type: 'string' }, fix: { type: 'string' }, rule: { type: 'string' } },
  required: ['id', 'quote', 'problem', 'fix', 'rule'] } } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' } }, required: ['refuted', 'reason'] }
const LENSES = [
  { key: 'facts', prompt: `Lens FACTS: verify every factual claim of the body against the code and git: function signatures and default values, the k_store_shared conditions (read the function: at most 16 items? one worker? more than 128 workers = helper_windows.size()? row-major layout?), the watchdog constant name and value, the generated call texts, what LoopyTronSpec checks (counts and texts), what t_llama_unit does (main_worker_ix, mark checks), the "Not changed" claims (llama.hpp and heterogeneous_scheduler_compile.cpp call forms; save_v untouched by the diff), the commit ids and parents (git log), the claim that the merge diff equals PR 4774's diff up to constant spellings and touches no kernel and no stored byte, the open-item counts (git grep -c save_k_helper bb32a80774 for PR 4737; gh pr view 4424 --json body for the three places; gh pr view 4746/4774 state). Report each wrong or unverifiable claim with the exact quote and the correction. Report only wrong or unverifiable claims; not style.` },
  { key: 'english', prompt: `Lens ENGLISH: apply the plain-English rules from ~/.claude/skills/plain-english/SKILL.md in Check mode to the body: terms defined at first use (project CLAUDE.md term list: /home/jhan/workspace/intel-AMX/CLAUDE.md), one claim per sentence, numbers with units and meaning, citations after sentences, Short version at most three sentences, no idioms/metaphors, bullets for multi-point paragraphs, short sentences. Also the project's rules: present tense, no narration of the PR's own history (the one sentence stating that PR 4774 is replaced is allowed), no "ctx" for prompt length. Report each violation with the exact quote, the rule, and the corrected text. Skip the pending table.` },
]
phase('Check')
const results = await pipeline(LENSES,
  l => agent(CTX + '\n' + l.prompt, { label: `check:${l.key}`, phase: 'Check', schema: FINDINGS }),
  (found, l) => {
    if (!found) return []
    log(`lens ${l.key}: ${found.findings.length} findings`)
    return parallel(found.findings.map(f => () => parallel([1, 2].map(i => () => agent(
      CTX + `\nRefuter ${i} of 2. Lens ${l.key} claims this problem in the body:\n` + JSON.stringify(f, null, 2) +
      `\nTry to REFUTE it by reading the body and (for fact claims) the code/git. Refuted = the body is right as written, or the claim is a style preference outside the stated rules. Default refuted=true if uncertain. Give evidence.`,
      { label: `verify:${l.key}:${f.id}:${i}`, phase: 'Verify', schema: VERDICT })))
      .then(vs => { const v = vs.filter(Boolean); return { lens: l.key, finding: f, confirmed: v.length > 0 && v.filter(x => x.refuted).length === 0, votes: v } })))
  })
const all = results.flat().filter(Boolean)
return { confirmed: all.filter(r => r.confirmed), refuted: all.filter(r => !r.confirmed).map(r => ({ lens: r.lens, id: r.finding.id, quote: r.finding.quote, reasons: r.votes.map(v => v.reason) })) }