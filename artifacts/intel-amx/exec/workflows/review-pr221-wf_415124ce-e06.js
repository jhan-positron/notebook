export const meta = {
  name: 'review-pr221',
  description: 'Review systems_test PR 221 across six dimensions, adversarially verify each finding',
  phases: [
    { title: 'Review', detail: 'six independent finders, one lens each' },
    { title: 'Verify', detail: 'three refuters per finding, distinct lenses' },
  ],
}

const CTX = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-CI-test/008e4377-f128-449a-a5d4-19d794f55499/scratchpad/pr221/context.md'
const DIFF = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-CI-test/008e4377-f128-449a-a5d4-19d794f55499/scratchpad/pr221/code.diff'
const REPO = '/home/jhan/workspace/ai-runs/systems_test-pr221'

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          failure_scenario: { type: 'string' },
          evidence: { type: 'string' },
          suggested_fix: { type: 'string' },
        },
        required: ['title', 'severity', 'file', 'claim', 'failure_scenario', 'evidence'],
      },
    },
    checked_fine: { type: 'array', items: { type: 'string' } },
  },
  required: ['findings', 'checked_fine'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    reasoning: { type: 'string' },
    corrected_severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit', 'not-a-finding'] },
    corrected_claim: { type: 'string' },
  },
  required: ['refuted', 'confidence', 'reasoning', 'corrected_severity'],
}

const COMMON = `You are one reviewer of a pull request. First read the context file ${CTX} completely (it holds the requester's actual ask, verified facts, repo conventions and things NOT to raise). Then read the code diff ${DIFF}. The clone at the PR head is ${REPO} (branch pr221); base versions: git -C ${REPO} show e4727d5:<path>. Read whole files where the diff context is not enough. Do not modify tracked files in the clone; experiments go in your own scratch folder. Never run anything against a remote machine. Report only findings tied to a specific diff line or a verified behaviour, each with a concrete failure scenario and the evidence you checked. Also list what you checked and found fine. Do not repeat the facts the context file already marks as verified or decided.`

const DIMENSIONS = [
  { key: 'prompt', prompt: `${COMMON}

Your lens: testlib/prompt.py (PromptGenerator: prune_convo, _system_prompt, prepare, generate, PromptTooShortError). Check: correctness of the eligibility cache key (prompt_length, system token length) across seeds with longer timestamps; whether prepare() run in the parent before fork is inherited by the pool workers (ProcessPoolExecutor default start method on Linux/Python 3.12, and what happens under forkserver/spawn); interplay of NUL stripping with prune_convo's decode/prefix slicing (can decode() of truncated tokens leave a partial prefix or re-introduce characters); the return type and the removed in-place mutation; exception types (PromptTooShortError vs other ValueError from the tokenizer); any behaviour change for the llama-3.2-3b row (prompt 200, shared_prompt_length 800) or other tokenizers that emit no BOS ([1:] slicing) or tokenizers with truncation enabled in tokenizer.json (silent truncation during encode could change eligibility); cost of prepare() for the 1024 rows; whether generate() for seeds >= 1e6 rescans in a worker; whether the docstrings/comments in prompt.py are accurate.` },
  { key: 'tps', prompt: `${COMMON}

Your lens: testlib/tps.py multiprocessing changes (Worker.sync 'raise exc from exc.__cause__', run_tps_worker: group_queue.cancel_join_thread(), None sentinel on ingress, openai.OpenAIError -> RuntimeError wrapping, benchmark_tps: prepare() call + log line, finally: put None into every ingress before executor.shutdown(wait=False, cancel_futures=True), followed by the 'with' block's shutdown(wait=True)). Reason precisely about: (1) can cancel_join_thread() lose a worker's FINAL sample in a successful run (who reads the queue, when does the pool process exit, does the parent loop guarantee receipt before shutdown)? (2) the None sentinel in the SUCCESS path: every ingress gets an unread None; does the parent hang at interpreter exit flushing Queue feeder threads, or leak? (3) the FAILURE path: a worker mid-request continues get_tps_sample after the parent raised; it puts samples into group_queue that nobody reads; with cancel_join_thread does the pool process exit; does shutdown(wait=True) from the context manager block until in-flight requests finish (openai client default timeout 600 s)? Is that acceptable or a regression vs base? (4) exception pickling: does 'from exc' survive the pool (BaseException.__reduce__ drops __cause__), and what does the parent see for openai.APIConnectionError vs BadRequestError vs httpx exceptions not derived from openai.OpenAIError; (5) is the RuntimeError wrapping hiding an exception type any caller relies on (grep callers of benchmark_tps and get_tps_sample, e.g. scripts/perf.py, scripts/tps_node.py, endless_perf); (6) the 'Worker {index} round ...' message vs the parent's own logging; (7) the tests in tests/test_tps.py: do they exercise the real code paths (fork context inside a multi-threaded pytest process, timeouts of 5-10 s, the 128 x 8 KB queue fill relying on pipe buffer size 64 KB), could they be flaky on the GitHub runner (pipeline.yaml), and do they assert intent (why) not just behaviour.` },
  { key: 'results', prompt: `${COMMON}

Your lens: testlib/results.py build_result_report changes (benchmark_label from result.context, display_name, the new bypass 'if current_format and not (label_suffix and not has_threshold)') and scripts/perf.py context plumbing (both the success and the exception branch). Trace the exact Slack lines produced for the new row in each report: CURRENT THRESHOLDS (get_goal, no (model,32) entry) and YAML THRESHOLDS (no YAML row), on granite and on genoa. Determine: the emitted line text; whether incomplete/actual_failed/verdict change relative to the same run without the new row; what happens later when a get_goal entry and/or a YAML row are added (does the label still show, does the bypass stop applying, any duplicate line); what happens when the new row FAILS (exception branch: tps_mean 0, context has label) in both reports; whether the label bypass leaks a threshold-less labelled row into the ENFORCED report in a way that could mislead (e.g. looks like a pass). Also compare the produced format with the requester's example 'llama-3.1-8b-instruct-good-tp2 @8u per machine, AMX benchmark'. Read testlib/system_ci_thresholds.py (thresholds_from_goal, YAML loader warnings) and tests/test_results_v2.py helpers to confirm. Note the docstring at the top of build_result_report or docs/ that describe the report format, and whether they need an update per repo CLAUDE.md.` },
  { key: 'ops', prompt: `${COMMON}

Your lens: does the PR deliver exactly what the requester asked, and how will it behave operationally in the nightly? Check scripts/perf.py: the new config's placement (directly after the existing llama-8b 8-user entry?) and testlib/inventory.py provision_model's skip logic (name and use_speculation equality; what resets _provisioned_model between configs; does the health check between the two llama-8b configs restart anything); the duplicate 'name' (config_name used in log lines and session.describe keys; Talos sample/graph names; anything keyed by name alone, e.g. scripts/system_ci.py, endless_perf, talos summaries); Config.goals default dict lookup by model (the 32-user row inherits the 8-user goal {'mean':144,'min':140}: effect on the per-user 'Done' colouring, is_suspicious diagnostics, test_passed with raise_for_goal=False, TPS_GOALS env in .github workflows); request timeouts at 32 users x 4096 prompt (TTFT about 19 s without AMX measured; openai client default timeout); the genoa nightly running the row with no gate (cost, no AMX, any threshold interplay, and whether the requester asked for gating: he did not); the 'AMX benchmark' label being a display label only (a package without AMX still shows the row, no failure); how thresholds would be added later (ratchet cannot create thresholds; manual get_goal + YAML edit); and the sequencing with tron PR #4505. Also check .github/workflows and scripts/system_ci.py for any hard-coded list of expected perf rows or counts that the new row would break (e.g. result count assertions, Talos summary parsers, history matching in the ratchet by (platform, model, users)). List deviations from the request as findings with severity; list matches as checked_fine.` },
  { key: 'tests', prompt: `${COMMON}

Your lens: tests and repo conventions (systems_test CLAUDE.md). For each new/changed test in tests/test_prompt.py, tests/test_tps.py, tests/test_perf.py, tests/test_results_v2.py: state what intent it encodes, whether it would FAIL on the base code (regression-test requirement for medium/high fixes: PromptTooShort at 4096, NUL rejection, BrokenProcessPool masking, worker hang after failure) — verify by actually running the new test files against a copy of the BASE modules if feasible (copy the base testlib files from git show e4727d5:... into a scratch package and run the PR's tests against them, or reason precisely from the code), whether it can pass vacuously (mock-heavy tests asserting on mocks), and whether the fork-based process tests are robust on a CI runner (timeouts, pipe buffer assumptions, DeprecationWarning about fork in a multi-threaded process). Check the documentation duty: docstrings/comments touched or made stale (e.g. the removed '# TODO: generate prompt', PromptGenerator docstrings, tps.py comments), README.md or docs/ sections that describe the perf configs, prompt source, Slack line format or the ShareGPT dataset; the commit 'Remove prompt dataset documentation from PR' removed a doc — check git log -p for what was removed and whether anything in the remaining tree references it. Check diff-cover plausibility (70 % of changed lines covered) and ruff.` },
  { key: 'data', prompt: `${COMMON}

Your lens: the data files. testlib/sharegpt_1000.json (now 1320 records) and testlib/sharegpt_long_manifest.json, plus pyproject.toml package-data. Verify: record schema consistency of the appended 320 records (keys, roles, id format, non-empty turns, alternating human/gpt); whether the manifest's per-record prompt_sha256 values can be reproduced (try plausible definitions: sha256 of the generated 4096-token prompt JSON at seed 0 without the timestamp, of the conversation JSON, of the concatenated turn text; use the venv ${REPO}/.venv/bin/python with HF_HUB_OFFLINE=1 and the cached tokenizer neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16 revision 6a426ef8...; report which definition matches or that none does); whether expanded_sha256 / original_sha256 / tokenizer_json_sha256 match the files (compute them); whether the manifest documents enough to regenerate the selection (source repo/revision/file/sha, selection parameters, seed, library versions) given that the selection script is NOT in the repo; licensing/attribution: the PR removed a standalone ShareGPT license file and its packaging entry (check git log -p on branch pr221 for what was removed) — does the manifest keep attribution and is the source dataset's license compatible with redistribution inside this internal repo (state facts about anon8231489123/ShareGPT_Vicuna_unfiltered licensing only if you can verify them from the manifest or a local copy; otherwise mark Insufficient data); file naming (sharegpt_1000.json holding 1320 records; who reads the name); repository/wheel size growth (+13.6 MB) and whether the Dockerfile or wheel path needs the package-data lines; the NUL record 3DGOV17 and whether other control characters (e.g. \\u0000 escapes, surrogates, other C0 controls) exist in the appended records that the inference server could reject.` },
]

phase('Review')
log('Six finders reviewing PR 221')

const REFUTER_LENSES = [
  { name: 'reproduce', instr: 'Your lens is REPRODUCTION: try to reproduce the failure scenario concretely (read the exact code paths, run a small experiment in your own scratch folder when feasible, using the venv python at ' + REPO + '/.venv/bin/python; never touch tracked files or remote machines). If it cannot be reproduced or the code path is unreachable in the nightly, refute.' },
  { name: 'impact', instr: 'Your lens is IMPACT on the nightly system CI and on what the requester asked: even if the claim is technically true, does it change the nightly numbers, the Slack report, the verdict, or the requester\'s stated goals (test added, placed after the existing llama-8b entry, labelled AMX benchmark, informational until thresholds exist)? If the impact is cosmetic or hypothetical, refute or downgrade severity.' },
  { name: 'precedent', instr: 'Your lens is PRECEDENT and BASE BEHAVIOUR: is the claimed problem already present in the base code or an established convention of this repo (check git show e4727d5:<path> and other configs/tests)? A pre-existing condition that the PR does not worsen is not a finding against the PR; refute it or downgrade it to nit with the precedent cited.' },
]

const results = await pipeline(
  DIMENSIONS,
  d => agent(d.prompt, { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (review, d) => {
    if (!review) return { key: d.key, findings: [], checked_fine: [], missing: true }
    log(`${d.key}: ${review.findings.length} findings, ${review.checked_fine.length} checked-fine items`)
    return parallel(review.findings.map(f => () =>
      parallel(REFUTER_LENSES.map(lens => () =>
        agent(`You are an adversarial verifier of ONE code-review finding on systems_test PR 221. Read the context file ${CTX} first (verified facts, the requester's ask, things already decided), then the diff ${DIFF}; the clone is at ${REPO} (branch pr221, base e4727d5).

${lens.instr}

The finding to attack:
- Title: ${f.title}
- Severity claimed: ${f.severity}
- File: ${f.file}${f.line ? ' line ' + f.line : ''}
- Claim: ${f.claim}
- Failure scenario: ${f.failure_scenario}
- Evidence given: ${f.evidence}
${f.suggested_fix ? '- Suggested fix: ' + f.suggested_fix : ''}

Try hard to REFUTE it. Default to refuted=true if you remain uncertain. If it survives, give the corrected severity and a corrected one-sentence claim that a reviewer could post to the author.`, { label: `verify:${lens.name}:${f.title.slice(0, 40)}`, phase: 'Verify', schema: VERDICT_SCHEMA })))
        .then(votes => {
          const v = votes.filter(Boolean)
          const surviving = v.filter(x => !x.refuted).length
          return { ...f, dimension: d.key, votes: v, survives: surviving >= 2, surviving_votes: surviving, total_votes: v.length }
        })
    )).then(verified => ({ key: d.key, findings: verified.filter(Boolean), checked_fine: review.checked_fine }))
  }
)

const dims = results.filter(Boolean)
const confirmed = dims.flatMap(r => r.findings.filter(f => f.survives))
const refuted = dims.flatMap(r => r.findings.filter(f => !f.survives))
const coverage = Object.fromEntries(dims.map(r => [r.key, r.checked_fine]))
const missing = dims.filter(r => r.missing).map(r => r.key)
log(`confirmed ${confirmed.length}, refuted ${refuted.length}, missing dimensions: ${missing.join(',') || 'none'}`)
return { confirmed, refuted, coverage, missing }