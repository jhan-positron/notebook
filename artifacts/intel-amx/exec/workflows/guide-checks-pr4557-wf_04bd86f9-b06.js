export const meta = {
  name: 'guide-checks-pr4557',
  description: 'Find C++ coding-guide violations (named constexpr values, braces) in the lines PR #4557 adds, verify each with two refuters, and run two independent plain-English checks of the PR description',
  phases: [{ title: 'Find' }, { title: 'Refute' }, { title: 'English' }],
}
const REPO = '/home/jhan/workspace/ai-runs/tron-issue4525'
const BODY = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/7a726337-9373-4eb4-935f-269e8630de97/scratchpad/pr-body.md'
const GUIDE = `
THE C++ CODING GUIDE (the user's rules; apply them to every line the PR ADDS, i.e. lines starting with + in \`git -C ${REPO} diff origin/main HEAD\`; moved code counts as added, unchanged main code does not):
Named values: define fixed values as named constexpr variables; keep the literal in that declaration and refer to the name elsewhere; name constexpr variables in UPPER_CASE with underscores; append the value to the name, separated by an underscore (DAYS_PER_WEEK_7 = 7, MAX_RETRIES_3 = 3; a value with punctuation or spaces uses an uppercase spelling valid in an identifier, e.g. V_ODD_TOKEN_LANE_MASK_0XFFFF0000).
Braces: enclose the body of every if/else/for/while/do in braces. Braces may be omitted only when the ENTIRE statement, including its body and any else branches, sits on ONE physical line. Keep braces where the syntax requires them.
Working interpretation for the finders (state any case you find ambiguous in a separate 'ambiguous' list instead of a finding): (a) loop initialisers/increments 0 and 1 (i = 0, ++i, i + 1 as 'next') are not domain values and are exempt; (b) a literal that is itself the initializer of a constexpr declaration, a static_assert operand that restates a declared constant, or an element of a constexpr test-data table (std::array of cases) is a declaration, not a use; (c) literals with domain meaning used in code are violations: pair size 2, lane counts 16, widths 32, alignments 64, bit shifts 16, masks, head sizes 128, page sizes 64, byte multipliers, test loop bounds like 7 or 3, magic bf16 bit patterns used outside a table; (d) when the repository already has a named constant for the value in scope (for example kv_block_alignment, TRON_CHUNK_SIZE, page_size, head_size, V_PAIR_TOKENS_2, V_ROW_WIDTH_MULTIPLE_32, BF16_BITS_16, PAGE_TOKENS_64, HEAD_SIZE_128, TILE_ROWS_16, DIM_STEP_32) the fix is to use it, not to add a new one; say which; (e) template arguments and alignas() arguments are uses too; (f) the value-suffix rule also applies to constexpr names the PR adds without a suffix (report them under rule 'named-value').`
const COMMON = `
You review PR #4557 of positron-ai/tron in the git worktree ${REPO} (branch jhan-kv-typed-tensors, HEAD 707159b9ef, 4 commits on origin/main 996f58ec82). READ-ONLY: do not edit files, do not run builds, do not ssh anywhere, do not change git state; use git diff/show/grep and file reads. Build tools are not on this host. ${GUIDE}
For every finding give: rule ('named-value' or 'braces'), file, line number at HEAD, the exact current line text, the exact replacement text (for named-value: the new constexpr declaration with its UPPER_CASE_VALUE name and where to put it, and the rewritten use; or the existing constant to reuse), and one sentence of reason. Be exhaustive within your files: list EVERY violating line, do not sample. Return at most 60 findings; if there are more, say how many you left out and where.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: { rule: { type: 'string', enum: ['named-value', 'braces'] }, file: { type: 'string' }, line: { type: 'integer' }, current: { type: 'string' }, replacement: { type: 'string' }, reason: { type: 'string' } }, required: ['rule', 'file', 'line', 'current', 'replacement', 'reason'] } }, ambiguous: { type: 'array', items: { type: 'string' } }, left_out: { type: 'string' } }, required: ['findings', 'ambiguous'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, corrected_replacement: { type: 'string' } }, required: ['refuted', 'reason'] }
const GROUPS = [
  { key: 'v_vnni', files: 'h/tron/tensor/v_vnni.hpp and h/tron/tensor/kv_cache_fwd.hpp (both new files: every line is PR-added)' },
  { key: 'cache-model', files: 'h/tron/models/kv_cache.hpp, h/tron/models/model.hpp, h/tron/models/self_attention.hpp, h/tron/scheduler/full.hpp, h/tron/kernels/amx_attn_iface.hpp, src/tron/kernels/amx_attn.cpp (PR-added lines only: git diff origin/main HEAD -- <file>)' },
  { key: 'llama-unit-a', files: 't/t_llama_unit.cpp, PR-added lines in the FIRST half of the diff hunks of that file (run git diff origin/main HEAD -- t/t_llama_unit.cpp, split the hunks in two halves by count, take the first half)' },
  { key: 'llama-unit-b', files: 't/t_llama_unit.cpp, PR-added lines in the SECOND half of the diff hunks of that file (same split, second half)' },
  { key: 'other-tests', files: 't/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp, t/heterogeneous_scheduler_compile.cpp (PR-added lines only)' },
]
phase('Find')
const reviewed = await pipeline(
  GROUPS,
  g => agent(`${COMMON}\nYOUR FILES: ${g.files}.`, { label: `find:${g.key}`, phase: 'Find', schema: FINDINGS }),
  (found, g) => parallel((found?.findings ?? []).map(f => () =>
    parallel([1, 2].map(i => () => agent(`${COMMON}
You are refuter ${i} of 2 for ONE finding. Check: (1) the line is PR-added (appears with + in git diff origin/main HEAD); (2) it is a real violation under the guide and the working interpretation (not a declaration, table element or exempt 0/1); (3) the replacement is right: name spelling, value suffix equals the value, declaration placement compiles (namespace scope in a header, before first use; test-file scope for tests; constexpr usable in template arguments/alignas), and an existing repository constant is preferred when one exists (name it). Refute if any of (1)-(3) fails and the fix cannot be corrected; otherwise confirm and give a corrected replacement when needed.
FINDING: rule=${f.rule} file=${f.file}:${f.line}
CURRENT: ${f.current}
REPLACEMENT: ${f.replacement}
REASON: ${f.reason}`, { label: `refute:${g.key}:${f.line}`, phase: 'Refute', schema: VERDICT })))
      .then(vs => ({ group: g.key, finding: f, votes: vs.filter(Boolean) })))).then(r => ({ group: g.key, ambiguous: found?.ambiguous ?? [], left_out: found?.left_out ?? '', items: r })),
)
phase('English')
const ENGLISH = `
Check mode of the plain-English rules on the GitHub PR description at ${BODY} (Markdown). Rules: (1) define every code name, acronym, metric and project term at first use or in the "Words used here" table (terms every tron engineer knows, such as PR, CI, git, main, and code identifiers whose sentence says what they do, need no definition); (2) one claim per sentence (split on because/since/which means/so that/semicolons); (3) numbers carry units and, where the reader cannot judge them alone, a plain meaning; estimates are labelled est.; (4) a citation follows a sentence and never replaces it; (5) a Short version of at most three sentences at the top; (6) no idioms, metaphors, wordplay or uncommon words (banned words: convoy, refund, "in disguise", swept); (7) bullets or blank lines separate separate points; (8) short sentences: no semicolons, at most one subordinate clause, join two clauses with ", and" or ", or" when they must stay together. Project term list (define at first use): tron, runtron, rinzler, AMX, AVX, AMX-on/AMX-off, bf16, ulp, logits, forced run, free-running run, control run, A/A control, canonical/mirror/truncation builds, KV page, layer, kv_mul/GQA, tron record labels, p95, relative L2 error, TVD, changed fraction, TTFT, TPS. Report every violation with the rule number, the exact original phrase and the corrected phrase. Table cells and code spans count as prose when they carry sentences. Do not invent violations; report zero for a rule when there is none. READ-ONLY.`
const ESCHEMA = { type: 'object', properties: { violations: { type: 'array', items: { type: 'object', properties: { rule: { type: 'integer' }, original: { type: 'string' }, fix: { type: 'string' }, where: { type: 'string' } }, required: ['rule', 'original', 'fix'] } }, summary: { type: 'string' } }, required: ['violations', 'summary'] }
const english = await parallel([1, 2].map(i => () => agent(`${ENGLISH}\nYou are checker ${i} of 2; work independently and be exhaustive.`, { label: `english:${i}`, phase: 'English', schema: ESCHEMA })))
const groups = reviewed.filter(Boolean)
const confirmed = groups.flatMap(g => g.items.filter(x => x.votes.filter(v => v.refuted).length < 2))
const refuted = groups.flatMap(g => g.items.filter(x => x.votes.filter(v => v.refuted).length >= 2))
log(`${confirmed.length} confirmed, ${refuted.length} refuted; english checkers: ${english.filter(Boolean).map(e => e.violations.length).join('/')} violations`)
return { confirmed, refuted, ambiguous: groups.map(g => ({ group: g.group, ambiguous: g.ambiguous, left_out: g.left_out })), english: english.filter(Boolean) }