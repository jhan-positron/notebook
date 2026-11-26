export const meta = {
  name: 'explain-code-and-data',
  description: 'Write and independently check the explanation files for the whole-chip test code and data (one group of units per run)',
  phases: [
    { title: 'Annotate', detail: 'one writer per file group or chunk' },
    { title: 'Verify', detail: 'one independent checker per annotation, fixes in place' },
    { title: 'Re-verify', detail: 'second checker when the first one found wrong statements' },
  ],
}

const T = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/code-data-list-2026-11-21'

const UNITS = {
  w1: [
    { id: 'bandwidth_orig', type: 'small' },
    { id: 'bandwidth', type: 'small' },
    { id: 'bwx12', type: 'big', key: 'bwx12', ranges: [[1, 529], [530, 1042], [1043, 1561], [1562, 2094], [2095, 2598], [2599, 3126]] },
    { id: 'drivers', type: 'small' },
    { id: 'partA-scripts', type: 'small' },
    { id: 'build12', type: 'small' },
    { id: 'selftests13', type: 'small' },
    { id: 'bwx12_selftest', type: 'small' },
    { id: 'check_listing12', type: 'small' },
    { id: 'test_kernels12', type: 'small' },
  ],
  w2: [
    { id: 'stats', type: 'small' },
    { id: 'facts_data', type: 'small' },
    { id: 'build_facts', type: 'big', key: 'build_facts', ranges: [[1, 535], [536, 1056]] },
    { id: 'facts_text', type: 'big', key: 'facts_text', ranges: [[1, 476], [477, 927], [928, 1488]] },
    { id: 'facts_text4', type: 'big', key: 'facts_text4', ranges: [[1, 521], [522, 1041], [1042, 1615]] },
    { id: 'make_report', type: 'big', key: 'make_report', ranges: [[1, 568], [569, 1139], [1140, 1694], [1695, 2265], [2266, 2834]] },
  ],
  w3: [
    { id: 'kprobe', type: 'small' },
    { id: 'bwx12_listing', type: 'small' },
    { id: 'partA-data', type: 'data' },
    { id: 'bwx12-csv', type: 'data' },
    { id: 'logs', type: 'small' },
    { id: 'specs', type: 'small' },
    { id: 'bwx12_build_records', type: 'small' },
    { id: 'rx-files', type: 'data' },
    { id: 'facts-outputs', type: 'data' },
    { id: 'report-and-rules', type: 'data' },
  ],
}

const ANNOT = {
  type: 'object',
  properties: {
    files_written: { type: 'array', items: { type: 'string' } },
    checks_passed: { type: 'boolean' },
    new_words: { type: 'array', items: { type: 'object', properties: { term: { type: 'string' }, def: { type: 'string' } }, required: ['term', 'def'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
  required: ['files_written', 'checks_passed', 'summary'],
}

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
        required: ['file', 'lines', 'kind', 'after'],
      },
    },
    unresolved: { type: 'array', items: { type: 'string' } },
    checks_passed: { type: 'boolean' },
    verdict: { type: 'string', enum: ['clean', 'fixed', 'needs-rework'] },
  },
  required: ['items_checked', 'defects', 'checks_passed', 'verdict'],
}

const group = args.group
const units = UNITS[group]

const HEAD = (id) => `Read ${T}/BRIEF.md first and follow it. In that file, T = ${T}.
Your unit is the entry with "id": "${id}" in the list "${group}" of ${T}/units.json. Read that entry now. It names your files (key, path, lang, lines, chunks), and its "extra" or "task" field holds instructions that are specific to these files. They are part of your task.
`

const JSON_TIP = `Write each JSON file with a small Python script that calls json.dump (hand-written JSON breaks on quotes and backslashes). Keep that script in your scratchpad folder, not in T.`

const RETURN_W = `Return: the files you wrote, whether every check printed OK, questions you could not resolve from the files (open_questions), and a summary of at most 5 sentences.`

function smallPrompt(u) {
  return HEAD(u.id) + `
Job: for each file of your unit, write the overview file T/ann/<key>.overview.json and one annotation file T/ann/<key>.c<NN>.json per chunk of that file (output format A of the brief).
Steps:
1. Read each source file in full, with line numbers.
2. Read the files that call it or that it calls, as far as you need them to explain it (section 2 of the brief).
3. Write the files. ${JSON_TIP}
4. Run check-ann and check-overview on every file you wrote, and fix until each prints OK. Read the warnings too: a segment with source text and no explanation is only right when the lines need none.
5. Read your explanations once more against the source, row by row, as a reader who doubts each sentence. Fix what does not hold.
${RETURN_W}`
}

function overviewPrompt(u) {
  return HEAD(u.id) + `
Job: write only the overview file T/ann/${u.key}.overview.json for your file (output format A of the brief). Other agents write the annotation files of the chunks after you, and they read your overview first. So the overview must define the words they will need, and its function list and call sequence must be exact.
Steps:
1. Read the whole source file, with line numbers (read it in parts of about 800 lines; do not skip a part).
2. Follow the "extra" instructions of your unit entry.
3. Write the file. ${JSON_TIP}
4. Run check-overview until it prints OK.
5. Check every line number of "functions", "call_sequence" and "main_flow" against the source once more.
${RETURN_W}`
}

function chunkPrompt(u, i, rg) {
  const nn = String(i + 1).padStart(2, '0')
  return HEAD(u.id) + `
Job: write only the annotation file T/ann/${u.key}.c${nn}.json: chunk ${i + 1} of your file, lines ${rg[0]} to ${rg[1]} (output format A of the brief). The "chunk_extra" field of your unit entry holds instructions for chunk writers. Other agents write the other chunks at the same time.
Steps:
1. Read T/ann/${u.key}.overview.json. Use its words and its function names. Do not rewrite it.
2. Read lines ${rg[0]} to ${rg[1]} of the source in full, with line numbers. Read other parts of the file as far as you need them to explain your lines (a function that starts before your range, a helper defined elsewhere).
3. Write the annotation file. ${JSON_TIP} If your range starts or ends inside a function, say so in the first or last row ("continues the function X that starts at line N").
4. Run check-ann until it prints OK. Read the warnings.
5. Read your explanations once more against the source, row by row, as a reader who doubts each sentence. Fix what does not hold.
If you use a term that needs a definition and the "words" list of the overview lacks it, return it in new_words (term and definition). Do not edit the overview.
${RETURN_W}`
}

function dataPrompt(u) {
  return HEAD(u.id) + `
Job: write the data explanation files that the "outputs" field of your unit entry names, as its "task" field says (output format B of the brief, in Markdown).
Steps:
1. Read the program lines that write the data file, and the lines of the analysis scripts that read it.
2. Look at the data files themselves (first lines, last lines, a count of each kind of line with a command). For a large file use grep, sed -n and python3. Do not load a large file whole.
3. Write the output files with the Write tool. Copy a sample line from a data file only with a command (sed -n), never from memory. Name the file and line of every sample.
4. Check every number that you state with a command (counts, sizes). Check that each column list has as many names as a real row has fields.
5. Read your text once more against the source and the data as a reader who doubts each sentence. Fix what does not hold.
${RETURN_W}`
}

function verifyPrompt(u, what, files, round, prev) {
  const again = round > 1
    ? `\nAnother reviewer checked these files before you and changed them (${prev[prev.length - 1] ? prev[prev.length - 1].defects.length : 'an unknown number of'} defects). Do not trust that review. Check everything again from the source, and look hardest at statements about what is timed, how a rate is computed, what a kernel loads, and what a check stops.\n`
    : ''
  return HEAD(u.id) + `
You are an independent reviewer. Another agent wrote ${what}:
${files.map(f => '- ' + f).join('\n')}
Its statements may be wrong. Assume that at least one statement is wrong until you have checked each one against the source.${again}
For each segment (format A) or each paragraph, table row and column (format B):
(a) Is every statement true? Read the source lines that it explains. When a statement is about what a shell construct, a regular expression, a Python expression, a C library call or an Arm instruction does and you have any doubt, test it with a small harmless experiment in your scratchpad, or look it up (man, --help, the objdump listings named in section 2 of the brief). A statement about data (a count, a value, a column) is checked with a command on the data file.
(b) Is something missing that a reviewer of the measurement must know (the list at the end of section 4 of the brief)? Is a line that changes behavior left without explanation?
(c) Does the text follow the plain-English rules of section 4 (no idiom, one claim per sentence, units, terms defined at first use, no file:line citation of another file inside a sentence)?
(d) Does it follow the format rules of section 5 or 6 and the "extra" or "task" instructions of the unit entry? For an overview: does every line number in "functions", "call_sequence" and "main_flow" point at the right line?
Fix every defect in the file itself. For a JSON file, change it with a small Python script (load, change, json.dump) so that it stays valid; keep the segments in order with no gap and no overlap (you may split or merge segments). Then run check-ann or check-overview on every JSON file until it prints OK.
Do not rewrite text that is correct and clear. Do not add praise or notes about the review to the files.
Return: how many items you checked; every defect you fixed (file, lines, kind, the text before, the text after, and the evidence in one sentence). kind is "wrong" for a false statement, "missing" for an important fact that was left out, "unclear" for a plain-English defect, "format" for a format defect. List under unresolved what you could not settle. verdict: "clean" when you changed nothing, "fixed" when you fixed all you found, "needs-rework" when the file needs more work than you could do.`
}

async function verifyLoop(u, label, what, files) {
  const rounds = []
  for (let r = 1; r <= 2; r++) {
    const v = await agent(verifyPrompt(u, what, files, r, rounds), {
      label: `verify${r}:${label}`, phase: r === 1 ? 'Verify' : 'Re-verify', schema: VERDICT,
    })
    rounds.push(v)
    if (!v) break
    const wrong = v.defects.filter(d => d.kind === 'wrong').length
    const missing = v.defects.filter(d => d.kind === 'missing').length
    log(`${label}: check ${r}: ${v.items_checked} items, ${wrong} wrong, ${missing} missing, ${v.defects.length - wrong - missing} other, verdict ${v.verdict}`)
    if (wrong === 0 && missing < 2 && v.verdict !== 'needs-rework') break
  }
  return rounds
}

async function runSmall(u) {
  const a = await agent(smallPrompt(u), { label: `annotate:${u.id}`, phase: 'Annotate', schema: ANNOT })
  const files = (a && a.files_written && a.files_written.length) ? a.files_written : [`the files T/ann/<key>.overview.json and T/ann/<key>.c<NN>.json of every key of the unit ${u.id}`]
  const v = await verifyLoop(u, u.id, 'the overview and annotation files of this unit', files)
  return { id: u.id, type: u.type, annotate: a, verify: v }
}

async function runData(u) {
  const a = await agent(dataPrompt(u), { label: `explain:${u.id}`, phase: 'Annotate', schema: ANNOT })
  const files = (a && a.files_written && a.files_written.length) ? a.files_written : [`the files named in "outputs" of the unit ${u.id}`]
  const v = await verifyLoop(u, u.id, 'the data explanation files of this unit', files)
  return { id: u.id, type: u.type, annotate: a, verify: v }
}

async function runBig(u) {
  const ov = await agent(overviewPrompt(u), { label: `overview:${u.id}`, phase: 'Annotate', schema: ANNOT })
  const chunks = await parallel(u.ranges.map((rg, i) => async () => {
    const nn = String(i + 1).padStart(2, '0')
    const a = await agent(chunkPrompt(u, i, rg), { label: `annotate:${u.id}.c${nn}`, phase: 'Annotate', schema: ANNOT })
    const v = await verifyLoop(u, `${u.id}.c${nn}`, `the annotation file of chunk ${i + 1} (lines ${rg[0]} to ${rg[1]}) of this unit. The chunk writers follow the "chunk_extra" instructions of the unit entry. Check only this chunk file; do not edit the overview`, [`${T}/ann/${u.key}.c${nn}.json`])
    return { chunk: i + 1, range: rg, annotate: a, verify: v }
  }))
  const words = chunks.filter(Boolean).flatMap(c => (c.annotate && c.annotate.new_words) || [])
  const wordNote = words.length
    ? `the overview file of this unit. The chunk writers asked for these words to be added to its "words" list; add each one that is correct and not yet there, with a definition that you checked: ${JSON.stringify(words)}`
    : 'the overview file of this unit'
  const ovv = await verifyLoop(u, `${u.id}.overview`, wordNote, [`${T}/ann/${u.key}.overview.json`])
  return { id: u.id, type: u.type, overview: ov, chunks, overview_verify: ovv }
}

const results = await parallel(units.map(u => () => (u.type === 'big' ? runBig(u) : u.type === 'data' ? runData(u) : runSmall(u))))
const out = results.map((r, i) => r || { id: units[i].id, failed: true })
return { group, units: out }
