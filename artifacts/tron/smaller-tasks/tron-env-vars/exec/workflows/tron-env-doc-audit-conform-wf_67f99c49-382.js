export const meta = {
  name: 'tron-env-doc-audit-conform',
  description: 'Blind audit of all 405 per-variable rows against the code, with reviewer findings applied and every row brought within the house rules',
  phases: [
    { title: 'Audit', detail: '34 agents, 12 rows each: re-derive from code, grade, correct, conform, validate' },
  ],
}

const ROOT = args.root
const WORK = args.work
const CHUNKS = args.chunks

const SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    validator: { type: 'string' },
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          verdict: { type: 'string', enum: ['correct', 'imprecise', 'wrong'] },
          changed: { type: 'boolean' },
        },
        required: ['name', 'verdict', 'changed'],
      },
    },
    unresolved: { type: 'array', items: { type: 'string' } },
    label_doubts: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'validator', 'rows', 'unresolved', 'label_doubts', 'notes'],
}

function prompt(c) {
  return `You are the last checker of ${c.n} rows of README.env-vars.md, a new reference file in the positron-ai/tron repository (Tron: LLM inference on FPGA cards). The file lists the environment variables that the source code reads or sets. Support engineers act on its rows, and all developers will copy the style of its rows. After you, the rows go into a pull request.

Checkout: ${ROOT}  (main at commit 7eddde7895; read-only for you)
The whole document, for context (read its top through "How to set a variable", about 330 lines): ${WORK}/README.env-vars.md
Your rows: ${WORK}/audit2/${c.id}.in.json
  It holds "rows": each with "name", "section", "table", "columns" (the table header), "cells" (the present text of each cell, exactly as rendered) and "hints".
  "hints" are findings of earlier reviewers about that row: a blind audit, a support-engineer reader, a developer reader, a plain-English check, a glossary check and a repository-conventions check. A hint can be wrong. Check each one against the code before you use it. A "suggested" text in a hint is a proposal, not a fact.

Hard rules: do NOT modify anything inside the checkout. Do NOT build, run tests, run repository scripts or start workloads. Only read (Read, grep, git grep, sed -n). Do not use "cd" in shell commands; use absolute paths or "git -C ${ROOT} ...". Write only your output file. You may run the validator named below; it is outside the checkout.

DO THIS FOR EVERY ROW

Step 1, audit (blind first). Before you trust the row, derive the facts yourself from the code: find every read and every set of the variable (git grep the name, follow helper functions and constants that hold the name), read the code around them, and work out who reads it, how the text is parsed, what happens when it is unset, empty or invalid, what the value changes, and what overrides or interacts with it. Then grade the PRESENT row:
 - "wrong": a statement contradicts the code, or a reader who follows the row gets a result that the row does not predict.
 - "imprecise": nothing contradicts the code, but a statement is vague, misses a condition that changes the outcome, or names a file that is not a main reader.
 - "correct": every statement holds.
 A missing detail that does not change what a reader would do is not a problem.

Step 2, rewrite the cells where needed. Fix what the audit found. Apply the hints that the code confirms. Then make the row follow the house rules below. Keep every cell that is already correct and within the rules exactly as it is: do not reword for taste. Set "changed" to true only when you changed at least one cell.

HOUSE RULES
 1. The whole row is at most 1,000 characters, counted as: | \`NAME\` | cell | cell | ... |. When a row is longer, remove the least important facts first: facts that only explain the code, facts about tests in a row about a product variable, history, second examples. Never remove: how the text is parsed, the behaviour when unset, the main effect, what overrides the variable, and what a wrong value does.
 2. Plain short sentences, one fact in each. Present tense. No idioms or metaphors. No "because", "since", "which means" chains and no semicolons: split the sentence. No vague words (typically, usually, normally, often, probably). American spelling (behavior, color, optimized).
 3. Every number has a unit.
 4. Code names in backticks: variables, options, files, functions, values a person types.
 5. No line numbers. No counts of files, tests, jobs, steps or workflows ("and other files", never "and 5 more files"; "the workflows that set it", never "all 5 workflows").
 6. Do not write about source comments ("A source comment says ..."). When the code itself shows the behaviour, state the behaviour. Otherwise delete the sentence.
 7. Quoted log lines and error texts: allowed in sections 1 and 2 only, and only when the quoted text is in the source as written (check with git grep -F; a text built from a format string may show the placeholder as <value>). In sections 3 to 7 do not quote workflow step names, issue titles or test error texts; describe them in plain words.
 8. Do not write pinned version numbers of tools (Python, uv, cabal, ruff and similar). Point to \`README.dependencies.md\` for the pinned value.
 9. Say "command-line option" or "option", never "flag". Write the project name as "Tron". The exception is a variable name such as \`TRON_LOG_DIR\`.
10. Terms. The document defines these terms once, in "Words used here" (read that list in the document). Use them without a definition, and REMOVE a definition of one of them from inside a cell: rinzler, runtron, rinzler_proxy, rinzler_host, libtron, libpos, platformd, FPGA card, bitfile, instance, physical slice, hugepage, NUMA node, resource map, arena allocator, legacy allocator, forward pass, minibatch, scheduler, token tree, KV cache, KV book, hardware attention, software attention, shared thread pool, main helper, attention worker, speculative decoding, draft model, draft tree, Python tokenizer, Rust tokenizer, Harmony, save_tokens, debug log line (log levels), FUSE stats, Perfetto, traced, traced_probes, Dice, slot, shared host, legacy host, submission, grant, Slice, launcher wrappers, LSF, Distributed Dice, remote build, LSF worker, Slice cost-data refresh, fake, stub, ingest, gen/, Nix dev shell, CI, and the parse functions atoi, atol, atof, stof, stoul, stoull, stoll, from_chars, strcmp. Any OTHER project term needs a short definition in a clause inside the cell.
11. Cell contents by column:
   - "For" (section 1 only): do NOT change it. If you believe the label is wrong, say so in "label_doubts" with your reason and the path:line. Meaning: Operators = the packaged service uses the variable, or another Tron document describes it for deployed systems. Developers = every other variable of section 1.
   - "Read by": program names in backticks, then the main source files in parentheses and backticks, at most 3 files, then "and other files". When nothing in Tron reads the name, start with "No reader in Tron." and then say who Tron sets it for.
   - "Set by": the person, program or file that sets the variable. Short.
   - "Values and default": the accepted values and how the text is parsed. Then "Unset:" and the behaviour when the variable is not set. Add "Empty:" only when an empty value behaves differently from unset. State what an invalid value does when the code handles it or when it ends the process.
   - "Effect": the first sentence says what the variable changes. Then what overrides it or interacts with it (command-line options, other variables). Then what a wrong value does, when not already in "Values and default". In section 1 only, when a log line, a FUSE stats file or a command shows the value in effect, end with "Check:" and that text. Leave out facts that only explain the code.
   - Section 7 columns: "Defined by" (the software that defines the name), "Tron" (exactly one of Reads, Sets, Reads and sets, Unsets), "Where" (the Tron files that read, set or unset it; start with "No reader in Tron." when Tron only sets or unsets it), "What Tron does with it" (at most 40 words: what Tron does with the value, or why Tron sets it; do not explain the general meaning of a well-known variable).
12. No "|" character and no line break in a cell. Do not mention this task, reviewers, hints, agents or audits.
13. A row whose variable has no effect on \`rinzler\` or \`runtron\` although it sits in section 1 starts its "Effect" cell with "No effect on \`rinzler\` or \`runtron\`."

OUTPUT. Write JSON to ${WORK}/audit2/${c.id}.json:
{ "rows": [ {
    "name": "...",
    "verdict": "correct" | "imprecise" | "wrong",        (grade of the PRESENT row, before your changes)
    "problems": [ { "cell": "...", "statement": "...", "code_says": "...", "site": "path:line" } ],
    "changed": true | false,
    "cells": { "<column name>": "final text", ... },      (EVERY column of the row except "Variable", also the unchanged ones)
    "evidence": [ "path:line - what it proves", ... ]      (the lines you read for this row; at least one per row)
  } ],
  "unresolved": [ "NAME - the fact you could not settle, and the measurement or source that would settle it" ],
  "label_doubts": [ "NAME - present label - your reason - path:line" ],
  "notes": "..." }

Then run the validator and fix your file until it prints OK:
  python3 ${WORK}/rowcheck.py ${WORK}/audit2/${c.id}.json
The validator checks the length limit, the forbidden forms of rules 5, 6, 9 and 12, the spelling, and that no row or cell is missing. It does not check facts. You do.

Return the summary: "validator" is the last line the validator printed; "rows" gives the verdict and the changed mark per row.`
}

log(`${CHUNKS.length} agents audit and conform ${CHUNKS.reduce((a, c) => a + c.n, 0)} rows`)

const results = await parallel(CHUNKS.map(c => () =>
  agent(prompt(c), { label: `audit:${c.id}`, phase: 'Audit', schema: SCHEMA })
    .then(r => r ? { id: c.id, n: c.n, ...r } : null)))

const done = results.filter(Boolean)
const failed = CHUNKS.filter(c => !done.some(d => d.id === c.id)).map(c => c.id)
if (failed.length) log(`CHUNKS WITHOUT A RESULT: ${failed.join(', ')}`)
const all = done.flatMap(d => d.rows)
const tally = { correct: 0, imprecise: 0, wrong: 0 }
for (const r of all) tally[r.verdict] = (tally[r.verdict] || 0) + 1
const changed = all.filter(r => r.changed).length
log(`graded ${all.length} rows: ${tally.correct} correct, ${tally.imprecise} imprecise, ${tally.wrong} wrong; ${changed} rows changed`)

return {
  failed,
  graded: all.length,
  tally,
  changed,
  notOk: done.filter(d => !/OK/.test(d.validator)).map(d => ({ id: d.id, validator: d.validator })),
  wrong: all.filter(r => r.verdict === 'wrong').map(r => r.name),
  unresolved: done.flatMap(d => d.unresolved),
  label_doubts: done.flatMap(d => d.label_doubts),
}
