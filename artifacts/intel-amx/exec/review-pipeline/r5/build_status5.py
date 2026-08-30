#!/usr/bin/env python3
"""Build r5/status.json for gen_review5.py from the round-5 verification workflow.

Sources: the workflow journal (journal.jsonl: one 'result' line per agent, keyed by agentId) and each
agent's transcript (agent-<id>.jsonl, line 0 = the prompt), which tells us what kind of agent it was:
  status verifier   -> prompt contains 're-anchor and re-judge' and 'group "<key>"'; result has "items"
  status refuter    -> prompt contains 'adversarially check these status verdicts'; result has "results"
  finder            -> prompt contains 'Lens:'; result has "candidates"
  candidate refuter -> prompt contains 'adversarially verify ONE candidate'; result has "refuted";
                       the candidate JSON follows 'Candidate:\n' in the prompt (paired by title+file+line)

Output: r5/status.json (id -> status dict; items in unchanged files carry their round-4 line/status),
r5/workflow_out.json (everything, for authoring round5_data.py).
"""
import json, sys, os, re, glob

SP = os.path.dirname(os.path.abspath(__file__))
WF = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/72fd1ccd-f69f-4237-958c-0f9519541d9b/subagents/workflows/wf_b8f009bd-07b"

items = json.load(open(f"{SP}/round4_comments.json"))
changed = {c["id"] for c in json.load(open(f"{SP}/changed_items.json"))}

def load_result(r):
    if isinstance(r, str):
        try: return json.loads(r)
        except Exception: return r
    return r

def prompt_of(agent_id):
    p = f"{WF}/agent-{agent_id}.jsonl"
    if not os.path.exists(p): return ""
    first = json.loads(open(p).readline())
    m = first.get("message", {})
    c = m.get("content") if isinstance(m, dict) else None
    if isinstance(c, str): return c
    if isinstance(c, list): return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""

status_verdicts, status_refutes, finders, refuters = {}, {}, {}, []
for line in open(f"{WF}/journal.jsonl"):
    try: j = json.loads(line)
    except Exception: continue
    if j.get("type") != "result": continue
    r = load_result(j.get("result")); aid = j.get("agentId", "")
    prompt = prompt_of(aid)
    if isinstance(r, dict) and "items" in r and "group" in r:
        status_verdicts[r["group"]] = dict(r, agentId=aid)
    elif isinstance(r, dict) and "results" in r and "adversarially check these status verdicts" in prompt:
        g = re.search(r'\(group "([^"]+)"\)', prompt)
        status_refutes[g.group(1) if g else aid] = dict(r, agentId=aid)
    elif isinstance(r, dict) and "candidates" in r:
        finders[r.get("lens") or aid] = dict(r, agentId=aid)
    elif isinstance(r, dict) and "refuted" in r:
        m = re.search(r"Candidate:\n(\{.*\})\s*$", prompt, re.S)
        cand = None
        if m:
            try: cand = json.loads(m.group(1))
            except Exception: cand = None
        lens = re.search(r'lens "([^"]+)"', prompt)
        refuters.append(dict(lens=lens.group(1) if lens else "", candidate=cand, refute=r, agentId=aid))

# status.json: changed-file items take the verifier's verdict (with the refuter's corrections applied
# when the refuter disagreed); everything else carries round-4 state.
corr = {}
for g, rr in status_refutes.items():
    for x in rr.get("results", []): corr[x["id"]] = x

st = {}
verdict_by_id = {}
for g, v in status_verdicts.items():
    for it in v["items"]: verdict_by_id[it["id"]] = dict(it, group=g)

for c in items:
    cid = c["id"]
    v = verdict_by_id.get(cid)
    if cid in changed and v:
        x = corr.get(cid)
        status = v["status"]; line = v["new_line"]; s0, s1 = v["snippet_start"], v["snippet_end"]
        note_corr = ""
        if x and not x.get("agree", True):
            if x.get("corrected_status") in ("FIXED", "PARTIAL", "NOT_ADDRESSED", "OBSOLETE"): status = x["corrected_status"]
            if x.get("corrected_line", 0) > 0: line = x["corrected_line"]
            if x.get("corrected_snippet_start", 0) > 0 and x.get("corrected_snippet_end", 0) >= x.get("corrected_snippet_start", 0):
                s0, s1 = x["corrected_snippet_start"], x["corrected_snippet_end"]
            note_corr = " | refuter: " + x.get("reason", "")
        st[cid] = dict(status=status, new_line=line, snippet_start=s0, snippet_end=s1,
                       remaining=v.get("remaining", ""),
                       evidence="; ".join(f"{e['file']}:{e['line']}" for e in v.get("evidence", [])[:3]) + note_corr,
                       followup_voice=v.get("followup_voice", ""), fixed_voice=v.get("fixed_voice", ""),
                       deviation=v.get("deviation_from_suggestion", ""), still_blocker=v.get("still_blocker", c["blocker"]) and status not in ("FIXED", "OBSOLETE"),
                       refuter_agrees=(x.get("agree", True) if x else None), refuter_followup_ok=(x.get("followup_ok", True) if x else None),
                       refuter_followup_correction=(x.get("followup_correction", "") if x else ""))
    else:
        # unchanged file: carry round-4 status; the r4 note says "partial" or "not addressed"
        status = "PARTIAL" if ", partial" in c["r4_note"] else "NOT_ADDRESSED"
        st[cid] = dict(status=status, new_line=c["line"], snippet_start=c["snip"][0], snippet_end=c["snip"][1],
                       remaining="", evidence="file unchanged since d176c88b3", followup_voice="", fixed_voice="",
                       deviation="", still_blocker=c["blocker"], refuter_agrees=None)

json.dump(st, open(f"{SP}/status.json", "w"), indent=1)
json.dump(dict(status_verdicts=status_verdicts, status_refutes=status_refutes, finders=finders, refuters=refuters),
          open(f"{SP}/workflow_out.json", "w"), indent=1)

print(f"status entries: {len(st)} | verifier groups: {sorted(status_verdicts)} | status refuter groups: {sorted(status_refutes)} | finders: {sorted(finders)} | candidate refuters: {len(refuters)}")
from collections import Counter
print("status counts:", Counter(v["status"] for v in st.values()))
print("\n== changed-file verdicts ==")
for cid in [c["id"] for c in items if c["id"] in changed]:
    v = st[cid]; x = corr.get(cid)
    print(f"  {cid:6s} {v['status']:13s} @{v['new_line']:5d} [{v['snippet_start']}-{v['snippet_end']}] blocker={v['still_blocker']} refuter_agree={v.get('refuter_agrees')} | {v['remaining'][:150]}")
    if v.get("followup_voice"): print(f"         followup: {v['followup_voice'][:300]}")
    if v.get("deviation"): print(f"         deviation: {v['deviation'][:300]}")
    if x and not x.get("agree", True): print(f"         REFUTER: {x.get('reason','')[:300]}")
    if x and not x.get("followup_ok", True): print(f"         REFUTER followup: {x.get('followup_correction','')[:300]}")
extra = {g: v.get("extra_observations", "") for g, v in status_verdicts.items()}
print("\n== extra observations ==")
for g, e in extra.items(): print(f"  [{g}] {e[:600]}")
print("\n== R4_FIXED re-checks (items not in changed set but reported) ==")
for cid, v in verdict_by_id.items():
    if cid not in changed: print(f"  {cid}: {v['status']} @{v['new_line']} | {v.get('remaining','')[:120]} | ev: {[e['file']+':'+str(e['line']) for e in v.get('evidence',[])[:2]]}")
print("\n== finder candidates and refutations ==")
for lens, f in finders.items():
    print(f"\n[{lens}] {len(f['candidates'])} candidates, {len(f.get('checked_clean', []))} clean rows")
    for c in f["candidates"]:
        match = [r for r in refuters if r["candidate"] and r["candidate"].get("title") == c.get("title") and r["candidate"].get("file") == c.get("file")]
        rv = match[0]["refute"] if match else None
        print(f"  - {c['title']} @ {c['file']}:{c['line']} [{c['persona_item']}] conf={c['confidence']} folds_into={c['folds_into']!r}")
        print(f"      claim: {c['claim'][:400]}")
        print(f"      voice: {c['comment_voice'][:400]}")
        if rv: print(f"      REFUTER: {rv['verdict']} refuted={rv['refuted']} would_he_raise_it={rv['would_he_raise_it']} | {rv['reason'][:400]} | corrections: {rv['corrections'][:400]}")
        else: print("      REFUTER: (none matched)")
    for cc in f.get("checked_clean", []): print(f"  clean: {cc['area']} | {cc['what_was_verified'][:200]} | {cc['source'][:120]}")
