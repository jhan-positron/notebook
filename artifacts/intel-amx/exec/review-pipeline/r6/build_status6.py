#!/usr/bin/env python3
"""Build r6/status.json for gen_review6.py from the round-6 verification workflow (wf_c1bf5118-492).

Same pairing method as round 5 (build_status5.py): the journal gives each agent's result; the agent transcript's
first line gives its prompt, which tells us the kind of agent and (for refuters) the candidate it judged.
Round-6 additions: statuses DECLINED / DEFERRED (author triage ignore / defer) with predicted_reply, and
triage_check for done/partial/question items. Items in unchanged files carry their round-5 state, except ids the
workflow judged anyway (R1-58, in the cmake-full-arena group).
"""
import json, sys, os, re

SP = os.path.dirname(os.path.abspath(__file__))
WF = sys.argv[1] if len(sys.argv) > 1 else "/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/72fd1ccd-f69f-4237-958c-0f9519541d9b/subagents/workflows/wf_c1bf5118-492"

items = json.load(open(f"{SP}/round5_comments.json"))
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

corr = {}
for g, rr in status_refutes.items():
    for x in rr.get("results", []): corr[x["id"]] = x
verdict_by_id = {}
for g, v in status_verdicts.items():
    for it in v["items"]: verdict_by_id[it["id"]] = dict(it, group=g)

VALID = ("FIXED", "PARTIAL", "NOT_ADDRESSED", "OBSOLETE", "DECLINED", "DEFERRED")
st = {}
for c in items:
    cid = c["id"]
    v = verdict_by_id.get(cid)
    if v:
        x = corr.get(cid)
        status = v["status"]; line = v["new_line"]; s0, s1 = v["snippet_start"], v["snippet_end"]
        note_corr = ""
        if x and not x.get("agree", True):
            if x.get("corrected_status") in VALID: status = x["corrected_status"]
            if x.get("corrected_line", 0) > 0: line = x["corrected_line"]
            if x.get("corrected_snippet_start", 0) > 0 and x.get("corrected_snippet_end", 0) >= x.get("corrected_snippet_start", 0):
                s0, s1 = x["corrected_snippet_start"], x["corrected_snippet_end"]
            note_corr = " | refuter: " + x.get("reason", "")
        st[cid] = dict(status=status, new_line=line, snippet_start=s0, snippet_end=s1,
                       remaining=v.get("remaining", ""),
                       evidence="; ".join(f"{e['file']}:{e['line']}" for e in v.get("evidence", [])[:3]) + note_corr,
                       followup_voice=v.get("followup_voice", ""), fixed_voice=v.get("fixed_voice", ""),
                       predicted_reply=v.get("predicted_reply", ""), triage_check=v.get("triage_check", ""),
                       still_blocker=bool(v.get("still_blocker", c["blocker"])) and status not in ("FIXED", "OBSOLETE", "DECLINED", "DEFERRED"),
                       refuter_agrees=(x.get("agree", True) if x else None), refuter_followup_ok=(x.get("followup_ok", True) if x else None),
                       refuter_followup_correction=(x.get("followup_correction", "") if x else ""))
    else:
        status = "PARTIAL" if ", partial" in c["r5_note"] else "NOT_ADDRESSED"
        st[cid] = dict(status=status, new_line=c["line"], snippet_start=c["snip"][0], snippet_end=c["snip"][1],
                       remaining="", evidence="file unchanged since 234c02bde", followup_voice="", fixed_voice="",
                       predicted_reply="", triage_check="", still_blocker=c["blocker"], refuter_agrees=None)

json.dump(st, open(f"{SP}/status.json", "w"), indent=1)
json.dump(dict(status_verdicts=status_verdicts, status_refutes=status_refutes, finders=finders, refuters=refuters),
          open(f"{SP}/workflow_out.json", "w"), indent=1)

from collections import Counter
print(f"status entries: {len(st)} | verifier groups: {sorted(status_verdicts)} | refuter groups: {sorted(status_refutes)} | finders: {sorted(finders)} | candidate refuters: {len(refuters)}")
print("status counts:", Counter(v["status"] for v in st.values()))
print("\n== verdicts (changed files + R1-58) ==")
for c in items:
    cid = c["id"]
    if cid not in verdict_by_id: continue
    v = st[cid]; x = corr.get(cid)
    print(f"  {cid:6s} {v['status']:13s} @{v['new_line']:5d} [{v['snippet_start']}-{v['snippet_end']}] blocker={v['still_blocker']} refuter_agree={v.get('refuter_agrees')} | {v['remaining'][:140]}")
    if v.get("triage_check"): print(f"         triage_check: {v['triage_check'][:300]}")
    if v.get("followup_voice"): print(f"         followup: {v['followup_voice'][:300]}")
    if v.get("predicted_reply"): print(f"         predicted_reply: {v['predicted_reply'][:300]}")
    if v.get("fixed_voice"): print(f"         fixed_voice: {v['fixed_voice'][:120]}")
    if x and not x.get("agree", True): print(f"         REFUTER: {x.get('reason','')[:300]}")
    if x and not x.get("followup_ok", True): print(f"         REFUTER followup: {x.get('followup_correction','')[:300]}")
print("\n== extra observations ==")
for g, v in status_verdicts.items(): print(f"  [{g}] {v.get('extra_observations','')[:700]}\n")
print("== finder candidates and refutations ==")
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
