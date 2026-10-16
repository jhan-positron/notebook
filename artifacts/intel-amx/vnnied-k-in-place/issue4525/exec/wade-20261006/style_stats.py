# Counts about Wade's wording and verdict habits, computed from corpus/corpus.json (non-own PRs only).
import json, re, collections, statistics, datetime
C = json.load(open("corpus/corpus.json"))
out = {}
texts = []
for e in C:
    for c in e["inline"]: texts.append({"kind":"inline","body":c["body"],"reply":c["in_reply_to"] is not None,"pr":e["number"],"id":c["id"]})
    for r in e["reviews"]:
        if r["body"].strip(): texts.append({"kind":"review","body":r["body"],"reply":False,"pr":e["number"],"id":r["id"]})
    for c in e["issue_comments"]: texts.append({"kind":"issue","body":c["body"],"reply":False,"pr":e["number"],"id":c["id"]})
top = [t for t in texts if not t["reply"]]
out["prs"] = len(C); out["texts"] = len(texts); out["top_level_texts"] = len(top)
out["reviews"] = sum(len(e["reviews"]) for e in C)
out["review_states"] = dict(collections.Counter(r["state"] for e in C for r in e["reviews"]))
L = sorted(len(t["body"]) for t in top); out["chars_median"] = L[len(L)//2]; out["chars_p90"] = L[int(.9*len(L))]
S = sorted(len(re.findall(r'[.?!](\s|$)', t["body"])) for t in top); out["sentences_median"] = S[len(S)//2]
out["ends_with_question"] = sum(1 for t in top if t["body"].strip().rstrip('`').rstrip().endswith('?'))
out["contains_question"] = sum(1 for t in top if '?' in t["body"])
out["suggestion_blocks"] = sum(1 for t in top if '```suggestion' in t["body"])
pats = {"nit": r"\bnit\b", "trivial": r"\btrivial\b", "minor": r"\bminor\b", "non-blocking": r"non-blocking|not blocking", "follow-up": r"follow[- ]?up",
        "should": r"\bshould\b", "would": r"\bwould\b", "could": r"\bcould\b", "maybe": r"\bmaybe\b", "seems": r"\bseems?\b", "I think": r"\bI think\b", "IMO": r"\bIMO\b",
        "please": r"\bplease\b", "unit test / UT": r"unit[- ]?tests?|\bUTs?\b", "perf": r"\bperf", "humor marker (lol ;p :))": r"\blol\b|;-?p\b|:-?\)", "squash": r"\bsquash", "LGTM": r"\bLGTM\b",
        "Claude mentioned": r"\bclaude\b|\bCC\b"}
out["phrase_counts_top_level"] = {k: sum(1 for t in top if re.search(p, t["body"], re.I)) for k, p in pats.items()}
rows = []
for e in C:
    n = len([c for c in e["inline"] if not c["in_reply_to"]]) + len(e["issue_comments"]) + sum(1 for r in e["reviews"] if r["body"].strip() and r["state"] != "APPROVED")
    final = e["reviews"][-1]["state"] if e["reviews"] else "none"
    rows.append((n, final))
byn = collections.defaultdict(collections.Counter)
for n, f in rows:
    b = "0" if n == 0 else "1-2" if n <= 2 else "3-5" if n <= 5 else "6+"
    byn[b][f] += 1
out["final_verdict_by_top_level_comment_count"] = {k: dict(v) for k, v in byn.items()}
out["approved_reviews_carrying_inline_comments"] = sum(1 for e in C for r in e["reviews"] if r["state"] == "APPROVED" and any(c["review_id"] == r["id"] for c in e["inline"]))
out["reviews_per_pr"] = dict(sorted(collections.Counter(len(e["reviews"]) for e in C).items()))
d = []
for e in C:
    if e["reviews"]:
        t0 = datetime.datetime.fromisoformat(e["created"].replace("Z", "+00:00")); t1 = datetime.datetime.fromisoformat(e["reviews"][0]["submitted"].replace("Z", "+00:00")); d.append((t1 - t0).total_seconds() / 86400)
out["days_to_first_review_median"] = round(statistics.median(d), 1)
out["last_review_at_current_head"] = sum(1 for e in C if e["reviews"] and e["reviews"][-1]["commit"] == e["head"])
def area(p):
    if not p: return "none"
    for a in ("t/", "h/", "src/", ".github", "docs", "doc/"):
        if p.startswith(a): return a
    return "other"
out["inline_by_area"] = dict(collections.Counter(area(c["path"]) for e in C for c in e["inline"]).most_common())
out["inline_by_month"] = dict(sorted(collections.Counter(c["created"][:7] for e in C for c in e["inline"]).items()))
out["silent_prs"] = sum(1 for e in C if not (e["inline"] or e["issue_comments"] or any(r["body"].strip() for r in e["reviews"])))
out["silent_by_author"] = dict(collections.Counter(e["author"] for e in C if not (e["inline"] or e["issue_comments"] or any(r["body"].strip() for r in e["reviews"]))))
out["commented_by_author"] = dict(collections.Counter(e["author"] for e in C if (e["inline"] or e["issue_comments"] or any(r["body"].strip() for r in e["reviews"]))))
out["pr_authors_total"] = dict(collections.Counter(e["author"] for e in C))
json.dump(out, open("style-stats.json", "w"), indent=1)
print(json.dumps(out, indent=1))
