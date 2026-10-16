# Fetch every review Wade (GitHub Wado-posi) left on PRs he did not author.
# Output: corpus.json (one entry per PR) + summary printed to stdout.
import json, subprocess, sys, collections
LOGIN = "Wado-posi"
def gh(path):
    out = subprocess.run(["gh","api","--paginate",path], capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write(f"FAIL {path}: {out.stderr[:200]}\n"); return []
    # --paginate concatenates JSON arrays; split them
    txt = out.stdout.strip()
    res = []
    dec = json.JSONDecoder(); i = 0
    while i < len(txt):
        while i < len(txt) and txt[i] in " \n\r\t": i += 1
        if i >= len(txt): break
        obj, j = dec.raw_decode(txt, i); i = j
        res.extend(obj if isinstance(obj, list) else [obj])
    return res
prs = json.load(open("prs-reviewed.json"))
prs = [p for p in prs if p["author"]["login"] != LOGIN]
print("non-own PRs", len(prs))
corpus = []
for k, p in enumerate(sorted(prs, key=lambda p: (p["repository"]["name"], p["number"]))):
    repo = p["repository"]["nameWithOwner"]; n = p["number"]
    base = f"repos/{repo}"
    pr = gh(f"{base}/pulls/{n}")
    pr = pr[0] if pr else {}
    reviews = [r for r in gh(f"{base}/pulls/{n}/reviews") if r.get("user",{}).get("login")==LOGIN]
    allinline = gh(f"{base}/pulls/{n}/comments")
    byid = {c["id"]: c for c in allinline}
    inline = []
    for c in allinline:
        if c.get("user",{}).get("login") != LOGIN: continue
        parent = byid.get(c.get("in_reply_to_id"))
        # replies to Wade's comment (thread context)
        replies = [{"id":r["id"],"user":r["user"]["login"],"created":r["created_at"],"body":r["body"]}
                   for r in allinline if r.get("in_reply_to_id")==c["id"]]
        inline.append({"id":c["id"],"created":c["created_at"],"path":c.get("path"),"line":c.get("line") or c.get("original_line"),
                       "side":c.get("side"),"commit":c.get("commit_id"),"review_id":c.get("pull_request_review_id"),
                       "in_reply_to":c.get("in_reply_to_id"),
                       "parent":{"user":parent["user"]["login"],"body":parent["body"]} if parent else None,
                       "diff_hunk":c.get("diff_hunk"),"body":c["body"],"replies":replies})
    issue = [{"id":c["id"],"created":c["created_at"],"body":c["body"]} for c in gh(f"{base}/issues/{n}/comments")
             if c.get("user",{}).get("login")==LOGIN]
    commits = gh(f"{base}/pulls/{n}/commits")
    files = gh(f"{base}/pulls/{n}/files")
    corpus.append({"repo":repo,"number":n,"title":p["title"],"author":p["author"]["login"],"url":p["url"],
                   "created":p["createdAt"],"state":pr.get("state"),"merged_at":pr.get("merged_at"),
                   "head":pr.get("head",{}).get("sha"),"base_ref":pr.get("base",{}).get("ref"),
                   "body":pr.get("body") or "","n_commits":len(commits),
                   "commit_subjects":[c["commit"]["message"].split("\n")[0] for c in commits],
                   "files":[{"path":f["filename"],"add":f["additions"],"del":f["deletions"]} for f in files],
                   "reviews":[{"id":r["id"],"state":r["state"],"submitted":r.get("submitted_at"),"commit":r.get("commit_id"),"body":r.get("body") or ""} for r in reviews],
                   "inline":inline,"issue_comments":issue})
    print(k, repo, n, len(reviews), len(inline), len(issue), flush=True)
json.dump(corpus, open("corpus.json","w"), indent=1)
c = collections.Counter()
for e in corpus:
    c["prs"] += 1; c["reviews"] += len(e["reviews"]); c["inline"] += len(e["inline"]); c["issue"] += len(e["issue_comments"])
    for r in e["reviews"]: c["state:"+r["state"]] += 1
print(dict(c))
