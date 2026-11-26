export const meta = {
  name: 'interpret-adam-pcie-request',
  description: 'Gather CRB die, PCIe and Slack context, then interpret the PCIe die-crossing request from three independent angles',
  phases: [
    { title: 'Gather', detail: 'five read-only readers: local records, vendor kit, device inventory, Slack history, public web' },
    { title: 'Interpret', detail: 'three independent readings of the Slack message, each with a draft reply' },
  ],
}

const SCRATCH = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-pcie/b662db86-cbfe-4b4a-a59a-37f11dacb0e7/scratchpad'

const SLACK_TEXT = [
  'adam  [11:56 AM]',
  'Hi guys, have you been able to do any testing on the PCIe port lancy for hopping though the extra die, or still waiting for a suitable PCIe card (which is currently blocked by the power subsystem issue when I tried last).',
  'Jibin Han  [12:04 PM]',
  'you talk about CRB? I do not, my testing so far are focusing on memory hierarchy from core to DDR. I think Jacob measured IO path',
  'adam  [12:11 PM]',
  'Yes, the CRB.   I haven\u2019t received any fix from Arm for the PCIe card power yet.  Maybe you can evaluate the impact of the NUMA-crossing using some onboard peripheral?',
].join('\n')

const BACKGROUND = [
  'Background that is already established (from the project records, read today, 2026-11-20):',
  '- "CRB" is the Arm AGI CPU customer reference board, also called the Arm "Phoenix Reference Server". It has 128 CPUs (Neoverse V3 class cores).',
  '- The chip has two CMN S3 meshes (Arm Coherent Mesh Network, the on-chip interconnect). Linux names them arm_cmn_0 (CPUs 0 to 63) and arm_cmn_1 (CPUs 64 to 127). The project records treat them as two chiplets / dies.',
  '- Firmware on the CRB was AGI-CPU-CRB-v0.7.2 on 2026-11-17. The firmware setting "NUMA Domain" was "UMA" then, so Linux saw ONE NUMA node (node0, CPUs 0-127). The Arm reference machine in the vendor kit ran with 2 NUMA nodes.',
  '- The user (Jibin Han) has so far measured only the memory path: core, L1/L2, SLC (system level cache, the L3), DDR. No PCIe or IO measurement exists in this project. The folder crb/pcie is new and empty.',
  '- Known from an earlier inspection: the board has a Broadcom bnxt_en network card and a local NVMe drive (the home folder is on it).',
  '- A memory test showed a cost for crossing meshes: a pointer chase by core 3 (mesh 0) took 29 ns per load, and the first walk of the same lines by core 67 (mesh 1) took 86 ns per load (crb/mesh0-or-mesh1.md).',
].join('\n')

const RULES = [
  'Hard rules for this task:',
  '- This is a READ-ONLY research task. Do not modify, create or delete any project file. Temporary files (for example text extracted from a PDF) go only under ' + SCRATCH + ' (create a sub-folder with your own name).',
  '- Do NOT log in to any remote machine. No ssh at all. In particular do not contact 192.168.2.45 (the CRB). Work only from files on this machine' + ' and the sources named in your task.',
  '- Do NOT send, post, schedule or draft any Slack message, email or comment.',
  '- Report only what a source states. For every fact give the source (absolute file path with line number or PDF page, or a URL, or a Slack channel + date) and a short verbatim quote. If you infer something, mark it as an inference. If the sources do not answer a question, list the question under gaps. Do not fill a gap with a guess.',
  '- Your final output is raw data for another program, not a message to a human.',
].join('\n')

const FACTS_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string', description: 'At most 8 sentences: what the sources establish that helps interpret the Slack request.' },
    facts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          claim: { type: 'string' },
          source: { type: 'string', description: 'absolute path:line, PDF page, URL, or Slack channel and date' },
          quote: { type: 'string', description: 'short verbatim quote from the source' },
          kind: { type: 'string', enum: ['stated', 'inference'] },
        },
        required: ['claim', 'source', 'quote', 'kind'],
      },
    },
    gaps: { type: 'array', items: { type: 'string' }, description: 'questions the sources could not answer' },
  },
  required: ['summary', 'facts', 'gaps'],
}

const QUESTIONS = [
  'Questions that the whole research has to answer (answer the ones your sources cover):',
  'Q1. What is "the extra die" on this chip? How many dies or chiplets does the Arm AGI CPU have, and what joins them (for example CMN CCG links, CXL-type links)?',
  'Q2. Where do the PCIe root ports / PCIe slots attach: to one die only, or to both? Which die serves which slot or which onboard device?',
  'Q3. Which onboard peripherals does our CRB have (network card, NVMe drive, USB controller, BMC, SATA, others)? What are their PCI addresses / segments, and which die or mesh do they hang off?',
  'Q4. What NUMA settings exist (UMA, NUMA, others)? In the current UMA mode, can a test still choose "same die" against "other die" by pinning a core to CPUs 0-63 or 64-127?',
  'Q5. Is there any record of the PCIe card power problem (add-in card not powered, auxiliary power, power subsystem), or of a fix that is pending from Arm?',
  'Q6. Is there any earlier measurement, by anyone, of PCIe / IO latency or of the cost of crossing dies for IO on this board? In particular anything by "Jacob" on the "IO path".',
  'Q7. Who is "adam" (role, team), and what did he say earlier about PCIe latency, the extra die, or the PCIe card?',
].join('\n')

function gatherPrompt(title, task) {
  return [
    'You are one of five independent researchers. Goal of the whole effort: understand a request that a colleague ("adam") made in Slack to the user (Jibin Han), so that the user can answer him correctly.',
    '',
    'The Slack exchange, verbatim ("lancy" is most likely a typing error for "latency"):',
    '"""',
    SLACK_TEXT,
    '"""',
    '',
    BACKGROUND,
    '',
    QUESTIONS,
    '',
    'YOUR PART: ' + title,
    task,
    '',
    RULES,
  ].join('\n')
}

const GATHERERS = [
  {
    key: 'local-records',
    title: 'the project records about the two dies / meshes and the cost of crossing them',
    task: [
      'Read these files on this machine and extract everything that bears on Q1, Q2, Q4 and Q6:',
      '- /home/jhan/workspace/titan/cache-perf/crb/mesh0-or-mesh1.md',
      '- /home/jhan/workspace/titan/cache-perf/crb/inspection-record-2026-10-30.md',
      '- /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html (large; search it for die, chiplet, mesh, cross, CCG, NUMA, PCI, hop)',
      '- /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/ (reports such as ASCT-cross-check.html; search for cross-node, NUMA, die)',
      '- /home/jhan/workspace/notebook/artifacts/titan/memory/cache-perf/crb-hierarchy-findings.md and crb-arm-docs.md',
      '- /home/jhan/workspace/titan/cache-perf/crb/refs/ (list it; read what is relevant)',
      'Wanted in particular: (a) the exact evidence that the chip has two dies and which CPUs sit on which; (b) every measured number for the cost of crossing from one mesh to the other (latency in ns, rate in GB/s), with its test name; (c) what the records say joins the two meshes (CCG, CCLA, CCHA, CCRA node names and what they mean); (d) anything at all about PCIe, HN-P or HN-I nodes (the CMN bridge nodes for IO) and which mesh has them, for example the per-mesh node counts "hnp" and "hni" of arm_cmn_0 and arm_cmn_1.',
    ].join('\n'),
  },
  {
    key: 'vendor-kit',
    title: 'the Arm vendor kit documents',
    task: [
      'The kit is at /home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/ (12 GB; read documents only, do not unpack big archives unless a document points to a small text file you need).',
      'Read at least:',
      '- svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf (whole document)',
      '- docs/arm_agi_cpu_1ou_reference_server_quick_start_guide_112283_a0_01_en.pdf (whole document)',
      '- svk-release/Validation_Report/0_9_0_test_report.html and sysdiag_L6_and_L10_results.txt (search for PCI, NVMe, slot, riser, NUMA, link)',
      '- svk-release/README.md, svk-release/docs/README.md, gitlab-profile/README.md, CHANGELOG.md, QuickStart.md, docs/README.md',
      '- svk-release/PDB_CPLD/README.md, HPM_CPLD/readme_v0.2.5.txt, SCM_CPLD/readme_v0.2.4.txt, VRM_FW release note PDF (power subsystem: anything on PCIe slot power, 12 V, auxiliary power, riser power, known issues)',
      '- tools/sysdiag/Arm_Sys_Diag_Tool_2.0.pdf and tools/soc-avl-validator/README.md (lists of supported / validated PCIe cards and onboard devices)',
      'The Read tool can read a PDF with its "pages" parameter (at most 20 pages per call). pdftotext is not installed; a small Python script is the other way.',
      'Answer Q1, Q2, Q3, Q4 and Q5 from these documents. Wanted in particular: a block diagram or text that says how many dies the SoC has, which die owns which PCIe root complexes / slots / M.2 / OCP NIC / BMC link / USB, how the dies are joined, the list of firmware NUMA options, known issues and changelog entries about PCIe add-in cards or their power, and any statement about extra latency for IO that crosses dies.',
    ].join('\n'),
  },
  {
    key: 'device-inventory',
    title: 'the saved hardware inventories of our own CRB (no login to the machine)',
    task: [
      'Find and read saved listings of our CRB hardware on this machine. Start with:',
      '- find /home/jhan/workspace/notebook -name "phoenix-crb-inspection.txt" (an inspection dump of 2026-10-21; it has a device inventory; look for lspci output, PCI domains / segments, block devices, network devices, USB, "firmware (dmi)")',
      '- the other files in that same evidence folder (phoenix-crb-evidence-2026-10-21)',
      '- /home/jhan/workspace/notebook/artifacts/titan/home-tmp/WRITEUP-phoenix-crb-evaluation.md',
      '- /home/jhan/workspace/notebook/artifacts/titan/memory/cache-perf/crb-machine-access.md and /home/jhan/workspace/notebook/artifacts/titan/memory/rampup/phoenix-crb-host.md',
      '- /home/jhan/workspace/machines/arm-crb/ (firmware-snapshot-20261117 with settings-forms-ifr.txt, settings-questions.json, derived/arm-platform-settings.json, derived/decoded-settings.json; DIMM-flaky-report.md; arm-support-case-20261117)',
      '- /home/jhan/workspace/titan/cache-perf/crb/results/uefisettings-20261117/ and /home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117/ (the k*.txt files mention PCI; say what they show)',
      '- grep -rIl -i -E "lspci|Root Port|PCI bridge|nvme|bnxt" under /home/jhan/workspace/titan/cache-perf/crb and /home/jhan/workspace/notebook/artifacts/titan for anything else',
      'Answer Q3, Q4 and Q5 for OUR board. Wanted in particular: the full list of PCI devices that are on the board today (address with segment/domain, name, driver), which of them are onboard (soldered or SoC-integrated) and which sit in a slot; the PCI segment / host bridge layout (how many host bridges, which segment numbers) and any hint that maps a host bridge to mesh 0 or mesh 1; the exact firmware choices for "NUMA Domain" and every firmware setting about PCIe (slot power, hot plug, bifurcation, link speed, per-root-port enable); any note that a PCIe card failed to power up.',
      'State clearly when the inventory does not say which die a device hangs off.',
    ].join('\n'),
  },
  {
    key: 'slack-history',
    title: 'the Slack history around this request',
    task: [
      'Use the Slack connector of this session, READ-ONLY. Its tools are deferred: load them first with ToolSearch, query "select:mcp__claude_ai_Slack__slack_search_public_and_private,mcp__claude_ai_Slack__slack_read_thread,mcp__claude_ai_Slack__slack_read_channel,mcp__claude_ai_Slack__slack_search_users,mcp__claude_ai_Slack__slack_search_channels". Never call a tool that sends, schedules or drafts a message or creates a canvas.',
      'If the Slack tools are not available or need a login, say so in gaps and stop; do not try another route.',
      'Find:',
      '1. The thread itself (today is Friday 2026-11-20; the messages are at 11:56 AM, 12:04 PM and 12:11 PM, probably today). Search for phrases such as "hopping though the extra die", "PCIe card power", "onboard peripheral", "NUMA-crossing". Report the channel name, whether it is a thread, who else is in it, and any message before or after the three lines that the user did not paste.',
      '2. Earlier messages by adam (find his full name, title and team with the user search) about: PCIe latency on the CRB, the "extra die", "hop", the PCIe card he tried, the "power subsystem" problem, the fix he expects from Arm. Search several word forms: PCIe, PCI, "extra die", "second die", chiplet, "die crossing", hop, riser, "power subsystem", "PCIe card", CRB, Phoenix, "AGI CPU".',
      '3. Messages by anyone named Jacob about measuring the IO path, PCIe, NVMe, network or latency on the CRB / Phoenix board.',
      '4. Any message that says which die the PCIe ports are on, why the latency of that path matters to the product (for example an accelerator card that sits behind PCIe), and what number or comparison adam wants.',
      'Answer Q5, Q6 and Q7, and add what you learn for Q1 and Q2. Quote the messages verbatim with author, channel and date. Keep the quotes short and relevant; do not copy unrelated private conversations.',
    ].join('\n'),
  },
  {
    key: 'public-web',
    title: 'public information about the chip architecture',
    task: [
      'Use web search (the WebSearch tool is deferred: load it with ToolSearch query "select:WebSearch"; if a WebFetch tool exists you may use it to read a page). If no web tool is available, say so in gaps and stop.',
      'PRIVACY RULE: search queries and fetched URLs must contain only public product terms (for example "Arm AGI CPU", "Neoverse V3", "CMN S3", "CCG", "dual chiplet", "PCIe Gen6", "reference server"). Never put a person name, a company name other than Arm and its public partners, an IP address, a file path or any text from the Slack exchange in a query.',
      'Find public descriptions of the Arm AGI CPU (announced 2026; a data-center CPU with up to 136 Neoverse V3 cores) and its reference server. Answer Q1, Q2 and Q4:',
      '- Is the SoC built from two dies / chiplets? What does each die hold (cores, memory controllers, PCIe/CXL root complexes)? Is the IO split evenly over the two dies or placed on one?',
      '- What joins the dies (CMN gateway "CCG", CXL-type link, AMBA CHI C2C)? Does Arm or the press give a latency cost for a request that crosses dies?',
      '- In Arm CMN terms, how does a core on one mesh reach a PCIe root port (HN-P / HN-I bridge node) that sits on the other mesh, and how does a PCIe device that does DMA reach memory on the other mesh? One or two sentences, with a source (CMN S3 or CMN-700 technical reference manual pages are fine).',
      '- General, well-sourced numbers for how much a remote-NUMA-node PCIe device costs on other dual-die or dual-socket servers (for example NVMe or NIC latency / throughput, local node against remote node). Label them as other platforms.',
      'Give a URL and a short verbatim quote for every fact. Prefer Arm documents and established trade press. Say when sources disagree.',
    ].join('\n'),
  },
]

phase('Gather')
const gathered = await parallel(GATHERERS.map(g => () =>
  agent(gatherPrompt(g.title, g.task), { label: 'gather:' + g.key, phase: 'Gather', schema: FACTS_SCHEMA })
    .then(r => (r ? { key: g.key, ...r } : null))
))
const usable = gathered.filter(Boolean)
const missing = GATHERERS.map(g => g.key).filter(k => !usable.some(u => u.key === k))
if (missing.length) log('Gather stage: no result from ' + missing.join(', '))
log('Gather stage: ' + usable.reduce((n, u) => n + u.facts.length, 0) + ' facts from ' + usable.length + ' of ' + GATHERERS.length + ' readers')

const factsText = usable.map(u => [
  '### Reader: ' + u.key,
  'Summary: ' + u.summary,
  'Facts:',
  ...u.facts.map((f, i) => '  [' + u.key + '-' + (i + 1) + '] (' + f.kind + ') ' + f.claim + ' | source: ' + f.source + ' | quote: "' + f.quote + '"'),
  'Gaps:',
  ...u.gaps.map(g => '  - ' + g),
].join('\n')).join('\n\n')

const READING_SCHEMA = {
  type: 'object',
  properties: {
    request: { type: 'string', description: 'What adam asks for, in plain words, 2 to 4 sentences.' },
    whoIsAsked: { type: 'string', description: 'Who adam expects to do it (the user, Jacob, the group), and the evidence in the wording.' },
    workaround: { type: 'string', description: 'What adam proposes as the workaround, in plain words, 2 to 4 sentences, including what the test would compare.' },
    termReadings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          term: { type: 'string' },
          reading: { type: 'string' },
          support: { type: 'string', description: 'fact ids or the wording that supports this reading' },
        },
        required: ['term', 'reading', 'support'],
      },
    },
    ambiguities: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          item: { type: 'string' },
          readings: { type: 'string', description: 'the competing readings' },
          bestReading: { type: 'string' },
          changesTheWork: { type: 'boolean', description: 'true if a wrong guess would make the user do different or wasted work' },
          canBeSettledWithoutAdam: { type: 'boolean' },
        },
        required: ['item', 'readings', 'bestReading', 'changesTheWork', 'canBeSettledWithoutAdam'],
      },
    },
    verdict: { type: 'string', enum: ['confirm', 'clarify'] },
    verdictReason: { type: 'string' },
    draft: { type: 'string', description: 'The Slack reply from Jibin to adam, under 100 words.' },
    draftWordCount: { type: 'integer' },
    feasibilityNotes: { type: 'string', description: 'What makes the workaround easy or hard on this board, from the facts; name the facts.' },
  },
  required: ['request', 'whoIsAsked', 'workaround', 'termReadings', 'ambiguities', 'verdict', 'verdictReason', 'draft', 'draftWordCount', 'feasibilityNotes'],
}

const LENSES = [
  {
    key: 'literal',
    lens: 'Read the exchange as a careful reader of English who also knows server hardware. Parse each clause of adam\'s two messages. Say what each clause asks or states, and what it leaves open. Do not add intent that the words do not carry.',
  },
  {
    key: 'platform-engineer',
    lens: 'Read the exchange as the platform / silicon engineer that adam probably is. Use the gathered facts about the chip (two dies, where the PCIe root ports are, how the dies are joined, the UMA setting) to say what physical path he worries about, what measurement would answer him, and what "some onboard peripheral" could be on this exact board. Say which comparison (which CPUs, which device, which metric) would answer his question, and whether the facts show that it is possible.',
  },
  {
    key: 'skeptic',
    lens: 'Assume the obvious reading is wrong somewhere. List every way the user could misread adam and then do the wrong test: the wrong metric (register access time, interrupt delay, DMA throughput, storage or network latency), the wrong crossing (core to device, device to memory, both), the wrong owner of the task, the wrong machine state (UMA against NUMA firmware mode), an onboard device that sits on the same die as everything else and so cannot show a crossing. For each one decide, from the facts, whether it really changes the work. Then decide whether the user must ask adam first or can confirm and start.',
  },
]

function readingPrompt(l) {
  return [
    'A colleague ("adam") made a request to the user (Jibin Han) in Slack. The user wants to know: (1) what is adam\'s request, (2) what workaround does adam suggest, (3) a reply of fewer than 100 words: a CLARIFICATION question if the request cannot be acted on without one, otherwise a CONFIRMATION that restates the understanding.',
    '',
    'The Slack exchange, verbatim ("lancy" is most likely a typing error for "latency"):',
    '"""',
    SLACK_TEXT,
    '"""',
    '',
    BACKGROUND,
    '',
    'Facts gathered by five independent researchers (each fact has an id, a source and a quote; "inference" marks a deduction, not a statement of the source):',
    '',
    factsText,
    '',
    'YOUR LENS: ' + l.lens,
    '',
    'Rules for your answer:',
    '- Work only from the Slack text, the background and the facts above. You may open a cited file on this machine to check a fact. Do not log in to any remote machine and do not send any message.',
    '- Give a reading for each of these terms: "PCIe port lancy", "hopping though the extra die", "a suitable PCIe card", "the power subsystem issue", "NUMA-crossing", "some onboard peripheral", and the "you" in "Maybe you can evaluate".',
    '- Choose "clarify" only if at least one ambiguity both changes the work and cannot be settled without adam. Otherwise choose "confirm". A confirmation may end with one short question if one open point remains.',
    '- The draft is a Slack reply from Jibin to adam. Fewer than 100 words (count them; aim for 60 to 90). Plain English for engineers: short sentences, one claim per sentence, no idioms, no metaphors, no greeting, no closing pleasantry. Every technical statement in the draft must be supported by a gathered fact, or be worded as a plan or a question. Do not promise a date. Do not state which die a device is on unless a fact states it.',
    '- Your final output is raw data for another program.',
  ].join('\n')
}

phase('Interpret')
const readings = await parallel(LENSES.map(l => () =>
  agent(readingPrompt(l), { label: 'interpret:' + l.key, phase: 'Interpret', schema: READING_SCHEMA })
    .then(r => (r ? { lens: l.key, ...r } : null))
))

return { gathered: usable, missingReaders: missing, readings: readings.filter(Boolean) }
