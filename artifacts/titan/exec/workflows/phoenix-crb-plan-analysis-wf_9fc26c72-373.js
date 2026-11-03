export const meta = {
  name: 'phoenix-crb-plan-analysis',
  description: 'Paraphrase Jeremy requests, analyze phoenix-crb evidence across 5 dimensions, adversarially verify, critique completeness',
  phases: [
    { title: 'Paraphrase', detail: '3 independent plain-English paraphrases + 1 judge' },
    { title: 'Analyze', detail: '5 dimension analysts over the evidence files' },
    { title: 'Verify', detail: '2 adversarial verifiers per dimension (evidence lens, Linux-semantics lens)' },
    { title: 'Critic', detail: 'completeness critic over everything' },
  ],
}

const SP = args.scratch
const COMMON = `
You are helping Jibin (jhan@positron.ai) plan work on the Arm server "phoenix-crb" (192.168.2.45) that Jeremy (SDK side) asked for.
Read these files first (absolute paths):
  ${SP}/plan/requests.txt           Jeremy's three messages, verbatim.
  ${SP}/plan/draft-findings.md      The orchestrator's numbered draft findings (F1-F20), Linux-semantics claims (S1-S8), ask status (A1-A10), decisions (D1-D4), plan (P0-P5), gaps (G1-G6). Treat every item as a claim to check, not as truth.
  ${SP}/inspect/phoenix-crb-inspection.txt   raw read-only inspection output (sections "=== name ===")
  ${SP}/inspect/phoenix-crb-followup.txt     staged workspace, toolchain, 3 s pinned-spin clock measurement, dmesg, timers
  ${SP}/inspect/phoenix-crb-round3.txt       key fingerprints, toolchain README, Jeremy's job scripts/results, residual tick measurement
  ${SP}/inspect/phoenix-crb-round4.txt       Jeremy's churn-r1 job log, latency-judge summary, isolation snapshot, SDK CI scripts
  ${SP}/inspect/phoenix-crb-round5.txt       SDK source grep: thread pinning, scheduling policy, perf-lane rules, lateness rule
  ${SP}/inspect/inspect.sh (and followup.sh, round3.sh, round4.sh)  the scripts that produced the outputs
Host access, if you need to re-check something: ssh -o BatchMode=yes -o ConnectTimeout=10 positron-perf@192.168.2.45 '<command>'
STRICT RULES for the host: read-only commands only (cat, ls, grep, awk, ps, systemctl show/cat/is-active, dmesg, stat, find, df, git log/status, python3 reading files). Never write, create, delete or modify any file on the host, never run sudo, never change any setting, never run anything that loads the machine for more than 5 seconds, never read ~/.ssh private material, never log in as any other user. Keep each command under 20 seconds (wrap with timeout). If you can answer from the files, do not touch the host.
Web access: you may use WebFetch/WebSearch for Linux kernel documentation and source (kernel.org, github.com/torvalds/linux, docs.kernel.org, man7.org, ubuntu docs) when a claim is about Linux behaviour.
Your final output is raw data for the orchestrator (not a human message); use the StructuredOutput tool with the schema you were given. Be precise: quote the exact evidence line (file name + section name + the text) for every claim. Numbers must carry units. Say "insufficient data" where the evidence does not decide a question, and name the command or source that would decide it. Do not invent facts about Positron, Jeremy or the SDK beyond what the files show.
`

const PARA_SCHEMA = {
  type: 'object',
  properties: {
    messages: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string', description: 'message-1 | message-2 | message-3' },
      title: { type: 'string' },
      plain_english_bullets: { type: 'array', items: { type: 'string' }, description: 'short bullets, one claim each, jargon defined inline in parentheses' },
      asks: { type: 'array', items: { type: 'object', properties: {
        ask: { type: 'string' },
        status: { type: 'string', description: 'done | not-done | partly-done | not-possible-on-current-kernel | unknown' },
        status_evidence: { type: 'string' },
        needs_root: { type: 'boolean' }, needs_reboot: { type: 'boolean' }, needs_kernel_change: { type: 'boolean' },
        needs_jeremy_input: { type: 'boolean' }, why_jeremy: { type: 'string' },
      }, required: ['ask', 'status', 'status_evidence', 'needs_root', 'needs_reboot', 'needs_kernel_change', 'needs_jeremy_input'] } },
    }, required: ['id', 'title', 'plain_english_bullets', 'asks'] } },
    corrections_to_jeremys_statements: { type: 'array', items: { type: 'string' }, description: 'where a statement in the messages is inaccurate for this host, with the evidence' },
    terms_to_define: { type: 'array', items: { type: 'object', properties: { term: { type: 'string' }, definition: { type: 'string' } }, required: ['term', 'definition'] } },
    draft_corrections: { type: 'array', items: { type: 'string' }, description: 'disagreements with draft-findings.md sections C and D, with reasons' },
  },
  required: ['messages', 'corrections_to_jeremys_statements', 'terms_to_define', 'draft_corrections'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      claim: { type: 'string', description: 'one precise sentence' },
      evidence: { type: 'string', description: 'file + section + quoted text/numbers, or URL' },
      confidence: { type: 'string', description: 'high | medium | low' },
      implication: { type: 'string', description: 'what it means for the plan' },
      action: { type: 'string', description: 'concrete step, with the exact command(s) where relevant' },
      owner: { type: 'string', description: 'Jibin | admin (arm account) | Jeremy | kernel provider' },
      needs_root: { type: 'boolean' }, needs_reboot: { type: 'boolean' }, needs_kernel_change: { type: 'boolean' }, needs_jeremy_input: { type: 'boolean' },
      draft_refs: { type: 'array', items: { type: 'string' }, description: 'draft item ids this confirms/corrects/refutes, e.g. F7, S2' },
    }, required: ['id', 'claim', 'evidence', 'confidence', 'implication', 'action', 'owner', 'needs_root', 'needs_reboot', 'needs_kernel_change', 'needs_jeremy_input'] } },
    draft_verdicts: { type: 'array', items: { type: 'object', properties: {
      draft_item: { type: 'string' }, verdict: { type: 'string', description: 'confirmed | corrected | refuted | unverifiable' }, note: { type: 'string' },
    }, required: ['draft_item', 'verdict', 'note'] } },
    additional_checks_run: { type: 'array', items: { type: 'string' }, description: 'commands you ran on the host or URLs you read, with the key result' },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['dimension', 'findings', 'draft_verdicts', 'additional_checks_run', 'open_questions'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    verdicts: { type: 'array', items: { type: 'object', properties: {
      finding_id: { type: 'string' },
      verdict: { type: 'string', description: 'confirmed | refuted | corrected | unverifiable' },
      reason: { type: 'string' },
      correction: { type: 'string', description: 'the corrected claim if refuted/corrected, else empty' },
      source: { type: 'string', description: 'evidence file+section, host command result, or URL' },
    }, required: ['finding_id', 'verdict', 'reason', 'correction', 'source'] } },
    extra_findings: { type: 'array', items: { type: 'string' }, description: 'important facts the analyst missed, each with its source' },
  },
  required: ['lens', 'verdicts', 'extra_findings'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    missing: { type: 'array', items: { type: 'object', properties: { item: { type: 'string' }, why_it_matters: { type: 'string' }, how_to_get_it: { type: 'string' } }, required: ['item', 'why_it_matters', 'how_to_get_it'] } },
    risks: { type: 'array', items: { type: 'string' } },
    contradictions: { type: 'array', items: { type: 'string' }, description: 'places where analysts/verifiers disagree, and which side the evidence favours' },
    questions_for_jeremy: { type: 'array', items: { type: 'string' }, description: 'ordered by how much the answer changes the plan; mark each MUST or NICE' },
    questions_for_admin: { type: 'array', items: { type: 'string' } },
    plan_edits: { type: 'array', items: { type: 'string' }, description: 'concrete edits to the draft plan P0-P5, with reasons' },
    recommended_friday_target: { type: 'string', description: 'what to promise Jeremy for Fri 23 Oct, in two sentences' },
  },
  required: ['missing', 'risks', 'contradictions', 'questions_for_jeremy', 'questions_for_admin', 'plan_edits', 'recommended_friday_target'],
}

// ---------- Phase 1: paraphrase (3 independent) + judge ----------
phase('Paraphrase')
const paraAngles = [
  'Read as a Linux systems administrator who must execute the asks: separate what needs root, what needs a reboot, what needs a different kernel, and what is already done on the host.',
  'Read as a careful technical writer: paraphrase each message in plain English for an engineer who has never seen the project (define every term inline), and extract every discrete ask, including implicit ones (deadlines, run windows, access paths, "one job at a time").',
  'Read as a skeptic: find every statement in the three messages that is wrong or outdated for this host (compare with the evidence files), every ambiguity (e.g. "one isolated core" vs "cores 120-127", "no outbound network", "both need root and a reboot"), and every ask that cannot proceed without Jeremy answering a question.',
]
const paras = await parallel(paraAngles.map((angle, i) => () => agent(
  `${COMMON}\nTask (paraphrase, angle ${i + 1}): ${angle}\nProduce: for each of the three messages, plain-English bullets (one claim per sentence, no idioms, terms defined inline) and the list of asks with their status on the host today (use the evidence files; cite the section). Then: corrections to Jeremy's statements, terms that a newcomer needs defined, and any disagreement with draft-findings.md sections C (ask status) and D (does the work need Jeremy's input).`,
  { label: `paraphrase:${i + 1}`, phase: 'Paraphrase', schema: PARA_SCHEMA, effort: 'high' },
)))
const paraOk = paras.filter(Boolean)
log(`paraphrases: ${paraOk.length}/3`)
const paraJudge = await agent(
  `${COMMON}\nTask (judge/merge): Three independent paraphrases of Jeremy's messages follow as JSON. Merge them into ONE best version: keep the clearest plain-English bullets (one claim per sentence; define terms inline; no idioms), union the asks (dedupe), and for each ask decide the status, root/reboot/kernel needs and whether Jeremy's input is needed, using the evidence files to settle disagreements (cite the section). Keep every correction to Jeremy's statements that the evidence supports; drop any that it does not. Output the merged result in the same schema.\n\nPARAPHRASES:\n${JSON.stringify(paraOk, null, 1)}`,
  { label: 'paraphrase:judge', phase: 'Paraphrase', schema: PARA_SCHEMA },
)

// ---------- Phase 2 + 3: analysts, each followed by two verifiers (pipeline, no barrier) ----------
const DIMS = [
  { key: 'kernel-isolation', prompt: `Dimension: KERNEL AND CPU ISOLATION. Cover: (1) exactly what the running vendor kernel 7.1.3-arm-agi supports and lacks for isolcpus / nohz_full / rcu_nocbs / irqaffinity (draft F2, S1, S2, S3, S7); check kernel/sched/isolation.c housekeeping_setup() behaviour for the "nohz" flag without CONFIG_NO_HZ_FULL, and whether unknown parameters like nohz_full= are merely warned about; (2) the three ways to get nohz_full (rebuild vendor kernel from commit 4dbc8bb88858 with CONFIG_NO_HZ_FULL=y; a build from the kernel provider; the installed stock 6.8.0-147-generic) with risk assessment for an EVT0 board whose vendor kernel has "Arm AGI CPU A0" GIC erratum and "Broken broadcast TLBI completion" workarounds (draft F3, F4, S6) — check whether those workarounds exist in upstream 6.8 (search the kernel source/docs for "AGI" errata); (3) the no-reboot alternative: cgroup v2 cpuset isolated partition on this kernel (draft S4): exact steps, what it gives (scheduler domain isolation, unbound workqueue exclusion since 6.7?) and what it does not (nohz_full, managed IRQs), and whether systemd 255 on Ubuntu 24.04 interferes; (4) whether isolcpus=domain alone also removes the CPUs from unbound workqueues (kernel/workqueue.c housekeeping HK_TYPE_DOMAIN use) and from timer migration; (5) the GRUB mechanics on this host (draft S8): the cloud-image drop-in overriding GRUB_CMDLINE_LINUX_DEFAULT, GRUB_DEFAULT=saved with saved_entry on the vendor kernel, /boot/vmlinuz symlink on the stock kernel, update-grub, how to add args to only the vendor entry or to all; (6) what isolcpus=domain on all 8 CPUs does to Jeremy's threads that are restricted to 120-126 as a group (no load balancing inside the isolated set: D3) and the recommended split (e.g. isolate only the pass-thread CPU(s)); (7) exact proposed kernel command line additions for the current kernel and for a NO_HZ_FULL kernel, and the exact verification commands after reboot (including dmesg lines "NO_HZ: Full dynticks CPUs" and "rcu: Offload RCU callbacks").` },
  { key: 'clock-cpufreq', prompt: `Dimension: CPU CLOCK AND CPUFREQ. Cover: (1) the current state (cppc_cpufreq, schedutil on 128 single-CPU policies, 1.6-2.8 GHz, boost 0, no cpuidle driver) and what "performance governor, no boost" means here (draft F6); (2) the live change (exact root commands for 120-127 only and for all 128 policies), its persistence across reboot (cpufreq.default_governor=performance boot parameter: does it apply to a modular driver loaded later? cite Documentation/admin-guide/pm/cpufreq.rst or kernel-parameters.txt; and/or a systemd oneshot unit), and anything on the host that could revert it (draft S5); (3) the measurement method the test account can use without root: acpi_cppc feedback_ctrs deltas (delivered perf = reference_perf x delta(del)/delta(ref); 1 perf unit = 20 MHz here) and cpuinfo_avg_freq via AMU — verify the formula against Documentation/admin-guide/acpi/cppc_sysfs.rst and check my 3 s measurement arithmetic in followup.txt (draft F7); (4) hypothesis H1 (draft F8): a thread that sleeps until 100 us before a deadline and then spins stays near 1.6 GHz under schedutil (schedutil rate limit, utilization of a mostly-sleeping task, CPPC transition behaviour) and this contributes to the fake device's lateness (late_max 220 us vs band 2.5 us); state what evidence supports/undermines it and the exact experiment with ~/positron/runs/hiccup/hiccup (read its usage from hiccup.c) to confirm or reject it, runnable by positron-perf before/after the governor change; (5) wake-up latency: cpuidle "driver: none" means CPUs idle in WFI only — what that implies for "waking a waiting reader", and whether anything else (e.g. arch_timer event stream, PSCI) matters; (6) thermal/power risk of host-wide performance governor on 128 cores (no CPU thermal zones are exposed; hwmon shows only NIC temperatures) and the recommendation (120-127 only vs host-wide); (7) what "clock stays fixed" evidence to give Jeremy and what acceptance rule to propose (D4).` },
  { key: 'interrupts-noise', prompt: `Dimension: INTERRUPTS, TICK AND BACKGROUND NOISE ON CPUs 120-127. Cover: (1) what currently lands on 120-127 (draft F9, F10): the managed NVMe queue IRQs (effective affinity one CPU each), arch_timer tick (HZ=250: measured 1261 ticks in 5 s on a busy CPU), function-call IPIs, rescheduling IPIs, unbound kworkers seen on those CPUs, per-CPU kthreads (migration/N, ksoftirqd/N, kworker/N) — explain which of these isolcpus=domain,managed_irq + irqaffinity=0-119 removes, which only nohz_full/rcu_nocbs remove, and which nothing removes (IPIs for TLB shootdown etc.); quantify from the evidence; (2) whether a managed NVMe IRQ on CPU N fires only for I/O submitted from CPU N (blk-mq queue mapping) and whether /proc/irq/N/smp_affinity writes are refused for managed IRQs; (3) the background services and timers that could disturb a timed run (draft F11): apt-daily/apt-daily-upgrade/unattended-upgrades (and the fact that unattended-upgrades already installed kernels on Oct 9 and Oct 15), sysstat-collect every 10 min, logrotate/dpkg-db-backup at 00:00 UTC, fstrim Mon 26 Oct 00:27 UTC, netperf server, smartd, man-db, motd-news, update-notifier, snapd timers, e2scrub — for each: what it does, how long/heavy, whether it can run on 120-127 today, and the exact root command to pause it for Oct 22 – Nov 5 and to restore after; (4) RCU: rcu_preempt and rcu_exp_* kthreads affinities seen in the evidence; what rcu_nocbs would change and what it would not; (5) a measurement protocol positron-perf can run during a quiet window to prove the CPUs are quiet (per-CPU /proc/interrupts deltas, /proc/stat idle, threads seen on 120-127 — note Jeremy's isol.py already does part of this); (6) the ordering of "nothing else running" with user arm's console session and the 192.168.1.200 logins — what reservation rule to propose.` },
  { key: 'access-tooling', prompt: `Dimension: ACCOUNT, ACCESS, TOOLING, STORAGE AND WHAT JEREMY'S SIDE ALREADY DID. Cover: (1) the account state (draft F12, F13): keys installed and whose, locked password, no usable sudo, the unreadable 49-byte sudoers drop-in positron-perf-setup, rtprio/nice hard limits 0, memlock, perf_event_paranoid=2, dmesg readable, sshd password auth enabled — which of these matter for Jeremy's runs (check round5: the runtime pins with sched_setaffinity/pthread_setaffinity_np only; no SCHED_FIFO/mlockall in runtime code; but the design doc mentions SCHED_FIFO for the interpreter core) and what, if anything, the admin should change; (2) the staged workspace ~/positron (draft F14, F15): confirm from round3/round4 what is there (toolchain versions, venvs, source commit, weights, build logs, the churn-r1 job and its INFRA verdict, hiccup/logits-bench probes) and conclude which of Jeremy's original requirements (clang 18, CMake >= 3.25, Ninja, Python >= 3.11 + headers, 100 GB, no sudo, no outbound) are satisfied and by whom; (3) the SDK's own host rules (round5): churn.py core_isolated = pass core in /sys/devices/system/cpu/isolated (isolcpus only), tools/perf/records.py requiring a core in BOTH isolcpus and nohz_full and "runner/service" checks, perf_lane.py refusing a host that is not "the perf host" — spell out exactly what each tool needs so Jibin can ask Jeremy which tool gates the demo numbers (D2); (4) what voided churn-r1 (round4: device late_mean 6.2 us, late_max 220 us, lateness_band 2.5 us, void=true; bind max 1482.5 us) and what host changes could plausibly fix it (label hypotheses as such, name the measurement); (5) network paths (draft F17): outbound works from the host; sw-dev-01 resolves only via Tailscale from Jibin's workstation; the one command to verify sw-dev-01 -> 192.168.2.45:22; which key/path Jeremy used is unknown (system journal unreadable) — what to ask; (6) storage: 1.7 TB free, no quota, Jeremy's layout under ~/positron; what, if anything, to do about "about 100 GB"; (7) what positron-perf can verify by itself after the admin's changes (exact commands: /proc/cmdline, /sys/devices/system/cpu/isolated, nohz_full, governors, dmesg greps, /proc/irq effective affinities, feedback_ctrs).` },
  { key: 'schedule-coordination', prompt: `Dimension: SCHEDULE, OWNERSHIP, DECISIONS AND THE MESSAGE TO JEREMY. Cover: (1) build the dated timeline from Wed 21 Oct 2026 to Thu 5 Nov 2026 with three clocks: host (UTC), Jibin (PDT, UTC-7), Jeremy (his git commit carries -0400, i.e. US Eastern, EDT) — deadlines: account + one isolated core by Fri 23 Oct; counted runs from Mon 26 Oct; demo Thu 5 Nov; note the host timers that collide with likely windows (fstrim Mon 26 Oct 00:27 UTC = Sun 25 Oct 17:27 PDT; logrotate 00:00 UTC daily = 17:00 PDT; apt-daily-upgrade 06:00-07:00 UTC = 23:00-00:00 PDT); (2) ownership: the only sudoer is the arm account; arm logged in today from 192.168.2.136 which is Jibin's own workstation address (draft F20) — do NOT assert that Jibin holds that account; phrase it as a question with the evidence; also the 192.168.1.200 sessions and the console session; what coordination the reboot needs; (3) the decisions Jeremy must make before counted runs (draft D1-D4) — check each against the evidence and the SDK tool rules in round5; add or remove decisions; for each say what happens if Jeremy does not answer by Friday; (4) the corrections to Jeremy's statements ("Both need root and a reboot"; "no outbound network"; "one isolated core" vs 120-127; "clock stays fixed" vs boost already disabled and measured ramp) and how to phrase them neutrally; (5) draft the message Jibin should send Jeremy today: plain English, at most 15 short lines, one claim per sentence, no jargon without definition, leading with the two things Jeremy most needs to know (nohz_full is not available on the current kernel; what WILL be ready by Friday) and ending with the yes/no questions; (6) the Friday hand-off checklist (what evidence to attach) and the Monday pre-run checklist (reusing ~/positron/runs/isol.py snap/diff where it fits); (7) rollback plan for each change (governor, timers, GRUB drop-in, kernel) with the exact steps and who runs them; (8) recommend what to promise for Friday (8 isolated CPUs on the current kernel with isolcpus+irqaffinity+performance, vs fewer) and say why.` },
]

const dimResults = await pipeline(
  DIMS,
  d => agent(`${COMMON}\n${d.prompt}\nReturn 6-14 findings, each with the exact evidence quote, a concrete action with commands where relevant, owner and the root/reboot/kernel/Jeremy flags; verdicts on every draft item (F/S/A/D/P/G) that your dimension touches; list the host commands and URLs you used.`,
    { label: `analyze:${d.key}`, phase: 'Analyze', schema: FINDINGS_SCHEMA }),
  (findings, d) => findings ? parallel([
    () => agent(`${COMMON}\nYou are an adversarial VERIFIER with the EVIDENCE lens for the dimension "${d.key}". For EACH finding below, try to REFUTE it from the evidence files (and, only if needed, a read-only host command under the strict rules): does the quoted evidence actually exist and say what the finding claims? Are the numbers exact (units, values)? Is any claim about Jeremy, the SDK or the host unsupported? Mark each finding confirmed / corrected / refuted / unverifiable with the exact source. Default to "unverifiable" rather than "confirmed" when you could not find the evidence. Then list important facts in the evidence files that the analyst missed for this dimension.\n\nFINDINGS:\n${JSON.stringify(findings, null, 1)}`,
      { label: `verify-evidence:${d.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }),
    () => agent(`${COMMON}\nYou are an adversarial VERIFIER with the LINUX-SEMANTICS lens for the dimension "${d.key}". For EACH finding below that states how Linux, the kernel (treat the running kernel as upstream-like 7.1 with the config shown in the evidence), cpufreq/CPPC, cgroup v2 cpuset, workqueues, IRQ affinity, GRUB on Ubuntu 24.04, systemd 255, unattended-upgrades or the SDK scripts behave, check it against authoritative sources: Documentation/admin-guide/kernel-parameters.txt, Documentation/timers/no_hz.rst, Documentation/admin-guide/cgroup-v2.rst, Documentation/admin-guide/pm/cpufreq.rst, Documentation/admin-guide/acpi/cppc_sysfs.rst, Documentation/core-api/irq/irq-affinity.rst, kernel/sched/isolation.c, kernel/time/Kconfig, kernel/rcu/Kconfig, kernel/workqueue.c, kernel/irq/manage.c, drivers/cpufreq/cppc_cpufreq.c (use WebFetch on docs.kernel.org / github.com/torvalds/linux raw files; cite the URL and the exact wording). Try to REFUTE: find version-specific behaviour, flags that do not exist, commands that would fail, or effects the finding overstates. Mark each finding confirmed / corrected / refuted / unverifiable with the source. Non-semantic findings (pure observations) may be marked "unverifiable" with reason "not a semantics claim". Then list semantics facts the analyst missed that change the plan.\n\nFINDINGS:\n${JSON.stringify(findings, null, 1)}`,
      { label: `verify-semantics:${d.key}`, phase: 'Verify', schema: VERDICT_SCHEMA }),
  ]).then(vs => ({ dim: d.key, findings, verdicts: vs.filter(Boolean) })) : null,
)
const dims = dimResults.filter(Boolean)
log(`dimensions analyzed+verified: ${dims.length}/5`)

// ---------- Phase 4: completeness critic (needs everything) ----------
phase('Critic')
const critic = await agent(
  `${COMMON}\nYou are the COMPLETENESS CRITIC. Below are: the merged paraphrase of Jeremy's requests, and for each of five dimensions the analyst's findings and two verifiers' verdicts. Ask: what is missing from the plan (a modality not checked, a claim no one verified, a source unread, a decision no one surfaced)? Where do the analysts and verifiers contradict each other, and which side does the evidence favour? Which risks could make Friday's hand-off or Monday's counted runs fail? Produce the ordered question lists for Jeremy (MUST vs NICE) and for the administrator, concrete edits to the draft plan P0-P5, and a two-sentence recommendation of what to promise for Friday 23 Oct.\n\nMERGED PARAPHRASE:\n${JSON.stringify(paraJudge, null, 1)}\n\nDIMENSIONS:\n${JSON.stringify(dims, null, 1)}`,
  { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA },
)

return { paraphrase: paraJudge, dimensions: dims, critic }