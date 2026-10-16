export const meta = {
  name: 'wade-skill-compress',
  description: 'Compress each verified check to skill size, apply the critic and fact-check corrections, and compress the style section',
  phases: [
    { title: 'Compress', detail: 'one agent per check: SKILL entry <= 170 words, procedure <= 2600 chars, critic lines applied, quotes verbatim' },
    { title: 'Style', detail: 'one agent: style summary <= 650 words for SKILL.md' },
  ],
}
const ROOT = '/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006'
const SKILL = '/home/jhan/.claude/skills/Wade-code-review'
const labels = args.labels
const OUT_SCHEMA = {
  type: 'object',
  properties: {
    label: { type: 'string' }, number: { type: 'number' }, disposition: { type: 'string' },
    heading: { type: 'string' },
    skill_md: { type: 'string' },
    question_line: { type: 'string' },
    procedure_md: { type: 'string' },
    widen_instructions: { type: 'string' },
    quotes: { type: 'array', items: { type: 'object', properties: { id: { type: 'number' }, pr: { type: 'string' }, quote: { type: 'string' } }, required: ['id', 'pr', 'quote'] } },
    precedent: { type: 'string' },
    applied: { type: 'array', items: { type: 'string' } },
  },
  required: ['label', 'number', 'disposition', 'heading', 'skill_md', 'question_line', 'procedure_md', 'widen_instructions', 'quotes', 'precedent', 'applied'],
}
phase('Compress')
const out = await parallel(labels.map(lab => () => agent(`Read ${ROOT}/CONTEXT.md fully and ${ROOT}/items2/${lab}.json fully (the verified draft under "final", the critic's lines about it under "critic_lines", and its check "number"). Read ${SKILL}/SKILL.md fully for the house form and the existing text of the check being widened (if disposition is widen_existing). Read ${ROOT}/codex-factcheck.md claims 1, 4, 5, 6 and 7.

Produce the FINAL text for the skill. Hard limits, counted by you before returning:
- heading: "### <number>. <name>" with a name of at most 12 words. For a widen_existing item, the heading keeps the existing check's number and name unless the critic or the draft renames it; if two items share number 3 (tests-run-at-head-before-approve, test-silently-skips-or-cannot-fail), use "3A" and "3B" as the heading number text and say so in widen_instructions.
- skill_md: at most 170 words. Markdown paragraphs in this order: "Trigger:" / "Procedure:" (3 to 6 numbered steps, each naming what to read or grep) / "Question:" / "Do not fire on:" / "Finding shape:" (one sentence in Wade's register for this check) / "Severity and precedent:" (his severity words, then "n = <count> comments over <PRs> PRs, <first>-<last date>" and "attributed" if any member is pasted assistant text). Plain English: define a code name at first use, one claim per sentence, no idioms. Every verbatim quote carries its comment id in parentheses.
- question_line: one line for the numbered question list at the top of SKILL.md: "<number>. <Subject>: <the one question>", at most 32 words.
- procedure_md: at most 2600 characters for references/procedures.md: "## Check <number>: <name>" then numbered shell commands with BASE, HEAD, WT, N placeholders, then one "On PR <n>:" line with real file:line values from the draft's run. Keep every command the executability refuter accepted; drop narration.
- widen_instructions: for widen_existing only: the exact edit to the existing SKILL.md check: quote the sentence to replace and give the replacement, or "append after <sentence>". For add_new: empty string.
- quotes: 2 to 4 of the draft's quotes whose verbatim_ok is true. Six draft quotes across the set are AUTHOR replies wrongly listed under Wade's id (verbatim_ok false): never use those.
- Apply EVERY critic line in critic_lines (do_not_fire additions, owner decisions, contradiction fixes) and these fact-check rulings: a measurement request is allowed when the PR trades memory for repeated work (4607543703); in shared code the value-suffixed form itself is a non-blocking nit when the partner site uses a literal plus a named local (6021333114); never say Wade never asks for a test run (4265644124, 3156090573); BASE is the merge base against the PR's base branch, not origin/main; a sentence derived only from a pasted assistant text is marked "(attributed: assistant text pasted by Wade in <id>)".
- applied: list each critic line or ruling you applied, one phrase each, and any you rejected with the reason.
Return raw data only.`, { label: `compress:${lab}`, phase: 'Compress', schema: OUT_SCHEMA })))

phase('Style')
const STYLE_OUT = { type: 'object', properties: { style_md: { type: 'string' }, full_reference_md: { type: 'string' } }, required: ['style_md', 'full_reference_md'] }
const style = await agent(`Read ${ROOT}/CONTEXT.md fully. Read the five drafted style sections in ${ROOT}/wf2-result.json under "style" (keys how_wade_words_a_finding, verdict_calibration, assisted_text, negative_space, when_replying_to_wade). Read ${ROOT}/codex-factcheck.md claims 1, 6 and 7, and ${ROOT}/style-stats.json.

Produce:
1. style_md: the SKILL.md section "## How Wade reviews and words a finding" in at most 650 words, with subsections: two registers by date (with 4 to 6 verbatim quotes and ids), verdict calibration (states 100/234/0 of 334; final verdict by comment count; the four must-change signals with one id each; the 48 silent PRs: median 2 files and 39 lines versus 7 files and 410 lines for commented PRs), pasted assistant text (the nine ids in one line; how to treat; PR 4557 Insufficient data), what he rarely comments on (one line per item with its count; the two exceptions 3778051701 and 4607543703), replying to Wade (concedes in writing with 2 ids; defers to owners; accepts next iteration; about one in six asks declined and let stand; an agent withdraws a nit after the author's fact). Every count carries its denominator. Plain English. Replace the sentence "He does not comment on formatting, brace style, benchmark method, the C++ guide, or kernel arithmetic line by line" with a corrected version that keeps what holds (0 of 269 texts on the C++ guide or kernel arithmetic) and names the exceptions.
2. full_reference_md: the five drafted sections verbatim, lightly corrected only where they contradict codex-factcheck.md, with a "Short version" of at most three sentences at the top, for references/wade-style.md. Keep every id.
Return raw data only.`, { label: 'style-compress', phase: 'Style', schema: STYLE_OUT, effort: 'high' })
return { checks: out.filter(Boolean), style }