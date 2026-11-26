export const meta = {
  name: 'check-until-clean',
  description: 'More independent check rounds on the explanation files, until a round finds no wrong statement',
  phases: [
    { title: 'Round 3', detail: 'independent recheck with the list of earlier defects' },
    { title: 'Round 4', detail: 'only for targets that were not clean in round 3' },
    { title: 'Round 5', detail: 'only for targets that were not clean in round 4' },
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
          kind: { type: 'string', enum: ['wrong', 'missing', 'unclear', 'format'] },
          before: { type: 'string' },
          after: { type: 'string' },
          evidence: { type: 'string' },
        },
        required: ['file', 'lines', 'kind', 'after', 'evidence'],
      },
    },
    unresolved: { type: 'array', items: { type: 'string' } },
    checks_passed: { type: 'boolean' },
    verdict: { type: 'string', enum: ['clean', 'fixed', 'needs-rework'] },
  },
  required: ['items_checked', 'defects', 'checks_passed', 'verdict'],
}

const targets = args.targets
const listFile = args.listFile

function prompt(t, round, last) {
  const lastTxt = last
    ? `The reviewer of round ${round - 1} fixed these defects (JSON): ${JSON.stringify(last.defects.map(d => ({ lines: d.lines, kind: d.kind, after: (d.after || '').slice(0, 300), evidence: (d.evidence || '').slice(0, 200) }))).slice(0, 6000)}`
    : ''
  return `Read ${T}/BRIEF.md first and follow it, including section 7 (facts that are already established). In that file, T = ${T}.
Your unit is the entry with "id": "${t.unit}" in the list "${t.group}" of ${T}/units.json. Read that entry: its "extra", "chunk_extra" or "task" field holds the instructions that the writer had.
You are reviewer number ${round} of the target "${t.name}". Its files are listed in the entry with "name": "${t.name}" of ${listFile} (field "files"). ${t.note || ''}

Earlier reviewers fixed the defects that ${T}/prior/${t.name}.json lists. The last round still found false statements or missing facts, so more are likely to remain. ${lastTxt}

Your job is to find what is still wrong and fix it. Method:
1. Read the earlier defects. Each one shows a kind of mistake that the writer made. For each kind, search the files for the same mistake in other places.
2. Then check every statement again against the source and the data, as if no review had happened. A statement is checked only when you have read the source lines it explains, or run a command on the data file, or tested the construct in a small harmless experiment in your scratchpad sub-folder, or read the public documentation page (section 7, point 4 of the brief). Statements about what is timed, how a rate is computed, what a kernel loads, what a check stops, which process runs in which order, and every number get this treatment without exception.
3. Check that the files agree with section 7 of the brief wherever they touch one of its points (how the run was started, the two texts of bandwidth.c, "On this page", the missing binaries).
4. Check the plain-English rules and the format rules of the brief.
Change only text that is false, that leaves out a fact a reviewer of the measurement needs, or that breaks a rule. Do not reword text that is correct and clear: a change without need can add a new mistake. Do not add notes about the review to the files.
For a JSON file, change it with a small Python script (load, change, json.dump); keep the segments in order with no gap and no overlap; then run "python3 ${T}/companion_tool.py check-ann FILE" or "check-overview FILE" until it prints OK. For a Markdown file, check after your edits that every table row has the column count of its header and that every [RefN] used is defined.
Return: how many items you checked; every defect you fixed (file, lines, kind, the text before, the text after, the evidence in one sentence). kind is "wrong" for a false statement, "missing" for an important fact that was left out, "unclear" for a plain-English defect, "format" for a format defect. Report a defect as "wrong" only when the old text was false, not when you made a true text more exact. List under unresolved what you could not settle. verdict: "clean" when you changed nothing, "fixed" when you fixed all you found, "needs-rework" when the files need more work than you could do.`
}

async function converge(t) {
  const rounds = []
  let last = null
  for (let r = t.rounds_done + 1; r <= t.rounds_done + 3; r++) {
    const v = await agent(prompt(t, r, last), { label: `check${r}:${t.name}`, phase: `Round ${r}`, schema: VERDICT })
    rounds.push({ round: r, result: v })
    if (!v) break
    const wrong = v.defects.filter(d => d.kind === 'wrong').length
    const missing = v.defects.filter(d => d.kind === 'missing').length
    log(`${t.name}: round ${r}: ${v.items_checked} items, ${wrong} wrong, ${missing} missing, ${v.defects.length - wrong - missing} other, verdict ${v.verdict}`)
    last = v
    if (wrong === 0 && missing <= 1 && v.verdict !== 'needs-rework') break
  }
  const lastV = rounds.length ? rounds[rounds.length - 1].result : null
  const clean = !!lastV && lastV.defects.filter(d => d.kind === 'wrong').length === 0 && lastV.defects.filter(d => d.kind === 'missing').length <= 1
  if (!clean) log(`${t.name}: NOT clean after round ${rounds.length ? rounds[rounds.length - 1].round : t.rounds_done}`)
  return { name: t.name, group: t.group, clean, rounds }
}

const results = await parallel(targets.map(t => () => converge(t)))
return { targets: results.map((r, i) => r || { name: targets[i].name, failed: true }) }
