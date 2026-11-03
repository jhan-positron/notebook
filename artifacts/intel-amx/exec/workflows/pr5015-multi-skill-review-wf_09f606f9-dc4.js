export const meta = {
  name: 'pr5015-multi-skill-review',
  description: 'Review PR 5015 with a general pass and six named skills, verify each finding adversarially, compose GitHub comments',
  phases: [
    { title: 'Find', detail: 'one finder per reviewer (Wade split into 4 check groups)' },
    { title: 'Verify', detail: '3 lenses per finding, majority survives' },
    { title: 'Critic', detail: 'what did the reviewer miss' },
    { title: 'Compose', detail: 'GitHub comment text per reviewer' },
  ],
}

const A = args
const CTX = `
You are reviewing positron-ai/tron pull request #5015 "AMX attention: serve kv_mul 16 (Muse Glimmer) with a group_heads template parameter".
HEAD = ${A.head} (branch jhan-amx-kvmul16). BASE (merge base with main) = ${A.base}.
Worktree checked out at HEAD, READ ONLY (never edit, build, checkout, stash or run git commands that change state there): ${A.worktree}
Full diff BASE..HEAD: ${A.diffPath}
PR body (the description the reviewer reads): ${A.bodyPath}
Branch commits (hash + message): ${A.commitsPath}
Files the diff touches: h/tron/kernels/amx_attn_iface.hpp, h/tron/models/self_attention.hpp, src/tron/kernels/amx_attn.cpp, t/t_amx_dispatch_dtype.cpp, t/t_amx_numerics.cpp, t/t_llama_unit.cpp.
HEAD-side line ranges that appear in the diff (a GitHub inline comment can anchor only to a line in these ranges): ${JSON.stringify(A.ranges)}
Existing discussion on the PR: no human review comments yet; one bot summary (cursor). Issue #5021 tracks the namespace/suffix rename (the PR keeps amx_attn_h128g4 and _128x4 on purpose; do not report the names as a finding).
Project facts: kv_mul = query heads per KV head; GROUP_HEADS_4 / GROUP_HEADS_16 are the two instantiated group sizes; kv_mul 8 stays refused by shape_ok. The value-suffix constant convention (NAME_<value>) is accepted inside amx_attn.cpp and amx_attn_iface.hpp and in the AMX test files; shared files follow their own idiom.
Read the full text at HEAD of every touched file (use sed -n / cat on the worktree), not only the diff. Line numbers in findings are HEAD line numbers of the file at HEAD (verify with grep -n or sed -n before reporting).
Every finding must quote the exact HEAD line(s) it rests on. A finding on unchanged code that the diff did not touch is out of scope unless the diff made it newly wrong; mark such a thing in_diff=false and keep it only if it is a real defect.
Do not report: the namespace or suffix names (issue #5021); style preferences that no rule you were given supports; anything already answered in the PR body.
`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer', description: 'HEAD line number the comment anchors to' },
          title: { type: 'string', description: 'one sentence, the claim' },
          body: { type: 'string', description: 'the finding in plain English: the rule or check it rests on, the evidence (quoted HEAD lines), the concrete consequence or reading cost, and the proposed fix (exact replacement text when possible)' },
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'nit', 'fwiw'] },
          rule: { type: 'string', description: 'the skill rule / check number / review question the finding applies' },
          in_diff: { type: 'boolean' },
          evidence: { type: 'string', description: 'verbatim HEAD line(s) with line numbers' },
        },
        required: ['file', 'line', 'title', 'body', 'severity', 'rule', 'in_diff', 'evidence'],
      },
    },
    checked_but_clean: { type: 'string', description: 'which rules/checks you ran that produced no finding, in one paragraph' },
  },
  required: ['findings', 'checked_but_clean'],
}

const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    corrected_line: { type: 'integer', description: 'the right HEAD line if the finding named the wrong one; 0 if the line is right' },
    correction: { type: 'string', description: 'any factual correction the comment text needs before posting; empty if none' },
  },
  required: ['refuted', 'reason', 'corrected_line', 'correction'],
}

const COMPOSED = {
  type: 'object',
  properties: {
    review_body: { type: 'string' },
    comments: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          path: { type: 'string' },
          line: { type: 'integer' },
          body: { type: 'string' },
        },
        required: ['path', 'line', 'body'],
      },
    },
  },
  required: ['review_body', 'comments'],
}

const SKILL_DIR = '/home/jhan/.claude/skills'
const REVIEWERS = [
  {
    key: 'PR review',
    finders: [
      { label: 'general:kernel-math', prompt: `General PR review, lens: kernel correctness and numerics. Check by hand, element by element: (1) the 16 x 16 register transpose in qk_rowmajor_128x4 at HEAD (stages 1-2 unpack loop and store_transposed_rows<lane> stages 3-4): for every lane 0..3 and k 0..3, which tile column ends up in which row of s, and does it match s[head][token] for both group sizes; (2) pack_q_group_128x4 index arithmetic for 16 heads against the documented packed[] formula and the tile B-operand VNNI layout; (3) weights_times_v_128x4 for 16 heads: P conversion loop, the thread_local P scratch per specialization, zero-padding assumptions, tile row counts; (4) buffer sizes at the call sites in self_attention.hpp (amx_qpack slot, s_pages, amx_o) for kv_mul 16; (5) any UB, aliasing, alignment or overrun. Reason from the code at HEAD, not from the PR body.` },
      { label: 'general:dispatch-build', prompt: `General PR review, lens: dispatch, gate, build and link consistency. Check: group_heads_ok vs shape_ok vs the explicit instantiations vs every call site (self_attention.hpp passes geometry.kv_mul() for pack and operation_kv_mul for QK/PV; are these the same compile-time value on every path, including prompt/mixed and decode variants and the second apply_page_range copy near line 1846/2000/2085 if any use AMX); template declarations without definitions in the header plus explicit instantiations in amx_attn.cpp (ODR, the test TU that defines fakes of the primary templates, inline/anonymous namespace choices, the requires clauses on declaration vs definition vs explicit instantiation); behavior with TRON_AMX_DISPATCH off, with the kill switch, on a non-AMX host; any other caller of the kernels in the tree (git grep at HEAD for pack_q_group_128x4, qk_rowmajor_128x4, weights_times_v_128x4, GROUP_HEADS_4, shape_ok) that the diff did not update; models in config/ or generated headers with head 128 and kv_mul 16 (which models does the gate now admit, and is that intended).` },
      { label: 'general:tests-claims', prompt: `General PR review, lens: tests and PR-body claims. For each changed test (t_amx_numerics.cpp, t_amx_dispatch_dtype.cpp, t_llama_unit.cpp): does it call the changed production boundary, what deliberate code break would make each new assertion fail, does any new assertion pass vacuously, do the section names match what they assert, is any coverage duplicated. For the PR body: check every sentence in "How to review this PR" and "Verification" against the code at HEAD (file names, function names, section names, selector values, numbers that the code fixes); flag any sentence the code does not support. Also check the two commit messages against the diff.` },
    ],
  },
  {
    key: 'ben-review',
    finders: [{ label: 'ben-review', prompt: `Load and follow the skill at ${SKILL_DIR}/ben-review/SKILL.md (read the whole file first). Apply it to the diff: missing shared domain abstractions, repeated low-level representation details introduced or worsened by the change, and parameter / template-argument lists longer than four at changed declarations or call sites. Judge against the baseline at BASE (git show ${A.base}:<path> in the worktree is allowed, it is read-only). Report only what the skill's calibration section would keep.` }],
  },
  {
    key: 'Wade-code-review',
    finders: [
      { label: 'Wade:hygiene-13-24', prompt: `Load ${SKILL_DIR}/Wade-code-review/SKILL.md (read it completely) and the matching procedures in ${SKILL_DIR}/Wade-code-review/references/procedures.md. Run checks 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24 (code hygiene) on this PR at HEAD, exactly as the procedures say (run the greps). Report findings in Wade's finding shape and severity from the skill.` },
      { label: 'Wade:behavior-25-32', prompt: `Load ${SKILL_DIR}/Wade-code-review/SKILL.md (read it completely) and the matching procedures in ${SKILL_DIR}/Wade-code-review/references/procedures.md. Run checks 25, 26, 27, 28, 29, 30, 31, 32 (behavior: silent behavior change, counts/index/wait sets, silent fallbacks, shared state, buffers, hot path, state ownership, operator view) on this PR at HEAD. Report findings in Wade's finding shape and severity from the skill.` },
      { label: 'Wade:tests-1-5-33-34', prompt: `Load ${SKILL_DIR}/Wade-code-review/SKILL.md (read it completely) and the matching procedures in ${SKILL_DIR}/Wade-code-review/references/procedures.md. Run checks 1, 2, 3A, 3B, 4, 5, 33, 34 (tests: value rows and fixture literals, compile-time shape checks, gated or blind tests, named runs, duplicate coverage, test labels, changed path entered at its production entry, workarounds) on this PR at HEAD. Read AGENTS.md "Test policy" (lines 20-56) and t/AGENTS.md and quote them by line where used. Report findings in Wade's finding shape and severity from the skill.` },
      { label: 'Wade:claims-scope-6-12-35', prompt: `Load ${SKILL_DIR}/Wade-code-review/SKILL.md (read it completely) and the matching procedures in ${SKILL_DIR}/Wade-code-review/references/procedures.md. Run checks 6, 7, 8, 9, 10, 11, 12, 35 (claims and scope: claim sentences, CI sentences, result rows and body sentences vs this head, body passages and Notes that decide nothing, hunks that revert alone, fixup commits, shared-header hunks, bot findings) on this PR at HEAD: the PR body, the two commits, the CI lanes (.github/workflows at HEAD: which lanes set TRON_AMX_DISPATCH, do they execute the AMX tests), and the cursor bot summary (gh api repos/positron-ai/tron/issues/5015/comments). Report findings in Wade's finding shape and severity from the skill.` },
    ],
  },
  {
    key: 'cpp-coding-guide',
    finders: [{ label: 'cpp-coding-guide', prompt: `Load and follow ${SKILL_DIR}/cpp-coding-guide/SKILL.md (read the whole file first). Flag every violation in the ADDED or MODIFIED lines of the diff: unnamed numeric literals outside the listed exceptions (0 for zero init/reset/compare, alignas), named constexpr naming (uppercase with underscores, value suffix), bare true/false passed as a function, constructor or template argument at a call site (named constexpr bool required there; a literal bool in a return, initialization, assignment or comparison is fine), control-flow bodies without braces unless the whole statement is on one physical line. Note: in the test files the existing idiom for bool arguments may be /*name=*/true; report it only if it appears on a changed line, and say that the file's existing lines use the same spelling. For each violation quote the HEAD line and give the exact replacement.` }],
  },
  {
    key: 'positron-code-review',
    finders: [{ label: 'positron-code-review', prompt: `Load and follow ${SKILL_DIR}/positron-code-review/SKILL.md (read the whole file first). Read every comment the diff adds or changes (production and test files) and flag temporary pull-request review narration: review rounds, reviewer-specific labels, "as requested", "review finding T1" and the like, or statements that a reviewer asked for the code without the technical reason. Keep references that add durable technical context. For each hit give the location, the temporary reference and a concise proposed replacement that keeps the technical reason. If the diff is clean, say so in checked_but_clean and return no findings.` }],
  },
  {
    key: 'simplify-cpp-comments',
    finders: [{ label: 'simplify-cpp-comments', prompt: `Load and follow ${SKILL_DIR}/simplify-cpp-comments/SKILL.md (read the whole file first), in Check mode. Rule 0: only comments the diff adds or changes. List every such comment with file:HEAD-line, classify it (contract / placement / anchored fact / restatement / name-carried / idiom note), and for every comment a rule would cut or shorten give the rule number, the original text and the proposed text (within the file's column limit, 90 columns as clang-format uses here; check .clang-format at HEAD). For a surviving comment longer than two lines show the Rule 4 line-to-code mapping in the body. Report each cut or shortening as one finding; comments that survive unchanged go in checked_but_clean.` }],
  },
  {
    key: 'tron-code-review',
    finders: [{ label: 'tron-code-review', prompt: `Load and follow ${SKILL_DIR}/tron-code-review/SKILL.md (read the whole file first). Trace the changed behavior beyond the diff: every caller of the three kernels, the gate (eligible/shape_ok), the model geometry on the production path (which models have head 128 and kv_mul 16: grep config/ and h/tron/models at HEAD), software-only vs FPGA-assisted attention for sliding-window and full layers, the feature enabled/disabled (TRON_AMX_DISPATCH, available(), kill switch), pure vs mixed batches, empty/singleton (partial page, one token), boundary shapes (kv_mul 2, 4, 8, 16, 32; head 64/128/256). The attention path stats (TRON_ATTN_STATS, attn_stats.hpp) classify K tokens per path: do they still count correctly for 16-head groups (per-group vs per-head token counts). Review the tests per the skill's three questions. Report each finding with trigger, consequence, location, evidence strength and a discriminating check; state which conditions you checked and which you did not in checked_but_clean.` }],
  },
]

const LENSES = [
  { name: 'code-truth', prompt: 'Lens: is the claim literally true of the code at HEAD? Open the file in the worktree, read the named lines and their surroundings, and re-derive the claim yourself (for index or selector claims, compute the example by hand). If the finding names the wrong line, give corrected_line. Default to refuted=true when you cannot confirm the claim from the code.' },
  { name: 'scope-and-rule', prompt: 'Lens: scope and rule. (a) Is the issue introduced or materially changed by this diff (compare with BASE via git show BASE:path in the read-only worktree), or is it pre-existing unchanged code? Pre-existing and untouched means refuted unless the finding marks it as such and it is a real defect. (b) Does the finding actually fall under the named reviewer rule or skill check (read the skill file named in the finding and quote the rule)? A finding the rule does not support is refuted. (c) Is it already answered in the PR body or excluded by the instructions (names tracked by issue #5021)? Then refuted.' },
  { name: 'fix-and-consequence', prompt: 'Lens: consequence and fix. Is the stated consequence (defect, reading cost, contradiction, missing consumer) real and worth a reviewer comment at the stated severity? Would the proposed fix compile, keep clang-format (90 columns, 2-space indent) and keep every test passing, and does it not reintroduce something the PR body says was avoided on purpose? If the fix is wrong but the problem is real, keep refuted=false and put the corrected fix in correction. Refute when the consequence is hypothetical, when the fix would be worse, or when a simpler reading of the code resolves it.' },
]

function verifyPrompt(f, lens) {
  return `${CTX}
You are an adversarial verifier. Try to REFUTE this review finding. ${lens.prompt}
Finding (reviewer "${f.skill}", rule "${f.rule}", severity ${f.severity}):
file: ${f.file} line ${f.line}
title: ${f.title}
body: ${f.body}
evidence quoted by the finder: ${f.evidence}
Answer with refuted, a reason that cites HEAD lines, corrected_line (0 if the line is right) and correction (empty if none).`
}

async function verifyAll(findings, skill, phaseTag) {
  const judged = await parallel(findings.map(f => () =>
    parallel(LENSES.map(l => () =>
      agent(verifyPrompt(f, l), { label: `verify:${skill}:${l.name}:${f.file.split('/').pop()}:${f.line}`, phase: 'Verify', schema: VERDICT })))
      .then(vs => {
        const votes = vs.filter(Boolean)
        const keep = votes.filter(v => !v.refuted).length >= 2
        const corr = votes.find(v => v.corrected_line && v.corrected_line > 0)
        const corrections = votes.filter(v => v.correction && v.correction.trim()).map(v => v.correction)
        const refutations = votes.filter(v => v.refuted).map(v => v.reason)
        return { ...f, line: corr ? corr.corrected_line : f.line, keep, corrections, refutations, votes: votes.length, tag: phaseTag }
      })))
  return judged.filter(Boolean)
}

function inDiff(ranges, file, line) {
  const rs = ranges[file] || []
  return rs.some(r => line >= r[0] && line <= r[1])
}

function dedup(findings) {
  const seen = new Set(); const out = []
  for (const f of findings) {
    const k = `${f.file}:${f.line}:${f.title.toLowerCase().slice(0, 40)}`
    if (seen.has(k)) continue
    seen.add(k); out.push(f)
  }
  return out
}

log(`Reviewing PR 5015 at ${A.head} with ${REVIEWERS.length} reviewers`)

const results = await pipeline(
  REVIEWERS,
  // stage 1: find
  async (r) => {
    const found = await parallel(r.finders.map(fd => () =>
      agent(`${CTX}\nReviewer: ${r.key}. ${fd.prompt}\nReturn every finding you can support with HEAD evidence; an empty list is a valid answer when the rules are met. Set the skill field implicitly: all findings belong to reviewer "${r.key}".`,
        { label: `find:${fd.label}`, phase: 'Find', schema: FINDINGS })))
    const ok = found.filter(Boolean)
    const findings = dedup(ok.flatMap(x => x.findings.map(f => ({ ...f, skill: r.key }))))
    log(`${r.key}: ${findings.length} raw findings from ${ok.length}/${r.finders.length} finders`)
    return { reviewer: r, findings, clean: ok.map(x => x.checked_but_clean) }
  },
  // stage 2: verify
  async (s) => {
    const judged = await verifyAll(s.findings, s.reviewer.key, 'round1')
    const kept = judged.filter(j => j.keep)
    log(`${s.reviewer.key}: ${kept.length}/${judged.length} findings survived verification`)
    return { ...s, judged, kept }
  },
  // stage 3: critic
  async (s) => {
    const r = s.reviewer
    const skillHint = r.key === 'PR review'
      ? 'a general PR review (correctness, build, tests, PR-body claims)'
      : `the skill at ${SKILL_DIR}/${r.key}/SKILL.md (read it completely${r.key === 'Wade-code-review' ? ', and the procedures in references/procedures.md' : ''})`
    const crit = await agent(`${CTX}
You are the completeness critic for reviewer "${r.key}", which applies ${skillHint}.
Confirmed findings so far (do not repeat them):
${s.kept.map(f => `- ${f.file}:${f.line} ${f.title}`).join('\n') || '(none)'}
Refuted findings (do not resurrect them unless you have new evidence):
${s.judged.filter(j => !j.keep).map(f => `- ${f.file}:${f.line} ${f.title} | refuted because: ${f.refutations.join(' / ').slice(0, 300)}`).join('\n') || '(none)'}
What the finders reported as checked and clean: ${s.clean.join(' || ').slice(0, 3000)}
Task: what did this reviewer miss? Walk the diff hunk by hunk against the reviewer's rules and name any rule or check that was not applied, any touched file or hunk nobody looked at, and any finding the rules support that is missing. Return only NEW findings with HEAD evidence.`,
      { label: `critic:${r.key}`, phase: 'Critic', schema: FINDINGS })
    const fresh = crit ? dedup(crit.findings.map(f => ({ ...f, skill: r.key })))
      .filter(f => !s.kept.some(k => k.file === f.file && Math.abs(k.line - f.line) <= 2 && k.title.toLowerCase().slice(0, 30) === f.title.toLowerCase().slice(0, 30))) : []
    log(`${r.key}: critic added ${fresh.length} new findings`)
    const judged2 = await verifyAll(fresh, r.key, 'critic')
    const kept2 = judged2.filter(j => j.keep)
    log(`${r.key}: ${kept2.length}/${judged2.length} critic findings survived`)
    return { ...s, judged: [...s.judged, ...judged2], kept: [...s.kept, ...kept2] }
  },
  // stage 4: compose
  async (s) => {
    const r = s.reviewer
    const kept = s.kept.map(f => ({ ...f, in_diff: inDiff(A.ranges, f.file, f.line) }))
    const composed = await agent(`${CTX}
You compose the GitHub review that reviewer "${r.key}" posts on PR 5015. Input: the confirmed findings below (each survived a 3-lens adversarial check; "corrections" are factual fixes the verifiers asked for and must be applied to the text).
${JSON.stringify(kept, null, 1)}

Write:
1. review_body: starts with the exact text "${r.key}: " then a "Short version" of at most three sentences (what was checked, how many findings, the overall verdict for this reviewer: approve / approve with nits / changes requested), then a bullet list of the findings that could NOT be anchored inline (in_diff=false, or no sensible line): each bullet starts with "${r.key}: " and names file:line. If every finding is inline, end the body after the Short version plus one line "All findings are inline comments." If there are no findings at all, say what was checked and that nothing was found.
2. comments: one inline comment per finding with in_diff=true. path = the file path, line = the HEAD line (must be inside the diff ranges given above; if the finding's line is outside every range but a line inside a range within 3 lines carries the same code, move it there, else put it in the body). body starts with the exact text "${r.key}: " and then: the claim in one sentence, the evidence (quote the HEAD line in a short code span or fenced block), the consequence or reading cost in one sentence, and the proposed fix (use a GitHub \`\`\`suggestion block only when the replacement is exactly the single line the comment sits on; otherwise a fenced code block or prose). Severity in brackets at the end of the first sentence: [must-fix], [should-fix], [nit] or [fwiw].
Plain-English rules apply (one claim per sentence, short sentences, define a project term at first use in each comment, no idioms, units on numbers, no em-dashes, no semicolons). Do not name any person. Merge two findings that are about the same line into one comment. Keep each comment under about 180 words.`,
      { label: `compose:${r.key}`, phase: 'Compose', schema: COMPOSED })
    return { reviewer: r.key, kept, judged: s.judged, composed }
  },
)

const out = results.filter(Boolean)
log(`done: ${out.map(o => `${o.reviewer}=${o.kept.length}`).join(', ')}`)
return out