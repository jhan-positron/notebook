#!/usr/bin/env python3
"""Score replay runs from workflow journals.

One journal holds one {"type":"result"} line per agent. A run is one agent that
applied one skill (or all five) to one change and returned a list of findings.

Scores per run:
- gap:     a finding says that the dispatch test (or, for the control, the new
           allocator case) does not run in a CI lane.
- sev:     the highest severity among those findings.
- define:  a proposed change names a compile definition for the one test target
           (keyword DEFINES in upper case, target_compile_definitions,
           "per-target define", or the sibling t_page_share_counters).
- lane:    a proposed change turns the option on for the whole lane.
- wrong:   a proposed change gives DEFINES to a target that cannot take it
           (t_amx_numerics, or HBM_ALLOC_SHADOW in the control). The pattern
           only selects sentences; each selected sentence was read by hand.
"""
import json, re, sys

SEV_ORDER = ["info", "nit", "question", "should-fix", "blocker"]

LANE = re.compile(
    r"required (CI )?(lane|suite|check)|gcp-nix|\bNix\b|GCP Nix|pull[- ]request (lane|run|workflow|pipeline)|PR lane|"
    r"no (CI )?lane|never run|does not (run|execute)|not (run|executed|compiled)|compiled out|compile[sd]? out|"
    r"option[- ]OFF|option is OFF|with (the option|it) off|flag is off|default (PR )?pipeline", re.I)
SUBJECT = {
    "dispatch": re.compile(r"t_amx_dispatch_dtype|dispatch (test|section|case)", re.I),
    "control": re.compile(r"HBM_ALLOC_SHADOW|t_hwalloc", re.I),
}
DEFINE = re.compile(
    r"\bDEFINES\b|(?i:target_compile_definitions|per-target define|per-test define|own (compile )?definition|"
    r"passes? (the|its own) defin\w+|t_page_share_counters)")
LANEFLAG = re.compile(
    r"cmake-tron-test-build\.nix|-DTRON_AMX_DISPATCH=ON|-DHBM_ALLOC_SHADOW=ON|"
    r"(?i:(turn|set|enable|build)\w* (the option|it|TRON_AMX_DISPATCH)( ON)? in (the )?(required|Nix|GCP Nix|gcp-nix))")
NEG = re.compile(r"(?i)\b(do not|don't|not allowed|cannot|can not|must not|no per-target|is not safe|unsafe|would not link|not propose|never)\b")


def text_of(f, keys=("check", "title", "claim", "evidence", "proposed_change")):
    return " \n".join(str(f.get(k, "")) for k in keys)


def sentences(s):
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", s) if x.strip()]


def load(journal):
    labels, results = {}, {}
    for line in open(journal):
        d = json.loads(line)
        if d.get("type") == "started":
            labels[d["agentId"]] = d["label"]
        elif d.get("type") == "result":
            results[d["agentId"]] = d.get("result")
    return [(labels[a], results[a]) for a in results]


def score(label, res, subject="dispatch"):
    fs = res.get("findings", []) if isinstance(res, dict) else []
    subj = SUBJECT[subject]
    gap = [f for f in fs if subj.search(text_of(f)) and LANE.search(text_of(f, ("title", "claim", "proposed_change")))
           and re.search(r"(?i)lane|CI|pipeline|workflow|required|compiled out|option", str(f.get("title", "")) + str(f.get("claim", ""))[:600])]
    sev = max((f.get("severity", "info") for f in gap), key=SEV_ORDER.index, default=None)
    define_sents, lane_sents, wrong_sents = [], [], []
    for f in fs:
        for s in sentences(str(f.get("proposed_change", ""))):
            if DEFINE.search(s):
                define_sents.append(s)
                wrong_target = re.search(r"t_amx_numerics|HBM_ALLOC_SHADOW|t_hwalloc", s) and not re.search(r"t_amx_dispatch_dtype", s)
                if wrong_target and not NEG.search(s):
                    wrong_sents.append(s)
            if LANEFLAG.search(s):
                lane_sents.append(s)
    # In the dispatch case, a define sentence counts only when it is a positive proposal.
    positive = [s for s in define_sents if not NEG.search(s) or re.search(r"t_amx_dispatch_dtype", s)]
    if subject == "control":
        positive = [s for s in define_sents if not NEG.search(s)]
    return {
        "label": label, "n": len(fs), "gap": bool(gap), "gap_n": len(gap), "sev": sev,
        "define": bool(positive), "define_sents": positive, "lane": bool(lane_sents),
        "wrong": bool(wrong_sents), "wrong_sents": wrong_sents,
        "outside": res.get("outside_sources_used", []) if isinstance(res, dict) else [],
    }


def summarize(rows, key):
    """Group rows by key(label) and count."""
    out = {}
    for r in rows:
        k = key(r["label"])
        g = out.setdefault(k, {"runs": 0, "gap": 0, "define": 0, "lane": 0, "wrong": 0, "sev": []})
        g["runs"] += 1
        g["gap"] += r["gap"]
        g["define"] += r["define"]
        g["lane"] += r["lane"]
        g["wrong"] += r["wrong"]
        if r["sev"]:
            g["sev"].append(r["sev"])
    return out


if __name__ == "__main__":
    journal = sys.argv[1]
    subject_for = (lambda lab: "control" if lab.startswith("control") else "dispatch")
    rows = [score(lab, res, subject_for(lab)) for lab, res in load(journal)]
    rows.sort(key=lambda r: r["label"])
    print(f"{'run':44} {'findings':>8} {'gap':>4} {'severity':>10} {'define':>7} {'lane flag':>9} {'wrong target':>12}")
    for r in rows:
        print(f"{r['label']:44} {r['n']:8d} {str(r['gap']):>4} {str(r['sev']):>10} {str(r['define']):>7} {str(r['lane']):>9} {str(r['wrong']):>12}")
    if "--show" in sys.argv:
        for r in rows:
            for s in r["wrong_sents"]:
                print(f"\nWRONG? {r['label']}: {s[:400]}")
            if r["label"].startswith("control"):
                for s in r["define_sents"]:
                    print(f"\nCONTROL define sentence {r['label']}: {s[:400]}")
