export const meta = {
  name: 'platformd-amx-sst-brief',
  description: 'Research notebook sources on AMX and Intel Speed Select, draft a platformd integration requirements brief, verify and revise it',
  phases: [
    { title: 'Read', detail: 'four parallel readers over notebook, tron packaging, speed-select and AMX project folders' },
    { title: 'Draft', detail: 'one writer produces the markdown brief' },
    { title: 'Verify', detail: 'each section checked by a source-fidelity lens and a scope lens' },
    { title: 'Critique', detail: 'completeness critic' },
    { title: 'Revise', detail: 'final markdown' },
  ],
}

const NO_SSH = 'Do not ssh to any machine and do not run anything on delphi-3bda or any other host. Work only from files on this filesystem. Cite every fact with an absolute file path (and line number or section heading where possible).'

const FACTS = {
  type: 'object',
  properties: {
    facts: { type: 'array', items: { type: 'object', properties: {
      claim: { type: 'string' },
      source: { type: 'string', description: 'absolute path plus line/section' },
      why_platformd_cares: { type: 'string' },
      confidence: { type: 'string', enum: ['measured', 'documented', 'inferred'] },
    }, required: ['claim', 'source', 'why_platformd_cares', 'confidence'] } },
    terms: { type: 'array', items: { type: 'object', properties: { term: { type: 'string' }, definition: { type: 'string' } }, required: ['term', 'definition'] } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['facts', 'terms', 'open_questions'],
}

const READERS = [
  { key: 'sst', prompt: `You are researching Intel Speed Select (SST, isst, intel-speed-select) as deployed and measured on delphi-3bda, to feed a requirements brief for platformd (Positron's platform daemon that provisions rinzler inference instances). ${NO_SSH}

Read, in full:
- /home/jhan/workspace/notebook/handoffs/claude_20260916-20260917_speed-select-retune-delphi-3bda.md
- /home/jhan/workspace/notebook/handoffs/claude_20260917_speed-select-recollect-paths-after-move.md
- /home/jhan/workspace/notebook/handoffs/codex_2026-06-22-2026-06-30_configure-xeon-6-core-speeds.md
- /home/jhan/workspace/notebook/handoffs/codex_2026-06-30_check-speed-select-config.md
- /home/jhan/workspace/notebook/artifacts/intel-speed-select/reminder.md
- /home/jhan/workspace/notebook/artifacts/intel-speed-select/results/sst-ab-20260917/summary.md
- /home/jhan/workspace/notebook/artifacts/intel-speed-select/results/sst-ab-20260917/part1-config-coverage.md
- /home/jhan/workspace/intel-vs-amd/speed-select/distilled_knowledge.md
- /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/core_power_help_source_distill.md
- /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/speed_select_intuition.html (read the text content)
- /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/core_power.html (text content)
Also grep /home/jhan/workspace/notebook/handoffs for 'intel-speed-select-state', 'CLOS', 'freq-service', 'Ansible' and read any other handoff that explains how the policy is deployed today.

Extract every fact relevant to WHAT a platform daemon would have to own, know, verify or expose if Speed Select policy became a platformd responsibility instead of an Ansible role plus a boot service. Cover: what the policy is (CLOS classes, which cpus, HT siblings, per-socket), how it is applied today (service name, config file, who owns it, when it runs, whether it survives reboot or a BIOS reset), its coupling to tron's config/resource-map.yaml core roles (app cores, dev cores, rinzler front-end cores, platform cores), machine-type specificity (granite_rapids_6962p vs other machine types, AMD hosts), the undeployed 'FE un-clamp' change, measured TPS/TTFT gains and package power cost per model, the boot-default state, failure modes and gotchas (e.g. config applied before or after rinzler start, driver/kernel/tool prerequisites, BIOS settings like SST-CP/SST-TF/SST-PP/SST-BF, turbo, intel_pstate), and anything that needs to be verified or observed (probe cpus, turbostat). Record numbers with units. Mark whether each fact is measured, documented, or inferred. Do NOT write how-to steps; collect requirements-grade facts.` },
  { key: 'amx', prompt: `You are researching Intel AMX (Advanced Matrix Extensions) support in tron (Positron's inference program) to feed a requirements brief for platformd (Positron's platform daemon that provisions rinzler inference instances). ${NO_SSH}

Read, in full:
- /home/jhan/workspace/notebook/artifacts/intel-amx/README.md
- every file under /home/jhan/workspace/notebook/artifacts/intel-amx/memory/
- /home/jhan/workspace/notebook/handoffs/claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md
- /home/jhan/workspace/notebook/handoffs/claude_20260916-20260917_tron-amx-dispatch-in-ci-builds-after-pr3879.md
- /home/jhan/workspace/notebook/handoffs/claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md
- /home/jhan/workspace/notebook/handoffs/claude_20260918_amx-compatible-128x4-models-in-nightly-ci.md
- /home/jhan/workspace/notebook/handoffs/claude_20260918_jhan-amx-deb-preset-branch-push-status.md
- /home/jhan/workspace/notebook/handoffs/claude_20260920_cmakepresets-json-amx-ci-pr.md
- /home/jhan/workspace/notebook/handoffs/claude_20260921_systems-test-pr-221-amx-ci-test.md
- /home/jhan/workspace/notebook/handoffs/claude_20260917-20260920_nightly-ci-mimic-with-amx-and-vnni-k.md
- /home/jhan/workspace/notebook/handoffs/claude_20260922_amx-benchmark-tps-llama-3-1-8b-good-tp2.md
- /home/jhan/workspace/notebook/handoffs/claude_20260923_amx-benchmark-tps-regression-between-ci-runs.md
- /home/jhan/workspace/notebook/handoffs/claude_20260921-20260922_amx-vs-attention-on-fpga-prefill-on-qwen3-4b.md
- /home/jhan/workspace/notebook/handoffs/claude_20261001-20261002_amx-attention-stats-comparison-at-3bda.md
- /home/jhan/workspace/notebook/handoffs/claude_20260902_tron-amx-distilled-cpu-attention-workers-lane.md
- /home/jhan/workspace/intel-AMX/amx-design.md and /home/jhan/workspace/intel-AMX/CLAUDE.md
Also read /home/jhan/workspace/notebook/artifacts/intel-amx/CI-test/status/*.md and skim the .html there for conclusions. In the tron checkout /home/jhan/workspace/tron, grep for TRON_AMX_DISPATCH, TRON_AMX, amx in CMakeLists.txt, CMakePresets.json, packaging/, config/resource-map.yaml, and any env-var parsing (rg -n 'TRON_AMX|TRON_VNNI|amx_' h/ src/ config/ packaging/ README.md 2>/dev/null) to learn the exact knobs and defaults.

Extract every fact relevant to WHAT platformd must own, know, decide, verify or expose for AMX to be used in production: build-time prerequisite (compile flag, deb preset, which CI apt build has it), run-time knobs (env vars, CLI flags, defaults, per-instance vs global), which models or shapes are eligible (the 128x4 shape rule, which production models fit, which do not), interaction with HW attention on the FPGA (when AMX is used vs FPGA attention, prefill vs decode), CPU and core requirements (attention worker threads, which core role, how many cores, pinning, HT), kernel and hardware prerequisites (AMX permission request, kernel version, cpu flags amx_tile/amx_bf16/amx_int8, tile data XSAVE), memory and hugepage implications, observability (stats/counters that show AMX actually ran), measured performance gains and regressions with units, known bugs or issues (issue numbers), and failure modes. Also note what breaks if AMX is enabled on a model or host that does not support it. Mark whether each fact is measured, documented, or inferred. Do NOT write how-to steps; collect requirements-grade facts.` },
  { key: 'platformd', prompt: `You are researching what platformd (Positron's platform daemon that provisions rinzler inference instances) does today, as seen from tron (Positron's inference program) and from the user's notebook, to feed a requirements brief. ${NO_SSH}

Read in /home/jhan/workspace/tron: README.md (all platformd/rinzler/resource-map mentions), README.stats.md (platformd mentions), packaging/postinst, packaging/systemd/rinzler@.service, packaging/systemd/rinzler-descriptor, config/resource-map.yaml (the whole file, note the granite_rapids_6962p section and every core role), CMakeLists.txt (platformd mentions), doc/memory_pressure_governor.md and doc/dice.md (platformd mentions), t/t_rinzler.cpp (platformd mentions). Grep the tron tree for 'platformd', 'RZ_CLI_ARGS', 'CPUAFFINITY', 'instance-', '/etc/rinzler', 'app-cores', 'dev-cores', 'TRON_USE_SPECULATION' and read the surrounding code or docs.
Then read /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/flat_freq_tests-README.md, at least every region that mentions platformd (grep -n platformd first, then read generously around each hit), and /home/jhan/workspace/notebook/artifacts/intel-amx/exec/results/p0perf-20260913/platformd-instance-1.env.txt if it exists (else find a platformd instance env file under /home/jhan/workspace/intel-AMX or /home/jhan/workspace/notebook). Also grep /home/jhan/workspace/notebook/handoffs for platformd and read the most informative hits.

Extract every fact about platformd's responsibilities and interfaces: what it reads (resource-map.yaml, when), what it writes (instance env files, their location and ownership, RZ_CLI_ARGS, CPUAFFINITY, env vars such as TRON_USE_SPECULATION), its HTTP API (/api/config PATCH, desired-state reconciliation), how it maps instances to units, FPGA devices, cores and NUMA, per-machine-type behaviour, hugepage handling (including the platformd#413 hugepage bug), restart semantics, which cores are platform cores, and which pieces of system state it does NOT own today (frequency policy, BIOS). Also list every env var and CLI arg that platformd currently passes to rinzler per the sources. Mark each fact measured, documented, or inferred.` },
  { key: 'freq', prompt: `You are researching the July 2026 'flat frequency' investigation on the delphi Xeon 6 machines and the resulting lessons about core-frequency policy, to feed a requirements brief for platformd (Positron's platform daemon that provisions rinzler inference instances). ${NO_SSH}

Read: /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/README.md, /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md, /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/PLAN_E5_TRON_TOKPS_20260702.md, /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/sysconfig-snapshots/canary_reference.md, one of the sysconfig snapshot .txt files there, /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/distilled_knowledge_visual.html (text content), /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/suspicion-ledger.html (text content), and the sections of /home/jhan/workspace/notebook/artifacts/delphi-flat-freq/docs/flat_freq_tests-README.md that cover: the core layout table (grep 'platform: platformd'), the freq-service / boot service, the 'clamped' vs 'fast' eras, the missing decode boost, the FE un-clamp ship candidate, canary snapshots, and the final recommendations. Also grep /home/jhan/workspace/notebook/handoffs for 'flat-freq', 'flat freq', 'clamped', 'FE un-clamp' and read the handoffs that summarise conclusions (prefer the latest ones).

Extract facts relevant to WHAT a platform daemon would need if it owned or verified frequency policy: the measured effect of capped vs fast app cores on decode TPS (with units and model), which core roles were found to matter (app, dev, rinzler front-end, platform), the heterogeneous ceiling finding (all-core ceiling vs per-core), interactions with HT siblings, the need for a canary or snapshot that fingerprints the frequency state before a run, the relationship between resource-map core roles and the fast set, surprises or gotchas (a service that applies the policy only at boot, platformd restart needed to re-read maps, instance-to-unit shuffle, a config drift that silently changed results), and open items that were never shipped. Mark each fact measured, documented, or inferred.` },
]

phase('Read')
log('Reading 4 source areas in parallel')
const reads = await parallel(READERS.map(r => () => agent(r.prompt, { label: `read:${r.key}`, phase: 'Read', schema: FACTS }).then(x => ({ key: r.key, ...x }))))
const good = reads.filter(Boolean)
log(`Readers done: ${good.map(r => `${r.key}=${r.facts.length} facts`).join(', ')}`)

const DRAFT = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    words_used_here: { type: 'string', description: 'markdown bullet list' },
    short_version: { type: 'string' },
    sections: { type: 'array', items: { type: 'object', properties: { heading: { type: 'string' }, body: { type: 'string', description: 'markdown' } }, required: ['heading', 'body'] } },
    sources: { type: 'string', description: 'markdown bullet list of source files used' },
  },
  required: ['title', 'words_used_here', 'short_version', 'sections', 'sources'],
}

phase('Draft')
const draftPrompt = `Write a markdown brief that the user (jhan, a Positron performance engineer) will bring to a meeting today, 2026-10-05, with John Mark, the owner of platformd (Positron's platform daemon that provisions rinzler inference instances). Topic: integrating two features into platformd: (1) Intel AMX attention dispatch in tron, (2) Intel Speed Select core-frequency policy.

Hard constraints from the user:
- The brief states WHAT platformd needs to do (responsibilities, inputs it must know, decisions it must make, state it must own, checks it must perform, outputs it must expose). It must NOT explain HOW to implement any of it. John knows his own codebase. No code, no commands, no step-by-step procedures.
- Follow the plain-english rules the user's CLAUDE.md gives you: Words used here list first, Short version of at most three sentences, one claim per sentence, numbers with units and meaning, citations in brackets after a plain sentence, no idioms, bullets for multi-point paragraphs, short sentences.
- Every factual claim must be traceable to the research facts below (keep the source path in a bracket after the sentence, shortened to the path under ~/workspace). Claims marked 'inferred' must be labelled as such ("inferred" or "hypothesis") or dropped. Where a needed fact is missing, write "Insufficient data" and name what would resolve it, do not invent.
- Measured performance numbers go in a compact table, not in prose.
- Separate clearly: (a) requirements for AMX, (b) requirements for Speed Select, (c) shared or cross-cutting requirements (e.g. machine-type detection, verification/observability, rollback, interaction with resource-map.yaml core roles), (d) open questions for John, (e) a short status table of what exists today vs what is missing (e.g. CI build has AMX dispatch compiled out, FE un-clamp not deployed, policy lives in an Ansible role plus a boot service).
- Keep it to what fits in roughly two to three screens. Prefer dropping low-value facts over padding.
- Prioritise: what breaks if platformd gets it wrong, what platformd must decide per model and per machine type, what must be verifiable after provisioning.

Research facts (JSON, from four readers):
${JSON.stringify(good, null, 1)}

Return the brief as the structured object. Section bodies are markdown. Do not include the title, words list, or short version inside sections.`
const draft = await agent(draftPrompt, { label: 'draft', phase: 'Draft', schema: DRAFT })
if (!draft) throw new Error('draft failed')
log(`Draft: ${draft.sections.length} sections`)

const VERDICT = {
  type: 'object',
  properties: {
    issues: { type: 'array', items: { type: 'object', properties: {
      quote: { type: 'string', description: 'exact text from the section' },
      problem: { type: 'string' },
      fix: { type: 'string', description: 'replacement text or "delete"' },
      evidence: { type: 'string', description: 'file path and line/section that supports the fix' },
      severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
    }, required: ['quote', 'problem', 'fix', 'evidence', 'severity'] } },
  },
  required: ['issues'],
}

const LENSES = [
  { key: 'fidelity', text: 'SOURCE FIDELITY lens: for every sentence that states a fact, open the cited source file (and any other file under /home/jhan/workspace/notebook, /home/jhan/workspace/tron, /home/jhan/workspace/intel-AMX or /home/jhan/workspace/intel-vs-amd that you need) and check the claim, the number, the unit and the attribution. Try hard to REFUTE each claim. Flag anything unsupported, misquoted, stale, or where an inferred claim is presented as fact. Flag a missing or wrong citation. Flag any number that lacks a unit or a meaning clause.' },
  { key: 'scope', text: 'SCOPE AND USEFULNESS lens: the reader is the platformd owner, an expert in platformd who does not need implementation guidance. Flag every sentence that explains HOW to implement rather than WHAT platformd must do or know. Flag requirements that are not actually platformd\'s job (e.g. tron build flags that belong to the tron deb, BIOS settings that belong to the datacenter) unless the text says why platformd still needs to know. Flag vague requirements that a platformd owner could not act on or verify. Flag missing consequences (what breaks if ignored). Flag plain-english violations: undefined term at first use, two claims in one sentence, idioms, long sentences. Do also check the cited files exist and support any WHAT claim you doubt.' },
]

phase('Verify')
const allIssues = await pipeline(
  draft.sections,
  (s, _item, i) => parallel(LENSES.map(l => () => agent(
    `You are verifying one section of a brief for the platformd owner about integrating Intel AMX attention dispatch (tron) and Intel Speed Select frequency policy into platformd. ${NO_SSH}

${l.text}

Context the reader also sees (do not verify these, just use them for term definitions):
Words used here:
${draft.words_used_here}
Short version: ${draft.short_version}

Section ${i + 1} heading: ${s.heading}
Section body:
${s.body}

Return issues only. An empty list is a valid answer if nothing is wrong. Default to flagging when uncertain about a factual claim.`,
    { label: `verify:${l.key}:${i + 1}`, phase: 'Verify', schema: VERDICT })
    .then(v => (v ? v.issues.map(x => ({ ...x, section: s.heading, lens: l.key })) : []))
  )).then(rs => rs.filter(Boolean).flat()),
)
const issues = allIssues.filter(Boolean).flat()
log(`Verify: ${issues.length} issues (${issues.filter(i => i.severity === 'blocker').length} blockers)`)

// Also verify the short version and words list
const headIssues = await agent(`Verify the 'Words used here' list and the 'Short version' of a brief for the platformd owner. ${NO_SSH}
Check: every term used in the sections below that is a code name, acronym, service name, metric, or machine name appears in the words list with a correct definition (check against the sources under /home/jhan/workspace/notebook/handoffs, especially claude_20260916-20260917_speed-select-retune-delphi-3bda.md which has a vetted glossary). Check the Short version has at most three sentences and that a newcomer can follow it. Flag any definition that is wrong per the sources.

Words used here:
${draft.words_used_here}
Short version: ${draft.short_version}
Sections (for term usage only):
${draft.sections.map(s => `## ${s.heading}\n${s.body}`).join('\n\n')}`, { label: 'verify:head', phase: 'Verify', schema: VERDICT })
const headList = headIssues ? headIssues.issues.map(x => ({ ...x, section: 'HEAD', lens: 'terms' })) : []

phase('Critique')
const CRITIC = { type: 'object', properties: { gaps: { type: 'array', items: { type: 'object', properties: { gap: { type: 'string' }, why_it_matters: { type: 'string' }, evidence: { type: 'string' } }, required: ['gap', 'why_it_matters', 'evidence'] } } }, required: ['gaps'] }
const critic = await agent(`You are the completeness critic for a brief the user brings to the platformd owner about integrating Intel AMX attention dispatch and Intel Speed Select frequency policy into platformd. ${NO_SSH}

Ask: what requirement, decision, failure mode, or verification need is MISSING from the draft, given the research facts? Think like the platformd owner: per-model decisions, per-machine-type decisions, ordering relative to instance start, reboot and restart behaviour, shared-machine (two sockets, two owners) behaviour, rollback, observability, interaction with resource-map.yaml core roles and the hugepage slices, what happens on AMD hosts or on machines without the SST tool or without AMX, and what the user must still measure before the meeting. Also check: does the draft say what exists today vs what is missing? Does it list concrete open questions for John? Each gap must cite a research fact or a source file; if the research has no data, say so as "Insufficient data: <what would resolve it>" instead of inventing.

Draft:
# ${draft.title}
${draft.words_used_here}
Short version: ${draft.short_version}
${draft.sections.map(s => `## ${s.heading}\n${s.body}`).join('\n\n')}

Research facts:
${JSON.stringify(good, null, 1)}`, { label: 'critic', phase: 'Critique', schema: CRITIC })
log(`Critic: ${critic ? critic.gaps.length : 0} gaps`)

phase('Revise')
const final = await agent(`Revise this markdown brief for the platformd owner. Apply every blocker and major issue, apply minor issues where they improve accuracy or plain English, and fill the critic's gaps only where a cited source supports the addition (otherwise add an "Insufficient data" line naming what would resolve it, or add the item to Open questions). Keep the user's constraints: WHAT platformd needs to do, never HOW; no code, no commands, no procedures; plain-english rules (Words used here first, Short version of at most three sentences, one claim per sentence, numbers with units and meaning, citations in brackets after the sentence shortened to paths under ~/workspace, no idioms, bullets for multi-point paragraphs, short sentences). Keep measured numbers in tables. Keep the length to two to three screens. End with a 'Sources' list. ${NO_SSH} You may open source files to check a disputed fact.

Return ONLY the final markdown document as your final text, starting with the '# ' title line.

Draft title: ${draft.title}
Words used here:
${draft.words_used_here}
Short version: ${draft.short_version}
Sections:
${draft.sections.map(s => `## ${s.heading}\n${s.body}`).join('\n\n')}
Sources:
${draft.sources}

Verification issues (${issues.length + headList.length}):
${JSON.stringify([...headList, ...issues], null, 1)}

Critic gaps:
${JSON.stringify(critic ? critic.gaps : [], null, 1)}`, { label: 'revise', phase: 'Revise' })

return { markdown: final, issueCount: issues.length + headList.length, blockers: issues.filter(i => i.severity === 'blocker'), gaps: critic ? critic.gaps : [], readerOpenQuestions: good.map(r => ({ key: r.key, q: r.open_questions })) }