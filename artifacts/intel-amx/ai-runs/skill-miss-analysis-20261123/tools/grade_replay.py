#!/usr/bin/env python3
"""Grade replay runs: does a run report the CI-lane gap of t_amx_dispatch_dtype,
how severe does it rate it, and which remedy does it propose.

Input: a workflow journal.jsonl (one {"type":"result",...} line per agent).
Output: one row per run, and the text of each gap finding for a manual read.
"""
import json, re, sys

journal = sys.argv[1]
show = "--show" in sys.argv

labels = {}
results = {}
for line in open(journal):
    d = json.loads(line)
    if d.get("type") == "started":
        labels[d["agentId"]] = d["label"]
    elif d.get("type") == "result":
        results[d["agentId"]] = d.get("result")

# A finding is about the gap when it names the dispatch test or its guard AND
# says that a CI lane does not build or run it.
SUBJECT = re.compile(r"t_amx_dispatch_dtype|TRON_AMX_DISPATCH|placeholder|SUCCEED", re.I)
LANE = re.compile(r"required (CI )?(lane|suite|check)|gcp-nix|\bNix\b|pull[- ]request (lane|run|workflow)|PR lane|no (CI )?lane|never run|does not (run|execute)|not (run|execute|compiled)|compiled out|compile[sd]? out|option[- ]OFF|option OFF|option is OFF|flag is off", re.I)
# Remedies.
# The keyword DEFINES is matched in upper case only: "defines its own fakes" is not the remedy.
DEFINE = re.compile(r"\bDEFINES\b|(?i:target_compile_definitions|per-target define|per-test define|own (compile )?definition|passes? (the|its own) defin\w+|defin\w* (it|the macro) itself|t_page_share_counters|compile definition (for|on|to) (the|this|that|one))")
NIXFLAG = re.compile(r"cmake-tron-test-build\.nix|-DTRON_AMX_DISPATCH=ON|turn\w* (the option|it|TRON_AMX_DISPATCH) ON|option ON in (the )?(Nix|gcp-nix|required)|set the option in|enable the option in", re.I)
MOVE = re.compile(r"(move|hoist|lift)\w* .{0,80}(above|out of|outside) .{0,40}(#ifdef|guard|gate)", re.I | re.S)
APPROVAL = re.compile(r"approv|exception", re.I)
DROP_PLACEHOLDER = re.compile(r"(remove|delete|drop)\w* .{0,60}(placeholder|#else|SUCCEED)", re.I | re.S)

def text_of(f):
    return " \n".join(str(f.get(k, "")) for k in ("check", "title", "claim", "evidence", "proposed_change"))

rows = []
for aid, res in results.items():
    label = labels.get(aid, aid)
    if not isinstance(res, dict):
        rows.append((label, "NO RESULT", 0, [], {}))
        continue
    fs = res.get("findings", [])
    gap = []
    for i, f in enumerate(fs):
        t = text_of(f)
        about_dispatch_test = re.search(r"t_amx_dispatch_dtype|dispatch (test|section)", t, re.I)
        if SUBJECT.search(t) and LANE.search(t) and about_dispatch_test:
            gap.append((i, f))
    flags = {"define": False, "nixflag": False, "move": False, "approval": False, "drop_placeholder": False}
    for i, f in gap:
        pc = str(f.get("proposed_change", "")) + " " + str(f.get("claim", ""))
        flags["define"] |= bool(DEFINE.search(pc))
        flags["nixflag"] |= bool(NIXFLAG.search(pc))
        flags["move"] |= bool(MOVE.search(pc))
        flags["approval"] |= bool(APPROVAL.search(pc))
        flags["drop_placeholder"] |= bool(DROP_PLACEHOLDER.search(pc))
    # The define remedy anywhere in the run, also outside the gap findings.
    anywhere = any(DEFINE.search(text_of(f)) for f in fs)
    rows.append((label, "ok", len(fs), gap, dict(flags, define_anywhere=anywhere,
                 outside=res.get("outside_sources_used", []), skipped=len(res.get("checks_skipped", [])))))

rows.sort(key=lambda r: r[0])
print(f"{'run':36} {'findings':>8} {'gap findings':>12} {'severities':24} define nixflag move approval drop_ph define_anywhere outside")
for label, st, n, gap, fl in rows:
    if st != "ok":
        print(f"{label:36} {st}")
        continue
    sev = ",".join(f.get("severity", "?") for _, f in gap) or "-"
    print(f"{label:36} {n:8d} {len(gap):12d} {sev:24} {str(fl['define']):6} {str(fl['nixflag']):7} {str(fl['move']):5} {str(fl['approval']):8} {str(fl['drop_placeholder']):7} {str(fl['define_anywhere']):15} {len(fl['outside'])}")

if show:
    for label, st, n, gap, fl in rows:
        if st != "ok":
            continue
        print("\n" + "=" * 100 + f"\n{label}: {n} findings, {len(gap)} about the gap")
        for i, f in gap:
            print(f"\n--- finding #{i+1} [{f.get('severity')}] {f.get('skill')} / {f.get('check')}\nTITLE: {f.get('title')}\nFILE: {f.get('file')}:{f.get('line')}\nCLAIM: {f.get('claim')}\nPROPOSED: {f.get('proposed_change')}")
