export const meta = {
  name: 'review2-l8b-levers-campaign',
  description: 'Second adversarial review round of the rewritten campaign.sh and patched driver before launch',
  phases: [{ title: 'Find' }, { title: 'Verify' }],
}
const CTX = `
CONTEXT (read-only review; do NOT edit files, do NOT launch anything, do NOT run anything on delphi-3bda except harmless
read-only ssh commands if truly needed; the nightly CI runs there now).
Second review round. Round 1 (27 confirmed findings, in /home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/review-findings.txt)
led to a REWRITE of campaign.sh and patches to st_ci_perf.py, dut.sh (serving-up now waits for platformd idle) and launch.sh.
Previous versions are kept as *.v1-prereview next to the files; diff against them to see what changed.
Files: /home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/{campaign.sh,launch.sh,dut.sh,st_ci_perf.py,analyze.py,configs*.json}
Plan: /home/jhan/workspace/intel-AMX/CI-test/status/Saturday-plan.md (section 2a = standing decisions, 6 = check cell, 7 = decision rule).
Harness: /home/jhan/workspace/ai-runs/systems_test (scripts/perf.py, testlib/tps.py, testlib/inventory.py, testlib/inference_provisioner.py,
testlib/platformd_health.py); talos stub exec/l8b-levers-20260919/talos_stub/talos.py; helpers exec/bill-share.sh, exec/lib-guard.sh.
Facts verified live today: platformd v0.10.7 (legacy posadm path; a same-model provision never restarts engines); /api/inference/status
returns results.activity ('idle'|'updating') and results.engines [{instance,status,...}]; /api/config returns
results.inference.engines.<name>.count; FUSE stats /var/run/rinzler/N/rinzler/stats/prompts_total readable as jhan; Caddy journal
(unit caddy) has JSON lines with logger 'http.handlers.reverse_proxy.health_checker.active'; CI_MIMIC_CHECK=1 of the patched driver
ran fine at 08:52 UTC; Bill's marker absent; nightly deb 2026.09.18-3faba6d0 installed; the CI lease clears about 13:20 UTC.
Report only concrete defects: file, line (from the CURRENT file), what goes wrong with concrete inputs, fix. No style.
Severity: high = wrong data / bad end state / wrong abort; medium = loses data or time; low = unlikely or cosmetic.`
const FINDINGS = { type: 'object', properties: { findings: { type: 'array', items: { type: 'object', properties: {
  file: { type: 'string' }, line: { type: 'integer' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] },
  title: { type: 'string' }, description: { type: 'string' }, evidence: { type: 'string' }, fix: { type: 'string' } },
  required: ['file', 'line', 'severity', 'title', 'description', 'evidence', 'fix'] } }, notes: { type: 'string' } }, required: ['findings'] }
const VERDICT = { type: 'object', properties: { refuted: { type: 'boolean' }, reason: { type: 'string' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, better_fix: { type: 'string' } }, required: ['refuted', 'reason', 'severity'] }
const LENSES = [
  { key: 'shell-trace', prompt: `${CTX}
LENS: trace campaign.sh line by line with concrete scenarios and find real defects. Scenarios to trace: (1) the normal day: lease clears
13:20Z, marker absent, preflight ok, check cell ok, 6 passes ok, restore; (2) check cell rc 7 (stale binary) then repeat ok; (3) check cell
rc 2 with FAILED_CONFIGS naming the 32u_p8192 config and no provisioning fault (must drop 8192 and run the 7168 check); (4) rc 1 twice
(must stop safely with marker released and flock freed); (5) base-pass2 driver rc 2 with one failed config, repeat ok; (6) the same config
failing twice in canon-pass2 then failing once in base-pass3 (must not repeat base-pass3); (7) operator kill -TERM of campaign.sh during
pass 3 and during the final restore; (8) pkill of the driver only (rc 143 -> operator stop path); (9) DUT ssh outage of 5 minutes between
passes (lease_state unknown -> stop safely) and during preflight (dut_retry); (10) PASS_TAGS resume with CHECK=0. For each check: variable
scoping (local vs global: LAST_RUN_S, LAST_FAILED_CONFIGS, LAST_COMPLETED, DRIVER_KILLED, CHECK_VERDICT set inside functions), exit-status
capture, set -u with unset variables (e.g. \${DRIVER_KILLED:+...} in stop_safely messages, tags), quoting, arithmetic, $(...) subshells that
lose variable updates (check_verdict is called in $(...): does it read LAST_FAILED_CONFIGS correctly? does anything it sets get lost?),
in_list edge cases, the mv/rm of failed dirs, the deadline comparisons, .done markers, outcome.txt, and the EXIT/TERM traps ordering.` },
  { key: 'driver-diff', prompt: `${CTX}
LENS: diff st_ci_perf.py against st_ci_perf.py.v1-prereview and against ../canon-ci-20260918/st_ci_perf.py and verify each change against the
harness code: the ssh() never-raise wrapper (return shapes used by callers: snapshot_layout, engine_counters, amx_probe, caddy_health_events,
versions_via_ssh); caddy_health_events parsing (grep -c output, rc 1 when zero, journalctl --since @epoch syntax and clock alignment between the
client host and the DUT); the provisioning wrapper (asyncssh.Error exists? does dut.conn/posadm_client reset lead to a working reconnect through
the connect_keys override? is StopPass after two wrong engine counts correct given perf.py's 3-attempt loop: first RuntimeError -> retry ->
second wrong count -> StopPass -> propagates out of perf.py's try/except Exception and out of loop.run_until_complete?); the benchmark wrapper
(talos.session.samples-based anomalous count: are the harness's per-request samples appended in the parent between n_samples0 and the end, and
does the tps>1000 condition match tps.py line 464; amx_probes[-1]/binary_checks[-1] alignment with the current config on the cached-provision
path; the finally-block ordering when orig_benchmark raises: is the raw record appended and does the exception still propagate so perf.py marks
the config failed?); the exit block (SystemExit handling, multiprocessing.active_children() actually listing ProcessPoolExecutor workers,
os._exit after logging.shutdown; does the 'FAILED_CONFIGS' line reach driver.log before os._exit given stdout is a file?); name_of() for
results; anything that could make rc wrong (0 vs 2 vs 7).` },
  { key: 'ops-and-plan', prompt: `${CTX}
LENS: machine operations and plan compliance of the NEW behaviours. (a) dut.sh serving-up: the idle wait (60 x 5 s), the python one-liners
(JSON shapes verified above), what happens if /api/config has more than one engine group or count is missing, the 10 s settle, and whether
campaign.sh's dut_t 900 timeout covers the worst case (soak config with 2 tp4 engines loading 4 models after the FIRST switch: estimate the
time from the precedent snapshots: gpt-oss-120b tp4 provision 102 s, 70b tp4 107 s). (b) The check-cell verdict logic against plan 2a
('engine error, timeout, no output' = drop; anything else = not evidence): does check_verdict classify a StopOverrideFailed worker error
(request-level) as fails, a provisioning failure as unknown, a StopPass as unknown, an ssh outage as unknown? Is 'grep -q Failed to provision
model' the right marker (perf.py line 330 text)? (c) The systematic rule now requires a config to fail in both runs of one pass before it is
known: confirm the loop variables (first_failed, known_failed) implement exactly that. (d) Deadlines: DEADLINE_START 19:30Z (campaign start),
PASS_DEADLINE 23:45Z, DRIVER_END_BY 01:00Z, DRIVER_TIMEOUT 5400, CHECK_TIMEOUT 2400: build the timeline from a 13:20Z start with the
first switch costing ~10 min, check cell ~20 min, each later switch ~5 min, each pass ~50 min, and from a 15:00Z late start; where is data
lost first? (e) End state on every exit path (abort_early, stop_safely, normal, signal): package restored? engines up? marker released?
flock released? config.env checked? .done-* marker written? (f) launch.sh preconditions: is the 'newer than check-mode/perf.json' test
correct with NFS mtimes; does the md5 loop's '../lib-guard.sh' path resolve on both hosts; PIPESTATUS use.` },
]
phase('Find')
const found = (await parallel(LENSES.map(l => () => agent(l.prompt, { label: `find:${l.key}`, phase: 'Find', schema: FINDINGS, effort: 'xhigh' }))))
  .filter(Boolean).flatMap((r, i) => (r.findings || []).map(f => ({ ...f, lens: LENSES[i].key })))
log(`${found.length} raw findings`)
const key = f => `${f.file.split('/').pop()}|${f.title.toLowerCase().replace(/[^a-z0-9 ]/g, '').split(' ').slice(0, 6).join(' ')}`
const seen = new Set(); const uniq = []
for (const f of found) { const k = key(f); if (!seen.has(k)) { seen.add(k); uniq.push(f) } }
phase('Verify')
const REFUTE = [
  'reproduce-from-code: re-read the exact current lines, trace the concrete inputs; refuted unless the defect is real as stated.',
  'does-it-matter-and-plan: even if real, does it change the campaign outcome (wrong data, bad end state, lost pass, wasted >15 min) and does the plan (section 2a) actually want the behaviour the finding demands? Refute if the plan or the precedent already sanctions the current behaviour.',
]
const verified = await parallel(uniq.map(f => () => parallel(REFUTE.map(lens => () => agent(`${CTX}
YOU ARE A REFUTER. Lens: ${lens}
Finding (lens ${f.lens}): ${f.severity.toUpperCase()} ${f.file}:${f.line} ${f.title}
${f.description}
Evidence: ${f.evidence}
Proposed fix: ${f.fix}
Read the actual current file(s). Default to refuted=true if you cannot confirm the defect from the code. Cite file:line in the reason.`,
  { label: `verify:${f.title.slice(0, 30)}`, phase: 'Verify', schema: VERDICT, effort: 'high' }))).then(votes => {
    const vs = votes.filter(Boolean); return { ...f, votes: vs, confirmed: vs.length > 0 && vs.every(v => !v.refuted) } })))
const confirmed = verified.filter(Boolean).filter(v => v.confirmed)
const refuted = verified.filter(Boolean).filter(v => !v.confirmed)
log(`${confirmed.length} confirmed, ${refuted.length} refuted`)
return { confirmed: confirmed.map(c => ({ file: c.file.split('/').pop(), line: c.line, severity: c.severity, severity_votes: c.votes.map(v => v.severity), title: c.title, description: c.description, evidence: c.evidence, fix: c.fix, better_fixes: c.votes.map(v => v.better_fix).filter(Boolean), lens: c.lens })),
         refuted: refuted.map(c => ({ file: c.file.split('/').pop(), line: c.line, title: c.title, reasons: c.votes.map(v => v.reason.slice(0, 300)) })) }