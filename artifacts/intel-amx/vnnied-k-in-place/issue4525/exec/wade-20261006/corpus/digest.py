# Write pr/<repo>-<n>.md digests from corpus.json (all PRs with any Wade text).
import json
C = json.load(open("corpus.json"))
n_text = 0
for e in C:
    n = len(e["inline"]) + len(e["issue_comments"]) + sum(1 for r in e["reviews"] if r["body"].strip())
    if n == 0: continue
    n_text += 1
    repo = e["repo"].split("/")[1]; fn = f"pr/{repo}-{e['number']}.md"; L = []
    L.append(f"# {e['repo']} PR #{e['number']}: {e['title']}")
    L.append(f"author: {e['author']}  created: {e['created'][:10]}  state: {e['state']}  merged: {str(e['merged_at'])[:10]}  head: {e['head']}  base: {e['base_ref']}  url: {e['url']}")
    L.append(f"commits: {e['n_commits']}")
    for s in e["commit_subjects"][:40]: L.append(f"  - {s}")
    if e['n_commits'] > 40: L.append(f"  ... {e['n_commits']-40} more")
    L.append(f"files ({len(e['files'])}):")
    for f in e["files"][:60]: L.append(f"  - {f['path']} (+{f['add']} -{f['del']})")
    if len(e["files"]) > 60: L.append(f"  ... {len(e['files'])-60} more")
    L.append("\n## PR body (as it is now; may have been edited after the review)\n")
    L.append(e["body"][:4000] + ("\n[... body truncated]" if len(e["body"]) > 4000 else ""))
    L.append("\n## Wade's reviews (summary verdicts)\n")
    for r in e["reviews"]:
        L.append(f"- review {r['id']} {r['state']} at {r['submitted'][:16]} commit {r['commit']}: " + (r["body"].strip() or "(no text)"))
    if not e["reviews"]: L.append("(no submitted review; conversation comments only)")
    if e["issue_comments"]:
        L.append("\n## Wade's conversation comments\n")
        for c in e["issue_comments"]:
            L.append(f"### issue-comment {c['id']} at {c['created'][:16]}\n{c['body']}\n")
    L.append("\n## Wade's inline comments\n")
    for c in e["inline"]:
        L.append(f"### inline {c['id']} at {c['created'][:16]}  {c['path']}:{c['line']} (commit {str(c['commit'])[:10]})" + ("  [reply to " + c['parent']['user'] + "]" if c['parent'] else ""))
        if c["diff_hunk"]:
            hunk = c["diff_hunk"].split("\n")
            if len(hunk) > 30: hunk = ["[... hunk truncated]"] + hunk[-30:]
            L.append("```diff\n" + "\n".join(hunk) + "\n```")
        if c["parent"]: L.append(f"> parent comment by {c['parent']['user']}: " + c["parent"]["body"][:600].replace("\n", "\n> "))
        L.append("WADE: " + c["body"])
        for r in c["replies"]: L.append(f"  reply by {r['user']} ({r['created'][:10]}): " + r["body"][:500].replace("\n", " "))
        L.append("")
    open(fn, "w").write("\n".join(L))
print("digests", n_text, "PRs", len(C))
