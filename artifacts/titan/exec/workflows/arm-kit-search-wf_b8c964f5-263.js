export const meta = {
  name: 'arm-kit-search',
  description: 'Search the Arm welcome kit for material on core prefetch and request-limit controls and CMN mesh tuning',
  phases: [{ title: 'Search' }],
}
const ROOT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit'
const CTX = `Context. On the Arm AGI CPU reference server ("CRB": 128 Neoverse V3AE cores, two CMN S3 meshes of 64 cores) a memory read benchmark with 120 threads reads about 300 GB/s with a load-only loop and about 468 GB/s with a loop whose out-of-order window covers fewer cache lines. Measurements show the mesh and DRAM are not congested in the slow case; each core just keeps fewer requests outstanding. The effect needs a sequential stream and threads on both meshes. Hypotheses: (a) the core has a dynamic limit on outstanding L2 requests or an adaptive hardware-prefetch mode (in Neoverse V2 these are in IMP_CPUECTLR_EL1 / IMP_CPUECTLR2_EL1: PF_MODE, TXREQ_LIMIT, TXREQ_LIMIT_DYNAMIC, CBUSY filter); (b) CMN CBusy / throttling settings; (c) firmware or BIOS options that set these.
We want to know whether this vendor kit helps to: read or change the core prefetch / request-limit controls (a tool, a kernel patch, a sysfs or debugfs node, a firmware / UEFI / BMC option, an SMC call, an EL3 setting), read CMN configuration (cbusy, throttling, HN-S/HN-F settings), find documented memory-bandwidth expectations or known issues, or find a support contact route to Arm.
Rules: read-only. Do not modify, build, install or execute anything from the kit. Do not log in to any machine. No network requests. Large binaries (OS images, firmware blobs) are not to be unpacked; tarballs of source or patches may be listed and their text files extracted ONLY into your scratch folder under /tmp (never into the kit or ~/workspace). PDFs: use the Read tool with pages, or pdftotext if present.
Report facts with exact file path and page / line, and quote the relevant text. Say plainly when you found nothing. Mark guesses as hypotheses.`
const SCHEMA = { type: 'object', properties: {
  summary: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', properties: {
    topic: { type: 'string' }, file: { type: 'string' }, location: { type: 'string' }, quote: { type: 'string' }, relevance: { type: 'string' }, usable_without_reboot_or_install: { type: 'string' } },
    required: ['topic', 'file', 'location', 'quote', 'relevance'] } },
  not_found: { type: 'array', items: { type: 'string' } } }, required: ['summary', 'findings', 'not_found'] }
const AREAS = [
  { key: 'docs', p: `Area: all documentation: ${ROOT}/docs, ${ROOT}/svk-release/docs (user guide PDFs), ${ROOT}/svk-release/README.md, RELEASE, Validation_Report, ${ROOT}/gitlab-profile. Look for: BIOS/UEFI setup options (prefetch, CMN, memory), firmware settings, known issues, memory bandwidth figures (for example STREAM results in the validation report), support contact route.` },
  { key: 'linux', p: `Area: ${ROOT}/svk-release/linux (patch list, patches tarball, kernel configs, README) and ${ROOT}/svk-release/kernels. Look for patches or config options that touch CPUECTLR, prefetch, IMP DEF registers, CMN, MPAM, errata workarounds for Neoverse V3AE, any sysfs/debugfs node for prefetch control, and config options that matter for loading a self-built module (CONFIG_MODULE_SIG, CONFIG_MODULE_SIG_FORCE, CONFIG_SECURITY_LOCKDOWN_LSM, CONFIG_MODULES, CONFIG_KPROBES, CONFIG_DEVMEM, CONFIG_ARM64_... ). List the patch titles that are relevant.` },
  { key: 'tools', p: `Area: ${ROOT}/tools (performix, arm-telemetrix, asct, soc-avl-validator, spec2017-toolkit, spec2026-toolkit, sysdiag) and ${ROOT}/svk-release/phx-soc-utils. Look for: any tool or script that reads or writes core system registers (CPUECTLR, prefetch), CMN registers or mesh configuration; telemetry definitions for the core or CMN (events about prefetch, cbusy, throttling); memory-bandwidth tests with expected values (asct, sysdiag); recommended tuning in the SPEC toolkits (prefetch settings, kernel boot parameters, BIOS settings). Say for each tool what it is and whether it needs root, a kernel module, or installation.` },
]
phase('Search')
const r = await parallel(AREAS.map(a => () => agent(`${CTX}\n\n${a.p}`, { label: a.key, phase: 'Search', schema: SCHEMA })))
return r.map((x, i) => ({ area: AREAS[i].key, ...(x || { summary: 'agent returned nothing', findings: [], not_found: [] }) }))
