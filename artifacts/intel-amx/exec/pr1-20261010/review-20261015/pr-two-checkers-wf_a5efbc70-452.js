export const meta = {
  name: 'pr-two-checkers',
  description: 'Named-constexpr-bool rule and simplify-cpp-comments Check on PRs 4824/4868/4887, every finding adversarially verified',
  phases: [
    { title: 'Find', detail: 'per changed C++ file: two comment finders (rule-by-rule, reader test) and one named-bool finder where the file has true/false candidates' },
    { title: 'Verify', detail: 'three refuter lenses per comment finding, two per named-bool finding' },
  ],
}

const REPO = args.repo
const ANNOT = args.annotDir
const units = args.units.map(u => ({
  ...u,
  head: args.heads[u.pr],
  base: args.bases[u.pr],
  annot: `${ANNOT}/${u.pr}/${u.path.replace(/\//g, '__')}.txt`,
}))
const short = p => p.split('/').pop()

const RULES_B = `simplify-cpp-comments, Check mode. Goal: every comment line that stays earns its place. A reader who knows C++ and the surrounding names learns one fact per comment line that the code does not already say.
Rule 0 - Diff only. Apply only to comments that are new or changed in the diff. Do not touch existing comments.
Rule 1 - The name carries it. A function whose name and body say the same thing as its comment gets no comment (typical: a one-expression accessor or predicate). Test: cover the comment and read the signature and the body. If nothing is missing, delete the comment.
Rule 2 - Do not restate identifiers. A comment does not repeat what names and types already say ("Only the blocks named by k_vnni_blocks hold the VNNI layout" restates k_vnni_blocks: cut the sentence). A pointer to a Note is kept only when the Note holds a fact the names do not.
Rule 3 - The one-line test. Write the function's contract in one line. If that line adds nothing to the signature and the body, delete the comment (Rule 1). If it adds one fact (a precondition, a lifetime rule, a unit, what an empty result means), keep that one fact as one line. If it needs more than one line, the function may be doing too much; say so. Prefer an attribute or a type over a comment when one exists (TRON(this_lifetimebound), [[nodiscard]], a requires clause, an assert).
Rule 4 - Every comment line maps to a code line. For a comment longer than two lines above a short body, map each comment line to the code line it explains. A line that maps to nothing is either caller context (why the function can be called in a given state: it moves to the caller or to the Note that owns that story, or is cut), a restatement (Rule 2: cut), or the one-line contract (Rule 3: keep as the first line). Put the surviving line next to the operand it explains when the body has several operands.
Rule 5 - A call-site comment says only why here. At a call, the comment states the placement reason: why the call sits at this point, what must have happened before it, what would break if it moved. What the callee does belongs to the callee's comment. A sentence that restates the callee's comment or a Note is cut.
Rule 6 - No comments on language idioms, and no idiom without a reason. Do not comment (void)x;, T{}, ~T{}, [[maybe_unused]], .template, or similar spellings. A warning-silencing idiom is kept only when the compile shows the warning without it.
Project facts: comment style is //, clang-format ColumnLimit is 88 (ReflowComments on: a long comment line gets split, short lines are never joined). The project keeps long design notes in "Note [Title]" blocks; do not propose cutting a Note, and inside a Note flag only a sentence that restates an identifier (Rule 2) or comments an idiom (Rule 6).`

const RULE_A = `The reviewer's rule, verbatim: "Use a named constexpr bool only where a bool is passed as an argument in a function call or constructor call or template argument. The reason is, at call site a bare true or false does not say what it means."
Apply it in both directions, on ADDED lines only (marker '+' in the annotated diff):
(a) rule 'bare-literal-argument': a bare true or false passed as an argument in a function call, member-function call, constructor call (T x(.., true), T x{.., true}, T{.., true}) or lambda call. A literal with a parameter-name comment, /*converted=*/true, is still a bare literal under this rule; report it and note that the comment carries the meaning.
(a2) rule 'bare-literal-aggregate': a bare true or false in positional aggregate initialization of a struct (S{a, b, true}). The rule text names constructor calls; report these separately and let the reviewer decide.
(a3) rule 'bare-literal-template-argument': a bare true or false passed as a template argument at a use site (f<true>(), make_llm_executor<false, tensor, tensor, tensor>, some_view<Cols, true, false>). Propose a named constant after the template parameter's name.
(c) rule 'named-constant-not-argument': a named constexpr bool whose value is a literal (constexpr bool FOO_TRUE = true;), defined or used on added lines, used in a position that is NOT a call argument and NOT a use-site template argument: return FOO_FALSE;, bool x = FOO_FALSE;, x = FOO_TRUE;, if (FOO_TRUE), a default function argument (bool repeat = REPEAT_FALSE) and a default template argument (template <bool Aligned = VIEW_ALIGNED_TRUE>). Precedent in this PR series: PR 4901 commit d0e6f816dd made the three default arguments of exercise_page bare literals and deleted RECORD_ROWS_TRUE, which had no call-site use. Report each such use site (one finding per line) and propose the bare literal there; a named literal constant with no call-site or template-argument use at all is deleted.
Do NOT report a bare literal in: return true;, assignments, comparisons (== true), variable or member initializers (bool x = false;, std::atomic<bool> y{false};), designated initializers (.flag = true), default arguments of functions or templates (the parameter name is adjacent), Catch2 macros (REQUIRE(false), CHECK(..)), comments or string literals. Do not report computed constexpr bools (constexpr bool x = std::is_same_v<...>, requires expressions, trait specializations such as "inline constexpr bool layout_on = false;" in a template specialization).
For (a)/(a2)/(a3): read the callee's parameter name, or the template parameter's name (git show the file at head, or the header that declares the callee or template), and propose a constant in the form this PR series already uses: ALL_CAPS parameter name plus _TRUE or _FALSE (example: RECORD_ROWS_TRUE), defined once as "constexpr bool" near the top of the file or test. If the file already defines a suitable constant (example: CONVERTED_TRUE in kv_cache.hpp), propose using it.`

const FIND_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          checker: { type: 'string', enum: ['A', 'B'] },
          line: { type: 'integer', description: 'new-file line number of the flagged line (for a comment block: its LAST added line)' },
          start_line: { type: 'integer', description: 'first line of the comment block; same as line for a single line' },
          rule: { type: 'string', description: "B: '1'..'6'. A: 'bare-literal-argument' | 'bare-literal-aggregate' | 'bare-literal-template-argument' | 'named-constant-not-argument'" },
          code: { type: 'string', description: 'the flagged text, first 120 characters' },
          action: { type: 'string', description: "B: 'cut' | 'shorten' | 'move'. A: 'name it' | 'use the literal'" },
          proposed: { type: 'string', description: "replacement text: the full new comment or code line(s); '' for cut" },
          reason: { type: 'string', description: 'one or two plain English sentences for the reviewer' },
          mapping: { type: 'string', description: 'B only: Rule 4 line-to-code mapping for a surviving comment over two lines, else empty' },
        },
        required: ['checker', 'line', 'start_line', 'rule', 'code', 'action', 'proposed', 'reason'],
      },
    },
    notes: { type: 'string', description: 'borderline cases not reported, with line numbers' },
  },
  required: ['findings', 'notes'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    reason: { type: 'string', description: 'at most two plain English sentences' },
    corrected_line: { type: 'integer', description: 'the right last line if the finding has it wrong, else 0' },
    corrected_start_line: { type: 'integer', description: 'the right first line if wrong, else 0' },
    corrected_proposed: { type: 'string', description: 'a better replacement text if the proposal should change, else empty' },
    better_rule: { type: 'string', description: 'a rule id that fits better, else empty' },
  },
  required: ['refuted', 'confidence', 'reason', 'corrected_line', 'corrected_start_line', 'corrected_proposed', 'better_rule'],
}

const SOURCES = u => `Sources (read them with cat or sed -n, in chunks for long files):
- Annotated diff of this file in PR ${u.pr}: ${u.annot}. Line format: "<new-file line>| <marker><text>" where marker '+' = added line, ' ' = unchanged context line, '-' = removed line (no number). Only '+' lines are in scope.
- The whole file at the PR head, for context: git -C ${REPO} show ${u.head}:${u.path}
- The file before the PR: git -C ${REPO} show ${u.base}:${u.path} (may not exist for a new file). Other files at head: git -C ${REPO} show ${u.head}:<path>.`

const FRAMING = {
  rules: `Framing: go rule by rule. First list every comment block that has at least one '+' line, with its line range. Then for each block apply Rules 1, 2, 3, 4, 5 and 6 in turn and record which rule, if any, cuts, shortens or moves it.`,
  reader: `Framing: the cover test. For each comment block that has at least one '+' line: cover it, read the signature and body (or the call and its callee), and write down the facts the comment adds that the code and the names do not carry. Zero facts: cut (Rule 1 or 2). One fact: shorten to that one line (Rule 3). A call-site comment that restates the callee or a Note: cut (Rule 5). A comment on an idiom: cut (Rule 6). More than two lines above a short body: do the Rule 4 mapping and move or cut the lines that map to nothing.`,
}

const finderB = (u, framing) => `You are checking the C++ comments of one file of PR ${u.pr} in positron-ai/tron under the simplify-cpp-comments skill, Check mode. You do not edit anything; you list what the rules would cut, shorten or move.
${SOURCES(u)}
${RULES_B}
Scope (Rule 0): a comment block is in scope when at least one of its lines is a '+' line; propose changes only to the changed sentences. A comment that is only context (' ' marker) is out of scope even if it breaks a rule.
${FRAMING[framing]}
For every comment the rules would cut, shorten or move, output one finding with checker 'B': line = the LAST added line of the comment block, start_line = the first line of the block, rule = '1'..'6', code = the first 120 characters of the comment, action = 'cut' | 'shorten' | 'move', proposed = the full replacement comment text ('' for cut; for 'move', the one line that stays here and, in reason, where the rest goes), reason = one or two plain English sentences a reviewer reads, mapping = the Rule 4 line-to-code mapping for a surviving comment longer than two lines, else ''. The proposed text must fit in 88 columns with the block's indentation and use //.
Calibration: a comment that carries one fact the code does not (a precondition, a unit, a lifetime rule, what an empty result means, why a call sits here) is kept; do not report it. Report only what a rule cuts, shortens or moves, and be exhaustive within that: every such comment in the diff, not a sample. Put borderline cases you did not report in notes, with line numbers.`

const finderA = u => `You are checking one file of PR ${u.pr} in positron-ai/tron against a reviewer's rule on named bools. You do not edit anything; you list the places that break the rule.
${SOURCES(u)}
${RULE_A}
Method: grep the annotated file for every '+' line containing true, false or constexpr bool, then classify each occurrence under the rule by reading the surrounding code and the callee at head. For rule (c), list every use of each named literal constant in the file at head (grep the full file) and report the uses that are not call arguments or use-site template arguments (a default argument, function or template, is such a use: report it).
Output one finding per line that breaks the rule, with checker 'A': line and start_line = that line's new-file number (for a multi-line call, the line that holds the literal), rule = one of the four rule ids (bare-literal-argument, bare-literal-aggregate, bare-literal-template-argument, named-constant-not-argument), code = the line text, action = 'name it' (for a bare literal) or 'use the literal' (for a named constant outside an argument position), proposed = the replacement line, plus the constant definition when a new one is needed, reason = one or two plain English sentences for the reviewer (name the callee parameter the literal binds to). Be exhaustive: every breaking line, not a sample. List template-argument literals and other excluded cases in notes with line numbers.`

const LENS_B = {
  'rule-text': `Lens: the rule as written. Does the cited rule, as written above, cut or shorten this comment? Does the comment carry a fact the code does not say (a precondition, a unit, a lifetime rule, what an empty result means, why a call sits here)? If it carries such a fact and the proposal drops it, refute. If a different rule number fits better, do not refute; put the id in better_rule.`,
  'code-context': `Lens: the code. Read the whole file at head around the comment and the code it describes (and the callee, for a call-site comment). Is the finding's claim true of the code? Does the proposed text keep every fact the code does not carry, read correctly, and fit in 88 columns with the block's indentation? Would a reader who knows C++ and the surrounding names lose something? Refute if the comment earns its place as it is. If the proposal is right in substance but the text should change, do not refute; give corrected_proposed.`,
  'diff-scope': `Lens: scope and anchoring. Is every flagged comment line a '+' line in this PR's annotated diff (Rule 0)? Are start_line and line exactly right per the annotated file (line = last added line of the block, start_line = first line of the block)? Is a "Note [..]" block being cut wholesale (not allowed)? Refute on a scope error. On an anchoring error you can fix, do not refute; give corrected_line and corrected_start_line.`,
}

const LENS_A = {
  'rule-text': `Lens: the rule as written. Is the literal really an argument in a function call, a constructor call or a template argument at a use site (not a return, an assignment, an initializer, a comparison, a designated initializer, a default argument of a function or a template, a Catch2 macro, a comment or a string)? For a named-constant-not-argument finding: is the constant really used in a position that is not a call argument or a use-site template argument (a default argument, function or template, is such a position, per the PR 4901 precedent d0e6f816dd)? Refute if the rule as written does not cover the line. For 'bare-literal-aggregate', do not refute on the constructor-call wording alone; judge whether the literal is positional and unnamed at the site.`,
  'code-context': `Lens: the code. Confirm from the annotated file that the line is a '+' line and the line number is right. Read the callee or template at head: which parameter does the literal bind to, and does the proposed constant name match that parameter's meaning and the naming already used in this PR series (ALL_CAPS + _TRUE/_FALSE)? If the file already defines a suitable constant, the proposal must use it. If the proposal is wrong in detail, do not refute; give corrected_proposed (and corrected_line if needed).`,
}

const verifyPrompt = (f, u, lens) => {
  const isB = f.checker === 'B'
  return `Adversarial check of one proposed review comment on PR ${u.pr} in positron-ai/tron. Your job is to try to REFUTE it. Default to refuted=true when you are uncertain.
Finding (JSON): ${JSON.stringify(f)}
${isB ? RULES_B : RULE_A}
${SOURCES(u)}
${isB ? LENS_B[lens] : LENS_A[lens]}
Return the structured verdict: refuted, confidence, reason (at most two plain English sentences), corrected_line and corrected_start_line (0 when the finding's numbers are right), corrected_proposed (empty unless the replacement text should change), better_rule (empty unless another rule id fits better).`
}

function overlaps(a, b) {
  return a.path === b.path && a.checker === b.checker && a.start_line <= b.line && b.start_line <= a.line
}

function dedupe(list) {
  const out = []
  for (const f of list) {
    const hit = out.find(g => overlaps(g, f))
    if (hit) {
      if (f.checker === 'A' && f.line !== hit.line) { out.push(f); continue }
      if (f.proposed && f.proposed !== hit.proposed) hit.alt_proposed = (hit.alt_proposed ? hit.alt_proposed + '\n---\n' : '') + f.proposed
      if (f.rule !== hit.rule) hit.alt_rule = f.rule
      hit.hits = (hit.hits || 1) + 1
      continue
    }
    out.push({ ...f, hits: 1 })
  }
  return out
}

let nFound = 0, nUnits = 0
const results = await pipeline(
  units,
  async u => {
    const tasks = [
      () => agent(finderB(u, 'rules'), { label: `findB-rules:${u.pr}:${short(u.path)}`, phase: 'Find', schema: FIND_SCHEMA }),
      () => agent(finderB(u, 'reader'), { label: `findB-reader:${u.pr}:${short(u.path)}`, phase: 'Find', schema: FIND_SCHEMA }),
    ]
    if (u.bool) tasks.push(() => agent(finderA(u), { label: `findA:${u.pr}:${short(u.path)}`, phase: 'Find', schema: FIND_SCHEMA }))
    const outs = (await parallel(tasks)).filter(Boolean)
    const raw = outs.flatMap(o => (o.findings || []).map(f => ({ ...f, pr: u.pr, path: u.path })))
    const findings = dedupe(raw)
    nUnits++; nFound += findings.length
    log(`Find ${u.pr} ${u.path}: ${raw.length} raw, ${findings.length} after dedupe (${nUnits}/${units.length} units, ${nFound} total)`)
    return { findings, notes: outs.map(o => o.notes).filter(Boolean), finders_ok: outs.length, finders_expected: tasks.length }
  },
  async (r, u) => {
    const judged = (await parallel(r.findings.map(f => () => {
      const lenses = f.checker === 'B' ? ['rule-text', 'code-context', 'diff-scope'] : ['rule-text', 'code-context']
      return parallel(lenses.map(l => () =>
        agent(verifyPrompt(f, u, l), { label: `verify-${l}:${u.pr}:${short(u.path)}:${f.line}`, phase: 'Verify', schema: VERDICT_SCHEMA })
          .then(v => ({ lens: l, v }))))
        .then(votes => ({ f, votes: votes.filter(Boolean) }))
    }))).filter(Boolean)
    const kept = judged.filter(j => {
      const n = j.votes.length, notRef = j.votes.filter(x => x.v && !x.v.refuted).length
      return j.f.checker === 'B' ? (n >= 2 && notRef >= 2) : (n >= 1 && notRef === n)
    }).length
    log(`Verify ${u.pr} ${u.path}: ${kept}/${judged.length} findings survive`)
    return { pr: u.pr, path: u.path, head: u.head, notes: r.notes, finders_ok: r.finders_ok, finders_expected: r.finders_expected, judged }
  },
)
const dropped = units.length - results.filter(Boolean).length
if (dropped) log(`WARNING: ${dropped} unit(s) dropped (a stage threw)`)
return { units: results.filter(Boolean), dropped }