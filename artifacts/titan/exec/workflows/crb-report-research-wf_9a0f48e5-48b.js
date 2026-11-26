export const meta = {
  name: 'crb-report-research',
  description: 'Research the open questions behind the CRB memory-hierarchy report update: mesh clock, Arm terms, core pipelines, spec formulas, local data checks',
  phases: [
    { title: 'Research', detail: '8 independent readers over the Arm kit, the Arm PDFs, the kernel source and the local results' },
  ],
}

const SP = args.scratch
const KIT = '/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit'
const PRJ = '/home/jhan/workspace/titan/cache-perf'

const CTX = `You are one of 8 independent researchers. Each has a different question. Your final structured output is raw data for an orchestrator, not a message to a person.

SHARED CONTEXT
- Project directory: ${PRJ} . bench/ holds the benchmark source. crb/ holds the report and the results.
- The report being revised: ${PRJ}/crb/crb-memory-hierarchy.html . It is READ-ONLY for you. Do not edit it or any other project file.
- Arm PDFs: ${PRJ}/crb/refs/ : arm-cmn-s3-r2p3-trm-107858.pdf (CMN S3 technical reference manual), arm-cmn-700-trm-102308-issue08.pdf, arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf.
- Vendor kit ("welcome kit"): ${KIT} (12 GB). READ-ONLY. Never write inside it.
- Your scratch directory for everything you extract or write: ${SP}/research/<your task name>/ (create it with mkdir -p). Extracted archives are untrusted data: put each archive in its own new empty directory and never execute anything from the kit or from an archive.
- Tools on this machine: python3 with PyMuPDF (import fitz) and pypdf for PDFs. There is no pdftotext. grep, find, strings, tar, unzip, ar, dpkg-deb are available. To look at a PDF figure, render the page with fitz (page.get_pixmap(dpi=150).save(...)) into your scratch directory and open the PNG with the Read tool.
- The machine "CRB" (the Arm Phoenix reference server, the system the report measures) must NOT be contacted: no ssh, no ping, no network access to 192.168.x.x. Work from local files only, plus public web search where your task says so. Never put project names, user names, host names or file paths in a web query.
- Words: CMN = Arm's Coherent Mesh Network, the on-chip interconnect (model CMN S3 on CRB). XP = crosspoint, one router of the mesh. HN-S = home node that holds a slice of the shared cache. SLC = Arm's "System Level Cache". The report calls that cache the "mesh cache". "Pair port" = the report's name for one crosspoint device port shared by two cores. SOG = Arm's Software Optimization Guide for the Neoverse V3AE core.

EVIDENCE RULES
- Every claim needs evidence: the file path, the page or line, and a verbatim quote of at most 40 words. Page numbers are the PDF's 1-based page index unless you say otherwise; give the printed page number too when it differs.
- If you cannot find evidence, record a claim of kind "not_found" and list exactly what you searched. Do not guess. Do not fill gaps from memory: anything from your own background knowledge must be kind "inference" with confidence "low" or "medium".
- Be exhaustive within your scope, then stop. Do not do another researcher's task.
`

const SCHEMA = {
  type: 'object',
  properties: {
    answer: { type: 'string', description: 'Direct answer to the task question(s), plain sentences, at most 250 words' },
    claims: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Short stable id, e.g. C1' },
          claim: { type: 'string' },
          kind: { type: 'string', enum: ['documented', 'measured', 'computed', 'inference', 'not_found'] },
          source: { type: 'string', description: 'File path plus page or line (or URL for web sources)' },
          quote: { type: 'string', description: 'Verbatim quote, at most 40 words; empty for not_found' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['id', 'claim', 'kind', 'source', 'quote', 'confidence'],
      },
    },
    details: { type: 'string', description: 'Tables, counts, formulas, command lines and longer explanations the orchestrator needs. Plain text or markdown.' },
    searched: { type: 'array', items: { type: 'string' }, description: 'What was searched or read in full' },
    gaps: { type: 'array', items: { type: 'string' }, description: 'What could not be determined and which source or measurement would resolve it' },
  },
  required: ['answer', 'claims', 'details', 'searched', 'gaps'],
}

const TASKS = [
  {
    key: 'kit-docs-clock',
    prompt: `TASK NAME: kit-docs-clock
QUESTION: Does any document in the vendor kit give the clock frequency of the CMN mesh (the on-chip interconnect; also called mesh, NoC, fabric, interconnect) of the Arm AGI CPU on the CRB ("Phoenix" 1OU reference server)? Does any document describe a way to read or measure that clock on a running system?
SCOPE: every document in the kit at any depth: all *.pdf (13 files), *.md, *.html, *.txt, *.rst. List them first with find. For each PDF, dump the text page by page with PyMuPDF into your scratch directory and grep the dump. Read the pages around every hit; do not judge a document by its file name.
SEARCH TERMS (case-insensitive): mesh, CMN, interconnect, NoC, fabric, uncore, clock, clk, PLL, MHz, GHz, frequency, SCP, MCP, SCMI, telemetry, "system level cache", SLC.
REPORT:
1. Every statement about the mesh or interconnect clock or its PLL (value, name, how it is set, whether firmware can change it).
2. Every other clock or frequency number the documents give (core, DDR, reference clocks, BMC), each with file, page and quote.
3. Every documented command, tool, firmware console or telemetry item that reports clock, PLL or frequency information of the SoC: name, how to run it, what it prints, privileges needed.
4. The exact words each document uses for the cache shared by all cores (for example "L3", "SLC", "system level cache", "LLC", "mesh cache"), with a count per document and one example quote.
If the mesh clock is in no document, say so plainly and list the documents you read in full.`,
  },
  {
    key: 'kit-tools-clock',
    prompt: `TASK NAME: kit-tools-clock
QUESTION: Does any tool, script, configuration or data file in the vendor kit read, set or report the CMN mesh clock (or any SoC PLL or clock), and how would a user run it on the CRB?
SCOPE: ${KIT}/tools/** (performix, arm-telemetrix, asct, soc-avl-validator, spec2017-toolkit, spec2026-toolkit, sysdiag), ${KIT}/svk-release/phx-soc-utils/**, ${KIT}/svk-release/arm-svk-installer/**, ${KIT}/svk-release/Flashing_Script, ${KIT}/svk-release/Validation_Report/**, ${KIT}/gitlab-profile/**. NOT the Linux source tarball and NOT the firmware images (another researcher has those).
METHOD: grep -rIi over text files for: cmn, mesh, pll, clk, clock, freq, MHz, GHz, interconnect, noc, scp, mcp, scmi, uncore, dtc, hns, slc. For binaries and libraries (ELF, .so, .a) use strings piped to grep -i for the same terms. For archives (tar.gz, zip, deb, rpm) list the contents first, then extract the promising ones into your scratch directory (each archive in its own new directory) and search inside. Never execute anything from the kit.
REPORT:
1. Every tool, script or telemetry item that reports a clock or frequency of the SoC: name, path, command line, output field, needed privileges, and whether it covers the mesh or interconnect clock or only core clocks.
2. Any configuration or data file that contains a mesh, interconnect or PLL frequency value (path, line, quote).
3. Telemetry: what arm-telemetrix can read from the SoC. List the metric groups relevant to CMN, mesh, clocks, PLLs and the shared cache. Quote its documentation.
4. What sysdiag and the validation report record about clocks or frequencies (quotes).
5. Which term these tools use for the shared last-level cache (L3, SLC, LLC and so on), with examples.`,
  },
  {
    key: 'kit-linux-firmware-clock',
    prompt: `TASK NAME: kit-linux-firmware-clock
QUESTION: Do the vendor's Linux patches, kernel configuration, kernel source or firmware images in the kit reveal the CMN mesh clock frequency, or a kernel or firmware interface that reports it?
SCOPE: ${KIT}/svk-release/linux/** (patch list, patches tarball, configs, source tarball), ${KIT}/svk-release/kernels/** (deb and rpm: list only, unpack only if needed), ${KIT}/svk-release/SoC_Flash/**, BMC_Flash/**, OS_Image/**, SCM_CPLD, HPM_CPLD, PDB_CPLD, VRM_FW (readme and release notes), RELEASE, README.md, checksums.
METHOD:
- Read README.md, RELEASE and arm-agi-cpu-patch-list.txt. Extract arm-agi-cpu-patches.tar.gz into scratch and grep every patch for: cmn, mesh, clk, clock, pll, freq, scmi, cppc, arm-cmn, dtc, slc, cache.
- From the source tarball extract only what you need (tar -xzf <tarball> --wildcards '<pattern>'): drivers/perf/arm-cmn.c, Documentation/admin-guide/perf/arm-cmn.rst, and any file the patches add for this platform (ACPI, clock, SCMI, EDAC, telemetry drivers). Report what the vendor patches change in arm-cmn.c, if anything.
- Kernel configs: which of these are enabled: CONFIG_ARM_CMN, CONFIG_ARM_SCMI_*, CONFIG_COMMON_CLK_SCMI, CONFIG_ACPI_CPPC_CPUFREQ, CONFIG_DEBUG_FS, CONFIG_COMMON_CLK_DEBUG or similar.
- Firmware images: run strings (strings -n 6, and strings -el for UTF-16) and grep -i for: mesh, cmn, pll, clock, clk, MHz, GHz, interconnect, INTCLK, SYSPLL, freq. Check with the file command and by looking at the first bytes whether an image is compressed or encrypted, and say so when strings are not meaningful. Do not run any binary.
REPORT:
1. Any mesh, interconnect or PLL frequency value or name found (path, offset or line, quote).
2. Any kernel interface that would expose SoC clocks at run time on this platform (SCMI clock protocol, debugfs clk_summary, ACPI tables, vendor sysfs), with evidence that it is enabled or present.
3. What the vendor changed about CMN support in Linux, if anything.
4. Negative results: what you searched that had nothing.`,
  },
  {
    key: 'mesh-clock-measure',
    prompt: `TASK NAME: mesh-clock-measure
QUESTION: How can the clock frequency of the CMN S3 mesh be read or measured on the running CRB (Linux 7.1.3, root available to the user, Linux arm_cmn PMU driver loaded as arm_cmn_0 and arm_cmn_1)? Give methods ranked by how likely they are to work, each with exact commands, needed privileges and the evidence behind it.
BACKGROUND: a root run on 2026-11-02 counted the PMU event dtc_cycles of the mesh driver during a write stream and got only about 6,500 counts per second, so that run did not give the mesh clock. Raw data: ${PRJ}/crb/results/sudo-20261102T211150Z/ (writepath.csv and logs). The script is ${PRJ}/bench/run_sudo.sh (part 5). The analysis is ${PRJ}/bench/analyze_writepath.py.
SOURCES:
- CMN S3 TRM: ${PRJ}/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf (about 1,700 pages; search the text with PyMuPDF). Look up the debug and trace controller (DTC) cycle counter: por_dt_pmccntr, por_dt_pmcr, por_dt_dtc_ctl, and every field that enables or gates it (dt_en, pmu_en, cntr_rst, cg_disable, clock gating, "HCG", "high-level clock gating"). What clock does it count? Is there a note on when it stops? Is there any register that reports a clock ratio or frequency? Which clocks does the TRM name, and do device ports use the same clock?
- Linux driver source: extract drivers/perf/arm-cmn.c and Documentation/admin-guide/perf/arm-cmn.rst from ${KIT}/svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz into your scratch directory (tar -xzf ... --wildcards '*/drivers/perf/arm-cmn.c' '*/Documentation/admin-guide/perf/arm-cmn.rst'). Read how dtc_cycles is implemented (event add, start, read; CMN_DT_PMCR; CMN_DT_DTC_CTL; the cycle counter), and what perf command line it needs (system-wide -a? which CPU? does it need another event to keep the DTC enabled?).
- The local result files above: how exactly dtc_cycles was invoked, the raw counts and the durations. Compute counts per second. Decide whether the low count is explained by the driver, by clock gating, or by the invocation.
- Optional web search for public facts only: the kernel's arm-cmn documentation, typical CMN mesh clock, the "interconnect" clock in Arm's open SCP-firmware for Neoverse reference designs.
DELIVER:
1. An explanation of the 6,500 per second result, with evidence (TRM quote, driver lines, data).
2. Method A: a corrected perf invocation for dtc_cycles if one exists (exact command, expected output, how to turn it into GHz, what would invalidate it).
3. Other methods (firmware console, SCMI or debugfs clk, ACPI, vendor tool, direct register read through /dev/mem with the TRM offsets, timing-based estimate), each with feasibility, risk (anything that writes a register is a risk: say so) and evidence.
4. What cannot be known from documents alone.`,
  },
  {
    key: 'terminology',
    prompt: `TASK NAME: terminology
QUESTION: Is "mesh cache" a term Arm uses? What do Arm's documents, the vendor kit and Linux call the 128 MiB cache that all 128 cores of the CRB share (the cache inside the CMN mesh home nodes)? Colleagues of the report's author suggested "SLC" as the common term. Recommend a term.
SOURCES:
- The three Arm PDFs in ${PRJ}/crb/refs/. In each, count case-insensitive occurrences of: "mesh cache", "System Level Cache", "system-level cache", "SLC", "L3", "LLC", "last-level cache", "last level cache", "shared cache". Count whole words for SLC, L3 and LLC. Give the sentence that defines SLC, with its page.
- The vendor kit documents (all PDFs and md, html, txt files under the kit): the same counts per document, with one example quote each.
- Linux: how the kernel names it. Extract drivers/perf/arm-cmn.c and Documentation/admin-guide/perf/arm-cmn.rst from ${KIT}/svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz into scratch and quote the PMU event names that contain slc. Note that Linux cacheinfo and lscpu show the cache as level 3 ("L3").
- Web search, public facts only: how Arm's public pages for Neoverse CMN S3 and CMN-700 and for the Arm AGI CPU name this cache, and how other vendors' documents for CMN-based server chips (Ampere, AWS Graviton, NVIDIA Grace) name it.
- The report itself: ${PRJ}/crb/crb-memory-hierarchy.html . Count "mesh cache" (case-insensitive) separately in the HTML body text and inside the <script> blocks. List every place a rename would touch that needs care: element ids and href anchors that contain "mesh-cache", SVG labels inside fixed-width boxes, chart labels built in JavaScript. Quote how the report already defines the term (section "Why mesh cache" and the "Words used here" list).
DELIVER: (1) a yes or no answer to "is mesh cache an Arm term", with evidence; (2) a table of term counts per source; (3) a recommendation among: keep "mesh cache", rename to "SLC", or another form such as "SLC (L3)", with the reasons for and against each, including what a reader who knows Linux expects (lscpu shows L3); (4) the size of a rename (number of text places, ids, figures).`,
  },
  {
    key: 'sog-pipelines',
    prompt: `TASK NAME: sog-pipelines
SOURCE: ${PRJ}/crb/refs/arm-neoverse-v3ae-r0p2-software-optimization-guide-110075.pdf (read with PyMuPDF; for figures render the page to PNG into your scratch directory and open it with the Read tool).
The report section 'What "3 loads + 2 stores of 16 B per cycle" means' (${PRJ}/crb/crb-memory-hierarchy.html lines 110 to 115, plus the JavaScript that draws the figure with id "pipes", about lines 562 to 588) makes claims about the core's pipelines. Check every claim against the guide and answer the questions. Quote the guide with page and table or figure number.
Q1. List every execution pipeline of the core exactly as the guide names them (Figure 2-1, Table 2-1): branch, integer, load, store, load/store, store data, FP/ASIMD and so on, with how many of each. The report says "five pipelines that handle memory instructions" and then names four (Load/Store 0, Load 1, Load 2, Store 1). What is correct? The report also says "the core has only two vector pipelines (FP/ASIMD 0 and 1)". Is that what the guide says?
Q2. Per cycle: the maximum number of loads, the maximum number of stores, and which mixes are possible (3 loads + 1 store? 2 loads + 2 stores? 4 loads + 1 store?). The report's author asks: "is that right the pipelines can be configured as 4 read plus 1 write?" Answer yes or no with the guide's evidence. Note any wording about address generation versus store data.
Q3. Throughput and latency rows for: LDR and LDP of Q registers, STR and STP of Q registers (the report cites Table 3-13 page 23 and Table 3-14 page 25), scalar LDR, LDP, STR, STP of X registers, and SVE contiguous loads and stores (LD1D, ST1D) if listed. Is 16 B the widest single load or store? What SVE vector length does this core have?
Q4. L1 load-to-use latency: what latency does the guide give for a plain 64-bit load such as "ldr x0, [x0]" (pointer chasing)? Is 4 cycles documented? Is there a faster path?
Q5. Vector add: the rows for ASIMD integer add (ADD Vn.2D) and SVE integer add: latency, throughput per cycle, pipelines. Also: branch throughput (taken branches per cycle), integer add and cmp, and any "dispatch constraints" section (micro-operations per cycle in total and per pipeline group). Quote them.
Q6. Does the guide say anything about L1 or L2 cache bandwidth, fill rate, or bytes per cycle the L1 or L2 can deliver? (Needed to decide whether a calculated "spec" throughput exists for L1 and L2.)
Q7. With your answers, check these computed limits: 3 loads x 16 B x 2.8 GHz = 134.4 GB/s read; 2 stores x 16 B x 2.8 GHz = 89.6 GB/s write; copy with 2 loads + 2 stores of 16 B = 64 B per cycle = 179.2 GB/s. State any assumption the guide does not support.
Finally list every statement in the report section that the guide contradicts or does not support, each with corrected wording.`,
  },
  {
    key: 'data-checks',
    prompt: `TASK NAME: data-checks
Work only from local files under ${PRJ}/crb/ (results/, inspection-record-2026-10-30.md, data-all.json, plan-2026-11-02.md, the report HTML) and ${PRJ}/bench/.
Q1 "still rising". The caption of the first figure in the report says the mesh-cache bandwidth "was still rising at the footprint limit". Other places say "The mesh-served part was still rising with thread count, so 0.62 TB/s is a lower bound". Find the raw data: results/slc-20261030T194835Z, results/uncore-20261030T203537Z, results/uncore2-20261030T203752Z, results/followup3-20261102T031936Z (perthread-asmread-3M-40.csv), and any mesh-counter file for thread counts other than 40. Report: the total GB/s at each thread count (8, 16, 24, 32, 40); for which thread counts the mesh counters give a mesh-served share, and that share; whether "the mesh-served part was rising" is measured, or only the total; what "footprint limit" means in numbers (3 MiB per thread times 40 threads = 120 MiB against the 128 MiB cache); which CPUs the threads were on at each count (the report says the last 8 of the 40 sit on the second mesh). Then explain in two plain sentences what the phrase means.
Q2 Core clock. The report says: "Core, 2.8 GHz fixed: Read from the machine (cpufreq governor and frequency). Consistent with the measured cycles: 1.43 ns x 2.8 GHz = 4.0." Find all local evidence for the core clock: the inspection-record lines (scaling_cur_freq, cpuinfo_max_freq, cpuinfo_avg_freq, governor, boost), and any direct measurement in results (perf stat output with cycles and elapsed time or a "GHz" figure; "cycles per line" in results/sudo-20261102T211150Z/writepath.csv; any task-clock plus cycles pair). Compute the frequency each one gives. State which evidence is a reading of a setting and which is a measurement of the delivered clock.
Q3 Numbers in the hierarchy figure. For each label give the raw value and the file it comes from: 1.43 ns; 133 GB/s (132.7); 3.75 ns; 85 GB/s (85.2); about 80 GB/s per 2 cores (78); 30 ns; at least 0.62 TB/s; 148 ns; 533 GB/s; 89.5 GB/s write; and at L1 the compiled read 66.8, compiled write 44.0 and compiled copy 88.0 GB/s.
Q4 Compiled kernels. Search every local file (results logs, plan and review documents, README) for a record of the disassembly of the compiled kernels (k_read, k_write, k_copy in bench/bandwidth.c), and for what gcc version, flags and -march=native resolved to on CRB (look for "gcc", "-march", "Features", "sve", "asimd" in the inspection record and in logs). Report the CPU feature flags recorded for CRB (from /proc/cpuinfo or lscpu) if present, with file and line.`,
  },
  {
    key: 'mesh-spec-formula',
    prompt: `TASK NAME: mesh-spec-formula
The report's first figure will get a "Spec" row: for each hardware block, the throughput that follows from its specification. For the core it is pipelines x 16 B x clock. For the "pair port" (two cores sharing one crosspoint device port, the report's reading is a CAL2) and for the "mesh cache" (the SLC inside the HN-S home nodes) the author wants "unknown", because the mesh clock is not known. Your job: find from the CMN S3 TRM what the calculation would be if the clock were known, and which other parameters it needs.
SOURCES: ${PRJ}/crb/refs/arm-cmn-s3-r2p3-trm-107858.pdf (PyMuPDF text search; about 1,700 pages). Also ${PRJ}/crb/results/cmn-map.txt (the mesh map printed by the Linux driver) and the report for what was measured (pair port: 78 GB/s for two partner cores together; one core alone 67 GB/s; the report says mesh data flits are "32 B each").
QUESTIONS:
Q1. CHI channels at a device port: which channels carry read data to a requester (RN-F) and write data from it? How many flits per clock cycle can one device port transfer per channel? How wide is a data flit (DAT channel data width options such as 128, 256, 512 bits)? How is the width configured and which register field reports it (register name, field, page)? Where does the report's "32 B per flit" come from: can you confirm it from the TRM or from local files (search ${PRJ}/crb and ${PRJ}/bench for "32 B", "flit", "256")?
Q2. CAL (Component Aggregation Layer), CAL2 and CAL4: does the TRM say how the devices behind one CAL share the port (arbitration, one flit per cycle in total)? Quote it. Any credit or throughput statement.
Q3. Mesh links between crosspoints: flits per cycle per link; any multi-lane or dual-channel option; the register fields that report them.
Q4. HN-S and SLC: does the TRM give any throughput figure or structural limit for the SLC (requests per cycle, number of pipelines, queue sizes)?
Q5. Clocks: what clocks does the TRM name for the mesh and for device ports? Any statement about the ratio to the core clock, or about asynchronous bridges between cores and the mesh? Any typical frequency?
Q6. Write the formulas: pair-port limit = f(mesh clock, flit width, flits per cycle); mesh-cache limit = f(...). List each input as: known for CRB (with source), readable from a register (which one), or unknown. With the measured 78 GB/s and a 32 B flit, one flit per cycle would imply a mesh clock of 78e9 / 32 = 2.44 GHz. Label that as inference and say what would confirm it.
Keep every claim tied to a TRM page and quote.`,
  },
]

phase('Research')
log('Launching ' + TASKS.length + ' research agents')
const results = await parallel(TASKS.map(t => () =>
  agent(CTX + '\n' + t.prompt, { label: t.key, phase: 'Research', schema: SCHEMA })
    .then(r => ({ key: t.key, result: r }))
))
const ok = results.filter(Boolean).filter(r => r.result)
log(ok.length + ' of ' + TASKS.length + ' research agents returned a result')
return { returned: ok.map(r => r.key), missing: TASKS.map(t => t.key).filter(k => !ok.some(r => r.key === k)), results: ok }
