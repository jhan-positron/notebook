export const meta = {
  name: 'tron-env-var-inventory',
  description: 'Inventory every environment variable used by TRON at main 7eddde7895: sweep 13 areas, independently verify each, then run whole-tree critics',
  phases: [
    { title: 'Sweep', detail: 'one agent per area lists every variable with facts from the code' },
    { title: 'Verify', detail: 'a fresh agent per area resolves scan differences, hunts for misses, corrects wrong facts' },
    { title: 'Critic', detail: 'whole-tree hunts for missing names, cross-area flows, and re-derivation of runtime variables' },
  ],
}

const ROOT = args.root
const WORK = args.work
const AREAS = args.areas
const CODE_AREAS = Object.keys(AREAS).filter(a => a !== 'docs')

const CTX = `
You are helping build the single reference document that lists every environment variable used by TRON.
TRON is the positron-ai/tron repository: LLM inference on FPGA cards. Main programs: rinzler (OpenAI-compatible server), runtron (command-line runner), rinzler_proxy (a test stand-in for rinzler), Dice and Slice (test dispatch tools under bin/), ingest tools, CI scripts.
All TRON developers and the support engineers will rely on the document. Every fact must come from the source code in the checkout. Never infer a fact from a variable's name or from memory.

Checkout: ${ROOT}
It is a read-only snapshot of main at commit 7eddde7895 (2026-11-21).

Hard rules:
- Do NOT modify anything inside the checkout. Do NOT build, do NOT run tests, do NOT run any script from the repository, do NOT start any workload. Only read (Read tool, grep, rg, git grep, sed -n, python3 for text processing of files you read).
- Do not use "cd" in shell commands. Use absolute paths or "git -C ${ROOT} ...".
- Write only the one output file named in your task. Do not create other files outside your scratch directory.
- The gen/ and build/ directories do not exist in this snapshot. Ignore generated code, with one exception: if a code generator or a template in your files EMITS code that reads an environment variable, report the variable and say which generated program reads it.

What counts as an environment variable for this inventory:
(a) READ. Any name whose value TRON code takes from the process environment. Examples of read mechanisms:
  - C/C++: getenv, secure_getenv, std::getenv, called directly or through a helper function, a macro, a constexpr name, or a table of names; scans of environ/envp; library calls that read the environment for TRON (for example spdlog::cfg::load_env_levels).
  - Rust: std::env::var, env!, option_env!.
  - Python: os.environ[...], os.environ.get, os.getenv, "X in os.environ", names held in module constants (for example NAME_ENV = "DICE_X" then os.environ.get(NAME_ENV)), argparse defaults taken from the environment, click envvar=.
  - Shell: $NAME or \${NAME...} where NAME is NOT assigned earlier in the same script, so the value comes from the caller. Especially \${NAME:-default}, \${NAME:?message}, : "\${NAME:=x}".
  - Make: variables the environment can supply: "NAME ?= value", "$(NAME)" that the makefile never assigns, "ifdef NAME", "$(origin NAME)".
  - CMake: $ENV{NAME}; CMakePresets "environment" blocks, $env{NAME}, $penv{NAME}.
  - Nix: builtins.getEnv.
  - GitHub Actions: env.NAME, vars.NAME, secrets.NAME, and runner-provided variables that repository scripts read.
  - systemd: \${NAME} or $NAME expansion in unit files, EnvironmentFile= loading.
(b) SET-ONLY. A name that TRON code sets, exports, or passes to a child process or a library, when no code in YOUR files reads it: setenv, putenv, os.environ[...] = value, env= dictionaries for subprocess, "export NAME=", "NAME=value command", CMake test ENVIRONMENT properties, Nix shellHook or makeWrapper --set, systemd Environment=, workflow "env:" blocks. These matter because a third-party library or another TRON program reads them.
Not in scope: CMake cache variables and -D options, C preprocessor macros, Python constants, command-line flags, and shell variables that the script assigns before use and never exports (pure locals). A shell or Make variable with a default form (\${X:-...}, X ?= ...) IS in scope, because the caller's environment can override it.

Audience values (pick the best one):
- operator: changes the behaviour of a deployed program or service (rinzler, runtron, rinzler_proxy, tokenizer sidecar, Dice daemon, FUSE stats, packaged systemd units). A support engineer or a person who runs the system may need to set or check it. Includes performance and memory tuning, feature switches, paths, logging.
- developer-debug: read by product code (not test code), but meant for debugging, tracing, experiments or fault injection.
- test: read only by test code (t/, *-tests directories), or only meaningful while running tests.
- tooling: read by developer, benchmark, ingest or trace tools and scripts that are not CI-specific.
- build: read at configure or build time (CMake, Make, Nix, cargo).
- ci: only meaningful inside CI jobs (GitHub Actions workflows, bin/ci).
- packaging: read by package install scripts or by the package build.

Owner values: "tron" for names TRON defines; "os" for standard names (HOME, PATH, USER, TMPDIR, SHELL, LANG, PWD, XDG_*); "github-actions" for GITHUB_*, RUNNER_*, CI; "third-party:<library or tool>" for names a library or tool defines (OMP_NUM_THREADS, MALLOC_CONF, HF_HOME, HF_TOKEN, CUDA_*, PYTHONPATH, CC, CXX, NIX_*, CARGO_*, CCACHE_*, LD_LIBRARY_PATH, SPDLOG_LEVEL, LSF names, and so on).

Output file format (JSON, UTF-8):
{
 "area": "<area name>",
 "variables": [
  {
   "name": "TRON_EXAMPLE",
   "role": "read" or "set_only",
   "owner": "tron",
   "audience": "operator",
   "readers": [ { "program": "rinzler", "site": "src/x.cpp:123", "mechanism": "std::getenv", "when": "once at startup" } ],
   "setters": [ { "site": "t/foo.cpp:45", "value": "1", "why": "forces the software path in the test" } ],
   "values": "exact accepted values and how the text is parsed, in plain words",
   "default": "exact behaviour when the variable is unset; say also what an empty value does when that differs",
   "effect": "one to three short plain sentences: what changes when it is set",
   "notes": "units, limits, interaction with flags or other variables, behaviour on a bad value; empty string if none",
   "confidence": "high" or "medium" or "low"
  }
 ],
 "wrappers": [ { "symbol": "env_flag", "site": "h/common/env.hpp:12", "description": "reads NAME with getenv and returns bool; callers pass the name" } ],
 "dynamic_sites": [ { "site": "path:line", "description": "the name is built at run time from ...; possible names: ..." } ],
 "files_skipped": [ "path - reason" ],
 "notes": "free text"
}
Field rules:
- "site" is path:line relative to the checkout root. Every site must exist and must really read or set that name.
- "program" names what reads it: a binary (rinzler, runtron, rinzler_proxy, a t_* test), a script path, a library (libtron, libpos), a workflow file, a makefile target.
- "when" is one of: "once at startup", "at static initialization", "once, on first use (cached)", "every call of <function>", "every request", "at configure time", "each run of the script", "unknown".
- "values" examples of the precision wanted: "any non-empty value enables it; the text is not parsed"; "integer parsed with atoi; 0 or non-numeric text means off"; "exactly the text 1 enables it; anything else is off"; "path to a directory"; "comma-separated list of ...".
- Give up to 6 reader sites and up to 4 setter sites per variable. If there are more, say how many in "notes".
- If you cannot determine a field, write "not determined: <what you looked at>" and set confidence to "low". Do not guess.
- Write plain short sentences. No idioms.
`

const SWEEP_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    names: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          role: { type: 'string', enum: ['read', 'set_only'] },
          audience: { type: 'string' },
          owner: { type: 'string' },
        },
        required: ['name', 'role', 'audience', 'owner'],
      },
    },
    wrappers: { type: 'array', items: { type: 'string' } },
    dynamic_sites: { type: 'array', items: { type: 'string' } },
    files_skipped: { type: 'integer' },
    notes: { type: 'string' },
  },
  required: ['out_file', 'names', 'wrappers', 'dynamic_sites', 'notes'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    names: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          role: { type: 'string', enum: ['read', 'set_only'] },
          audience: { type: 'string' },
          owner: { type: 'string' },
        },
        required: ['name', 'role', 'audience', 'owner'],
      },
    },
    added: { type: 'array', items: { type: 'string' } },
    removed: { type: 'array', items: { type: 'string' } },
    corrected: { type: 'array', items: { type: 'string' } },
    unresolved: { type: 'array', items: { type: 'string' } },
    wrappers: { type: 'array', items: { type: 'string' } },
    dynamic_sites: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'names', 'added', 'removed', 'corrected', 'unresolved', 'wrappers', 'dynamic_sites', 'notes'],
}

const DOCS_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    names: { type: 'array', items: { type: 'string' } },
    central_lists: { type: 'array', items: { type: 'string' } },
    deployment_facts: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'names', 'central_lists', 'deployment_facts', 'notes'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    out_file: { type: 'string' },
    missing: { type: 'array', items: { type: 'string' } },
    role_changes: { type: 'array', items: { type: 'string' } },
    disagreements: { type: 'array', items: { type: 'string' } },
    stale_docs: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['out_file', 'missing', 'role_changes', 'disagreements', 'stale_docs', 'notes'],
}

const AREA_HINTS = {
  'cpp-pos-system': 'C and C++ of the FPGA driver layer (pos), the hardware system layer (system), and common helpers. Known helpers to trace: src/pos/device.cpp:103 reads std::getenv(env_name); src/pos/perf.cpp:50 reads std::getenv(trace_categories_variable); tron::hardware::system::system_parse_env; SYSTEM_CONFIG handling. Find every caller and every name.',
  'cpp-tron': 'C and C++ of the tron core library (models, attention, heap, scheduler, stats, tracing). Known helpers to trace: read_arena_allocator_env, read_heap_shadow_env, parsed_hw_attn_env, hwattn_env_override, rtm_disabled_by_env, attn_stats::env_enabled, env_enabled. Many reads are in headers under h/tron.',
  'cpp-rinzler-runtron': 'C and C++ of the rinzler server, rinzler_proxy, runtron, and the Rust crates under rust/. Known helpers to trace: configure_system_start_date_from_env, load_golden_map_from_env, spdlog::cfg::load_env_levels, dice_grant_env_complete. Check startup code in src/rinzler.cpp and src/runtron.cpp line by line for environment reads.',
  'cpp-tests': 'C and C++ test code under t/. Tests both READ variables (to find models, select instances, skip) and SET variables to steer product code (setenv, scoped environment guards). For each set, name the product variable it steers. Test-only variables have audience "test".',
  'python-bin': 'Python programs under bin/ (not bin/ci): dice, slice, the bin/rinzler and bin/runtron launcher wrappers, dice-lsf-*, benchmark and trace tools. Many names are held in module constants such as _HOST_CONFIG_ENV, DICE_GRANT_ID_ENV, LSF_TERMINAL_OUTPUT_ENV: resolve every constant to its string value. Also record names these programs set for their child processes.',
  'python-ci': 'Python under bin/ci, bin/ci-tests and .github. Names held in constants and passed as function arguments (for example os.environ[variable], default=os.environ.get(variable)) must be resolved to the real names at every call site.',
  'python-rest': 'Python outside bin/: ingest/, perfetto/, t/ (including t/proxy), config/, doc/, datasets/, rust/, .agents/. Includes test harness code that sets variables for rinzler and rinzler_proxy.',
  'shell-bin': 'Shell scripts under bin/ (not bin/ci). List every variable a script takes from its caller environment.',
  'shell-ci': 'Shell scripts under bin/ci, bin/ci-tests and .github. There are many names here. List every variable a script takes from its caller environment, and say which workflow or caller normally provides it when the script or its comments say so.',
  'shell-rest': 'Shell scripts outside bin/, plus the GNUmakefile and other makefiles, packaging maintainer scripts, perfetto shell tools and lefthook hooks. For makefiles: "NAME ?= value", "$(NAME)" never assigned in the makefile, "ifdef NAME", "export NAME" and environment passed to recipes all count. The GNUmakefile is long: read all of it.',
  'build-ci': 'GitHub Actions workflows and actions under .github (YAML), CMake files, CMakePresets.json, flake.nix and nix/*.nix. For workflows: record repository variables (vars.X), secrets (secrets.X), and env: values that a script in the repository reads. A workflow env: value that is used only inside the same step is step-local: list it with a note "step-local". For CMake: $ENV{X} reads and test ENVIRONMENT properties (set-only for the test). For Nix: variables exported by dev shells and wrappers.',
  'pkg-config-misc': 'Everything else that is not Markdown: packaging/ (systemd units, descriptor files, conf files, Debian control and maintainer files without a shell shebang), config/ YAML and JSON, Haskell sources of the ingest pipeline (127 .hs files: use grep for getEnv, lookupEnv, System.Environment, and for C++ or Python text that the generator EMITS which reads the environment), TOML, cfg and other data files. For systemd units, record which file a person edits to set variables for the service (EnvironmentFile=) and every Environment= line.',
}

function sweepPrompt(area) {
  return `${CTX}

YOUR TASK: sweep area "${area}".
Scope hint: ${AREA_HINTS[area]}

The files of your area are listed, one path per line, in: ${WORK}/areas/${area}.files.txt (${AREAS[area]} files). Every file in that list is yours, and no other agent sweeps them. Cover all of them.

Method:
1. Find helper functions, macros, classes, constants and tables that read the environment first. A helper may be defined outside your files (for example under h/common, h/system, or a shared Python module). When your files call a function whose name suggests an environment read (env, getenv, flag, knob, option, setting, config), open its definition anywhere in the checkout and check. Then list every call site in your files with the real variable name.
2. Use several different searches over your file list, not one: the read mechanisms listed above, plus the set mechanisms. Then READ the code around each hit. A grep line alone is not enough to state the default, the accepted values or the effect.
3. Fill every field of every entry from the code. Follow the value to where it is used, so that "effect" says what really changes.
4. Write the JSON file to: ${WORK}/inventory/sweep/${area}.json
5. Validate it: python3 -m json.tool ${WORK}/inventory/sweep/${area}.json > /dev/null
6. Return the compact summary. "names" must list every variable in your file. "wrappers" is one string per helper: "symbol @ site - what it does". "dynamic_sites" is one string per site where a name is built at run time.

Completeness matters more than speed. A second agent will check your list against an independent scan and against the code, so do not pad it and do not skip the dull names.`
}

function verifyPrompt(area, sweep) {
  return `${CTX}

YOUR TASK: independently verify and correct the inventory of area "${area}". A first agent swept this area. Assume its list has both missing names and wrong facts, and find them.
Scope hint: ${AREA_HINTS[area]}

Inputs:
- File list of the area: ${WORK}/areas/${area}.files.txt (${AREAS[area]} files).
- The first agent's inventory: ${WORK}/inventory/sweep/${area}.json (${sweep.names.length} entries).
- A regular-expression scan of the whole checkout: ${WORK}/baseline.json. Its "names" object maps NAME to {"read": [sites], "set": [sites]}.
- The names that the scan found in your files but that are ABSENT from the first agent's list. Print them, with their sites, by running this helper (it lives outside the checkout, so running it is allowed): python3 ${WORK}/baseline_only.py ${area}
- Helpers the first agent reported: ${sweep.wrappers.length ? sweep.wrappers.join(' | ') : '(none)'}
- Run-time-built names the first agent reported: ${sweep.dynamic_sites.length ? sweep.dynamic_sites.join(' | ') : '(none)'}

Duties:
A. Resolve every absent name that the helper prints. Open the code at the printed sites, and decide. If it is in scope, add a full entry. If it is out of scope (for example a pure shell local, or a regex false match), record it under "rejected" with the reason.
B. Hunt for names that BOTH the first agent and the scan missed. Use methods the scan cannot do:
  - every call site of every helper, constant or table that carries a variable name;
  - reads with a non-literal argument, traced back to the callers;
  - for shell and Make: every uppercase $NAME / \${NAME} / $(NAME) that is used but never assigned in that file;
  - for Python: os.environ used as a mapping (copy, dict(os.environ), **os.environ, .items()) followed by lookups; env= dictionaries; argparse or click defaults;
  - for C/C++: constexpr or static const char* names, X-macro tables, string concatenation that builds a name;
  - usage text, --help strings and comments that claim a variable controls something: confirm the read exists, then add it. If the comment names a variable that nothing reads, record it under "notes".
C. Check EVERY entry of the first agent against the code: each site exists and really reads or sets that name; "values", "default", "effect", "when", "audience", "owner" and "role" are correct and exact. Rewrite what is wrong or vague. Remove entries that are out of scope (record them under "rejected"). Sample is not enough: check all ${sweep.names.length}.
D. Write the corrected full inventory to: ${WORK}/inventory/verified/${area}.json
   Same format as the input, plus two top-level arrays:
   "changes": [ { "name": "...", "change": "added" | "removed" | "corrected", "detail": "what was wrong and what the code says, with site" } ]
   "rejected": [ { "name": "...", "reason": "..." } ]
   Validate it: python3 -m json.tool ${WORK}/inventory/verified/${area}.json > /dev/null
E. Return the compact summary. "names" lists every variable in your corrected file. "added", "removed", "corrected" are lists of names. "unresolved" lists names you could not settle, each with a short reason. "wrappers" and "dynamic_sites" are the final lists as strings ("symbol @ site - what it does").

Do not copy the first agent's facts without opening the code. Do not modify the first agent's file.`
}

const docsPrompt = `${CTX}

YOUR TASK: sweep the documentation, area "docs". Your files are the ${AREAS.docs} Markdown files listed in ${WORK}/areas/docs.files.txt.
You do not look for reads in code. You record what the existing documentation already says about environment variables, so that the new reference can link to it and so that stale statements can be found.

Method:
1. Build candidate names: every token in your files that looks like an environment variable (uppercase with digits and underscores) and appears in an environment context: near the words "environment", "env", "export", "unset", in a NAME=value command example, or in a table of variables. Use ${WORK}/baseline.json ("names" keys) as a list of known names to search for, and also catch names that are not in it.
2. For each name, record every place that documents it and what the text claims (meaning, default, values).
3. Record every section that acts as a list of environment variables (file, heading, how many names).
4. Record every statement about HOW a variable is set on a deployed or packaged system: systemd unit, EnvironmentFile path, /etc files, platformd, posadm, wrapper scripts. Quote the file and line.
5. Write JSON to: ${WORK}/inventory/sweep/docs.json with this format:
{
 "area": "docs",
 "variables": [ { "name": "X", "mentions": [ { "site": "README.stats.md:120", "claim": "what the text says, short" } ] } ],
 "central_lists": [ { "site": "README.proxy.md:274", "heading": "Environment variables", "count": 8, "names": ["..."] } ],
 "deployment_facts": [ { "site": "path:line", "fact": "..." } ],
 "notes": "..."
}
   Validate it: python3 -m json.tool ${WORK}/inventory/sweep/docs.json > /dev/null
6. Return the compact summary: "names" = every documented name; "central_lists" and "deployment_facts" as one string each ("site - text").

CHANGELOG.md and changelog.d entries count as documentation too, but mark their claims "changelog".`

phase('Sweep')
log(`Sweeping ${CODE_AREAS.length} code areas plus docs; each code area gets an independent verifier (${CODE_AREAS.length * 2 + 1} agents before the critics)`)

const [codeResults, docsResult] = await parallel([
  () => pipeline(
    CODE_AREAS,
    area => agent(sweepPrompt(area), { label: `sweep:${area}`, phase: 'Sweep', schema: SWEEP_SCHEMA }),
    (sweep, area) => {
      if (!sweep) { log(`sweep of ${area} returned nothing; no verification possible`); return null }
      log(`${area}: sweep reported ${sweep.names.length} names`)
      return agent(verifyPrompt(area, sweep), { label: `verify:${area}`, phase: 'Verify', schema: VERIFY_SCHEMA })
        .then(v => v ? { area, sweepCount: sweep.names.length, ...v } : null)
    },
  ),
  () => agent(docsPrompt, { label: 'sweep:docs', phase: 'Sweep', schema: DOCS_SCHEMA }),
])

const verified = (codeResults || []).filter(Boolean)
const failedAreas = CODE_AREAS.filter(a => !verified.some(v => v.area === a))
if (failedAreas.length) log(`AREAS WITHOUT A VERIFIED RESULT: ${failedAreas.join(', ')}`)

// Union by name across areas.
const union = {}
for (const v of verified) {
  for (const n of v.names) {
    const u = union[n.name] || (union[n.name] = { name: n.name, areas: [], roles: [], audiences: [], owners: [] })
    u.areas.push(v.area); u.roles.push(n.role); u.audiences.push(n.audience); u.owners.push(n.owner)
  }
}
const unionNames = Object.keys(union).sort()
const readNames = unionNames.filter(n => union[n].roles.includes('read'))
const setOnlyNames = unionNames.filter(n => !union[n].roles.includes('read'))
log(`Union after verification: ${unionNames.length} names (${readNames.length} read somewhere, ${setOnlyNames.length} set-only everywhere)`)

const allWrappers = verified.flatMap(v => v.wrappers.map(w => `[${v.area}] ${w}`))
const allDynamic = verified.flatMap(v => v.dynamic_sites.map(w => `[${v.area}] ${w}`))
const docNames = docsResult ? docsResult.names : []
const docOnly = docNames.filter(n => !union[n])

phase('Critic')

const tokenCritic = `${CTX}

YOUR TASK: whole-tree completeness critic, method "token sweep". Twelve area agents and twelve verifiers produced an inventory. Find environment variables that are in scope but MISSING from it.

The verified inventories are in ${WORK}/inventory/verified/*.json (one file per area; "variables"[].name). The union has ${unionNames.length} names:
${unionNames.join(' ')}

Method (mechanical first, then judgement):
1. With a script, list every token in tracked non-Markdown text files (git -C ${ROOT} ls-files) that matches an uppercase name of two or more characters ([A-Z][A-Z0-9_]+) AND sits on a line with an environment cue: getenv, environ, setenv, putenv, unsetenv, "env" as a word or key, ENV{, export, \${NAME, $NAME inside shell or YAML run blocks, Environment=, EnvironmentFile=, vars., secrets., "?=" in makefiles. Remove the names already in the union. Count what is left.
2. Triage every remaining candidate by opening the code. Group obvious non-variables (macros, CMake cache variables, shell locals assigned in the same script, enum values) and reject them in bulk with one reason per group.
3. Also check names WITHOUT an underscore that the regex families tend to miss (HOME, USER, CI, DEBUG, REMOTE, VERBOSE, DISPLAY, TERM, EDITOR, PAGER, SHELL, TMPDIR, LANG and similar), and lowercase or mixed-case names (http_proxy, no_proxy and similar).
4. For each truly missing in-scope variable, write a full entry in the inventory format.
5. Write JSON to: ${WORK}/inventory/critic/token-sweep.json
   { "candidates_checked": <int>, "missing": [ <full entries, with an extra field "area_hint"> ], "rejected_groups": [ { "reason": "...", "count": <int>, "examples": ["..."] } ], "notes": "..." }
   Validate it with python3 -m json.tool.
6. Return: "missing" = list of "NAME - site - one line"; "role_changes", "disagreements", "stale_docs" may be empty lists; "notes" = counts and anything the document authors must know.`

const flowCritic = `${CTX}

YOUR TASK: whole-tree critic, method "cross-area flows and indirect reads". Twelve area agents and twelve verifiers produced an inventory, each looking at its own files only. Find what falls between areas.

The verified inventories are in ${WORK}/inventory/verified/*.json. The documentation sweep is in ${WORK}/inventory/sweep/docs.json.
Union: ${unionNames.length} names. Names that are set-only in EVERY area that reports them (${setOnlyNames.length}):
${setOnlyNames.join(' ')}
Names that the documentation mentions but the union lacks (${docOnly.length}):
${docOnly.join(' ') || '(none)'}
Helpers reported:
${allWrappers.join('\n') || '(none)'}
Run-time-built names reported:
${allDynamic.join('\n') || '(none)'}

Duties:
1. For every set-only name: search the WHOLE checkout for a reader in TRON code (any language). If TRON code reads it, report a role change with the reader site, values, default and effect. If no TRON code reads it, say who reads it (which third-party library or tool, or "nothing found") in one line.
2. For every documentation-only name: search the whole checkout. Either it is read (then it is missing from the inventory: write a full entry), or it is not read at this commit (then the documentation is stale: report file:line of the stale text).
3. For every helper and every run-time-built name: confirm that every call site in the whole checkout, in any area, is represented in the inventory. Report missing names with full entries.
4. Look for the same variable reported by two or more areas with DIFFERENT default, values or audience (read the verified files with a script and compare). Open the code and report which statement is right, or that the variable really behaves differently per reader (then say so precisely: the document needs both).
5. Write JSON to: ${WORK}/inventory/critic/flows.json
   { "role_changes": [ { "name": "...", "reader_site": "...", "values": "...", "default": "...", "effect": "...", "program": "..." } ],
     "set_only_readers": [ { "name": "...", "read_by": "third-party:... or nothing found" } ],
     "missing": [ <full entries with "area_hint"> ],
     "stale_docs": [ { "name": "...", "site": "...", "text": "..." } ],
     "conflicts": [ { "name": "...", "areas": ["..."], "finding": "..." } ],
     "notes": "..." }
   Validate it with python3 -m json.tool.
6. Return the compact lists as strings ("NAME - site - one line").`

// Runtime variables that people set on running systems get an independent re-derivation.
const RUNTIME_AREAS = ['cpp-pos-system', 'cpp-tron', 'cpp-rinzler-runtron']
const runtimeNames = unionNames.filter(n =>
  union[n].roles.includes('read') && union[n].areas.some(a => RUNTIME_AREAS.includes(a)))
const CHUNK = 14
const chunks = []
for (let i = 0; i < runtimeNames.length; i += CHUNK) chunks.push(runtimeNames.slice(i, i + CHUNK))
log(`Re-deriving ${runtimeNames.length} variables read by product C/C++/Rust code in ${chunks.length} chunks of up to ${CHUNK}`)

function rederivePrompt(names, i) {
  return `${CTX}

YOUR TASK: independent re-derivation of ${names.length} variables that product code (C, C++ or Rust outside t/) reads. Support engineers will set these on running systems, so a wrong default or a wrong accepted value in the document causes real harm.

Variables: ${names.join(', ')}

Step 1 (blind). WITHOUT opening the inventory files, derive for each variable, from the code only: every read site in product code (path:line), which programs or libraries contain that code, when it is read, exactly how the text is parsed, exactly which values are accepted, the exact behaviour when unset, when empty, and on an invalid value, and the effect (follow the value to where it is used). Note any command-line flag or other variable that overrides or interacts with it. Note any log line the program prints that shows the value in effect (this helps support engineers check it).
Step 2 (compare). Then open the verified inventory files ${WORK}/inventory/verified/cpp-pos-system.json, cpp-tron.json and cpp-rinzler-runtron.json, find each variable, and compare with your derivation. Where they differ, open the code again and decide which is right.
Step 3. Write JSON to: ${WORK}/inventory/critic/rederive-${i}.json
{ "variables": [ { "name": "...", "readers": [ { "program": "...", "site": "...", "mechanism": "...", "when": "..." } ],
    "values": "...", "default": "...", "empty_value": "...", "invalid_value": "...", "effect": "...",
    "interactions": "...", "how_to_check": "log line or stat that shows the value in effect, with site; or 'none found'",
    "audience": "operator or developer-debug", "audience_reason": "one line",
    "agrees_with_inventory": true or false, "disagreement": "what the inventory said and what the code says; empty if it agrees" } ],
  "notes": "..." }
   Validate it with python3 -m json.tool.
Step 4. Return: "disagreements" = one string per variable where the inventory was wrong or vague ("NAME - what was wrong - what the code says"); "missing" = any in-scope variable you met in this code that is not in your list and not in the inventory files; other lists may be empty.`
}

const critics = await parallel([
  () => agent(tokenCritic, { label: 'critic:token-sweep', phase: 'Critic', schema: CRITIC_SCHEMA }),
  () => agent(flowCritic, { label: 'critic:flows', phase: 'Critic', schema: CRITIC_SCHEMA }),
  ...chunks.map((c, i) => () =>
    agent(rederivePrompt(c, i), { label: `critic:rederive-${i}`, phase: 'Critic', schema: CRITIC_SCHEMA })
      .then(r => r ? { chunk: i, names: c, ...r } : null)),
])

return {
  commit: '7eddde7895',
  areas: verified.map(v => ({
    area: v.area, sweepCount: v.sweepCount,
    verifiedCount: v.names.length, added: v.added, removed: v.removed, corrected: v.corrected,
    unresolved: v.unresolved, out_file: v.out_file, notes: v.notes,
  })),
  failedAreas,
  union: { total: unionNames.length, read: readNames.length, setOnly: setOnlyNames.length },
  docs: docsResult ? { names: docNames.length, docOnly, central_lists: docsResult.central_lists, deployment_facts: docsResult.deployment_facts, notes: docsResult.notes, out_file: docsResult.out_file } : null,
  runtimeNames: runtimeNames.length,
  critics: {
    tokenSweep: critics[0],
    flows: critics[1],
    rederive: critics.slice(2),
  },
}
