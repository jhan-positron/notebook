export const meta = {
  name: 'perf-pages-update',
  description: 'Rebuild the four Asimov perf pages on run 4 boot E data, verify every number against the CSVs, fix findings',
  phases: [
    { title: 'Data layer', detail: 'gen_perf.py: boot E tables beside run 3' },
    { title: 'Pages', detail: 'core page, CME page, two briefs in parallel' },
    { title: 'Verify', detail: 'one independent checker per page' },
    { title: 'Fix', detail: 'apply confirmed findings, regenerate' },
    { title: 'Re-verify', detail: 'fixed items, print check, hashes' },
  ],
}
const SPEC = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/perf-update/SPEC.md'
const DIR = '/home/jhan/workspace/titan/cache-perf/asimov'
const COMMON = `Work in ${DIR}. Read ${SPEC} first and follow its hard rules (section 2) exactly: never edit gen_run3.py, gen_run4.py or anything under results/; never run gen_run3.py or gen_run4.py as scripts; import them only. The previous pages and scripts are in the spec's prev/ folder. Keep prose to the plain-english rules in CLAUDE.md. Your final text is returned to the orchestrator as data, not shown to the user: report facts, file names and numbers, no pleasantries.`

phase('Data layer')
const data = await agent(`${COMMON}

Task: write ${DIR}/gen_perf.py, the data layer for the four pages described in the spec, plus its main().

Requirements:
- At the top: \`import gen_run3 as g\` and \`import gen_run4 as r4\` (both import in about 3 s; gen_run4 computes every boot's tables at import: r4.BT['A'..'E'] are dicts with the names load_boot() returns (LV, CLV, OCM, ALL5, TLB, ROUTE, FIT, COCM, CALL5, W, REPEAT_SAME, N_WITHIN, CTRL, RT_NS, P4K, CHIP_S, CMDS, README, LOG, SPLIT, SPLIT_ALL5, ...), and r4 has module-level EX, FIVE, G8, G8_MARGINAL, RP_BEST, RP_KERNELS, RP_SIZES, E_L3, L3_HIT_EST, EC_RATIO, ALL5_DENSE_BEST, RATIOS, TLB_PASS, TLB_PASS_RNG, GAP_MEAN, STIM, WALK_STIM, CME_INNER_SHARE, EC_CLV_RATIO, BOOT_ORDER, BOOT_RUN_ID, BOOT_NAME, BOOT_COL, dotplot, stacked_h, hyp, ok, no, gap, rng, mono). Read gen_run4.py (lines 1-760) and gen_run3.py (lines 1-700) to learn the exact shapes before you write anything.
- Expose, with a module docstring that lists every exported name and its meaning and source file, everything the three page builders need per the spec's sections 3 and 4: the boot tables (E, C, A, B, D as short names), the level map of boot E with run 3 and boot C beside each row (ns3, nsC, E/C ratio, E's L3 hits per load from the hit set where measured, refills), the sequential row, the hit set, the read variants, the G8 rows and fits and the marginal rate, the small write rows (W), the route rows of E and A with E's L3 refills per hop and distance, the dense all-five rows for CPUs 2 and 8 across boots and run 3, the OCM pair ratios and TLB-per-pass ranges from r4, the CME level map of E with run 3 and C beside it (ratios, outer/inner refills, inner share), the CME OCM rows (E, run 3), the roundtrip controls, the repeat check E vs run 3 and A vs run 3, platform facts per boot (commit, scp, tfa, pwrstat, date from the README, chip seconds, command count), and helper functions level_name_e(size, kind) (L3-on wording: 192 to 384 KiB "L2 and L3 (mixed)", 512 KiB "L3 and SLC (mixed)", else as gen_run3.level_name but never the "held no data" wording) and bw_level_e(size).
- A META string for the four pages' subtitle (boot E as the latest, run 3 beside it, the L3 point) and a SOURCES list.
- main(): for each of (gen_perf_core.core_page -> asimov-c1nano-perf.html, gen_perf_cme.cme_page -> asimov-cme-perf.html, gen_brief.core_brief -> asimov-c1nano-perf-brief.html, gen_brief.cme_brief -> asimov-cme-perf-brief.html) import the module inside try/except, write the page, and print which pages were written and, for a failure, the module and the exception. Those page modules do not exist yet; main must not crash when they are missing.
- Assert the sanity facts the spec lists (controls 2.002 and 21.00 ns, E pwrstat 0x70, boot C 0x0, E's hit at 256 KiB > 0.7) so a wrong data wiring fails loudly.
- Run \`python3 gen_perf.py\` and also \`python3 -c "import gen_perf as p; print(...)"\` to print the key values and confirm they match the spec's verified facts (section 3). Report any value that does not match the spec, with both numbers, instead of adjusting the code to the spec.

Return: the list of exported names with one-line meanings (the page builders will be briefed from it), the key values you printed, and anything that did not match the spec.`, { label: 'data-layer', phase: 'Data layer' })

phase('Pages')
const PAGE_COMMON = `${COMMON}

The data layer gen_perf.py exists; import it as \`import gen_perf as p\` (it imports gen_run3 as g and gen_run4 as r4; both are reachable as p.g and p.r4). Its author reported:
${data}

Build your page module so that \`python3 gen_perf.py\` writes your page; the other page modules may not exist yet or may be mid-edit, so judge only your own page's line of the output. Do not edit gen_perf.py's exported names; if you need a value gen_perf.py does not expose, compute it in your own module from p.r4 / p.g data (never type a number in). Keep gen_run3's page shell, CSS and chart helpers (p.g.page, p.g.fig, p.g.table, p.g.line_chart, p.g.dumbbell, p.g.strip, p.g.bars_h, p.g.mesh_map, p.g.cme_path_fig, p.g.words, p.g.legend; p.r4.dotplot, p.r4.stacked_h). Read the previous version of your page in prev/ and the builder that made it (prev/gen_run3.py core_page/cme_page, or prev/gen_brief.py) and keep every section with the same subject and order. After building, open the written HTML and self-check per spec section 6 (headings order against prev/, charset meta, light theme, ASCII SVG text, est. labels, hypothesis labels, run 3 bandwidth rows labelled L3 off, plain-English rules, no "held no data" wording on boot E rows, dense all-five quoted as the OCM number). Fix what you find, then return: the sections you built, every number in the Short version with the file and row it comes from, and anything in the spec you could not satisfy and why.`

const pages = await parallel([
  () => agent(`${PAGE_COMMON}

Your page: asimov-c1nano-perf.html, built by ${DIR}/gen_perf_core.py with core_page() -> HTML string. Follow spec section 4's mapping for this page (sections 1 to 12) and section 5 for the open items (section 11). The old core_page() is in prev/gen_run3.py lines 695-908; reuse its figure and table code where the subject is unchanged (sections 4.4 to 4.6, 8, 9, 10 stay run 3 data from p.g with the L3-off label). Build a new words list from p.g.WORDS_COMMON plus the new terms; do not modify p.g.WORDS_COMMON.`, { label: 'core-page', phase: 'Pages' }),
  () => agent(`${PAGE_COMMON}

Your page: asimov-cme-perf.html, built by ${DIR}/gen_perf_cme.py with cme_page() -> HTML string. Follow spec section 4's CME mapping (sections 1 to 11) and section 5 for section 10 (settled and open). The old cme_page() is in prev/gen_run3.py lines 908-1076; reuse its figure and table code where the subject is unchanged (4.3, 4.4, 4.5, 4.6, 6, 8 stay run 3 data from p.g with the L3-off label). Boot E's CME chases come from p (r4.BT['E']['CLV'] etc.), run 3's from p.g.CLV, boot C's from r4.BT['C']['CLV'], boot B's for the prefetcher-off reading.`, { label: 'cme-page', phase: 'Pages' }),
  () => agent(`${PAGE_COMMON}

Your pages: the two briefs, built by ${DIR}/gen_brief.py (rewrite the existing file; keep its CSS, page(), fig(), the META idea and the structure of core_brief() and cme_brief(); the old file is prev/gen_brief.py). Follow spec section 4 "The briefs" and section 5 for the caveats bullets. Both briefs must print on at most 2 A4 pages: run the headless print check from spec section 2 on both files and report the page counts; if a brief exceeds 2 pages, shorten its prose (not its tables) until it fits. gen_brief.py must not run gen_perf.main() at import; its __main__ block writes the two briefs.`, { label: 'briefs', phase: 'Pages' }),
])

phase('Verify')
const FINDINGS = {
  type: 'object',
  properties: {
    page: { type: 'string' },
    generated_ok: { type: 'boolean' },
    numbers_checked: { type: 'integer' },
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['wrong-number', 'missing-label', 'structure', 'prose', 'other'] },
      where: { type: 'string' }, page_says: { type: 'string' }, csv_says: { type: 'string' }, fix: { type: 'string' } },
      required: ['severity', 'where', 'page_says', 'fix'] } },
  },
  required: ['page', 'generated_ok', 'numbers_checked', 'findings'],
}
const VERIFY_COMMON = `${COMMON}

You are an independent checker. Do NOT edit any file in ${DIR}. Write your check scripts in the spec's scratchpad folder and run them with python3 -I against the CSV files directly; do not import gen_perf, gen_run3 or gen_run4 for the check (the point is independence). CSV format notes: lines starting with # are comments; bandwidth files repeat the header line per command and their "best" rows carry "-" in the perf columns; latency rows have mode "best"/"cme-best" summary rows and numbered pass rows. The page builders' reports (what they built and where each Short-version number comes from):
${pages.map((x, i) => `--- builder ${i + 1} ---\n${x}`).join('\n')}

Check per spec section 6: (1) the page exists and was written by python3 gen_perf.py (run it once; it writes all four pages), charset meta, light theme only, ASCII in SVG text, headings of prev/ kept in order; (2) recompute the numbers listed in spec 6.2 from the CSVs and compare; (3) labels; (4) plain English (report only clear violations); (5) for a brief, the 2-page print check. Confirm every finding by re-reading the page text before reporting it; a difference in rounding (the page prints fewer decimals) is not a finding. Return the structured result.`
const verdicts = await parallel([
  () => agent(`${VERIFY_COMMON}\n\nYour page: ${DIR}/asimov-c1nano-perf.html (previous: prev/asimov-c1nano-perf.html).`, { label: 'verify:core', phase: 'Verify', schema: FINDINGS }),
  () => agent(`${VERIFY_COMMON}\n\nYour page: ${DIR}/asimov-cme-perf.html (previous: prev/asimov-cme-perf.html).`, { label: 'verify:cme', phase: 'Verify', schema: FINDINGS }),
  () => agent(`${VERIFY_COMMON}\n\nYour page: ${DIR}/asimov-c1nano-perf-brief.html (previous: prev/asimov-c1nano-perf-brief.html).`, { label: 'verify:core-brief', phase: 'Verify', schema: FINDINGS }),
  () => agent(`${VERIFY_COMMON}\n\nYour page: ${DIR}/asimov-cme-perf-brief.html (previous: prev/asimov-cme-perf-brief.html).`, { label: 'verify:cme-brief', phase: 'Verify', schema: FINDINGS }),
])
const found = verdicts.filter(Boolean)
const total = found.reduce((n, v) => n + v.findings.length, 0)
log(`verify: ${found.map(v => `${v.page}: ${v.findings.length} findings over ${v.numbers_checked} numbers`).join('; ')}`)

phase('Fix')
let fixReport = 'no findings, nothing to fix'
if (total > 0) {
  fixReport = await agent(`${COMMON}

Four independent checkers reviewed the four generated pages. Apply every finding that is a real defect (a wrong number, a missing est./hypothesis/run-3 label, a lost section, a clear plain-English violation); skip a finding only if you verify it is wrong, and say which and why. The fixes go in gen_perf.py, gen_perf_core.py, gen_perf_cme.py or gen_brief.py (never in the HTML directly, never in gen_run3.py/gen_run4.py). After editing, run python3 gen_perf.py and confirm the four pages regenerate, then re-run the headless print check on both briefs (spec section 2).

Findings:
${JSON.stringify(found, null, 1)}

Return: each finding with fixed / skipped (reason), and the four files' sha256 (first 16 hex) after regeneration.`, { label: 'fix', phase: 'Fix' })
}

phase('Re-verify')
const final = await agent(`${COMMON}

Final check after the fix pass. Do not edit any file in ${DIR}. Run python3 gen_perf.py once. Then: (a) for every finding below marked fixed, re-read the page and confirm the fix is in place; (b) run the headless print check on both briefs and report the page counts; (c) report sha256 (first 16 hex) of the four pages and of gen_run3.py and gen_run4.py, and confirm gen_run3.py's hash is 4f4109038fb89144 (prefix) and gen_run4.py's equals that of the copy you compute at the start before running anything; (d) grep each page for "held no data" and report every occurrence with its sentence, so the orchestrator can judge whether it refers to a boot E row; (e) grep for "0.003" and report the sentence; (f) list the h2/h3 headings of each page.

Fix report:
${fixReport}

Return a plain report with those six items.`, { label: 'final-check', phase: 'Re-verify' })

return { data, pages, verdicts: found, fixReport, final }