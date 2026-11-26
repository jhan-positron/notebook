export const meta = {
  name: 'false-statement-rounds',
  description: 'Final check rounds that look only for false statements, until two rounds in a row find none',
  phases: [
    { title: 'Numbers and references', detail: 'every number, line reference, path and sha value against source and data' },
    { title: 'Behavior', detail: 'every statement on what the code does, against the source lines' },
  ],
}

const T = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/code-data-list-2026-11-21'

const VERDICT = {
  type: 'object',
  properties: {
    items_checked: { type: 'integer' },
    defects: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          lines: { type: 'string' },
          kind: { type: 'string', enum: ['wrong', 'format'] },
          before: { type: 'string' },
          after: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['file', 'lines', 'kind', 'before', 'after', 'evidence'],
      },
    },
    unresolved: { type: 'array', items: { type: 'string' } },
    checks_passed: { type: 'boolean' },
  },
  required: ['items_checked', 'defects', 'checks_passed'],
}

const LENS = {
  numbers: {
    phase: 'Numbers and references',
    text: `Your lens is NUMBERS AND REFERENCES. Check every number, count, size, time, rate, percent value, line number, line range, function name, file name, path, sha256 value and date in the files, and every entry of the reference lists. Check each one with a script or a direct read of the cited lines (for example: print the cited line and compare, count rows with a script, recompute a rate from the data file, run sha256sum on a local file). A cited line range must hold what the text says it holds. A count must equal the count that a script gives.`,
  },
  behavior: {
    phase: 'Behavior',
    text: `Your lens is BEHAVIOR. Check every statement on what the code or the tool does: the order of execution, who calls whom, what is inside and outside the timed window, how a rate is computed, what a kernel loads, adds or stores per loop pass, what a check tests and what happens when it fails (exit status, message, does the caller stop), what happens for an edge value (zero, empty, one thread, a division that gives 0), which process waits for which, and what a column or a field means. Read the source lines for each statement. For a shell or Python construct whose behavior you are not sure of, run a small harmless experiment in your scratchpad sub-folder or read the public documentation page (section 7, point 4 of the brief). A statement that holds for most cases and is false for a case that the whole-chip test uses is false.`,
  },
}

const targets = args.targets
const listFile = args.listFile

function prompt(t, round, lens) {
  return `Read ${T}/BRIEF.md first and follow it, including section 7 (facts that are already established). In that file, T = ${T}.
Your unit is the entry with "id": "${t.unit}" in the list "${t.group}" of ${T}/units.json. Read that entry: its "extra", "chunk_extra" or "task" field holds the instructions that the writer had.
You are reviewer number ${round} of the target "${t.name}". Its files are listed in the entry with "name": "${t.name}" of ${listFile} (field "files"). ${t.note || ''}

${round - 1} reviewers before you fixed the defects that ${T}/prior/${t.name}.json lists (field "round" gives the round). The files are close to final. This round has one purpose: find statements that are still FALSE, and correct them.

${LENS[lens].text}

Rules of this round:
1. Read the list of earlier defects first. The "wrong" entries show the kinds of mistake that were made in these files. Search for the same kinds in other places of the files.
2. Go through the files statement by statement under your lens. Do not skip a statement because an earlier reviewer checked it.
3. Edit a text only when it is false. Make the smallest change that makes it true. Keep the plain-English rules of the brief in the new text (one claim per sentence, units on numbers, no idioms).
4. Do not add facts, do not reword true text, do not change the structure, do not add notes about the review. If you see an important missing fact or an unclear sentence, do not edit: name it under "unresolved" (at most 5 entries, only what a reviewer of the measurement needs).
5. Work in a scratchpad sub-folder named ${t.name}-r${round}. Do not use ssh. Do not run go.sh, go2.sh, ra.sh, rx.sh, run_kernels.sh, build12.sh or any benchmark binary. Do not run "companion_tool.py build" or data_companions.py without --check: the main session builds the pages.
6. For a JSON file, change it with a small Python script (load, change, json.dump with the same indentation and ensure_ascii as the file has); keep the segments in order with no gap and no overlap; then run "python3 ${T}/companion_tool.py check-ann FILE" or "check-overview FILE" until it prints OK. For a Markdown file, check after your edits that every table row has the column count of its header and that every [RefN] used is defined.

Return: items_checked (the number of statements you checked under your lens); defects: one entry for every text you changed (file, lines, kind "wrong" when the old text was false, kind "format" only when a check tool failed and you repaired the file, the text before, the text after, the evidence in one sentence that names the source line or the command). Report "wrong" only when the old text was false, not when you made a true text more exact. An empty list means that you found no false statement. checks_passed: true when every check tool printed OK after your last edit, or when you changed nothing.`
}

async function converge(t) {
  const rounds = []
  let streak = t.streak || 0
  let r = t.rounds_done
  const order = ['numbers', 'behavior']
  let i = 0
  while (streak < 2 && r < t.rounds_done + (t.max_rounds || 4)) {
    r += 1
    const lens = order[i % 2]
    i += 1
    const v = await agent(prompt(t, r, lens), { label: `${lens}${r}:${t.name}`, phase: LENS[lens].phase, schema: VERDICT })
    rounds.push({ round: r, lens, result: v })
    if (!v) break
    const wrong = v.defects.filter(d => d.kind === 'wrong').length
    log(`${t.name}: round ${r} (${lens}): ${v.items_checked} statements, ${wrong} false, checks ${v.checks_passed ? 'OK' : 'FAILED'}`)
    streak = wrong === 0 ? streak + 1 : 0
  }
  if (streak < 2) log(`${t.name}: NOT settled after round ${r} (rounds without a false statement in a row: ${streak})`)
  return { name: t.name, group: t.group, settled: streak >= 2, streak, last_round: r, rounds }
}

const results = await parallel(targets.map(t => () => converge(t)))
return { targets: results.map((r, i) => r || { name: targets[i].name, failed: true }) }
