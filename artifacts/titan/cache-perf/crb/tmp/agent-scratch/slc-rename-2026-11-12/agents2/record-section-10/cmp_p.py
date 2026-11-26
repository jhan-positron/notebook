#!/usr/bin/env python3
import re, json, difflib
S="/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
rec=open("/home/jhan/tmp/update-crb-memory-hierarchy.md",encoding="utf-8").read().split("\n")
d=json.load(open(S+"/check1_results.json"))
D=dict((n,v) for n,v in d)
ver={v["id"]:v for v in D["verify:replacement-statements"]["verdicts"]}
ext={v["id"]:v for v in D["verify:replacement-statements"]["extra_findings"]}
def quoted(s):
    # the longest "..." block
    m=re.findall(r'"((?:[^"]|"(?=[A-Za-z]))+?)"(?=\s|$|\.)',s)
    return max(m,key=len) if m else None
def grab(fix, start):
    i=fix.index(start); return fix[i:]
P1=[l for l in rec if l.startswith("> With a buffer of 1 GiB for each core")][0][2:]
P2=[l for l in rec if l.startswith("> For software.")][0][2:]
P3=[l for l in rec if l.startswith("> What limits one writer at 8 MiB")][0][2:]
def sents(t): return [x.strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"])",t) if x.strip()]
def compare(name, final, fix, start):
    src=grab(fix,start)
    # cut the source at the closing quote that ends the proposed text: find longest common prefix-based end
    fs=sents(final)
    missing=[s for s in fs if s not in src]
    # source sentences (up to the end of the quoted text): take the part up to '" Line' or '" Sources' or end quote
    m=re.search(r'"\s+(Line|Sources|These|Apply|Then)',src)
    body=src[:m.start()] if m else src
    ss=sents(body)
    extra=[s for s in ss if s not in final]
    print(f"== {name}: final {len(fs)} sentences, source {len(ss)} sentences; final-not-in-source {len(missing)}; source-not-in-final {len(extra)}")
    for s in missing: print("   FINAL ONLY:",s)
    for s in extra: print("   SOURCE ONLY:",s)
    print("   identical text:", final.strip()==body.strip())
    if final.strip()!=body.strip():
        sm=difflib.SequenceMatcher(None,body.strip(),final.strip(),autojunk=False)
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag!="equal": print("   DIFF",tag,repr(body.strip()[max(0,i1-40):i2+40]),"=>",repr(final.strip()[max(0,j1-40):j2+40]))
compare("P1 vs RS4 skeptic fix", P1, ver["RS4"]["fix"], "With a buffer of 1 GiB for each core")
compare("P2 vs RS2 skeptic fix", P2, ver["RS2"]["fix"], "For software. The rates below")
compare("P3 vs RS1 skeptic fix", P3, ver["RS1"]["fix"], "What limits one writer at 8 MiB was not measured")
print()
print("RS4 fix tail:", ver["RS4"]["fix"][-330:])
print()
print("RS2 fix tail:", ver["RS2"]["fix"][-420:])
print()
print("RS1 fix tail:", ver["RS1"]["fix"][-700:])
