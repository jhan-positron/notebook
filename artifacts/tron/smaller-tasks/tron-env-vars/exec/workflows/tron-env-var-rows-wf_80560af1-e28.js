export const meta = {
  name: 'tron-env-var-rows',
  description: 'Condense the verified inventory into document rows (28 chunks), then adversarially check every row against the code',
  phases: [
    { title: 'Write', detail: 'one writer per chunk turns verified records into short exact rows' },
    { title: 'Check', detail: 'a fresh checker per chunk tries to refute every cell against the code and fixes it' },
  ],
}

const ROOT = args.root
const WORK = args.work
const CHUNKS = args.chunks

const COMMON = `
You work on README.environment.md, the one reference list of every environment variable that TRON uses.
TRON is the positron-ai/tron repository: LLM inference on FPGA cards.
Readers of the document:
 (1) Support engineers who run TRON on customer and lab servers. They are not TRON developers. They act on what a row says.
 (2) All TRON developers. They will add a row for each new variable later, so every row must be a model of the expected quality.
A wrong default or a wrong accepted value in a row causes real harm. Every fact must come from the code in the checkout.

Checkout: ${ROOT}  (read-only snapshot of main at commit 7eddde7895)
Hard rules: do NOT modify anything inside the checkout; do NOT build, run tests, run repository scripts or start workloads; only read. Do not use "cd" in shell commands; use absolute paths or "git -C ${ROOT} ...". Write only the output file named in your task.

ROW FORMAT. The output file is JSON:
{ "chunk": "<id>", "rows": [ <one object per variable> ], "new_terms": [ { "term": "...", "definition": "..." } ], "notes": "..." }

Fields that every row has:
 "name": the variable name, exact case.
 "drop": false. Set true only when the name is not an environment variable in scope after all (for example a Nix attribute that never reaches a process environment). Then give "drop_reason" and leave other fields empty.
 "read_by": who reads it. Program names in backticks, then the main source files in parentheses and backticks. At most 3 files, then "and N more files". Example: "\`rinzler\`, \`runtron\` (\`src/system/memory.cpp\`)". If nothing in TRON reads it, write "Nothing in TRON." and then who TRON sets it for, for example "Nothing in TRON. \`flake.nix\` exports it for cargo."
 "values": accepted values and how the text is parsed. At most 30 words. Example: "Integer, parsed with \`atoi\`. Text that is not a number counts as \`0\`."
 "default": behaviour when the variable is unset. Start with "Unset:". Add "Empty:" only when an empty value behaves differently from unset. At most 25 words.
 "effect": what changes when it is set. 1 to 3 short sentences, at most 50 words.
 "notes": interactions and limits. At most 45 words. Empty string when there is nothing to add.
 "evidence": 1 to 4 objects { "site": "path:line", "quote": "exact text of that source line, at most 120 characters" } that prove values, default and effect. Copy the quote from the file as it is in the checkout. A checker will open each site.

STYLE RULES for every text field:
 - Plain short sentences. One claim per sentence. No idioms, no metaphors, no uncommon words.
 - Do not chain clauses with "because", "since", "which means" or a semicolon. Split the sentence.
 - Present tense. Say exactly what the code does. Do not state an intention that the code does not show. Do not write "probably", "typically" or "should".
 - Every number carries a unit: "48 hugepages of 1 GiB each", "30 seconds", "4 slots".
 - Code names in backticks: variables, flags, files, functions, and values a person types (\`1\`, \`true\`).
 - No line numbers outside "evidence". Line numbers go stale.
 - No "|" character and no line break inside any field. The fields become cells of a Markdown table.
 - Use the glossary terms below as they are. If you need another project term, define it in a short clause in the cell and add it to "new_terms".
 - Do not write "see the code". Do not mention this task, agents, records or inventories.
 - Respect the word limits. A shorter exact cell is better than a long one.

GLOSSARY (terms the document defines once, near its top; use them without redefining):
 rinzler: the TRON server program. It serves an OpenAI-compatible HTTP API.
 runtron: the TRON command-line program. It runs a model without the server.
 rinzler_proxy: a test build of rinzler. It replays recorded tokens and needs no FPGA card.
 libtron, libpos: the TRON core library and the FPGA driver library that the programs link.
 instance: one rinzler or runtron process that owns a fixed share of the server (FPGA cards, CPU cores, memory). The option \`--instance id,count\` selects the share.
 FPGA card: the accelerator card that runs the matrix operations of the model.
 bitfile: the FPGA image that is loaded into a card.
 hugepage: a memory page of 1 GiB that the programs use for FPGA buffers.
 NUMA node: one CPU package with its own memory.
 KV cache: the stored attention keys and values of tokens that were already processed.
 hardware attention, software attention: attention computed on the FPGA cards, or on the CPU.
 FUSE stats: run-time statistics that rinzler and runtron publish as files through a FUSE mount.
 Perfetto: the tracing system that TRON uses to record timing events.
 Dice: the daemon and client that queue work and grant FPGA slots on a shared server.
 slot: one equal share of a server that Dice can grant.
 Slice: the test launcher (\`bin/slice\`). It spreads tests over instances.
 LSF: the batch scheduler that Distributed Dice and remote builds submit jobs to.
 platformd: the Positron service manager that starts rinzler instances on production systems. It is not part of this repository.
 ingest: the pipeline that converts a PyTorch model into TRON model code.
 gen/: the build output directory of the repository.
 Nix dev shell: the development environment that \`nix develop\` starts.
 CI: the GitHub Actions workflows under \`.github/workflows\`.
`

const SECTION_RULES = {
  runtime: `SECTION: runtime. These variables are read by the product programs and libraries (rinzler, runtron, rinzler_proxy, libtron, libpos, the Rust crates they link). This is the section that support engineers use most.
Extra fields for every row:
 "topic": exactly one of:
   "system"     - devices, instances, CPU cores, hugepages, startup checks
   "weights"    - where model files, weight caches and resource maps are found
   "memory"     - heap, allocator, KV cache size, token books
   "attention"  - choice and tuning of the attention path
   "generation" - speculation, draft trees, scheduling, chunk limits, timing models
   "server"     - rinzler HTTP behaviour, prompt rendering, save_tokens, run files
   "tokenizer"  - tokenizer choice and validation
   "logging"    - log level, log files, log content
   "stats"      - FUSE stats, counters, hardware sampler
   "tracing"    - Perfetto and other trace output
 "for": "operators" when a support engineer or an operator may reasonably set it on a deployed system (tuning, paths, feature switches, logging). "developers" when it exists for debugging, experiments, tests or fault injection, and nobody should set it on a customer system without engineering advice. Decide from the code, its comments, and the "rederive" record (audience, audience_reason).
For "notes" in this section, include when they exist: the command-line flag that does the same thing or that overrides the variable; interaction with other variables; how to see the value in effect (the exact log text or stats file, from "rederive.how_to_check" after you confirm it in the code).
State exactly what an invalid value does when the code handles it (rejects at startup, logs and ignores, counts as 0).`,

  dispatch: `SECTION: dispatch. Variables of Dice, Slice and the launcher wrappers \`bin/rinzler\` and \`bin/runtron\`, including the variables that Dice sets for the programs it starts.
Extra fields for every row:
 "group": exactly one of "dice" (daemon and client settings), "dice-grant" (set by Dice for the program it starts; describes the grant), "dice-lsf" (Distributed Dice over LSF), "dice-test-hooks" (overrides that only tests may use), "slice", "wrappers".
 "who_sets": who normally sets it, at most 12 words. Examples: "A person, by hand." "The Dice daemon." "\`bin/slice\`, for each test it starts."`,

  tools: `SECTION: tools. Variables of developer tools and scripts that are not CI-only: benchmark and load tools, Perfetto capture tools, ingest tools, coverage tools, lint helpers.
Extra fields for every row:
 "group": exactly one of "load-test" (request generators and benchmark clients), "benchmark", "perfetto", "ingest", "coverage", "lint", "hardware-tools", "other".
 "who_sets": who normally sets it, at most 12 words.`,

  build: `SECTION: build. Variables read at configure or build time by the GNUmakefile, CMake, the Nix files, remote build helpers and packaging scripts.
Extra fields for every row:
 "group": exactly one of "make" (GNUmakefile inputs), "remote-build" (LSF remote build and remote execution switches), "cmake", "nix", "ingest-build", "packaging".
 "who_sets": who normally sets it, at most 12 words.
For a Make variable, say in "values" or "notes" whether a command-line assignment (make NAME=value) also works, when the code shows it.`,

  tests: `SECTION: tests. Variables that only test code reads, or that only matter while tests run.
Extra fields for every row:
 "hand_set": true when a person or a CI job sets it to steer or enable tests (paths to model files, opt-in switches, the binary under test, stress factors). false when only a test sets it for its own helper process (a fake program, a stub, a fixture, a marker) and nobody sets it by hand.
 "group": for hand_set true, one of "models" (paths to model or tokenizer files), "hardware" (FPGA and memory tests), "proxy" (rinzler_proxy tests), "tool-tests" (tests of Dice, Slice, CI scripts), "other". For hand_set false, use "fixture".
 "set_in": for hand_set false, the test file that sets it (one path in backticks). Empty string otherwise.
For hand_set false rows: "effect" states the purpose in at most 18 words; "values" and "default" may be empty strings; "read_by" names the helper file that reads it.`,

  ci: `SECTION: ci. Variables that only matter inside CI jobs: GitHub Actions workflows and the scripts under \`bin/ci\`.
Extra fields for every row:
 "source": exactly one of
   "repository variable" - a GitHub repository variable (vars.NAME);
   "repository secret"   - a GitHub secret (secrets.NAME);
   "workflow env"        - an env: entry at workflow or job level with the value written in the YAML;
   "step env"            - set for one step, usually from an expression or a previous step output;
   "runner"              - provided by the runner machine or its service configuration;
   "script"              - a script variable with a default that the caller can override.
 "who_sets": the workflow or script files that set it, in backticks, at most 3 then "and N more".
"read_by" names the scripts or workflow steps that read it. "values" may merge the usual value written in the workflow. Keep "effect" at most 35 words.`,

  external: `SECTION: external. Variables that other software defines (the operating system, GitHub Actions, compilers, build tools, Python, libraries) and that TRON code reads or sets.
Extra fields for every row:
 "defined_by": the software that defines the variable, short. Examples: "POSIX shell", "GitHub Actions", "cargo", "Nix", "CMake", "GNU Make", "Python", "pytest", "Hugging Face libraries", "LSF", "ccache", "sudo", "glibc".
 "tron_use": exactly one of "reads", "sets", "reads and sets", "unsets".
 "group": exactly one of "os" (shell, user, locale, temporary directories, time zone), "github-actions", "build-tools" (make, cmake, ninja, compilers, cargo, rustc, ccache, nix, cabal, ghc), "python" (python, pytest, uv, coverage), "ml-libraries" (Hugging Face, transformers, tokenizers, OpenMP), "network" (proxy variables), "sanitizers" (sanitizer and coverage run times), "lsf", "tracing", "other".
"read_by" lists the TRON files that read or set it. "effect" says what TRON does with the value, or why TRON sets it, in at most 35 words. "values" and "default" describe only what TRON code depends on; they may be empty strings when TRON only passes the variable on. Do not explain the general meaning of a well-known variable at length.`,
}

const WRITE_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    rows: { type: 'integer' },
    dropped: { type: 'array', items: { type: 'string' } },
    opened_code_for: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'rows', 'dropped', 'opened_code_for', 'notes'],
}

const CHECK_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    rows: { type: 'integer' },
    changed: { type: 'array', items: { type: 'string' } },
    dropped: { type: 'array', items: { type: 'string' } },
    unresolved: { type: 'array', items: { type: 'string' } },
    source_bugs: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'rows', 'changed', 'dropped', 'unresolved', 'source_bugs', 'notes'],
}

function writePrompt(c) {
  return `${COMMON}
${SECTION_RULES[c.section]}

YOUR TASK: write the rows of chunk "${c.id}" (${c.n} variables).

Input: ${WORK}/chunks/${c.id}.in.json. It is a JSON list with one record per variable. Each record holds:
 - "entries": facts collected per source area by a sweep agent and corrected by a verifier (area, role, owner, audience, readers, setters, values, default, effect, notes, confidence).
 - "rederive": present for variables that product C, C++ or Rust code reads. It is an independent third derivation, with empty_value, invalid_value, interactions and how_to_check.
 - "conflicts": findings of a cross-area critic where two areas described the variable differently.
 - "set_only_reader": for names that nothing in TRON reads, who reads them.
 - "stale_docs", "doc_mentions": what the existing documentation says.
The records were checked against the code, but they are long and they sometimes disagree. Produce one short exact row per variable.

Method:
1. Read the whole input file.
2. For each variable, decide the facts. OPEN THE CODE whenever entries disagree, a "conflicts" finding exists, a field says "not determined", a confidence is not "high", or you are not sure that a condensed sentence is still exact. Prefer what the code says over any record.
3. When a variable behaves differently in different readers (for example the C++ program and a Python wrapper parse it differently), say so in the row in plain words. Do not average the behaviours.
4. Write the file ${WORK}/chunks/${c.id}.rows.json and validate it: python3 -m json.tool ${WORK}/chunks/${c.id}.rows.json > /dev/null
5. Check your own file with a small script: every variable of the input has exactly one row; no field contains "|" or a line break; the word limits hold.
6. Return the summary. "opened_code_for" lists the variables for which you read source code.`
}

function checkPrompt(c, w) {
  const strict = ['runtime', 'dispatch', 'tools', 'build'].includes(c.section)
  return `${COMMON}
${SECTION_RULES[c.section]}

YOUR TASK: check and correct the rows of chunk "${c.id}" (${c.n} variables). Another agent wrote them. Assume that some cells are wrong, too broad, or vague, and find them. You succeed when a support engineer can act on every row without being misled.

Inputs:
 - The rows: ${WORK}/chunks/${c.id}.rows.json
 - The records the writer used: ${WORK}/chunks/${c.id}.in.json
 - The checkout.
Writer notes: ${w.notes ? w.notes.slice(0, 1500) : '(none)'}

For EVERY row:
1. Open each "evidence" site. Confirm that the quote is on that line (or within 3 lines) and that it supports the row. Replace wrong evidence.
2. ${strict
    ? 'Read the surrounding code yourself and try to REFUTE each cell. Is the text really parsed the way "values" says? Does an empty value behave like unset? What does an invalid value do? Does a command-line flag or another variable override it? Does the effect happen only under a condition that the row omits? Is there another reader in the checkout (git grep the name) that behaves differently and that the row does not mention?'
    : 'Compare each cell with the record. Open the code when the row and the record differ, when the record has a confidence that is not "high", when a "conflicts" finding exists, or when a cell claims something the record does not say. Also run git grep for the name and confirm that the files in "read_by" exist and contain it.'}
3. Check that the files named in "read_by" (and "set_in", "who_sets") exist in the checkout and contain the name.
4. Check the section fields (topic, for, group, hand_set, source, defined_by, tron_use) against their definitions.
5. Check the style rules and the word limits. Rewrite cells that break them. Keep the meaning exact.
6. Every variable of the input file must have exactly one row. Write a missing row yourself.
7. A row marked "drop": confirm the reason in the code, or restore the row.

Then write the corrected file to ${WORK}/chunks/${c.id}.final.json. Same format as the rows file, plus a top-level array
 "changes": [ { "name": "...", "field": "...", "was": "...", "now": "...", "why": "what the code says, with path:line" } ]
Validate it: python3 -m json.tool ${WORK}/chunks/${c.id}.final.json > /dev/null
Run a small script on your file: one row per input variable; no "|" and no line break in any field; word limits hold.

Return the summary. "changed" lists the names whose rows you changed in meaning (not pure wording). "unresolved" lists facts you could not settle, each with the measurement or source that would settle it. "source_bugs" lists places where the SOURCE itself looks wrong or misleading (a comment that contradicts the code, a variable that is set and never read, documentation that names a variable nothing reads), each with path:line. Do not fix the source.`
}

log(`${CHUNKS.length} chunks, ${CHUNKS.reduce((a, c) => a + c.n, 0)} variables; every chunk gets a writer and a checker (${CHUNKS.length * 2} agents)`)

const results = await pipeline(
  CHUNKS,
  c => agent(writePrompt(c), { label: `write:${c.id}`, phase: 'Write', schema: WRITE_SCHEMA }),
  (w, c) => {
    if (!w) { log(`writer of ${c.id} returned nothing`); return null }
    return agent(checkPrompt(c, w), { label: `check:${c.id}`, phase: 'Check', schema: CHECK_SCHEMA })
      .then(k => ({ id: c.id, section: c.section, n: c.n, write: { rows: w.rows, dropped: w.dropped, opened: w.opened_code_for.length }, check: k }))
  },
)

const done = results.filter(Boolean)
const failed = CHUNKS.filter(c => !done.some(d => d.id === c.id && d.check)).map(c => c.id)
if (failed.length) log(`CHUNKS WITHOUT A CHECKED RESULT: ${failed.join(', ')}`)

return {
  failed,
  chunks: done.map(d => ({
    id: d.id, n: d.n, written: d.write.rows, writerOpenedCodeFor: d.write.opened,
    checkedRows: d.check ? d.check.rows : null,
    changed: d.check ? d.check.changed : [],
    dropped: d.check ? d.check.dropped : d.write.dropped,
    unresolved: d.check ? d.check.unresolved : [],
    source_bugs: d.check ? d.check.source_bugs : [],
    notes: d.check ? d.check.notes.slice(0, 600) : '',
  })),
}
