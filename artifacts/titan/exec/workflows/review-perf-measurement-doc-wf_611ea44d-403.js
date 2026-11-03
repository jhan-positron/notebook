export const meta = {
  name: 'review-perf-measurement-doc',
  description: 'Review perf-measurement-tech.html for accuracy against the code, plain English, requirement coverage and diagram geometry',
  phases: [{ title: 'Review' }, { title: 'Verify' }],
}
const DOC = '/home/jhan/workspace/titan/cache-perf/crb/perf-measurement-tech.html'
const BENCH = '/home/jhan/workspace/titan/cache-perf/bench'
const CRB = '/home/jhan/workspace/titan/cache-perf/crb'
const CTX = `Document under review: ${DOC} (read it in full with cat -n).
Sources it must agree with: ${BENCH}/bandwidth.c, ${BENCH}/run_sudo.sh, ${BENCH}/README.md, ${BENCH}/Makefile, ${BENCH}/subtract.py, ${BENCH}/run_crb.sh; measured numbers in ${CRB}/crb-memory-hierarchy-brief.html and ${CRB}/crb-memory-hierarchy.html (strip tags with sed 's/<[^>]*>/ /g' to read); cache sizes in ${CRB}/results/20261030T193108Z/sysinfo.txt; mesh map ${CRB}/results/cmn-map.txt.`
const FIND = {
  type: 'object',
  properties: {
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['high', 'medium', 'low'] },
      location: { type: 'string', description: 'line number(s) in the HTML file and a short quote of the offending text' },
      problem: { type: 'string' },
      evidence: { type: 'string', description: 'file:line of the source that contradicts or supports' },
      fix: { type: 'string', description: 'the exact replacement text or SVG attribute change' },
    }, required: ['severity', 'location', 'problem', 'evidence', 'fix'] } },
    summary: { type: 'string' },
  }, required: ['findings', 'summary'],
}
const VERDICT = { type: 'object', properties: {
  valid: { type: 'boolean', description: 'true only if the finding is a real defect confirmed against the sources' },
  reason: { type: 'string' }, refined_fix: { type: 'string' } }, required: ['valid', 'reason', 'refined_fix'] }

const LENSES = [
  { key: 'accuracy', prompt: `Lens: TECHNICAL ACCURACY. Check every factual claim in the prose, figure captions, table and card bullets against the code and the measured reports: numbers (GB/s, ns, B/cycle, counts per line, sizes, line numbers in the ref lines), code behaviour descriptions, and hardware statements. Flag any number that does not appear in the sources, any claim about what the code does that the code does not do, any hypothesis presented as fact, and any line-number reference that is off. Do not flag style.` },
  { key: 'english', prompt: `Lens: PLAIN ENGLISH (the plain-english skill rules in your CLAUDE.md). Check: every code name, acronym and metric defined at first use or in "Words used here"; one claim per sentence (split on because/since/which means/so that/semicolons); every number with a unit and meaning where needed, estimates marked est.; no idioms or metaphors; short sentences; the Short version at most three sentences. Report concrete violations with the corrected sentence. Ignore text inside <pre> blocks (verbatim code) and SVG labels under 6 words.` },
  { key: 'coverage', prompt: `Lens: REQUIREMENT COVERAGE and SUCCINCTNESS. The user asked for: (1) distilled techniques of cache/DRAM perf measurement with relevant code snippets quoted; (2) top-down order: architecture overview, data paths, potential bounds along the paths; (3) highlighted implementation techniques: data set sizes, load/write instructions, read/write patterns, avoiding/causing cache hits/misses, core/cache/mesh/dram spread and shape; (4) a closing summary of key take-aways; (5) reader = experienced software engineer who wants to implement it manually; (6) diagrams; (7) succinct, bullets, no lengthy prose. Check each requirement is met, name anything missing or thin (compare against the full list of techniques in bandwidth.c and run_sudo.sh: read both files), and flag any passage that is verbose relative to its information content with a shorter replacement. Also flag duplicated content between cards.` },
  { key: 'geometry', prompt: `Lens: DIAGRAM GEOMETRY. No browser is available, so check the eight inline SVGs by their coordinates. For each <svg>: compute whether any <text> label (estimate width as 6.3 px per character at font-size 12, 5.8 at 11) overlaps another text or a box edge it is not inside, whether every element lies inside the viewBox, whether dumbbell dot positions in Figure 3 match the stated numbers with the scale x = 70 + 4 * GB/s (check every circle cx against its label), whether Figure 4's log-scale positions match x = 60 + 52 * log2(size / 16 KiB), and whether arrows start and end at box edges. Also check the HTML layout rules: side gutters via max(16px, env(safe-area-inset-*)), min-width: 0 on grid children holding code, overflow-x: auto on wide containers, single light theme with explicit body background. Report each defect with the exact attribute change.` },
]

phase('Review')
const results = await pipeline(LENSES,
  l => agent(`${l.prompt}\n${CTX}\nReturn findings ordered by severity. Be specific: an exact location and an exact fix for each. Do not pad with trivial items; an empty list is a valid answer if the lens is clean.`, { label: `review:${l.key}`, phase: 'Review', schema: FIND }),
  (res, l) => {
    if (!res) return null
    log(`${l.key}: ${res.findings.length} findings`)
    return parallel(res.findings.map(f => () =>
      agent(`Adversarially verify ONE review finding about ${DOC}. Default valid=false if you cannot confirm it against the sources.\nFinding: ${JSON.stringify(f, null, 1)}\nOpen the document at the cited lines and the cited source. Confirm the defect is real (for accuracy: the source really says otherwise; for English: the rule really is violated; for coverage: the item really is missing from the whole document, search it; for geometry: recompute the coordinates). Give a refined_fix that is minimal and exact.\n${CTX}`, { label: `verify:${l.key}:${f.location.slice(0, 24)}`, phase: 'Verify', schema: VERDICT, effort: 'high' })
        .then(v => ({ lens: l.key, finding: f, verdict: v })))).then(vs => ({ lens: l.key, summary: res.summary, items: vs.filter(Boolean) }))
  })
const out = results.filter(Boolean)
const confirmed = out.flatMap(r => r.items.filter(i => i.verdict && i.verdict.valid).map(i => ({ lens: r.lens, ...i.finding, refined_fix: i.verdict.refined_fix })))
const rejected = out.flatMap(r => r.items.filter(i => !i.verdict || !i.verdict.valid).map(i => ({ lens: r.lens, location: i.finding.location, problem: i.finding.problem, reason: i.verdict ? i.verdict.reason : 'no verdict' })))
log(`confirmed ${confirmed.length}, rejected ${rejected.length}`)
return { confirmed, rejected, summaries: out.map(r => ({ lens: r.lens, summary: r.summary })) }