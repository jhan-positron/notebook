export const meta = {
  name: 'review-l8b-levers-campaign',
  description: 'Adversarial review of the l8b-levers campaign scripts against the Saturday plan before launch',
  phases: [
    { title: 'Find', detail: 'five lenses over the campaign scripts, the driver, the prompt change and the plan' },
    { title: 'Verify', detail: 'three refuters per finding' },
    { title: 'Critic', detail: 'what is missing' },
  ],
}

const CTX = `
CONTEXT (read-only review; do NOT edit any file, do NOT launch anything, do NOT run anything on delphi-3bda except
harmless read-only ssh commands such as cat/ls/stat if you truly need one; the nightly CI is running there now).

A campaign will run today on the whole of delphi-3bda after the nightly CI lease clears (about 13:20 UTC). It measures
the AMX attention kernel's gain on llama-3.1-8b with the nightly's own client (systems_test scripts/perf.py) against
rinzler engines in the nightly layout, nightly deb (base) against canonical-AMX deb (canon), 3 interleaved passes,
10 configs per pass (users x prompt length grid). The executing agent's handoff is the plan file; the scripts implement it.

Files to review (all under /home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/):
  campaign.sh   (new, forked from ../canon-ci-20260918/campaign.sh)   launch.sh (new)
  st_ci_perf.py (modified copy of ../canon-ci-20260918/st_ci_perf.py; diff it against that file)
  dut.sh        (unchanged copy of ../canon-ci-20260918/dut.sh; note its OUT dir is still /var/tmp/jhan/canon-ci-20260918)
  configs.py + configs-full.json, configs-no8192.json, configs-no7168.json, check-32u-p8192.json, check-32u-p7168.json
  prompt.py.patch / prompt.py.before / prompt.py.after  (the change applied to
      /home/jhan/workspace/ai-runs/systems_test/testlib/prompt.py, the checkout the driver runs)
  prompt_check.py (offline check; its output is in /home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/prompt-check/)
The plan: /home/jhan/workspace/intel-AMX/CI-test/status/Saturday-plan.md
Line-level change note: /home/jhan/workspace/intel-AMX/exec/canon-ci-20260918/T0-script-changes.md
Precedent campaign (worked, 2026-09-18): /home/jhan/workspace/intel-AMX/exec/canon-ci-20260918/ (campaign.sh, dut.sh, launch.sh,
  st_ci_perf.py), its results /home/jhan/workspace/intel-AMX/exec/results/canon-ci-20260918/ (canon/driver.log, perf.json, preflight.txt),
  its log /home/jhan/workspace/intel-AMX/exec/logs/canon-ci-20260918.log
Harness code: /home/jhan/workspace/ai-runs/systems_test/ (scripts/perf.py, testlib/tps.py, testlib/prompt.py, testlib/inventory.py,
  testlib/inference_provisioner.py, testlib/platformd_health.py); the talos stub is exec/l8b-levers-20260919/talos_stub/talos.py.
Helpers used over ssh: /home/jhan/workspace/intel-AMX/exec/bill-share.sh, /home/jhan/workspace/intel-AMX/exec/lib-guard.sh (ci_lease_busy).
Facts verified live today (07:2x-07:4x UTC): installed tron 2026.09.18-3faba6d0 (rinzler sha 27e6883c...); platformd v0.10.7 ->
  the harness uses the LEGACY posadm provisioning path (models.load, restart=False because capability 'base' is present); a
  same-model provision does NOT restart engines; the rinzler journal has NO per-request line (the dut.sh idle-test grep for request
  lines always counts 0; the SYSTEM_STATS #EVT# line every ~5-6 min carries Open/Closed/Busy and decides the idle test);
  rinzler FUSE stats at /var/run/rinzler/N/rinzler/stats/prompts_total (requests admitted since process start, readable as jhan
  without sudo) and monitor/cumulative/* exist; the driver's CI_MIMIC_CHECK=1 mode ran fine with the new configs file and
  reported 4 pids on the installed sha; the offline prompt check passed (0 exceptions, deterministic, stored lists unchanged,
  prompt-1024 identical to the old code). Bill's marker /bill-has-instance-0,2 is absent now (whole machine is ours).
Known intentional deviations from the plan text (judge them, do not just repeat them): DRIVER_TIMEOUT 5400 s per pass instead
  of "about 3600 s"; DEADLINE_START 19:30Z read as the campaign-start deadline with a separate PASS_DEADLINE 00:00Z and the
  DRIVER_END_BY 01:15Z finish guard; IDLE_MIN=1 for intra-campaign engine restarts (5 at the final handoff); a failed pass is
  not repeated when its failed configs already failed in an earlier pass-run; serving-up is called after serving-down before
  the harness provisions.
Report findings as concrete defects or risks with file, line (1-indexed, from the current file), what goes wrong, and the fix.
Do not report style. Severity: high = wrong data / machine left in a bad state / campaign aborts wrongly; medium = loses
part of the data or time; low = cosmetic or unlikely.`

const FINDINGS = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      file: { type: 'string' }, line: { type: 'integer' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      title: { type: 'string' }, description: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
      required: ['file', 'line', 'severity', 'title', 'description', 'evidence', 'fix'] } },
    notes: { type: 'string' },
  },
  required: ['findings'],
}
const VERDICT = {
  type: 'object',
  properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, better_fix: { type: 'string' } },
  required: ['refuted', 'reason', 'severity'],
}

const LENSES = [
  { key: 'shell', prompt: `${CTX}
LENS: shell correctness of campaign.sh, launch.sh and their use of dut.sh. Read every line. Look for: exit-status capture errors
($? after if/&&/pipelines), quoting and word splitting (set -u, empty vars, tags), arithmetic, the ssh remote-command quoting in
dut_env_t/hold_lock/engine_counters, timeout wrappers and their rc 124, traps (TERM/INT/HUP/EXIT ordering, double release), the
check-cell branch and CONFIGS selection, the pass loop (k counting, tags, repeat logic, known_failed/systematic test, PASS_S/need
arithmetic, deadline comparisons with date -d), mv of failed dirs, restore_and_release on every exit path, .done markers,
status/say output, grep patterns in run_pass (do they match what st_ci_perf.py actually logs?), launch.sh preconditions
(md5 list, cmp, python check, pgrep anchoring, PIPESTATUS). Trace each path mentally with concrete values. Also verify dut.sh
serving-down/serving-up/ensure-base/ensure-canon/save-base-deb behave as campaign.sh assumes (IDLE_MIN env passes through
the ssh command; return codes; the 12-minute idle loop; hugepage checks).` },
  { key: 'plan', prompt: `${CTX}
LENS: plan compliance. Read the plan file (every section) and T0-script-changes.md, then check each requirement and each standing
decision of section 2a against the scripts: arms and identity checks (section 1, EXPECTED_BASE, manifest sha, restart after every
switch, stop on a deleted binary, after-provision snapshot on the installed sha), machine/time rules (section 2: marker, lease,
flock, hard limits, end state incl. config.env 0 bytes), section 2a decisions (Bill retry every 30 min, latest start, check-cell
fallbacks 8192 -> 7168 -> drop, failed-pass repeat rule, no changes to grid/rule/arms, no filing/posting, stop-safely triggers),
section 3 (prompt source, copy, offline check recorded in the results dir), section 4 driver changes (each of the 4 items),
section 5 config grid (names, fields, order, values), section 6 pre-pass steps (check cell timeout, identity check, preflight),
section 8 monitoring, section 9 outputs (what must be recorded per pass; is every listed output produced or derivable?), section 10
traps. For every deviation state whether it is harmless, beneficial or a defect, and what the plan literally says.` },
  { key: 'driver', prompt: `${CTX}
LENS: the Python driver st_ci_perf.py and the prompt.py change, against the harness code. Diff st_ci_perf.py against the precedent
copy. Check: CI_MIMIC_CONFIGS_JSON handling and that scripts/perf.py test_performance really iterates the replaced module global
and reads only keys the configs have; StopPass (a BaseException) really propagates out of perf.py's retry loops and asyncio
loop.run_until_complete (read perf.py lines 309-330 and 440-455 and think about asyncio Task exception handling); the
provision_and_snapshot wrapper is called on the cached-model path too (inventory.py provision_model) and what its checks cost;
binary_check parsing against the exact snapshot text format produced by snapshot_layout (pid lines, "(deleted)", sha16, the
'=== rinzler' section; what if pgrep -x rinzler returns helper processes or zero pids during a restart); the benchmark wrapper
(exception paths, record consistency, config_name lookup uniqueness, counters before/after and the AMX probe ordering, the
_CountingHandler and whether the harness's 'anomalous tps=' lines reach the root logger through the talos stub); exit codes 0/2/7
and the FAILED_CONFIGS line format campaign.sh parses; the CHECK mode; JSON dump of non-serializable values; the ssh() helper's
timeouts; anything in the harness that could break at nominal_users 32 or prompt_length 8192 (tps.py Config, max_tokens,
goals, StopOverrideFailed, ProcessPoolExecutor, .perf directory, prefix cache). For prompt.py: the loop condition versus
prune_convo's raise condition, seed wrap-around modulo 1000, the copy semantics, the fork-based workers of tps.py, at prompt 1024
identical output, cost of _token_count.` },
  { key: 'machine', prompt: `${CTX}
LENS: what actually happens on delphi-3bda, step by step, from the lease clearing to the end state. Walk the sequence: preflight,
save-base-deb, ensure-canon (apt remove + install of a local deb), sleep 20, serving-down with IDLE_MIN=1 (journal idle test that
counts SYSTEM_STATS lines every ~5-6 min: how long does it really wait after our benchmark, can it exceed its 12-minute loop and
fail, what does that do to the campaign), slice-file removal, serving-up (POST inference/up: which model starts, how long), then
the harness's legacy posadm provisioning of llama-3.1-8b-instruct-good-tp2 (same model or different model cases: does models.load
re-create engines, does the model poll succeed, does the health check handle 'updating'), the binary check, the AMX probe (sudo
perf stat with perf_event_paranoid 4), the benchmark at 32 users x prompt 8192 (KV need 9.5 GiB per engine vs 128 x 1 GiB
hugepages, max_total_tokens 131072, max_concurrent_requests 0), then each package switch, the final restore (ensure-base from
the saved deb, serving-down IDLE_MIN=5, serving-up), Bill marker release, flock release. Estimate the wall time of each step and the
whole campaign from a 13:20 UTC start using the precedent's measured numbers (canon-ci log: apt swap 9 s, idle wait 6 min at
IDLE_MIN 5, provisioning 40-60 s, llama-8b 2-user cell 2.52 min) and say whether it fits before PASS_DEADLINE 00:00Z and
DRIVER_END_BY 01:15Z with margin, and where DRIVER_TIMEOUT 5400 s could cut a pass. Flag every step that can leave the machine in a
state the plan forbids (canon deb installed at the end, engines down, config.env not 0 bytes, marker not released, flock held,
production engines running a deleted binary).` },
  { key: 'data', prompt: `${CTX}
LENS: is every measurement the analysis and report need actually recorded, in a shape the analysis can use? The report (plan
section 9) needs per config and pass: clean and canon TPS mean, paired t over 3 passes (pass r base with pass r canon), gain %,
p05, slowest sample (min TPS), TTFT, duration, anomalous-sample counts, per-engine request counts (Caddy spread, with the
nominal_users-4 rule of section 7), AMX-busy probe per config or per pass, snapshots proving the binary per pass, client CPU
pressure, prompt-token counts observed by the server (the 31-token overhead assumption), the check cell's duration, the offline
prompt check, identity checks per pass. Read st_ci_perf.py's record structure (record["raw"], record["results"], snapshots,
amx_probes, binary_checks, engine counters) and campaign.sh's status/outcome files, and the precedent perf.json in
results/canon-ci-20260918/canon/perf.json for the shape. Point out anything missing, ambiguous (e.g. how a raw record is matched
to a config when a config failed; whether the AMX probe runs per config on the cached-provision path; whether the probe's 4
requests inflate the before/after counters; whether wall_seconds includes prompt generation), or fragile for pairing passes.
Also judge whether the decision rule of section 7 can be computed from the records exactly as pre-registered.` },
]

phase('Find')
const found = (await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS, effort: 'xhigh' })
))).filter(Boolean).flatMap((r, i) => (r.findings || []).map(f => ({ ...f, lens: LENSES[i].key })))
log(`${found.length} raw findings from ${LENSES.length} lenses`)

// dedup by file + title words
const key = f => `${f.file}|${f.title.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(' ').slice(0, 6).join(' ')}`
const seen = new Set(); const uniq = []
for (const f of found) { const k = key(f); if (!seen.has(k)) { seen.add(k); uniq.push(f) } }
log(`${uniq.length} after dedup`)

phase('Verify')
const REFUTE_LENSES = [
  'reproduce-from-code: re-read the exact lines and trace the concrete inputs; is the defect real as stated?',
  'does-it-matter: even if real, does it change the campaign outcome (wrong data, bad machine state, lost pass, wasted time)? A finding that changes nothing is refuted.',
  'plan-and-precedent: does the plan actually require what the finding demands, and did the precedent campaign (which worked) do the same thing? A finding that contradicts the plan or reports the precedent behaviour as a new defect is refuted.',
]
const verified = await parallel(uniq.map(f => () =>
  parallel(REFUTE_LENSES.map(lens => () =>
    agent(`${CTX}
YOU ARE A REFUTER. Try to refute this finding. Lens: ${lens}
Finding (from lens ${f.lens}): ${f.severity.toUpperCase()} ${f.file}:${f.line} ${f.title}
${f.description}
Evidence: ${f.evidence}
Proposed fix: ${f.fix}
Read the actual file(s) and the referenced harness/plan text. Default to refuted=true if you cannot confirm the defect from the code.
Return refuted, the reason (cite file:line), your severity judgement and a better fix if you have one.`,
      { label: `verify:${f.lens}:${f.title.slice(0, 30)}`, phase: 'Verify', schema: VERDICT, effort: 'high' })))
    .then(votes => {
      const vs = votes.filter(Boolean)
      const keep = vs.filter(v => !v.refuted).length >= 2
      const sev = vs.map(v => v.severity)
      return { ...f, votes: vs, confirmed: keep, severity_votes: sev }
    })
))
const confirmed = verified.filter(Boolean).filter(v => v.confirmed)
const refuted = verified.filter(Boolean).filter(v => !v.confirmed)
log(`${confirmed.length} confirmed, ${refuted.length} refuted`)

phase('Critic')
const critic = await agent(`${CTX}
YOU ARE THE COMPLETENESS CRITIC. Confirmed findings so far (each will be fixed): ${JSON.stringify(confirmed.map(c => ({ file: c.file, line: c.line, title: c.title, severity: c.severity })))}
Refuted findings (do not repeat them): ${JSON.stringify(refuted.map(c => ({ title: c.title })))}
What is still missing or unexamined? Consider: a failure mode nobody listed (DUT ssh hiccups mid-pass, NFS attribute cache for files
the DUT reads, disk/.perf, the client host's 32 worker processes, the openai client's timeouts at prompt 8192, platformd job
queue, the nightly's leftover state, Caddy behaviour at 32 users, the results directory reuse after an aborted attempt, the
background monitoring the executing agent must do, what the agent should verify right after launch and right after the check
cell). Report only concrete, checkable items with a fix or a verification step.`,
  { label: 'critic', phase: 'Critic', schema: FINDINGS, effort: 'xhigh' })

return { confirmed: confirmed.map(c => ({ file: c.file, line: c.line, severity: c.severity, severity_votes: c.severity_votes, title: c.title, description: c.description, evidence: c.evidence, fix: c.fix, better_fixes: c.votes.map(v => v.better_fix).filter(Boolean), lens: c.lens })),
         refuted: refuted.map(c => ({ file: c.file, line: c.line, title: c.title, reasons: c.votes.map(v => v.reason) })),
         critic: critic ? critic.findings : null, critic_notes: critic ? critic.notes : null }