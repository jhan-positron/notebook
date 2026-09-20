export const meta = {
  name: 'ci-mimic-feasibility',
  description: 'Read the systems_test nightly harness, platformd provisioning, prior campaign scripts, deb mechanics and nightly reference numbers; then assess whether a whole-3bda run through rinzler+Caddy can reproduce the nightly TPS/TTFT',
  phases: [
    { title: 'Read', detail: 'parallel readers over harness, provisioning, prior scripts, deb build, nightly logs, Slack history, 3bda live state' },
    { title: 'Assess', detail: 'synthesize differences vs the nightly, then adversarial verification' },
  ],
}

const COMMON = `
CONTEXT. jhan wants to run the nightly System CI perf test (repo positron-ai/systems_test, workflow
.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml, DUT delphi-3bda) by hand tomorrow
2026-09-18 after the nightly ends (~13:20 UTC), on the WHOLE machine, with the SAME config as the nightly:
client goes through the Caddy proxy at http://delphi-3bda.positron.internal/v1 (port 80) to the platformd-started
rinzler@N systemd engines, same perf.py configs (12 configs, listed in scripts/perf.py), same load shape, USE_HW_ATTN
NOT set (ingested models keep FPGA attention). Two arms: BASE = the tron .deb the nightly installs (no AMX compiled);
TARGET = our .deb built from PR #4424 (branch jhan-amx-vnniK, head 30c4ac82cb) merged with the same main, with the deb
preset carrying TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON. Goal: BASE must reproduce the nightly's TPS/TTFT per model;
identify EVERYTHING that could prevent that. The client would run from this container (hostname claude-agentsrv), which
reaches the proxy in 2.7 ms, or from the DUT itself if that is closer to CI. The CI runner host is 'system-ci-runner'
(runs-on [self-hosted, system-ci]); we have no access to it.

LOCAL PATHS (this container): systems_test clone = /home/jhan/workspace/ai-runs/systems_test (at origin/main fc27f07,
2026-09-17). Prior campaign scripts: /home/jhan/workspace/intel-AMX/exec/{more-testing-r1,p0perf-20260913,wedperf-20260916,
ci-enable-20260917,nightly-amx-check-20260916}/, guard library /home/jhan/workspace/intel-AMX/exec/lib-guard.sh,
Bill marker tool /home/jhan/workspace/intel-AMX/exec/bill-share.sh. tron worktree at PR #4424 head:
/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K. Results of prior runs: /home/jhan/workspace/intel-AMX/exec/results/.
REMOTE (ssh delphi-3bda, user jhan, passwordless sudo): tron worktrees under /var/tmp/jhan/tron-*; /var/tmp/jhan/tron-ci-enable
holds commit 6f37cd2ed9 (deb preset + TRON_AMX_DISPATCH ON); built deb at /var/tmp/jhan/ci-enable-deb/; cached nightly debs in
/var/cache/apt/archives/; installed tron 2026.09.17-31b80a18; platformd instance envs /etc/rinzler/instance-{0..3}.env (need sudo cat);
Caddy admin API curl localhost:2019/config/; platformd API on localhost:8080.

HARD RULES. On delphi-3bda run READ-ONLY commands only (cat, ls, grep, curl GET, systemctl show/status, journalctl, dpkg -l,
dpkg-deb -e/-c/--fsys-tarfile into /var/tmp/jhan or stdout, git log/show/diff, sudo cat of env files). Never start, stop, restart,
install, remove, write or delete anything on delphi-3bda. Do not run builds. Do not touch the marker /bill-has-instance-0,2.
Do not use the Workflow tool. Return facts with evidence (file:line or command output excerpt), and label anything not verified as
"unverified". Return raw data, not a human-facing narrative.`

const FACTS_SCHEMA = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' }, evidence: { type: 'string' }, confidence: { type: 'string', enum: ['verified', 'likely', 'unverified'] } },
      required: ['claim', 'evidence', 'confidence'] } },
    differences_vs_nightly: { type: 'array', items: { type: 'string' }, description: 'anything in your area that would make our run differ from the nightly' },
    open_questions: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['facts', 'differences_vs_nightly', 'open_questions', 'notes'],
}

const READERS = [
  { key: 'harness-flow', prompt: `${COMMON}
TASK: Read /home/jhan/workspace/ai-runs/systems_test/scripts/system_ci.py fully (952 lines) and scripts/perf.py (test_performance).
Answer precisely: (1) the exact sequence of the perf phase: which functions run, in what order the 12 configs run, how the DUT is
provisioned before/between configs (which model groups are loaded together for tp2 and for tp4, how many engines, calls to
provision/cfgdut/posadm, waits for health), whether the tron package is (re)installed by the harness itself anywhere (grep apt-get,
dpkg, install). (2) Every side effect: talos DB writes, Slack posts (PUBLISH env), threshold evaluation, github, files written,
DUT lease handling (manage_dut_lease.py), DutMonitor over ssh (which user, what it does, could it perturb the DUT). (3) Every env
variable read by the perf path (OPENAI_HOST, OPENAI_TOKEN, PLATFORMD_PORT, DUT, PLATFORM_TYPE, SYSTEM_CI_SPECULATION, SKIP_PROVISION,
HF_TOKEN, PUBLISH ...) and what each changes. (4) How to run ONLY the perf phase standalone with identical behavior (entry point,
minimal env, which pieces to stub: talos, slack), and what the harness would do if the tron package version is unusual
(e.g. a locally built 2026.09.17-<sha>-jhan-... version) - does anything parse the version? (5) The exact log lines the perf phase
prints per config (e.g. 'Perf test for X completed in N mins', 'Running averages: TTFT=, TPS=') so results can be parsed.
Also read scripts/provision.py, scripts/cfgdut.py, scripts/posadm.py and testlib/inventory.py (class Andoria) for the platformd
calls the perf path makes (HTTP endpoints, payloads: model lists, tp, engine counts, hugepages, speculation).` },
  { key: 'load-shape', prompt: `${COMMON}
TASK: Read /home/jhan/workspace/ai-runs/systems_test/testlib/tps.py fully (530 lines), scripts/perf.py configs + format_perf_params,
testlib/prompt.py (or wherever prompts are built; grep sharegpt, shared_prompt_length), testlib/config.py, and testlib/results.py
(Goal/thresholds), thresholds/system_ci_perf.yaml. Answer precisely: (1) for each of the 12 configs: users, rounds, prompt_length,
shared_prompt_length, generate_length, start_capture/end_capture, prompt_mode, ignore_eos / max_tokens / temperature / stream,
how the prompts are generated and seeded (random.seed in system_ci.py: seed = time-based! -> are prompts different every night? does
that matter for TPS?), which tokenizer (HF hub id per model via testlib/hf_models.py hf_map; needs HF_TOKEN for gated repos? which
repos are gated), (2) exactly how TPS is computed (per user, capture window, mean across users and rounds, 'slowest user'), how TTFT
is computed (first token wall time incl. network?), how the numbers in the Slack line and in 'Running averages' relate to the
per-user Done lines, (3) how users are dispatched: all users start at once per round? any stagger? one connection each? through
OPENAI_HOST (the proxy), (4) whether the client host CPU/network could limit anything at 32 users (llama-3b config: 32 users,
generate 845), (5) the goal/threshold per config on granite_rapids_72_rinzler (scripts/system_ci.py get_goal + yaml) as reference.` },
  { key: 'provisioning-platformd', prompt: `${COMMON}
TASK: Establish how the nightly lays out engines on delphi-3bda and how we would reproduce it with our own .deb installed.
(A) Read (local) scripts/cfgdut.py, scripts/provision.py, scripts/posadm.py, testlib/inventory.py, testlib/dut_monitor.py in
/home/jhan/workspace/ai-runs/systems_test: what HTTP calls to platformd (port 8080) configure models/tp/engine counts; does any step
ssh to the DUT as 'positron' and run sudo apt-get (the workflow yaml does that OUTSIDE the harness; check whether cfgdut/provision
also do it); what 'legacy posadm path' means; how the harness decides 4 tp2 engines / 2 tp4 engines; how it waits for 'All N inference
engines are running' / 'All N Caddy upstreams are healthy'. (B) On delphi-3bda (read-only, ssh delphi-3bda): sudo cat
/etc/rinzler/instance-{0,1,2,3}.env (all four; instance-2/3 dated 08:43 UTC may be the tp2 layout, instance-0/1 10:13 the tp4 layout),
curl -s localhost:2019/config/ (Caddy: upstream list, lb policy least_conn, health checks), curl the platformd API (try
curl -s localhost:8080/ and the endpoints the harness uses; GET only), cat /etc/systemd/system/rinzler@.service (note the hand-added
--num-expert-replicas 750 in ExecStart and whether it is a regular file of the deb: dpkg -S), systemctl show rinzler@1 -p ExecStart
-p NeedDaemonReload, ls /dev/hugepages, grep Huge /proc/meminfo, cat /etc/default/grub or /proc/cmdline for hugepages, and check what
a fresh 'apt-get remove tron; dpkg -i X.deb' does to running units: dpkg-deb -e /var/cache/apt/archives/tron_2026.09.17-31b80a18_amd64.deb
/var/tmp/jhan/deb-ctl-inspect (extracts control scripts; then cat preinst postinst prerm). (C) Explain how the nightly's engines get
started after the apt install (platformd? the ci-runner-stop timer at 02:45 UTC? the harness's provision call?) using journalctl
-u platformd --since '2026-09-17 03:00' --until '2026-09-17 11:00' --no-pager | head -200 (sudo if needed) and
sudo journalctl _COMM=sudo --since '2026-09-17 03:00' --until '2026-09-17 04:00' --no-pager. (D) Report whether stopping Bill's
rinzler@1 and re-provisioning the whole machine through platformd would give exactly the nightly's layout.` },
  { key: 'prior-scripts', prompt: `${COMMON}
TASK: Read our prior campaign scripts to list what can be reused and what traps they record: /home/jhan/workspace/intel-AMX/exec/
more-testing-r1/{run_cell.sh,rz.sh,st_perf.py,smoke.sh,talos_stub/talos.py}, /home/jhan/workspace/intel-AMX/exec/more-testing-r1.sh,
p0perf-20260913/{campaign.sh,rz.sh,launch.sh,combine.py}, wedperf-20260916/{campaign.sh,build.sh,build-chain.sh,launch-campaign.sh},
ci-enable-20260917/runtime-check.sh, lib-guard.sh (all functions, esp. rinzler_takeover_if_idle, ci_lease_busy, campaign_guard_acquire,
wait_for_ci_release, blackout_active), bill-share.sh. Answer: (1) how each script waited for the CI lease and took the machine
(exact function calls, hold windows 01:40-04:30 UTC, idle checks), (2) how the DUT-side python venv for systems_test was set up
(/var/tmp/jhan/st-venv? uv? which python) and how the client was pinned, (3) how st_perf.py differs from the harness's own perf
phase (tokenizer source, talos stub, no provisioning), (4) how results were stored (json layout) and how the report generators
(p0perf-20260913/gen_report.py, wedperf-20260916/gen_report.py) read them, so a new campaign can reuse the format, (5) the deadline /
abort / pgrep traps recorded in comments, (6) how the ci-enable runtime-check ran the deb-extracted rinzler (LD_LIBRARY_PATH, cwd,
fusermount3 trap) - relevant if we ever run the packaged binary by hand instead of via systemd.` },
  { key: 'deb-build', prompt: `${COMMON}
TASK: Work out exactly how to build the TARGET .deb and what its identity will be. Read (local) /home/jhan/workspace/intel-AMX/
VNNIed-K-in-place/tron-VNNIed-K/{CMakeLists.txt (options TRON_AMX_DISPATCH, TRON_K_VNNI and any dependency between them, lines ~40-60
and wherever they are used), CMakePresets.json (preset deb and its inherits chain), GNUmakefile (deb rule ~line 440-470, DEB_NAME,
version string derivation: grep -n 'DEB_NAME\\|VERSION\\|git describe\\|rev-parse' GNUmakefile CMakeLists.txt cmake/*.cmake
packaging/*), packaging/ (cpack config, postinst/prerm, systemd unit install)}. Answer: (1) does TRON_K_VNNI=ON need anything beyond
TRON_AMX_DISPATCH=ON at configure time; is either option's code active by default at run time or gated by an env var (TRON_AMX_DISABLE,
TRON_K_VNNI env?) - grep h/ src/ for getenv of TRON_AMX_DISABLE, TRON_K_VNNI, USE_HW_ATTN; (2) how the deb version is built from the
git state (branch name in version? dirty flag?) so we can predict the filename and whether dpkg -i would be a downgrade relative to a
2026.09.18-<sha> nightly deb (dpkg --compare-versions locally if available); (3) the exact 'make deb' recipe that worked on 2026-09-17
on 3bda: read /home/jhan/workspace/intel-AMX/exec/results/ci-enable-20260917/make-deb.log head/tail and any build script in
/home/jhan/workspace/intel-AMX/exec/ci-enable-20260917/ or PR3879/new-PRs/CI-enable/Thursday-report.md (find it under
/home/jhan/workspace/intel-AMX/) for PATH/uv/ghcup/NPROC_BUILD/taskset details and duration; (4) on delphi-3bda (read-only):
git -C /var/tmp/jhan/tron-ci-enable show 6f37cd2ed9 (the preset one-liner), git -C /var/tmp/jhan/tron-ci-enable log --oneline -3
origin/main, origin/jhan-amx-vnniK, merge-base; and whether origin/jhan-amx-vnniK merges cleanly into origin/main WITHOUT writing:
use 'git -C /var/tmp/jhan/tron-ci-enable merge-tree $(git -C /var/tmp/jhan/tron-ci-enable merge-base origin/main origin/jhan-amx-vnniK)
origin/main origin/jhan-amx-vnniK | grep -c "^<<<<<<<"' (git 2.34 three-arg form; prints conflict marker count) and list the files
main touched since the merge base that the PR also touches (git diff --name-only merge-base..origin/main | sort > A; same for the PR;
comm -12). (5) What in the packaged binary proves both options are compiled in (strings/objdump recipe from the ci-enable work:
TRON_AMX_DISABLE literal, AMX tile instruction count; is there a TRON_K_VNNI-specific literal or symbol?).` },
  { key: 'nightly-logs', prompt: `${COMMON}
TASK: Get the nightly's own measured numbers and timings as the reference for tomorrow. (1) Check 'gh auth status' and
'gh run list -R positron-ai/systems_test -w "System CI (Rinzler 72-core Intel system OCI version)" -L 6 --json databaseId,createdAt,
conclusion,headSha' . If it works, download the log of the most recent completed run (gh run view <id> -R positron-ai/systems_test
--log > /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/cfafa211-4409-4b46-a9f5-c701b81efeba/scratchpad/nightly-<id>.log;
create the dir if missing) and extract with grep: the tron package version installed ('Setting up tron' / 'Version'), the perf
section: for each of the 12 configs the 'Perf test for <model> completed in <N>mins' line and the preceding 'Running averages: TTFT=,
TPS=' line, the per-user 'Done' lines count and their TPS spread (two speed groups?), the provisioning lines ('Provisioning models via
legacy posadm path', 'All N inference engines are running', 'All N Caddy upstreams are healthy'), the timestamps of perf phase start
and end (total perf-phase minutes), and the order in which configs ran. Do this for the two most recent runs if possible (09-17 and
09-16) to see night-to-night variation. Also fetch 'gh run list -R positron-ai/tron -w publish-deb.yml -L 3 --json databaseId,
createdAt,headSha,status,conclusion' to learn which main sha the deb of 2026-09-18 is (or will be) built from. (2) If gh fails, say so
and fall back to /home/jhan/workspace/intel-AMX/exec/results/more-testing-r1/ci-reference-20260904.json and
/home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/{slack-reports.tsv,evidence.json}. Return per-config reference numbers
(TPS mean, slowest user, TTFT ms, minutes) per run as data.` },
  { key: 'slack-history', prompt: `${COMMON}
TASK: Build the night-to-night reference distribution from Slack. Use ToolSearch to load the Slack tools (query
"select:mcp__claude_ai_Slack__slack_read_channel,mcp__claude_ai_Slack__slack_search_public_and_private"). Read channel C06S8PNDBQA
(#ci-cd-notifications) for the last ~10 days of GRANITE_RAPIDS_72_RINZLER System CI reports (DUT delphi-3bda; the qwen tp2 threshold
175.00 identifies this machine - the GENOA96 reports with threshold 195.00 are the AMD machine, exclude them). For each report
(date, tron version) extract every perf line of the 12 configs: model, users, TPS mean, threshold, slowest user TPS, TTFT ms, and
the verdict. Also capture the 'YAML THRESHOLDS' section if present. Return a table as JSON in notes: per config -> list of
{date, tron_version, tps, slowest, ttft_ms}. Compute per config the mean, sd and min-max of TPS and TTFT across nights (use python3
if convenient). If the Slack tool is not reachable, say so and fall back to /home/jhan/workspace/intel-AMX/exec/nightly-amx-check-20260916/
slack-reports.tsv (only the qwen tp2 line per night).` },
  { key: 'client-env', prompt: `${COMMON}
TASK: Determine where the client can run and what it needs. (1) On this container: which uv; which python3 and version; ls
/home/jhan/workspace/ai-runs/systems_test/.venv 2>/dev/null; cat pyproject.toml (deps, python version); is HF_TOKEN set in the env or
in ~/.cache/huggingface/token or ~/.huggingface; does ~/.cache/huggingface/hub already hold tokenizers for the 11 model slugs (list dirs);
can this host resolve/reach system-ci-runner (getent hosts system-ci-runner system-ci-runner.positron.internal; curl -sS -m 3
http://system-ci-runner:80 || true) - do not attempt logins; measure the HTTP round trip to the proxy 20 times: for i in $(seq 20); do
curl -s -o /dev/null -w '%{time_total}\\n' http://delphi-3bda.positron.internal/v1/models; done | sort -n | awk 'NR==1||NR==10||NR==20';
nproc and load on this container (it must drive 32 concurrent streams). (2) On delphi-3bda (read-only): ls /var/tmp/jhan/st-venv/bin/python
&& /var/tmp/jhan/st-venv/bin/python -c 'import sys;print(sys.version)'; ls /opt/positron/weights/huggingface/ | head -40 (local
tokenizer dirs used by st_perf.py); which cores would be free for a DUT-local client in the nightly's 4-engine tp2 layout (read
sudo cat /etc/rinzler/instance-*.env CPUAFFINITY and --app-cores/--dev-cores and compute the complement of 0-287). (3) Read the
README.md and CLAUDE.md of the systems_test clone for how the harness is meant to be run (uv run system_ci; env). (4) Check whether
the harness's prompt generation needs network: grep -n 'from_pretrained\\|hf_hub\\|snapshot_download\\|requests.get\\|urlopen' -r
/home/jhan/workspace/ai-runs/systems_test/testlib /home/jhan/workspace/ai-runs/systems_test/scripts | head -40.` },
]

phase('Read')
const reads = await parallel(READERS.map(r => () =>
  agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: FACTS_SCHEMA }).then(x => ({ key: r.key, result: x }))))
const readsOk = reads.filter(Boolean)
log(`readers done: ${readsOk.length}/${READERS.length}`)

const ASSESS_SCHEMA = {
  type: 'object',
  properties: {
    differences: { type: 'array', items: { type: 'object', properties: {
      item: { type: 'string' }, area: { type: 'string' },
      expected_effect_tps: { type: 'string' }, expected_effect_ttft: { type: 'string' },
      mitigation: { type: 'string' }, blocking: { type: 'boolean' }, evidence: { type: 'string' } },
      required: ['item', 'area', 'expected_effect_tps', 'expected_effect_ttft', 'mitigation', 'blocking', 'evidence'] } },
    plan_steps: { type: 'array', items: { type: 'string' } },
    risks: { type: 'array', items: { type: 'string' } },
    reference_numbers_note: { type: 'string' },
    verdict: { type: 'string' },
    open_questions_for_jhan: { type: 'array', items: { type: 'string' } },
  },
  required: ['differences', 'plan_steps', 'risks', 'reference_numbers_note', 'verdict', 'open_questions_for_jhan'],
}

phase('Assess')
const synth = await agent(`${COMMON}
You are the synthesizer. Below are the structured findings of 8 readers (JSON). Produce: (1) the complete list of DIFFERENCES between
our planned run (whole 3bda after the nightly, client from claude-agentsrv or the DUT through Caddy, platformd-provisioned engines,
BASE = nightly deb, TARGET = our deb) and the real nightly, each with expected effect on TPS and on TTFT (quantify when a reader gave
numbers, else say 'unknown; measurement: ...'), a mitigation, and whether it blocks the goal 'BASE reproduces nightly TPS/TTFT';
(2) a step-by-step plan for the campaign script (wait for lease clear + takeover, stop rinzler units, base arm provisioning + perf, deb
swap with exact commands, target arm, restore, marker release), with the exact harness entry point and env; (3) risks; (4) which
reference numbers to compare BASE against (last nightly + night-to-night sd); (5) a verdict on achievability; (6) questions only jhan can
answer. Be exhaustive; do not drop reader facts. Verify any claim you are unsure of by reading the file yourself.

READER FINDINGS:
${JSON.stringify(readsOk, null, 1)}`, { label: 'synthesize', phase: 'Assess', schema: ASSESS_SCHEMA })

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    refuted_or_wrong: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why: { type: 'string' }, evidence: { type: 'string' } }, required: ['item', 'why', 'evidence'] } },
    missing: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why_it_matters: { type: 'string' }, evidence: { type: 'string' } }, required: ['item', 'why_it_matters', 'evidence'] } },
    confirmed_blocking: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['refuted_or_wrong', 'missing', 'confirmed_blocking', 'notes'],
}
const LENSES = [
  { key: 'harness-code', lens: 'the systems_test harness code: re-read scripts/system_ci.py, scripts/perf.py, testlib/tps.py, scripts/cfgdut.py, scripts/provision.py and check every claim about provisioning order, env vars, side effects, entry point and log lines' },
  { key: 'machine-ops', lens: 'machine operations on delphi-3bda: deb swap (apt remove/dpkg -i, postinst daemon-reload, prerm), platformd re-provisioning, Caddy upstreams, hugepages, the hand-edited unit file with --num-expert-replicas 750 (reverted by the nightly apt reinstall at ~03:39 UTC; would it be back?), Bill marker, lease + takeover timing, restore path; verify by read-only commands on the DUT' },
  { key: 'measurement', lens: 'measurement validity: client host (network RTT, CPU for 32 streams), prompt seeding, capture windows, TTFT definition, night-to-night variance, n=1 per arm, order effects (base first then target), thermal/warm-up, prefix cache, what "same TPS" can mean statistically' },
]
const verdicts = await parallel(LENSES.map(l => () => agent(`${COMMON}
You are an adversarial verifier with the lens: ${l.lens}. Try to REFUTE or find MISSING items in the synthesizer's assessment below.
Every refutation and every missing item needs evidence you obtained yourself (file:line or read-only command output). Default to
reporting nothing rather than speculation. ASSESSMENT:
${JSON.stringify(synth, null, 1)}`, { label: `verify:${l.key}`, phase: 'Assess', schema: VERDICT_SCHEMA }).then(v => ({ lens: l.key, verdict: v }))))

return { readers: readsOk, assessment: synth, verifications: verdicts.filter(Boolean) }