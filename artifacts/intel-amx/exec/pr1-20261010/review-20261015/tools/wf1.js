export const meta = {
  name: 'apply-4868-threads',
  description: 'Turn each accepted review thread on PR 4868 into exact whole-line edits (read-only agents, edits returned as data)',
  phases: [{ title: 'Edit', detail: 'one agent per accepted thread' }],
}
const W = args.worktree, HEAD = args.head, items = args.items, ITEMDIR = args.itemdir
const SCHEMA = { type: 'object', properties: {
  id: { type: 'string' }, applicable: { type: 'boolean' },
  edits: { type: 'array', items: { type: 'object', properties: { old_text: { type: 'string' }, new_text: { type: 'string' } }, required: ['old_text', 'new_text'] } },
  note: { type: 'string' }, max_new_line_len: { type: 'integer' } },
  required: ['id', 'applicable', 'edits', 'note', 'max_new_line_len'] }
function prompt(it) {
  const dec = it.target_kind === 'cut'
    ? 'CUT: delete the comment this thread addresses. (' + it.decision + ')'
    : 'REPLACE: replace the comment this thread addresses with exactly the accepted text given as target_text in the item file (' + it.decision + (it.decision === 'settle' ? ', the PR author\'s own wording' : '') + ').'
  const sib = it.kind === 'A' ? '\n\nThe item file lists sibling named-bool threads in the same file under "siblings" (for coordination; do NOT produce their edits).' : ''
  return `You turn ONE accepted review thread of PR 4868 (positron-ai/tron) into exact edits. READ-ONLY: do not modify any file; return the edits as data via StructuredOutput.

Worktree: ${W} (clean checkout of the PR head ${HEAD}; the GitHub line numbers below refer to this file as it is now).
File: ${W}/${it.path}
Thread anchor: lines ${it.start_line}..${it.line} (the lines the finder anchored the comment on).
Thread id: ${it.id}

First run: cat ${ITEMDIR}/${it.id}.json
It holds: body (the review comment as posted, with the Proposed block), reply (the PR author's reply; empty means no reply, and the author said no reply means accept the proposed change or cut), target_text (the accepted replacement text, already final), and for named-bool items siblings.

Decision to apply: ${dec}${sib}

Read the file around the anchor (sed -n or Read with offset/limit) and produce the edits.

Output rules (whole-line edits, applied by a script):
- old_text: verbatim contiguous lines copied from the file, exact indentation, no line numbers, joined with newlines. It must occur EXACTLY ONCE in the file; if the comment lines alone are not unique, extend old_text to a neighbouring code line and repeat that code line unchanged in new_text.
- new_text: the replacement lines; an empty string deletes the old lines.
- The accepted text is applied VERBATIM: do not reword it. Only adjust leading indentation to the surrounding code if the block was shown at a different indentation.
- The anchor marks the comment lines the finding replaces. Cross-check with the reason text: sentences it quotes as cut must disappear, sentences it says stay must survive exactly once. If the proposed block repeats unchanged context lines (the reason says so), include those lines in old_text so nothing is duplicated.
- A trailing comment on a code line: old_text is that code line, new_text is the line without the comment and without trailing spaces.
- A "move" finding, or a named-bool finding whose Proposed block contains a definition line or a location note (e.g. "near the top of the test case", "directly after \`namespace {\`", "next to the add lambda", "above the STATIC_REQUIRE"), needs a second edit at that location: choose the exact place (after the opening brace of the test case body next to the existing constexpr constants, or directly after the named anchor), keep the file's formatting, and explain in note. Insert a definition ONLY if your own Proposed block contains the definition line; a finding that says "uses the pair proposed for line N" or "shares the definition" produces only the use-site edit. Trailing comments in the Proposed block (for example "// make_llm_executor<Permuted, ...>" or "// near the top of the test case") are kept only when they document the code; a comment that is only a placement instruction is dropped.
- Cutting a comment: if the cut would leave two consecutive blank lines, or a blank line directly after an opening brace, include that blank line in old_text.
- Every new line must be at most 88 columns (clang-format ColumnLimit 88). If a line of the accepted text is longer, re-wrap that comment paragraph at word boundaries keeping every word, and say so in note.
- Set applicable=false with a note if the thread cannot be applied as decided (the comment is not there, or the decision contradicts the file). Report max_new_line_len (0 for a pure cut).`
}
const results = await parallel(items.map(it => () => agent(prompt(it), { label: `edit:${it.id}:${it.path.split('/').pop()}:${it.line}`, phase: 'Edit', schema: SCHEMA })))
const missing = items.filter((it, i) => !results[i]).map(it => it.id)
log(`edits returned: ${results.filter(Boolean).length}/${items.length}; missing: ${missing.join(',') || 'none'}`)
return { results: results.filter(Boolean), missing }
