export const meta = {
  name: 'gdn-split-handoff-recheck',
  description: 'Second read-only check of the revised GDN PR split handoff: were the first-round findings resolved, and is the revised text consistent',
  phases: [{ title: 'Recheck', detail: 'one resolution audit and one fresh consistency read' }],
}

const FILE = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-gdn-pr-split-20261122.md'
const MAT = '/home/jhan/workspace/intel-AMX/GDN/status/handoff-material'
const FIRST = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad/check-results.json'

const SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          section: { type: 'string' },
          quote: { type: 'string', description: 'exact words of the revised handoff (short)' },
          problem: { type: 'string' },
          evidence: { type: 'string' },
          fix: { type: 'string', description: 'the corrected text, ready to paste' },
          severity: { type: 'string', enum: ['wrong', 'gap', 'unclear'] },
        },
        required: ['section', 'quote', 'problem', 'evidence', 'fix', 'severity'],
      },
    },
    summary: { type: 'string', description: 'two or three sentences: is the file fit to hand to the next agent' },
  },
  required: ['findings', 'summary'],
}

const COMMON = `
You check a REVISED handoff document: ${FILE}. Another agent will use it to split one draft PR of the repository positron-ai/tron into four draft PRs. Five fact files that it cites are in ${MAT}/.

HARD RULES
- Read-only. Do not edit the handoff or any other file outside your scratchpad. Do not check out, commit, push or change any branch or working tree. Never run "git worktree prune". No ssh. No builds. No test runs. GitHub: read-only "gh pr view" / "gh api" GET only. Post nothing.
- Git: "git -C /home/jhan/workspace/ai-runs/tron-gdn-amx ..." with "git show <sha>:<path>", "git diff", "git log", "git grep <pattern> <sha> -- <path>". A plain "cd" prints a directory listing, so avoid it.
- Report a finding only with evidence (a command output or a file:line or two quoted places of the handoff that contradict each other). Do not report taste, wording style or length. Report at most 15 findings, the most harmful first. If the file is sound, return few or none.
- Copy "quote" exactly from the handoff so the author can find the place. Give a "fix" that can be pasted.
`

phase('Recheck')
const [audit, fresh] = await parallel([
  () => agent(`${COMMON}
YOUR LENS: resolution audit. A first round of six checkers reported findings on the first version of this file. Their results are in ${FIRST} (JSON: results[].key and results[].findings[] with section, quote, problem, evidence, fix, severity). Read all findings whose severity is "wrong", "gap" or "unclear" from the keys facts-repo, facts-numbers, decisions, cold-git and cold-measure (skip the key plain-english and skip severity "style").
For each such finding decide, by reading the revised handoff: resolved, resolved in another way that is also sound, or NOT resolved. Report only the NOT resolved ones and the ones whose fix in the revised text is itself wrong (for example a command that does not do what the text says, a number that the evidence of the finding contradicts, an instruction that now contradicts another section). Where two first-round findings proposed different fixes for the same place, check that the revised text is consistent with the facts in the evidence fields.
Test the revised commands that you can test read-only (git grep patterns, git diff --stat ranges, git log ranges, gh pr view fields).`, { label: 'recheck:resolution', phase: 'Recheck', schema: SCHEMA }),
  () => agent(`${COMMON}
YOUR LENS: fresh consistency read. You have NOT seen any earlier version. Read the whole revised handoff once as the agent who must execute it, then the fact files where the handoff points to them.
Look only for:
1. Contradictions inside the file: between the decision tables (2.1, 2.2), the questions (2.3), the go (3), the order of work (5) and the detail sections (6, 7, 8, 9). Examples to test: does every step of section 5 point to a section that says how; do the step numbers that other sections cite (step 1, step 11, step 12, step 13) match section 5; does the rule for question Q2 (what may be done without an answer, with a yes, with a no) agree in sections 2.3, 3, 5, 6.4 and 7.6; are the arm names, tags and model lists of sections 7.2, 7.3, 7.4, 7.5 and 7.6 the same everywhere; does each arm exist in a build that holds its model and its switch; do sections 8.2, 7.2 and step 12 agree on which commit a body cites.
2. A step that cannot be executed as written, or whose check cannot pass or cannot fail.
3. An instruction that would make the agent act beyond section 3 (the go), or against a rule quoted in section 10.
4. A term that the text uses in an instruction but neither "Words used here" nor the place of use explains, where a wrong guess would change what the agent does.
Verify with the repository (read-only) where a statement about code, branches or files decides the point.`, { label: 'recheck:fresh', phase: 'Recheck', schema: SCHEMA }),
])
return { audit, fresh }
