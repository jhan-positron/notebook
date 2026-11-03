export const meta = {
  name: 'rampup-read',
  description: 'Read the rampup plan files to learn what Jeremy runs on CRB and whether dmidecode / perf_event_paranoid changes would affect it',
  phases: [
    { title: 'Read', detail: 'one reader per document' },
    { title: 'Answer', detail: 'merge and answer the question' },
  ],
}
const Q = `
QUESTIONS TO ANSWER FROM THIS DOCUMENT (quote supporting text with line numbers of the .txt file; say "not in this document" when absent):
A. Who is Jeremy, what account does he use on CRB (the Phoenix CRB host), what job does he run (tool names, labels), on which CPUs (pinning), for what deadline (demo date), and how long does each run take?
B. Timeline: which dates/times are Jeremy's runs scheduled or expected between 2026-10-22 and 2026-11-05? Is there a standing "quiet host" requirement, and what does "quiet" mean concretely (no other load on which CPUs? no other logins? no other memory traffic?)
C. Does any of Jeremy's tooling or the plan rely on: Linux perf, perf_event_paranoid, PMU counters, /sys/firmware/dmi, dmidecode, SMBIOS? Quote the text. Would a one-time 'sudo dmidecode -t 17' (reads SMBIOS tables, milliseconds, no state change) or a live change of the sysctl kernel.perf_event_paranoid (from 2 to 0 or -1; this only widens who may read hardware counters) affect anything Jeremy runs? Answer with reasoning tied to quotes, and label anything not supported by the text as inference.
D. Host policy for other users: any note, message, or rule telling other accounts (arm, jhan) what not to do while Jeremy is running (e.g. "do not run load on 120-127", "announce in channel X", "do not reboot", "do not change governor"). Quote it. Name the Slack channel or contact path if given.
E. Who is Jibin, and what is the relation between Jibin and the jhan account?
F. Any mention of cache, memory bandwidth, STREAM, latency microbenchmarks, DRAM, or "other benchmark jobs on the host" that would interfere with Jeremy's runs or that Jeremy's runs would interfere with.
G. What live/root changes were already made to CRB (sysctl, systemd drop-ins, GRUB) and by whom, with timestamps. Is there a rule about who may make further root changes?
Return concise structured answers. Do not modify any file. Read the .txt with sed -n / grep; the .txt is a plain-text extraction of the HTML.`
const DOCS = [
  { key: 'jeremy-tasks', path: '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/jeremy-tasks.html.txt', note: 'oldest file (2026-10-21 18:40): initial task analysis' },
  { key: 'for-jeremy', path: '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/phoenix-crb-for-jeremy-2026-10-22.html.txt', note: 'middle file (2026-10-22 11:55): handoff written for Jeremy' },
  { key: 'tasks-plan', path: '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf/ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e/scratchpad/jeremy-tasks-plan.html.txt', note: 'newest file (2026-10-22 12:11): full plan, 150k chars; read it all in chunks of ~400 lines' },
  { key: 'evidence-notes', path: '/home/jhan/workspace/titan/rampup/phoenix-crb-evidence-2026-10-21', note: 'directory of evidence; read ONLY these plain-text files fully: requests.txt, jeremy-replies-2026-10-22.txt, reply-to-jeremy-2026-10-22.txt, message-to-jeremy-2026-10-22.txt, note-to-arm-users-2026-10-22.txt, t2-channel-note-2026-10-22.txt, t3-access-details-2026-10-22.txt, phoenix-crb-inspection.txt (skim with grep for perf|dmi|paranoid|channel|quiet|bandwidth). Do not run any .sh or .py file.' },
]
const ANS = { type: 'object', properties: {
  A: { type: 'string' }, B: { type: 'string' }, C: { type: 'string' }, D: { type: 'string' }, E: { type: 'string' }, F: { type: 'string' }, G: { type: 'string' },
  key_quotes: { type: 'array', items: { type: 'string' } },
}, required: ['A','B','C','D','E','F','G','key_quotes'] }

phase('Read')
const reads = await parallel(DOCS.map(d => () =>
  agent(`Document: ${d.path} (${d.note}).\n${Q}`, { label: `read:${d.key}`, phase: 'Read', schema: ANS }).then(r => ({ key: d.key, ...r }))))
const ok = reads.filter(Boolean)
log(`read ${ok.length}/${DOCS.length} documents`)

phase('Answer')
const answer = await agent(`Merge these per-document answers into one record (markdown, raw, every claim followed by [file:line]). Where documents disagree, prefer the newest (tasks-plan, then for-jeremy, then jeremy-tasks) and say so.
Then give a direct verdict on this question from the user: "would running 'sudo dmidecode -t 17' or relaxing perf_event_paranoid on CRB impact what Jeremy is doing?" Separate: (1) what the documents literally support, (2) inference from general Linux knowledge, labelled as such.
Also produce a 'constraints for our cache/DRAM benchmark runs' list: time windows to avoid, CPUs to avoid, announcements to make, and anything about memory/cache traffic interfering with Jeremy's latency runs (shared L3 and DRAM are shared by all 128 cores, so an all-core bandwidth sweep on CPUs 0-119 still competes with CPUs 120-127 for L3 and DRAM; state whether the documents address this).
DATA:\n${JSON.stringify(ok, null, 1)}`, { label: 'answer', phase: 'Answer' })
return { answer, reads: ok }