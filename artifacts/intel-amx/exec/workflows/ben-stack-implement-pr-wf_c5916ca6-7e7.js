export const meta = {
  name: 'ben-stack-implement-pr',
  description: 'Implement one re-expressed stack branch per design.md, review it from four lenses, refute findings, fix, audit',
  phases: [
    { title: 'Implement', detail: 'merge + topical commits in the worktree, syntax matrix, greps' },
    { title: 'Review', detail: 'Ben persona, merge/behaviour audit, Wade checks, prose+commits' },
    { title: 'Verify', detail: 'three refuters per finding' },
    { title: 'Fix', detail: 'apply kept findings as fixups into the topical commits' },
    { title: 'Audit', detail: 'final checks and PR-body facts' },
  ],
}

const A = args
const S = A.scratch
const W = A.worktree
const COMMON = `
Environment and rules (read fully):
- Worktree: ${W} (branch ${A.branch}, a git worktree of the shared tron repo; this is the ONLY tree you may modify).
  Reference trees (READ-ONLY, never modify, never run git write commands in them): ${A.ref_trees}.
- Use absolute paths and \`git -C ${W} ...\`; avoid \`cd\` (the shell prints a directory listing on every cd).
- Never push. Never touch branches ${A.pr_branches}. Never run git in any /var/tmp/jhan tree. Never \`git worktree prune\`.
- Commits: \`git -C ${W} commit --no-verify\` (the lefthook hook is missing here). Every commit message ends with the line
  "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>". No message line may start with '#'. Subjects: "<area>: <what>".
- clang-format: \`uvx --from clang-format==19.1.7 clang-format --style=file:${W}/.clang-format -i <files>\` on every C++ file
  you change (headers and tests). Then \`git -C ${W} diff --check\` must be clean.
- Syntax matrix (the only compile check available on this host; nix and cmake are NOT available):
  \`W=${W} P=${S}/stack/lcheck bash ${S}/stack/lcheck/matrix.sh <label>\` prints "MATRIX OK" (22 cells; about 3 minutes;
  logs in ${S}/stack/lcheck/out/<label>/). Use a fresh label per run (e.g. pr${A.pr}-<step>-<n>). On failure read the
  cell's .log for the first 'error:' lines. The matrix compiles t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype,
  t_amx_numerics, heterogeneous_scheduler_compile and amx_attn.cpp in gen/gen-amxoff x option off/on.
- Tools: ugrep fails on long regexes ("exceeds complexity limits"): use grep -E or python3 -I for text work. The Read tool
  refuses files over 25k tokens: read big files in parts (offset/limit) or with sed -n.
- The design brief ${S}/stack/design.md is the specification (read it in full first; it is 40 KB, read in parts).
  ${S}/stack/findings-${A.pr_number}.md lists the verified objections Ben would raise (read it in full).
  ${S}/stack/ben-profile.md is Ben's taste profile (P1-P5, C1-C16).
- Plain English in every comment and commit message: define a term from outside the code at first use, one claim per
  sentence, no idioms, no issue or PR numbers in code comments, no history narration in comments ("previously", "now").
- Shared files keep their own constant idiom (kv_cache.hpp lower_snake; the hetero test NAME_<value>); never add a
  NAME_<value> constant outside the AMX kernel files (amx_attn.cpp, amx_attn_iface.hpp).
- Do not modify files outside what the brief lists for this branch. Do not "improve" adjacent code.
${A.extra ? "- Branch-specific instructions: " + A.extra : ""}
`

const IMPL_SCHEMA = { type: 'object', properties: {
  head_sha: { type: 'string' },
  commits: { type: 'array', items: { type: 'object', properties: { sha: { type: 'string' }, subject: { type: 'string' }, files: { type: 'array', items: { type: 'string' } } }, required: ['sha', 'subject'] } },
  matrix_verdict: { type: 'string' }, greps: { type: 'string' }, deviations: { type: 'string' },
  open_questions: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } },
  required: ['head_sha', 'commits', 'matrix_verdict', 'greps', 'summary'] }

const FINDINGS_SCHEMA = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, file: { type: 'string' }, line: { type: 'integer' },
    severity: { type: 'string', enum: ['block', 'should', 'nit'] },
    summary: { type: 'string' }, evidence: { type: 'string' }, remedy: { type: 'string' } },
    required: ['id', 'file', 'line', 'severity', 'summary', 'evidence', 'remedy'] } },
  notes: { type: 'string' } }, required: ['findings'] }

const VERDICT_SCHEMA = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, severity: { type: 'string', enum: ['block', 'should', 'nit'] } }, required: ['refuted', 'reason'] }

const FIX_SCHEMA = { type: 'object', properties: {
  head_sha: { type: 'string' },
  applied: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, commit: { type: 'string' }, what: { type: 'string' } }, required: ['id', 'what'] } },
  skipped: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, why: { type: 'string' } }, required: ['id', 'why'] } },
  matrix_verdict: { type: 'string' }, greps: { type: 'string' }, summary: { type: 'string' } },
  required: ['head_sha', 'applied', 'skipped', 'matrix_verdict', 'greps', 'summary'] }

const FINAL_SCHEMA = { type: 'object', properties: {
  head_sha: { type: 'string' }, branch: { type: 'string' },
  commits: { type: 'array', items: { type: 'object', properties: { sha: { type: 'string' }, subject: { type: 'string' }, stat: { type: 'string' } }, required: ['sha', 'subject'] } },
  matrix_verdict: { type: 'string' }, greps_verdict: { type: 'string' }, diff_check: { type: 'string' }, status_clean: { type: 'boolean' },
  problems: { type: 'array', items: { type: 'string' } },
  pr_body_facts: { type: 'array', items: { type: 'string' } },
  ben_objections_removed: { type: 'array', items: { type: 'string' } },
  residual_risks: { type: 'array', items: { type: 'string' } },
  diffstat_vs_pr_head: { type: 'string' } },
  required: ['head_sha', 'branch', 'commits', 'matrix_verdict', 'greps_verdict', 'diff_check', 'status_clean', 'problems', 'pr_body_facts', 'ben_objections_removed', 'residual_risks'] }

phase('Implement')
log(`Implementing ${A.label} in ${W}`)
const impl = await agent(`You are the implementer of ${A.label} (branch ${A.branch}).
${COMMON}
Task: carry out section 3 "${A.design_section}" of ${S}/stack/design.md exactly, commit by commit, in ${W}.
Before coding: read design.md sections 1, 2, 4, 5 and the section for this branch; read findings-${A.pr_number}.md; read
ben-profile.md. Read the files you will change in BOTH merge parents before resolving a conflict (the PR head is the
current HEAD of ${W}; the other parent is ${A.merge_ref}).
Step 0: confirm \`git -C ${W} status --short\` is empty and \`git -C ${W} rev-parse HEAD\` is ${A.pr_head}.
Step 1: \`git -C ${W} merge --no-ff --no-commit ${A.merge_ref}\` then resolve every conflict by the brief's resolution rules
(hand-edit the files; remove all markers; \`git -C ${W} diff --check\` must report no leftover markers), run clang-format
on the resolved files, run the matrix; only when it prints MATRIX OK commit the merge with the message the brief gives
(body: the resolutions, one line each). If the merge touches files the brief does not mention, list them in
'deviations'.
Steps 2..n: one topical commit per numbered commit of the brief. After each commit: clang-format, diff --check, matrix
(MATRIX OK), and the greps of section 4 (report their output verbatim in 'greps' for the final state).
If the brief's instruction is impossible or wrong against the code you see, do the closest behaviour-preserving thing,
and record it in 'deviations' with the reason. Do not skip a numbered item silently; record skipped items in
'open_questions'.
Behaviour preservation is the first rule: same stored bytes, same scores, same test expectations (section 4).
Return: head_sha, the commits (sha, subject, files), matrix_verdict (the exact MATRIX line of the final run), greps (the
section-4 grep outputs), deviations, open_questions, summary (what changed against the PR head, in plain English, 10
lines at most).`, { label: `implement:${A.label}`, phase: 'Implement', schema: IMPL_SCHEMA })
if (!impl) throw new Error('implementer returned nothing')
log(`Implemented: ${impl.head_sha} ${impl.commits.length} commits; ${impl.matrix_verdict}`)

const LENSES = [
  { key: 'ben', prompt: `You review as Ben Gamari (profile: ${S}/stack/ben-profile.md; also apply the ben-review skill at
/home/jhan/.claude/skills/ben-review/SKILL.md: shared domain abstractions, more than four parameters as a prompt to
investigate, preserve existing code). Report what he would still object to on this branch. Tie every finding to a line
the branch adds or changes relative to the PR head (${A.pr_head}) or resolves differently from his own head
(${A.ben_head}); cite P1-P5 / C1-C16. Also check that every numbered item of the brief's section for this branch is
done (a missing item is a 'block' finding). Pre-existing smells outside the stack's changes are not findings.` },
  { key: 'merge-behaviour', prompt: `You audit the merge resolution and behaviour preservation. Compute
\`git -C ${W} diff ${A.pr_head}...HEAD\` and \`git -C ${W} diff ${A.merge_ref}...HEAD\` (and the merge commit's own diff
against each parent). For every file with a conflict in the brief's resolution rules, check that the rule was applied and
that no hunk of either parent was lost or doubled (a loop or store present in both parents, a deleted helper still
called, a comment for a function that no longer exists). Check types at every new call (view constness, template
arguments, requires clauses, static_asserts), the fake-kernel call counts the dispatch test expects, and that stored
bytes, scores and test expectations are unchanged except for the brief's named exceptions. Check that the defects d1,
d2, d3 of design.md section 2 are fixed as specified and that nothing in the tree still calls a removed accessor
(page::k<, k_packed, kv_block( outside kv_cache.hpp). Severity: block = wrong code or lost hunk; should = contract or
comment contradicts code; nit = cosmetic.` },
  { key: 'wade', prompt: `You review with the Wade-code-review skill (/home/jhan/.claude/skills/Wade-code-review/SKILL.md;
read it): dead symbols and includes, debug switches, comments that contradict code, magic literals and NAME_<value>
constants in shared files, duplicated logic, names, silent fallbacks, hardware-gated or silently skipped tests, tests
that bypass the changed path, unrelated hunks, fixup clusters, commit messages that narrate history, stale text in
comments. Scope: \`git -C ${W} diff ${A.pr_head}...HEAD\` plus each commit of \`git -C ${W} log ${A.pr_head}..HEAD\`.
Pre-existing issues outside the diff are not findings.` },
  { key: 'prose', prompt: `You check prose: every comment line added or changed in \`git -C ${W} diff ${A.pr_head}...HEAD\`
and every commit message of \`git -C ${W} log ${A.pr_head}..HEAD\` against the plain-English rules
(/home/jhan/.claude/skills/plain-english/SKILL.md): terms from outside the code defined at first use, one claim per
sentence, no idioms, no issue/PR numbers in code comments, no history narration in comments, Note names unchanged or
consistently renamed (grep every 'Note [' reference that the diff touches and check its definition exists), trailer
line present on every commit, no commit message line starting with '#'. Also run
\`uvx --from clang-format==19.1.7 clang-format --style=file:${W}/.clang-format --dry-run -Werror <changed C++ files>\`
and report any file it would change as a 'should' finding. Report exact phrase and corrected phrase.` },
]

async function review(round) {
  const results = await parallel(LENSES.map(l => () => agent(`Round ${round} review of ${A.label} (branch ${A.branch}, worktree ${W}).
${COMMON}
Context: the branch re-expresses PR ${A.pr_number} on Ben's PR 5047 structure; the specification is ${S}/stack/design.md
(read sections 2, 3-"${A.design_section}", 4 fully) and the predicted objections are ${S}/stack/findings-${A.pr_number}.md.
Implementer's report: ${JSON.stringify(impl.summary)}; deviations: ${JSON.stringify(impl.deviations || '')};
open questions: ${JSON.stringify(impl.open_questions || [])}.
Lens: ${l.prompt}
Do NOT modify any file. Each finding: id '${l.key}-<n>', file (repo-relative), line (at HEAD of ${W}), severity, one-sentence
summary, evidence (what you verified in the tree, with file:line), remedy (smallest change; say which commit it belongs to).
Report at most 12 findings, most severe first. Report zero findings plainly if there are none.`,
    { label: `review:${l.key}:r${round}`, phase: 'Review', schema: FINDINGS_SCHEMA })))
  return results.filter(Boolean).flatMap(r => r.findings || [])
}

async function verify(findings, round) {
  const judged = await pipeline(findings, f => parallel([
    `Factual lens: is the finding true in the tree at HEAD of ${W}? Re-read the cited lines and the surrounding function in both merge parents (${A.pr_head}, ${A.merge_ref}). Refute if the cited code does not say what the finding claims, if the issue is pre-existing (present at ${A.pr_head} or ${A.ben_head} in unchanged code), or if the brief explicitly chose this shape (cite the brief line).`,
    `Behaviour lens: would the remedy change stored bytes, scores, test expectations or synchronization in a way the brief's section 4 forbids, or break the syntax matrix? Refute the finding if its remedy is worse than the current code or not smaller than the problem.`,
    `Ben-record lens: does Ben's record (ben-profile.md P1-P5, C1-C16; ben-corpus.md quotes) actually support that he would raise this? Refute if it is taste without evidence, or if the severity is more than one step too high (then say the right severity).`,
  ].map((lens, i) => () => agent(`Refute this review finding on ${A.label} (worktree ${W}, read-only for you).
${COMMON}
Finding: ${JSON.stringify(f)}
${lens}
Default to refuted=true when uncertain. Return refuted, reason (what you verified, file:line), and the severity you would give.`,
    { label: `refute:${f.id}:${i}`, phase: 'Verify', schema: VERDICT_SCHEMA }))).then(votes => {
      const v = votes.filter(Boolean)
      const kept = v.filter(x => !x.refuted).length >= 2
      const sev = kept ? (v.filter(x => !x.refuted).map(x => x.severity).filter(Boolean).sort()[0] || f.severity) : f.severity
      return { ...f, severity: sev, votes: v, kept }
    }))
  return judged.filter(Boolean)
}

let round = 1
let finalKept = []
let fixReport = null
while (round <= 2) {
  phase('Review')
  const found = await review(round)
  log(`Round ${round}: ${found.length} findings from ${LENSES.length} lenses`)
  if (!found.length) break
  phase('Verify')
  const judged = await verify(found, round)
  const kept = judged.filter(j => j.kept)
  const dropped = judged.filter(j => !j.kept)
  log(`Round ${round}: kept ${kept.length} (block ${kept.filter(k => k.severity === 'block').length}, should ${kept.filter(k => k.severity === 'should').length}, nit ${kept.filter(k => k.severity === 'nit').length}), dropped ${dropped.length}`)
  finalKept = kept
  if (!kept.length) break
  phase('Fix')
  fixReport = await agent(`You fix ${A.label} (branch ${A.branch}) in ${W} after review round ${round}.
${COMMON}
Kept findings (each survived three refuters): ${JSON.stringify(kept.map(k => ({ id: k.id, file: k.file, line: k.line, severity: k.severity, summary: k.summary, evidence: k.evidence, remedy: k.remedy })))}
Apply every 'block' and 'should' finding, and every 'nit' whose remedy is a few lines. Keep the branch's topical history:
a fix that belongs to one of the branch's own commits after the merge commit goes in as \`git -C ${W} commit --no-verify
--fixup=<that commit sha>\` and is then folded with \`GIT_SEQUENCE_EDITOR=: git -C ${W} rebase --autosquash <merge commit sha>\`
(this rebases only the commits after the merge commit; verify afterwards with \`git -C ${W} log --oneline ${A.pr_head}..HEAD\`
that the merge commit is unchanged and no fixup commit remains). A fix that belongs to the merge resolution itself goes in
as a new topical commit (do not rewrite the merge commit). Then clang-format, \`git diff --check\`, the matrix (MATRIX OK)
and the section-4 greps. Skip a finding only with a reason (wrong, pre-existing, or would break behaviour), and say so.
Return head_sha, applied (id, commit, what), skipped (id, why), matrix_verdict, greps, summary.`,
    { label: `fix:r${round}`, phase: 'Fix', schema: FIX_SCHEMA })
  if (!fixReport) throw new Error('fixer returned nothing')
  log(`Round ${round} fix: ${fixReport.applied.length} applied, ${fixReport.skipped.length} skipped; ${fixReport.matrix_verdict}`)
  if (!kept.some(k => k.severity !== 'nit')) break
  round++
}

phase('Audit')
const audit = await agent(`Final audit of ${A.label} (branch ${A.branch}, worktree ${W}; read-only for you except the checks below).
${COMMON}
Run and report: \`git -C ${W} branch --show-current\` (must be ${A.branch}); \`git -C ${W} status --short\` (must be empty);
\`git -C ${W} log --oneline ${A.pr_head}..HEAD\` (first commit after the PR head must be the merge commit of ${A.merge_ref};
no 'fixup!' subjects); every commit message ends with the Co-Authored-By trailer and has no line starting with '#';
\`git -C ${W} diff --check ${A.pr_head}...HEAD\`; the matrix \`W=${W} P=${S}/stack/lcheck bash ${S}/stack/lcheck/matrix.sh pr${A.pr}-audit\`
(report the MATRIX line); the section-4 greps of ${S}/stack/design.md (report each with its output); clang-format dry run
on the changed C++ files; \`git -C ${W} diff --stat ${A.pr_head}...HEAD\`; \`git -C ${W} merge-base --is-ancestor ${A.merge_ref} HEAD\`.
Then read the full diff \`git -C ${W} diff ${A.pr_head}...HEAD\` and write:
- pr_body_facts: 8 to 15 one-sentence facts for the PR description (what the branch does, what it removes, the named
  behaviour exceptions, what is pending measurement), present tense, plain English, with function names a reviewer can find;
- ben_objections_removed: the predicted objections of ${S}/stack/findings-${A.pr_number}.md that this branch removes
  (id: how), and those it does not (id: why);
- residual_risks: what the syntax matrix cannot prove (run-time counts, static probes, link errors, performance).
Previous fix report: ${JSON.stringify(fixReport ? fixReport.summary : 'none')}. Kept findings of the last round not fixed:
${JSON.stringify(finalKept.filter(k => !(fixReport && fixReport.applied.some(a => a.id === k.id))).map(k => k.id + ': ' + k.summary))}.
problems: anything above that failed (empty if all passed).`, { label: `audit:${A.label}`, phase: 'Audit', schema: FINAL_SCHEMA })

return { impl, audit, lastKept: finalKept.map(k => ({ id: k.id, severity: k.severity, summary: k.summary, file: k.file, line: k.line })), fixReport }