export const meta = {
  name: 'refute-drop-a-repeat',
  description: 'Three independent skeptics try to refute the claim that the run 4 boot A repeat on commit 7921962 can be dropped',
  phases: [{ title: 'Refute' }],
}
const VERDICT = {
  type: 'object',
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    evidence: { type: 'string' },
    unique_to_A_repeat: { type: 'array', items: { type: 'string' } },
  },
  required: ['refuted', 'reason', 'evidence', 'unique_to_A_repeat'],
}
const LENSES = [
  'script and code: read the diff `git diff e8e4580..7921962` in the clone and decide whether any added or changed row depends on the /dev/ocm mapping mode or on anything else that differs between boot A and boot C',
  'plan and comparisons: read follow-up-run-plan.md sections on boots A to D and the G-e controls, and decide whether any planned comparison needs the new rows on the A platform specifically rather than on C',
  'measurement validity: decide whether using boot C (prefetchers on, /dev/ocm contiguous-hint mapping, Jesse\'s build copy that samples IMP_CLUSTERPWRSTAT_EL1 before and after the latency-dram-small-l3.csv command) as the prefetchers-on source of the hit-counter rows and the software-prefetch read rows is sound, and what check in C\'s own data would confirm or reject it',
]
const BRIEF = `
Context. Repo clone: /home/jhan/workspace/ai-runs/asimov-repo (read-only; do not commit, build, or run anything on remote machines). Plan: /home/jhan/workspace/titan/cache-perf/asimov/follow-up-run-plan.md. Run 4 boot A has finished on commit e8e4580 (prefetchers on, run 3 firmware, normal /dev/ocm 4 KiB mappings). Commit 7921962 adds, in cache-mem-perf/run_followup.sh: (1) latency-dram-small-l3.csv, chase rows 64K..512K under the L2/L3 hit counter set, DRAM buffer; (2) G7 bandwidth-read-prefetch.csv, one-core read rows at 2M and 32M with kernels read, read-pf4/8/16, read-2s under --perf, DRAM buffer; (3) the G5 write-small row now runs bandwidth_r3 (ba834c0's bandwidth.c verbatim) instead of bandwidth; the write loop and the timed region are byte-identical when --perf is absent (perf_start/perf_stop are guarded by g->ok). Boots B (prefetchers off), D (prefetchers off + /dev/ocm contiguous hint) and C (prefetchers on + contiguous hint) will run on Jesse's build copy of 7921962, which also samples IMP_CLUSTERPWRSTAT_EL1 via a /dev/ocm sysfs file before and after the latency-dram-small-l3.csv command. Jesse asks whether a repeat of boot A on 7921962 is necessary; he is inclined to drop it.
Claim to refute: "Dropping the A repeat loses nothing that boot C does not already provide, because the rows added by 7921962 do not use /dev/ocm, and C runs with the prefetchers on like A; the only A-specific information the repeat would add is a second sample of the unchanged rows, which the G-e controls already cover."
Your lens: `
phase('Refute')
const votes = await parallel(LENSES.map((lens, i) => () =>
  agent(BRIEF + lens + '\nTry hard to refute the claim. Default to refuted=true only with concrete evidence from the files (quote file:line). List anything the A repeat would give that C cannot. Return structured output.', { label: `refute:${i}`, phase: 'Refute', schema: VERDICT })))
return { votes: votes.filter(Boolean) }
