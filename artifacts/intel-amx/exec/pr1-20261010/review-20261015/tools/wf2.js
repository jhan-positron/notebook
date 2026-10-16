export const meta = {
  name: 'verify-4868-applied',
  description: 'Verify that every accepted review thread of PR 4868 is applied exactly as decided: one agent per thread, then one per file for whole-diff checks',
  phases: [{ title: 'Per-thread', detail: 'one verifier per thread' }, { title: 'Per-file', detail: 'one verifier per changed file' }],
}
const W = args.worktree, HEAD = args.head, BASE = args.base, ITEMDIR = args.itemdir, items = args.items
const byPath = {}
for (const it of items) { (byPath[it.path] = byPath[it.path] || []).push(it) }
const files = Object.keys(byPath).map(p => ({ path: p, threads: byPath[p] }))
const V = { type: 'object', properties: { id: { type: 'string' }, applied_as_decided: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } }, note: { type: 'string' } }, required: ['id', 'applied_as_decided', 'problems', 'note'] }
const FV = { type: 'object', properties: { path: { type: 'string' }, ok: { type: 'boolean' }, problems: { type: 'array', items: { type: 'string' } }, unexpected_changes: { type: 'array', items: { type: 'string' } }, note: { type: 'string' } }, required: ['path', 'ok', 'problems', 'unexpected_changes', 'note'] }
function tp(it) {
  return `You verify that ONE accepted review thread of PR 4868 (positron-ai/tron) was applied exactly as decided. READ-ONLY: do not modify files.

Worktree: ${W}. HEAD commit ${HEAD} is the PR head BEFORE the edits; the working tree holds the edits (uncommitted). So:
- the old file: git -C ${W} show ${HEAD}:${it.path}
- the new file: ${W}/${it.path}
- the change: git -C ${W} diff ${HEAD} -- ${it.path}
Thread ${it.id}: anchored at old lines ${it.start_line}..${it.line}. Decision: ${it.decision} (${it.target_kind}).
First run: cat ${ITEMDIR}/${it.id}.json  -- it holds body (the review comment with its Proposed block), reply (the PR author's reply; empty = no reply = accept the proposal or cut), target_text (the accepted replacement text; for a cut the comment is deleted).

Check, by comparing old and new file around the anchor (use the diff hunk nearest to the anchor):
1. For a replace: the accepted target_text appears in the new file verbatim (word for word; only indentation may differ, and a line may have been re-wrapped at a word boundary only if it exceeded 88 columns), exactly once, at the place of the old comment. The old comment's sentences that the finding cut are gone; sentences the finding said stay are present exactly once (no duplicate from context lines).
2. For a cut: the old comment is gone, and no code line was removed with it. A trailing comment cut leaves the code line intact.
3. For a "move" or a named-bool thread whose Proposed block carries a definition or a location note: the definition or moved line is present exactly once at a sensible place (a definition precedes its first use, inside the right scope), with no leftover placement-instruction comment such as "// near the top of the test case".
4. No other change to this file's lines in the hunk belongs to this thread beyond what the decision requires (changes from OTHER threads in the same file are expected; ignore them unless they damage this thread's result).
5. Every new line is at most 88 columns.
Report applied_as_decided=true only if all checks pass; list each failed check in problems with the exact text involved.`
}
function fp(f) {
  return `You verify the whole diff of ONE file of PR 4868 (positron-ai/tron) after review-thread edits were applied. READ-ONLY.

Worktree: ${W}. HEAD ${HEAD} = the PR head before the edits; the working tree holds the edits. Merge base with main: ${BASE}.
File: ${f.path}. Threads applied in this file (id: old anchor lines, decision): ${f.threads.map(t => `${t.id}: ${t.start_line}-${t.line} ${t.decision}/${t.target_kind}`).join('; ')}.
Item files with each thread's body and accepted text: ${ITEMDIR}/<id>.json

Run: git -C ${W} diff ${HEAD} -- ${f.path}
Then check:
1. Every hunk of this diff belongs to one of the listed threads (match by position and content). List any changed line that no listed thread explains under unexpected_changes (quote it).
2. Rule 0 of the comment skill: only comments that PR 4868 itself added or changed may be edited. For each hunk, confirm the removed comment lines were added by the PR: git -C ${W} diff ${BASE} ${HEAD} -- ${f.path} shows the PR's own additions; a removed line that exists unchanged in ${BASE} (git -C ${W} show ${BASE}:${f.path}) is a violation, EXCEPT where the thread's finding explicitly says it replaces or repeats unchanged context lines.
3. No duplicated sentence or paragraph was left behind (a comment paragraph that now appears twice), no empty comment line pair ("//" directly followed by "//" with nothing between), no two consecutive blank lines introduced, no blank line directly after an opening brace introduced, no trailing whitespace on changed lines.
4. For code changes (named-bool items): every new constexpr bool is defined exactly once, before its first use, in a scope visible to every use; every use site the threads named uses the constant; no bare literal the threads replaced remains; no definition is unused.
5. The file still parses as C++ on a read-through of each hunk (balanced braces and comment markers; no comment marker left on a code line by mistake).
Report ok=true only if all checks pass; put each failure in problems with the exact line text.`
}
const perThread = await parallel(items.map(it => () => agent(tp(it), { label: `verify:${it.id}:${it.path.split('/').pop()}:${it.line}`, phase: 'Per-thread', schema: V })))
const perFile = await parallel(files.map(f => () => agent(fp(f), { label: `file:${f.path.split('/').pop()}`, phase: 'Per-file', schema: FV })))
const bad = perThread.filter(Boolean).filter(r => !r.applied_as_decided)
const badFiles = perFile.filter(Boolean).filter(r => !r.ok)
log(`threads not applied as decided: ${bad.length}; files with problems: ${badFiles.length}; missing results: ${items.length - perThread.filter(Boolean).length} + ${files.length - perFile.filter(Boolean).length}`)
return { perThread: perThread.filter(Boolean), perFile: perFile.filter(Boolean), missingThreads: items.filter((it, i) => !perThread[i]).map(it => it.id), missingFiles: files.filter((f, i) => !perFile[i]).map(f => f.path) }
