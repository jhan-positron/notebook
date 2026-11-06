import re, sys
D = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/ca8b250c-52a6-45d3-bbc5-a704f24ca1dd/scratchpad/comments/"
files = {"S1": "-root-ed41c79f.md", "S1b": "-crb-e794ebbe.md", "S2": "-asimov-ca8b250c.md", "S3": "-asimov-bd044fcf.md"}
def load(fn):
    txt = open(D + fn).read()
    out = {}
    for m in re.finditer(r"^## \[(.+?)\]\n(.*?)(?=^## \[|\Z)", txt, re.S | re.M):
        out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out
msgs = {k: load(v) for k, v in files.items()}
# (session, timestamp, text-prefix or None, tags)
SEL = [
 ("S1","2026-10-30 16:47",None,"CRB plan"),
 ("S1","2026-10-30 18:37",None,"ocm-interpretation.html; re-wording"),
 ("S1","2026-10-30 18:50",None,"ocm-interpretation.html; diagram"),
 ("S1","2026-10-30 18:56",None,"ocm-interpretation.html; term"),
 ("S1","2026-10-30 22:23",None,"CRB report; re-run"),
 ("S1","2026-11-01 11:01",None,"crb-memory-hierarchy.html; comments in edited copy"),
 ("S1","2026-11-01 12:21",None,"crb-memory-hierarchy.html; broken characters"),
 ("S1","2026-11-01 12:31",None,"crb-memory-hierarchy.html; cache ways explanation"),
 ("S1","2026-11-01 12:42",None,"crb-memory-hierarchy.html; cache ways explanation"),
 ("S1","2026-11-01 12:45",None,"crb-memory-hierarchy.html; add worked example"),
 ("S1","2026-11-01 12:47",None,"crb-memory-hierarchy.html; cache ways explanation"),
 ("S1","2026-11-01 12:59",None,"crb-memory-hierarchy.html; re-wording"),
 ("S1","2026-11-01 17:00",None,"crb-memory-hierarchy.html; CMN topology; pair finding sentence"),
 ("S1","2026-11-01 18:33",None,"crb-memory-hierarchy.html; re-run with CMN map"),
 ("S1","2026-11-01 19:12",None,"crb-memory-hierarchy.html; open items; re-run"),
 ("S1","2026-11-01 19:30",None,"Asimov test code; CMN mesh; re-run"),
 ("S1","2026-11-01 20:39",None,"crb-memory-hierarchy.html; measured or spec"),
 ("S1","2026-11-01 20:45",None,"crb-memory-hierarchy.html; add table; table of contents"),
 ("S1","2026-11-01 22:11",None,"crb-memory-hierarchy-brief.html; new page for Bill"),
 ("S1","2026-11-02 08:02",None,"CRB; re-run after codex review"),
 ("S1","2026-11-02 09:38",None,"crb-memory-hierarchy.html; write throughput question"),
 ("S1","2026-11-02 09:40",None,"crb-memory-hierarchy.html; whole chip wording"),
 ("S1","2026-11-02 09:57",None,"crb-memory-hierarchy.html; collect counters; re-run"),
 ("S1","2026-11-02 11:59",None,"crb-memory-hierarchy.html; whole chip table; new data-path section"),
 ("S1","2026-11-02 12:04",None,"crb-memory-hierarchy-brief.html; term"),
 ("S1","2026-11-02 12:12",None,"crb-memory-hierarchy.html; interleave paragraph re-wording"),
 ("S1","2026-11-02 12:24",None,"crb-memory-hierarchy.html; interleave paragraph"),
 ("S1","2026-11-02 12:26",None,"crb-memory-hierarchy.html; interleave paragraph"),
 ("S1","2026-11-02 12:31",None,"crb-memory-hierarchy.html; interleave paragraph"),
 ("S1","2026-11-02 12:33",None,"crb-memory-hierarchy.html; interleave paragraph"),
 ("S1","2026-11-02 13:10",None,"crb-memory-hierarchy.html; add two tables"),
 ("S1","2026-11-02 13:13",None,"crb-memory-hierarchy-brief.html"),
 ("S1","2026-11-02 13:15",None,"crb-memory-hierarchy.html; interleave paragraph re-wording"),
 ("S1b","2026-11-02 11:22",None,"perf-measurement-tech.html; new page"),
 ("S2","2026-11-01 21:04",None,"Asimov run 2; plain English; test update rationale"),
 ("S2","2026-11-01 21:46",None,"process; verify other agents"),
 ("S2","2026-11-01 22:01",None,"Asimov run 2; commit; plan for codex"),
 ("S2","2026-11-02 20:42",None,"reporting; conflicting statements"),
 ("S3","2026-11-02 15:13",None,"CME test; new measurement"),
 ("S3","2026-11-02 15:53",None,"CME test; Bill's request"),
 ("S3","2026-11-02 15:56",None,"CME test; one core"),
 ("S3","2026-11-02 15:58","Do not use emulator","CME test; no emulator"),
 ("S3","2026-11-02 16:39",None,"Asimov run 3; fix known defect; re-run"),
 ("S3","2026-11-02 16:43",None,"Asimov run 3; where the fix goes"),
 ("S3","2026-11-02 16:55",None,"Asimov run 3; top-level script; re-run"),
 ("S3","2026-11-02 20:44",None,"message to Jesse; wrong SCP version"),
 ("S3","2026-11-02 20:53",None,"message to Jesse; re-wording"),
 ("S3","2026-11-03 10:35",None,"asimov-c1nano-perf.html; asimov-cme-perf.html; new pages"),
 ("S3","2026-11-03 11:04",None,"asimov-c1nano-perf.html; term"),
 ("S3","2026-11-03 11:11",None,"asimov-c1nano-perf.html; L1 miss question"),
 ("S3","2026-11-03 11:19",None,"asimov-c1nano-perf.html; kernel on all CPUs"),
 ("S3","2026-11-03 11:23",None,"asimov-c1nano-perf.html; term 'not isolated'"),
 ("S3","2026-11-03 11:26",None,"asimov-c1nano-perf.html; table 4.1 change column"),
 ("S3","2026-11-03 11:29",None,"asimov-c1nano-perf.html; add run 2 vs run 3 section"),
 ("S3","2026-11-03 12:04","What do repeat","asimov-c1nano-perf.html; define repeat/fresh/flushed"),
 ("S3","2026-11-03 12:53",None,"run 3 results; re-test or report update"),
 ("S3","2026-11-03 12:56",None,"run 3 results; codex view on re-test"),
 ("S3","2026-11-03 13:00",None,"follow-up run; re-run plan"),
 ("S3","2026-11-03 13:04",None,"asimov-c1nano-perf-brief.html; asimov-cme-perf-brief.html; new pages"),
 ("S2","2026-11-03 09:49",None,"asimov-memory-hierarchy.html; broken characters; sizes; redraw diagram"),
 ("S2","2026-11-03 10:47",None,"asimov-memory-hierarchy.html; Linux on DSUs"),
 ("S2","2026-11-03 10:52",None,"asimov-memory-hierarchy.html; kernel on all cores"),
 ("S3","2026-11-03 15:26",None,"asimov-c1nano-perf.html; fresh vs flushed"),
 ("S3","2026-11-03 15:32",None,"asimov-c1nano-perf.html; explain fresh with examples"),
 ("S3","2026-11-03 15:47",None,"asimov-c1nano-perf.html; section 3 diagram re-wording"),
 ("S3","2026-11-03 15:52",None,"asimov-c1nano-perf.html; OCM range; open item; add dense range"),
 ("S3","2026-11-03 15:58",None,"asimov-c1nano-perf.html; sparse vs dense"),
 ("S3","2026-11-03 16:03",None,"asimov-c1nano-perf.html; refill meaning"),
 ("S3","2026-11-03 16:09",None,"asimov-c1nano-perf.html; add to run 4; proof request"),
 ("S3","2026-11-03 16:25",None,"asimov-c1nano-perf.html; table 4.3 column"),
 ("S3","2026-11-03 16:32",None,"asimov-c1nano-perf.html; units; proof; follow-up plan"),
 ("S3","2026-11-03 16:34",None,"asimov-c1nano-perf.html; remove table 4.3 column"),
 ("S3","2026-11-03 16:36",None,"asimov-c1nano-perf.html; table 4.3 write bandwidth question"),
 ("S3","2026-11-03 16:47",None,"asimov-c1nano-perf.html; table 4.3 bullet"),
 ("S3","2026-11-03 16:48",None,"asimov-c1nano-perf.html; table 4.3 note"),
 ("S3","2026-11-03 16:55",None,"asimov-c1nano-perf.html; table 4.4 add ratio column"),
 ("S3","2026-11-03 16:59",None,"asimov-c1nano-perf.html; table 4.4 cells"),
 ("S3","2026-11-03 17:00",None,"asimov-c1nano-perf.html; table 4.4 undo"),
 ("S3","2026-11-03 17:04",None,"asimov-c1nano-perf.html; table 4.4 add potential column"),
 ("S3","2026-11-03 17:08",None,"asimov-c1nano-perf.html; table 4.4 read vs write pattern"),
 ("S3","2026-11-03 17:11",None,"asimov-c1nano-perf.html; table 4.4 missing 16 MiB rows; add note"),
 ("S3","2026-11-03 17:55",None,"asimov-c1nano-perf.html; re-wording with shorter sentences"),
 ("S3","2026-11-03 18:01",None,"asimov-c1nano-perf.html; tables 4.3 and 4.6 L3 vs OCM"),
 ("S3","2026-11-03 18:12",None,"asimov-c1nano-perf.html; SLC vs OCM"),
 ("S3","2026-11-03 18:18",None,"asimov-c1nano-perf.html; section 3 diagram re-wording"),
 ("S3","2026-11-03 18:22",None,"asimov-c1nano-perf.html; table of contents; new section 4.6.1"),
 ("S3","2026-11-03 18:29",None,"asimov-c1nano-perf.html; diagrams 5 and 7 add L3 and sizes"),
 ("S3","2026-11-03 18:33",None,"asimov-c1nano-perf-brief.html; keep in step; new run"),
 ("S3","2026-11-03 18:39",None,"asimov-c1nano-perf.html; section 11 review; re-wording; re-run coverage"),
 ("S3","2026-11-03 19:03",None,"asimov-c1nano-perf.html; section 11; settle vs explain"),
 ("S3","2026-11-03 19:06",None,"asimov-c1nano-perf.html; section 11 rename 'Open items'; labels"),
 ("S3","2026-11-03 19:08",None,"asimov-c1nano-perf.html; add to run 4; hold section 6"),
 ("S3","2026-11-03 19:52",None,"asimov-c1nano-perf.html; table 4.6.1 top row"),
 ("S3","2026-11-03 19:54",None,"asimov-c1nano-perf-brief.html; bandwidth chart"),
 ("S3","2026-11-03 19:56",None,"run 4 plan; optional boots"),
 ("S3","2026-11-03 19:58",None,"run 4 plan; boot B mandatory"),
 ("S3","2026-11-04 09:07",None,"asimov-cme-perf.html; data path diagram"),
 ("S2","2026-11-04 09:46",None,"asimov-c1nano-perf-brief.html; Bill's comments"),
 ("S2","2026-11-04 10:01",None,"asimov-c1nano-perf-brief.html; Bill's comments; re-wording 'chase'; run 4"),
 ("S2","2026-11-04 10:13",None,"asimov-c1nano-perf-brief.html; Bill's comments; test script update; re-run"),
 ("S2","2026-11-04 10:27",None,"run 5; test script changes; re-run"),
 ("S2","2026-11-04 11:50",None,"asimov-c1nano-perf-brief.html; re-wording 'chase'"),
 ("S2","2026-11-04 14:01",None,"run 4; A repeat question"),
 ("S2","2026-11-04 14:03",None,"asimov-c1nano-perf-brief.html; re-wording 'chase'; apply"),
 ("S2","2026-11-04 14:14",None,"run 5b; test script update; re-run"),
 ("S2","2026-11-04 14:17",None,"follow-up-run-plan.md; review loop"),
 ("S2","2026-11-04 14:19",None,"asimov-c1nano-perf.html; open items; Bill's comments; latest results"),
 ("S2","2026-11-04 14:23",None,"run 4 status"),
 ("S2","2026-11-04 14:26",None,"asimov-c1nano-perf.html; open items; follow-up"),
 ("S2","2026-11-04 14:27",None,"pages update from boot A"),
 ("S2","2026-11-04 14:45",None,"asimov-cme-perf.html; asimov-cme-perf-brief.html; update from latest data"),
]
items = []
for s, ts, pre, tags in SEL:
    cands = msgs[s].get(ts + " PST")
    if not cands: sys.exit(f"missing {s} {ts}")
    if pre: cands = [c for c in cands if c.startswith(pre)]
    if len(cands) != 1: sys.exit(f"ambiguous {s} {ts}: {len(cands)}")
    t = cands[0]
    t = re.sub(r'<pasted_content id="[^"]*">\s*', "", t); t = re.sub(r'\s*</pasted_content id="[^"]*">', "", t)
    t = t.replace("<bash-input>", "").replace("</bash-input>", "")
    items.append((ts, s, tags, t))
items.sort(key=lambda x: x[0])
sess = {"S1": "session 1 (CRB, cache-perf folder, Oct 30 to Nov 2)",
        "S1b": "session 1b (crb folder, Nov 2)",
        "S2": "session 2 (asimov folder, asimov-04, Nov 1 to Nov 4)",
        "S3": "session 3 (asimov folder, peer asimov-be / asimov-05, Nov 2 to Nov 4)"}
# index by page
pages = ["crb-cache-perf-measurement-plan.html / CRB plan","ocm-interpretation.html","crb-memory-hierarchy.html","crb-memory-hierarchy-brief.html","perf-measurement-tech.html","asimov-memory-hierarchy.html","asimov-c1nano-perf.html","asimov-c1nano-perf-brief.html","asimov-cme-perf.html","asimov-cme-perf-brief.html","message to Jesse","re-run and test-script requests"]
def page_keys(tags):
    ks=[]
    for p in pages:
        key = p.split(" /")[0]
        if key in tags: ks.append(p)
    if "CRB plan" in tags and pages[0] not in ks: ks.append(pages[0])
    if re.search(r"re-run|re-test|run [2345]|test script|CME test|Asimov test code|follow-up run|boot|A repeat", tags): ks.append(pages[-1])
    return ks
idx = {p: [] for p in pages}
for n,(ts,s,tags,t) in enumerate(items,1):
    for p in page_keys(tags): idx[p].append(n)
out = []
out.append("# Jibin's comments on the perf-modeling reports and tests\n")
out.append("Collected 2026-11-04 from the Claude Code transcripts of four sessions and from Bill's Slack direct messages. Every entry is the message as typed, in time order, Pacific time. Operational messages (Slack relays, push, status checks, pasted run logs, review-loop bookkeeping) are left out.\n")
out.append("## Short version\n")
out.append(f"{len(items)} inputs from Oct 30 to Nov 4, 2026: comments on the report pages, requests to re-word them, and requests to change the test scripts and re-run the tests. The index below maps each page to its entry numbers. The entries follow, one per message, then Bill's Slack requests and comments that need an answer.\n")
out.append("## Words used here\n")
out.append("- CRB: the Arm Linux server at 192.168.2.45 (phoenix CRB), measured in session 1.")
out.append("- Asimov: the emulated chip (five DSUs of two C1-Nano cores, CMN S3 mesh, OCM); Jesse runs our scripts on the emulator.")
out.append("- CME: the matrix engine next to each C1-Nano pair, measured from session 3 on.")
out.append("- codex: the second reviewer agent that writes to the codex-review-*.md files.")
out.append("- Bill: William Baumann, who asked for the measurements and commented on the brief.")
out.append("- Sessions:")
for k in ["S1","S1b","S2","S3"]: out.append(f"  - {k}: {sess[k]}")
out.append("")
out.append("## Index by page\n")
out.append("| Page or topic | Entries |\n|---|---|")
for p in pages:
    out.append(f"| {p} | {', '.join(map(str, idx[p])) or '-'} |")
out.append("")
out.append("## Jibin's inputs\n")
for n,(ts,s,tags,t) in enumerate(items,1):
    out.append(f"### {n}. {ts} ({s}) - {tags}\n")
    out.append("\n".join("> " + l if l.strip() else ">" for l in t.splitlines()))
    out.append("")

BILL = [
 ("2026-10-30 09:53 PDT", "request; CRB and Asimov", "How are you doing?  We've got a question regarding CRB performance. I'd like to know latency and bandwidth for each of the cache infrastructures, including DRAM: maximum throughput and best-case latencies for each, and then do the same for Asimov.  This would be a timely thing in the next couple of days, today or Monday. Any chance you have time for that?\nTalk to Jacob or Jesse about doing that Asimov run."),
 ("2026-11-02 14:22 PST", "request; CME", "Is it possible to get similar statistics from the CME as well as the C1 Nano? We're seeing great performance prefetching with CME.\n[Jibin: So the CME test will be performing some matrix calculations, and compare them with vector/cpu calculations?]\nCorrect.  Testing it may not as straightforward.\nNo.  Just loading registers and writing them back.\nJacob has been doing the prefetch measurements.  He may have tips."),
 ("2026-11-04 09:17 PST", "Bill 1; asimov-c1nano-perf-brief.html; DRAM timing", "A few key questions. When it says emulator memory, not DDR, do we have the same timing physics as real DRAM?  I started thinking this might be a question mark, but then I see the DRAM latency at 52 ns. That's much too low for random access."),
 ("2026-11-04 09:19 PST", "Bill 2; asimov-c1nano-perf-brief.html; wording", "There's some of AI extraneous verbiage and terminology.  \"chase\"?"),
 ("2026-11-04 09:19 PST", "Bill 4; asimov-c1nano-perf-brief.html; L3", "L3 is confusing.  42% L2 hit rate?"),
 ("2026-11-04 09:21 PST", "Bill 5; asimov-c1nano-perf-brief.html; compare with CRB", "L1,2,3,SLC,DRAM compared vs the CRB.  I remember the CRB's L1 is also 4 cycles.  Don't spend too much time on DRAM. That's going to look very different between the two platforms."),
 ("2026-11-04 09:26 PST", "Bill 6; asimov-c1nano-perf-brief.html; DRAM read bandwidth", "The read throughput from DRAM is too slow.  I doubt that's reality. It's probably a software mechanism issue. Write speeds are great, though.   155 GB/s is around max theoretical."),
 ("2026-11-04 09:28 PST", "Bill 7; asimov-c1nano-perf-brief.html; L1 read bandwidth", "The 1 core read from L1 is only 58GB/s.  That's WAY too slow."),
]
out.append("## Bill's requests and comments (Slack DM, to be answered)\n")
out.append("Bill's comments of 2026-11-04 keep the numbers 1 to 7 used in the chat replies. Number 3 (\"This shows that the time to get to OCM is, in fact, much smaller than DRAM, so this is very interesting. The chart is great.\") is left out because it needs no answer.\n")
for ts, tags, t in BILL:
    out.append(f"### Bill, {ts} - {tags}\n")
    out.append("\n".join("> " + l if l.strip() else ">" for l in t.splitlines()))
    out.append("")

open("/home/jhan/workspace/titan/cache-perf/asimov/jibin-comments-perf-modeling.md","w").write("\n".join(out)+"\n")
print(len(items), "entries written")
