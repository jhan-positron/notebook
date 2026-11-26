export const meta = {
  name: 'crb-mesh-map-research',
  description: 'Research and adversarially verify facts about the CRB mesh map (ports, cores, home nodes) for a new diagram',
  phases: [{ title: 'Research' }, { title: 'Verify' }],
}
const DIR = '/home/jhan/workspace/titan/cache-perf/crb'
const COMMON = `Context: ${DIR}/crb-memory-hierarchy.html is a report on the Phoenix Reference Server (CRB), an Arm machine with two CMN S3 meshes (arm_cmn_0, arm_cmn_1). Section 'Why "mesh cache"' has an SVG diagram (script block starting with the comment "// Mesh map:", data array D, about line 718-760) drawn from the Linux arm-cmn debugfs map saved in ${DIR}/results/cmn-map.txt (raw copies: ${DIR}/results/map and ${DIR}/results/map_1). This is READ-ONLY research: do not modify any file under ${DIR}. Put scratch scripts under ${DIR}/tmp/agent-scratch/ only if you need them. Do not scan the whole filesystem (no "find /"). Every claim must cite its evidence: a file path with line number, a PDF page with a verbatim quote, or a URL with a verbatim code quote. If you cannot find evidence, say "Insufficient data" and name what would resolve it. Do not guess.`
const SCHEMA = { type: 'object', properties: {
  summary: { type: 'string' },
  claims: { type: 'array', items: { type: 'object', properties: {
    claim: { type: 'string' }, evidence: { type: 'string' }, source: { type: 'string' },
    confidence: { type: 'string', enum: ['verified', 'likely', 'hypothesis', 'insufficient-data'] } },
    required: ['claim', 'evidence', 'source', 'confidence'] } } },
  required: ['summary', 'claims'] }
const TASKS = [
  { key: 'map', prompt: `${COMMON}

Task: compute, with a script (python3), the exact facts in the map files.
1. Parse results/cmn-map.txt (it holds both maps, "map" then "map_1") and results/map, results/map_1. Report grid size (columns X, rows Y), and whether mesh 0 and mesh 1 maps are byte-identical / cell-identical.
2. Extract the D array from the HTML (the "// Mesh map:" script) and compare every one of the 72 entries (x, y, XP number, port 0 type, port 0 logical ids, port 1 type, port 1 logical ids) with the parsed map of mesh 0. Report every mismatch, or state there are none.
3. Counts per mesh: crosspoints with port 0 = HN-S and two ids; crosspoints with port 0 = HN-S and no ids (list XP numbers and x,y); crosspoints with port 1 = RN-F_F_E (list x,y range); crosspoints with no RN-F port. Does any RN-F port row print a logical id? Which HN-S logical ids between the minimum and maximum are missing, and do the gaps line up with the id-less HN-S ports (e.g. would XP 46 be ids 56,57)?
4. Does the map print only ports 0 and 1 (the P column)? How many device rows (D column) per port?
5. For each of the 72 crosspoints give: XP number, x, y, port 0 type+ids, port 1 type+ids, in a compact list (put it in the summary as JSON).` },
  { key: 'driver', prompt: `${COMMON}

Task: read the Linux driver source drivers/perf/arm-cmn.c (fetch https://raw.githubusercontent.com/torvalds/linux/master/drivers/perf/arm-cmn.c with WebFetch or curl; if a local kernel tree exists under /usr/src use it too; if fetch fails try https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/drivers/perf/arm-cmn.c). Answer with verbatim code quotes:
1. How arm_cmn_map_show prints a crosspoint: what the P column and the D column (rows "0|" and "1|") are, where the port's device type string comes from (which register/function, e.g. arm_cmn_device_connect_info / arm_cmn_device_type), and where the "#N" numbers come from (arm_cmn_show_logid: which nodes it searches).
2. What exactly the strings "RN-F_F_E", "SN-F_F", "HN-S", "????" and a blank cell mean in arm_cmn_device_type (list the full switch table with codes).
3. Why an RN-F port never prints a "#N" id (is an RN-F a CMN-internal node the driver discovers, or an external device?). Why a port can print "HN-S" with no "#N" under it (which conditions in discovery skip or omit a node: e.g. child node pointer flagged external, node not present, type filtered). State what can and cannot be concluded from "HN-S port type with no logical ids".
4. Does the driver read whether a CAL is on a port (CMN__CONNECT_INFO / CAL_CONNECTED bits), and does the map print it? How many device ports per XP does the driver support (CMN_MAX_PORTS) and how many devices per port does the map print? How does the driver decide how many ports to print (ports_used)?
5. Can the map tell how many cores sit on an RN-F port? Answer yes/no with reason.` },
  { key: 'trm', prompt: `${COMMON}

Task: read the Arm CMN S3 Technical Reference Manual at ${DIR}/refs/arm-cmn-s3-r2p3-trm-107858.pdf (13 MB; use pdftotext if installed, e.g. "pdftotext -layout file.pdf ${DIR}/tmp/agent-scratch/cmn-s3.txt", or python with pypdf/PyMuPDF if installed, or the Read tool with the pages parameter; search for keywords, do not read all pages). Give verbatim quotes with PDF page numbers for:
1. How many device ports one crosspoint (XP) can have (the maximum, and any dependence on the number of mesh ports or position in the mesh).
2. What an RN-F is, and whether the RN-F (the core / processor) is a device outside CMN connected to an XP device port, i.e. whether "device port" and "device (RN-F)" are separate entities. Same question for HN-S: is HN-S a CMN-internal node attached to an XP device port?
3. Component Aggregation Layer (CAL): which variants exist in CMN S3 (CAL2, CAL3, CAL4?), which device types each supports, and so the maximum number of RN-Fs (cores) on one device port and on one XP. Also any limit on total RN-Fs in a mesh.
4. The por_mxp_device_port_connect_info register (or equivalent): the device_type field encodings (especially the code and name for the type the Linux driver prints as "RN-F_F_E": RN-F CHI-F with ESAM?), and any field that says a CAL is connected or how many devices are behind the CAL.
5. Any statement on whether an XP port configured as HN-S can exist without an HN-S node, or about HN-S nodes that are isolated/disabled/absent (for example por_hnf/hns isolation, or build options).
6. Whether a core with DSU/cluster counts as one RN-F.` },
  { key: 'cores', prompt: `${COMMON}

Task: establish from measured data how many cores sit on each crosspoint on CRB.
1. Read ${DIR}/results/sudo-20261102T054936Z/core-positions.json (and nearby files, run.log, and ${DIR}/../bench/fitpos.py or wherever fitpos.py lives near ${DIR}; search inside /home/jhan/workspace/titan/cache-perf only). With a script, compute per mesh: number of CPUs placed, number of crosspoints that have CPUs, CPUs per crosspoint (min/max/histogram), and the list of crosspoints (x,y) that the map shows with an RN-F core port (x 1..7, y 1..5) but that received no CPUs. Compare with the POS array in the "// Core map:" script in the HTML and report mismatches.
2. How was the position inferred (method, residuals, how confident), and is it a measurement or a fit? Quote the code/log.
3. From ${DIR}/inspection-record-2026-10-30.md, ${DIR}/mesh0-or-mesh1.md and the HTML: how many CPUs the machine has (128?), which are reserved (120 to 127?), which CPUs belong to which mesh, and the measured evidence that cores 2k and 2k+1 share one port (the "pair finding": 78 GB/s vs 134 GB/s). Cite file and line.
4. State explicitly: per mesh, 35 RN-F ports in the map; how many carry 2 cores, 1 core, 0 cores according to the fit (mesh 0 with CPUs 0-63, mesh 1 with CPUs 64-119 measured and CPUs 120-127 not measured). Flag anything that is inference rather than measurement.` },
]
const results = await pipeline(TASKS,
  t => agent(t.prompt, { label: `research:${t.key}`, phase: 'Research', schema: SCHEMA }),
  (r, t) => r ? agent(`${COMMON}

You are a skeptical verifier. Another agent researched the topic "${t.key}" and returned the claims below. Independently re-check EACH claim against the primary source it cites (re-open the file / PDF page / URL yourself; re-run counts with your own script). Try to refute. For each claim return it with confidence 'verified' only if you reproduced the evidence yourself; otherwise downgrade it and say what is wrong in the evidence field. Add any important correction or missing fact as a new claim. Original task was:
${t.prompt}

Claims to check:
${JSON.stringify(r, null, 1)}`, { label: `verify:${t.key}`, phase: 'Verify', schema: SCHEMA }).then(v => ({ key: t.key, research: r, verified: v })) : null)
return results