export const meta = {
  name: 'verify-reply-to-adam',
  description: 'Check the draft Slack reply and the claims behind it: file facts, Slack facts, a reader in the role of adam, plain-English rules',
  phases: [
    { title: 'Verify', detail: 'four independent checkers, each with a different lens' },
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

const DRAFT = [
  'My reading: you want the extra latency when a core on one die reaches a PCIe port on the other die. The add-in card test is blocked, so I use a device already in the board.',
  '',
  'Plan: run the same access to an installed NVMe drive or the USB controller, pinned to die 0 (CPUs 0-63), then to die 1 (CPUs 64-127). Compare the two. First I will confirm which die each device connects to.',
  '',
  'The CRB ran as one NUMA node (UMA mode) on Nov 17. So I can choose the die of the core, not the die of the memory.',
  '',
  'Which matters more: core-to-device access, or device DMA to memory?',
].join('\n')

const INTERPRETATION = [
  'The interpretation that the user will be given:',
  'I1. Request: adam asks whether anyone has measured the latency of a PCIe port on the CRB (the Arm AGI CPU customer reference board) for a path that crosses to the second die of the two-die chip, or whether that test still waits for a PCIe add-in card. The card route is blocked: the board loses power with any add-in card installed, and Arm has sent no fix.',
  'I2. Workaround: do not wait for the card. Use a PCIe device that is already in the board ("some onboard peripheral") as the endpoint, and compare the same access from a core on the device\'s own die and from a core on the other die. "NUMA-crossing" is his word for the die crossing.',
  'I3. "The extra die" is the other 64-core chiplet, not a separate IO die.',
  'I4. "You" is most likely Jibin (the sentence answers his message), possibly Jibin and William Baumann. It is a suggestion ("Maybe ...?"), with no metric, device, firmware mode or date named.',
  'I5. Verdict: the request and the workaround are understood, so the reply is a confirmation. One open point remains that only adam can settle and that changes the test: which path he cares about (a core reaching the device, or the device doing DMA to memory). The confirmation ends with that one question.',
].join('\n')

const RULES = [
  'Hard rules:',
  '- READ-ONLY task. Do not modify, create or delete any project file. Temporary files only under ' + SCRATCH + ' (own sub-folder).',
  '- Do NOT log in to any remote machine (no ssh; in particular not 192.168.2.45).',
  '- Do NOT send, post, schedule or draft any Slack message, email, comment or canvas.',
  '- Your job is to find what is WRONG. Do not approve a claim because it sounds right: open the source and read it. If you cannot open a source, the verdict is "unverified", not "confirmed".',
  '- Your final output is raw data for another program.',
].join('\n')

const CLAIMS_SCHEMA = {
  type: 'object',
  properties: {
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'partly', 'refuted', 'unverified'] },
          evidence: { type: 'string', description: 'source path:line / page / Slack channel+date and a short verbatim quote that you read yourself' },
          correction: { type: 'string', description: 'corrected wording if the verdict is not confirmed; empty otherwise' },
        },
        required: ['id', 'verdict', 'evidence', 'correction'],
      },
    },
    draftProblems: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          phrase: { type: 'string' },
          problem: { type: 'string' },
          fix: { type: 'string' },
          severity: { type: 'string', enum: ['must-fix', 'should-fix', 'minor'] },
        },
        required: ['phrase', 'problem', 'fix', 'severity'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['checks', 'draftProblems', 'notes'],
}

const FILE_CLAIMS = [
  'F1. Arm\'s SVK user guide lists the platform as a dual-chip boot with 64 cores per chip. Source given: /home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf page 10.',
  'F2. Arm calls the link between the dies a die-to-die UCIe interface. Source given: /home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/sysdiag/Arm_Sys_Diag_Tool_2.0.pdf page 37.',
  'F3. The kernel boot log of OUR CRB labels CPUs 0-63 "chip number 0" and CPUs 64-127 "chip number 1" (64 lines each). Source given: /home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117/k0.txt (around lines 315 and 529).',
  'F4. Each chip has 3 PCIe subsystems (PSS). Source given: /home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/phx-soc-utils/scripts/power_management/phx_pwr_thermal_monitor.py:82-84 ("PSS_COUNT = 3"). Check that the count is per chip and not for the whole package.',
  'F5. The PCI devices in the saved boot logs of our CRB are exactly: two NVMe drives (0000:01:00.0 and 000b:01:00.0), a two-port Broadcom BCM57508 network card (0007:01:00.0 and .1), the ASPEED BMC bridge and graphics device (0005:01:00.0, 0005:02:00.0) and a TI USB controller (0010:01:00.0). No add-in card appears in any of the 12 saved boots (files k0.txt, k-1.txt ... k-11.txt in /home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117/). Count with grep; do not trust the claim.',
  'F6. SMBIOS names two x16 card slots: "HHHL x16 CEM Slot (PSS0 ...)" on PCI segment 0002 and "FHHL x16 CEM Slot (PSS4 ...)" on segment 0017. Source given: /home/jhan/workspace/machines/arm-crb/firmware-snapshot-20261117/smbios-dmidecode.txt:188-320.',
  'F7. No saved file states in words which chip a PCI segment or device belongs to. The mapping "segments 0000-000e on chip 0, segments 0010-001e on chip 1" is an inference from address blocks (the chip 1 units sit at an offset of 0x10_0000_0000). Under that inference both NVMe drives, the network card and the BMC device are on chip 0, and the USB controller is the only installed device on chip 1. Check the basis in k0.txt (SMMU, ITS and GIC redistributor addresses, PCI host bridge ECAM and memory windows per segment) and say how strong the inference is. Look for any counter-evidence.',
  'F8. The firmware setting "NUMA Domain" has the options UMA, PER_CHIPLET_NUMA and PER_SOCKET_NUMA and its answer was UMA when read on 2026-11-17. Source given: /home/jhan/workspace/titan/cache-perf/crb/results/uefisettings-20261117/ifr.txt:14005-14016. Also check the date of that listing.',
  'F9. In the saved boots Linux has one NUMA node and every PCI bus is reported "on NUMA node 0". Source given: k0.txt (grep "on NUMA node").',
  'F10. In UMA mode each 64-byte line of a buffer is homed on mesh 0 or mesh 1 by a hash of its physical address, half on each. Source given: /home/jhan/workspace/titan/cache-perf/crb/mesh0-or-mesh1.md:7. Then judge the step that the draft takes from it: "So I can choose the die of the core, not the die of the memory." Is that step sound for an IO buffer, or is it wider than the record supports? Note that the record is about where a line is HOMED in the cache system; say whether it also tells which die\'s DDR holds the data.',
  'F11. The memory test in the project measured 29.0-29.3 ns per load on the own chiplet and 85.0-88.5 ns on the first walk from the other chiplet (16 MiB pointer chase). Source given: /home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html:253.',
  'F12. Login shells on the CRB start on CPUs 0-119 and CPUs 126-127 are isolated, so a pinned test on "die 1" would in practice use CPUs 64-119 unless taskset names others. Sources given: /home/jhan/workspace/machines/arm-crb/firmware-snapshot-20261117/when.txt:3 and /home/jhan/workspace/notebook/artifacts/titan/memory/rampup/phoenix-crb-host.md:15.',
].join('\n')

const SLACK_CLAIMS = [
  'S1. The exchange is in a group DM of adam, William Baumann and Jibin Han. It holds only the three pasted messages, all on 2026-11-20, and William Baumann has posted nothing. (Re-read the conversation now: a new message may have arrived since the first check. Report any new message verbatim.)',
  'S2. On 2026-11-09 in #phoenix-crb adam wrote that two ConnectX-7 (CX7) network cards in two different PCIe slots of the CRB and a ConnectX-4 (CX4) card all made the motherboard lose all power about 45 s after power-on.',
  'S3. On 2026-11-10 in #phoenix-crb adam wrote that the PCIe card power issue is known to Arm and that the FAE is looking for the fix. No later status exists before 2026-11-20.',
  'S4. Slack shows no PCIe, network or disk latency measurement on the CRB by Jacob Geldbach. His measurement work recorded in Slack is DMA throughput on the Asimov chip in emulation (a direct message to Jibin of 2026-11-02), which is a different machine from the CRB. Try to REFUTE this: search for any message where Jacob reports an IO, PCIe, NVMe, network or latency measurement on the CRB or Phoenix board, in any channel, with several word forms.',
  'S5. No Slack message states which latency adam wants (register access from a core, device DMA, interrupt, or end-to-end network or storage latency), which onboard device he has in mind, or a date. Try to REFUTE this: search adam\'s messages of the last 60 days for PCIe, latency, NUMA, die, hop, onboard, peripheral, NVMe, NIC, DMA, MMIO, doorbell, and also messages by William Baumann and others that describe the planned PCIe latency test on the CRB.',
  'S6. In June 2026 adam used the word "die" for a sub-NUMA domain in experiments on an Intel Xeon. This supports reading "extra die" and "NUMA-crossing" as the same thing.',
].join('\n')

const AGENTS = [
  {
    key: 'file-facts',
    schema: CLAIMS_SCHEMA,
    prompt: [
      'You are a fact checker. A Slack reply will be sent by the user (Jibin Han) to a colleague ("adam"), and the user will be given an interpretation of adam\'s request. Both rest on claims taken from files on this machine. Check every claim against its source by reading the source yourself.',
      '',
      'The Slack exchange:', '"""', SLACK_TEXT, '"""',
      '',
      INTERPRETATION,
      '',
      'The draft reply (from Jibin to adam):', '"""', DRAFT, '"""',
      '',
      'Claims to check (give one entry per id, F1 to F12):',
      FILE_CLAIMS,
      '',
      'Then list under draftProblems every statement in the DRAFT that the files do not support, that is stated more firmly than the files allow, or that is false. In particular: "die 0 (CPUs 0-63)" and "die 1 (CPUs 64-127)", "an installed NVMe drive or the USB controller", "The CRB ran as one NUMA node (UMA mode) on Nov 17", "I can choose the die of the core, not the die of the memory".',
      'The Read tool reads PDF pages with its "pages" parameter.',
      '',
      RULES,
    ].join('\n'),
  },
  {
    key: 'slack-facts',
    schema: CLAIMS_SCHEMA,
    prompt: [
      'You are a fact checker with READ-ONLY access to the user\'s Slack through the Slack connector of this session. Its tools are deferred: load them with ToolSearch, query "select:mcp__claude_ai_Slack__slack_search_public_and_private,mcp__claude_ai_Slack__slack_read_thread,mcp__claude_ai_Slack__slack_read_channel,mcp__claude_ai_Slack__slack_search_users,mcp__claude_ai_Slack__slack_search_channels". Never call a tool that sends, schedules or drafts a message or creates a canvas. If the tools are not available, give every claim the verdict "unverified" and say why.',
      '',
      'The user (Jibin Han) will reply to a colleague ("adam"). The Slack exchange (today, Friday 2026-11-20, group DM id C0CKJHWGF19):', '"""', SLACK_TEXT, '"""',
      '',
      INTERPRETATION,
      '',
      'The draft reply (from Jibin to adam):', '"""', DRAFT, '"""',
      '',
      'Claims to check against Slack (one entry per id, S1 to S6). Known locations from a first search: channel #phoenix-crb is C0C1R7XEVU6; the adam-Jibin direct message is D0B75QD9YDP; the Jibin-Jacob direct message is D0C6V968RNE; a June 2026 group DM is C0B70J0UP5K.',
      SLACK_CLAIMS,
      '',
      'Then list under draftProblems anything in the DRAFT or in the interpretation (I1 to I5) that a Slack message contradicts, or that an existing Slack message already answers (for example: if adam or someone else already said which latency matters, the closing question of the draft is not needed; if someone already measured it, the plan is not needed).',
      'Quote only short, relevant passages. Do not copy unrelated private conversations.',
      '',
      RULES,
    ].join('\n'),
  },
  {
    key: 'reader-as-adam',
    schema: {
      type: 'object',
      properties: {
        whatAdamUnderstands: { type: 'string', description: 'In adam\'s voice: what does this reply tell me, sentence by sentence?' },
        matchesHisIntent: { type: 'string', description: 'For each plausible intent of adam (list them), does the reply fit it, and would adam have to correct something?' },
        canAnswerQuestionInOneLine: { type: 'boolean' },
        questionAssessment: { type: 'string', description: 'Is the closing question the right one, clear, and answerable? Is a better single question available?' },
        problems: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              phrase: { type: 'string' },
              problem: { type: 'string' },
              fix: { type: 'string' },
              severity: { type: 'string', enum: ['must-fix', 'should-fix', 'minor'] },
            },
            required: ['phrase', 'problem', 'fix', 'severity'],
          },
        },
        interpretationChallenges: { type: 'string', description: 'Where could the interpretation I1 to I5 be wrong? Give the strongest alternative reading of adam\'s two messages and say whether the draft would still be a sound reply under it.' },
        improvedDraft: { type: 'string', description: 'Your best version of the reply, fewer than 100 words, only if it is clearly better; otherwise repeat the draft unchanged.' },
      },
      required: ['whatAdamUnderstands', 'matchesHisIntent', 'canAnswerQuestionInOneLine', 'questionAssessment', 'problems', 'interpretationChallenges', 'improvedDraft'],
    },
    prompt: [
      'Play the reader. You are "adam": a senior hardware / system engineer at a company that builds an AI accelerator ("Asimov") which will sit behind PCIe on a host CPU. The host CPU under evaluation is the Arm AGI CPU on a reference board (the "CRB"). The chip is one package with two 64-core dies (chiplets) joined by a die-to-die UCIe link; each die has its own cores, memory channels and PCIe subsystems. You are the contact to the Arm field engineer. You tried three PCIe add-in cards on the CRB in early November; the board lost all power about 45 s after power-on each time, and Arm has not sent a fix. In June 2026 you measured small CPU-to-PCIe writes on another SoC and found the root complex and bus latency to be the limit, and you ran die-against-die experiments on an Intel Xeon where you called a sub-NUMA domain a "die".',
      '',
      'You wrote messages 1 and 3 of this exchange in a group DM with Jibin Han and William Baumann:', '"""', SLACK_TEXT, '"""',
      '',
      'Jibin now sends you this reply:', '"""', DRAFT, '"""',
      '',
      'Facts that Jibin holds and you may not (true as far as the records show): the CRB firmware was in "UMA" mode on 2026-11-17, so Linux sees one NUMA node; the firmware also offers PER_CHIPLET_NUMA. In UMA mode each buffer is spread over both dies by an address hash. The installed PCIe devices are two NVMe drives, a Broadcom network card (its port 0 carries the SSH connection), the BMC graphics device and a USB controller. No document states which die each device connects to; by an inference from address blocks the NVMe drives, network card and BMC are on die 0 and the USB controller on die 1.',
      '',
      'The interpretation behind the reply:', INTERPRETATION,
      '',
      'Tasks:',
      '1. Read the reply as adam. Say what you understand from each sentence. Flag anything unclear, wrong, too detailed, missing, or likely to make you ask "what do you mean?".',
      '2. List the plausible things adam could have meant (at least three different intents, for example: MMIO or doorbell write latency from a core to a device on the other die; DMA by the device into memory on the other die; an end-to-end network or storage number; a comparison of the two card slots; a rough yes/no "does it matter"). For each, say whether the reply fits or whether adam would have to correct it.',
      '3. Judge the closing question. Can adam answer it in one line? Is it the single most useful question, or would another question remove more risk of wasted work?',
      '4. Attack the interpretation: give the strongest alternative reading of the two messages.',
      '5. Give an improved reply only if clearly better. Constraints for any reply: fewer than 100 words; plain English for engineers; short sentences; one claim per sentence; no idioms or metaphors; no greeting and no closing pleasantry; no date promise; do not state as fact which die a device is on.',
      '',
      'Work only from the text above. Do not log in to any machine and do not send any message. Your final output is raw data for another program.',
    ].join('\n'),
  },
  {
    key: 'plain-english',
    schema: {
      type: 'object',
      properties: {
        wordCount: { type: 'integer', description: 'computed with a script, not by eye' },
        wordCountMethod: { type: 'string' },
        violations: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              rule: { type: 'string' },
              phrase: { type: 'string' },
              fix: { type: 'string' },
            },
            required: ['rule', 'phrase', 'fix'],
          },
        },
        correctedDraft: { type: 'string' },
        correctedWordCount: { type: 'integer' },
      },
      required: ['wordCount', 'wordCountMethod', 'violations', 'correctedDraft', 'correctedWordCount'],
    },
    prompt: [
      'Check a short Slack reply against the user\'s plain-English rules. The rules are in /home/jhan/.claude/skills/plain-english/SKILL.md (read that file; use its Check mode). The reply is a short chat message from one engineer to another who knows the project, so Rule 7 (Short version) does not apply, and terms that the recipient himself used in the thread (CRB, PCIe, NUMA, die, onboard) need no definition. Terms the recipient may not know DO need a short definition or simpler wording (judge "UMA mode", "DMA", "pinned").',
      '',
      'The thread the reply answers:', '"""', SLACK_TEXT, '"""',
      '',
      'The reply to check:', '"""', DRAFT, '"""',
      '',
      'Tasks:',
      '1. Count the words with a script (python3 -c with str.split on the exact text; write the text to a file under ' + SCRATCH + '/plain-english-check first). The hard limit is fewer than 100 words. Report the number and the method.',
      '2. List every rule violation with the exact phrase and a fix. Do not invent violations. Check in particular: idioms or metaphors, sentences with two claims, sentences with more than one subordinate clause, numbers without units or meaning, undefined terms the recipient may not know, a semicolon, and whether "so I use a device" should be "so I will use a device".',
      '3. Give the full corrected reply. It must stay under 100 words (count it with the script), keep every point of the original (reading, reason, plan with the two CPU groups, the die check first, the one-NUMA-node limit, the closing question), and must not add technical claims.',
      '',
      'Do not modify any project file. Your final output is raw data for another program.',
    ].join('\n'),
  },
]

phase('Verify')
const results = await parallel(AGENTS.map(a => () =>
  agent(a.prompt, { label: 'verify:' + a.key, phase: 'Verify', schema: a.schema })
    .then(r => (r ? { key: a.key, ...r } : null))
))
const done = results.filter(Boolean)
const lost = AGENTS.map(a => a.key).filter(k => !done.some(d => d.key === k))
if (lost.length) log('Verify stage: no result from ' + lost.join(', '))
return { results: done, lost }
