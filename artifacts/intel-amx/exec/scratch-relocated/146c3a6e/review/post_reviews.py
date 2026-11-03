#!/usr/bin/env python3
"""Post one GitHub review per reviewer on PR 5015 from reviews.json.

reviews.json: [{"reviewer": str, "review_body": str, "comments": [{"path","line","body"}]}]
Usage: post_reviews.py reviews.json [--dry-run]
"""
import json, subprocess, sys
REPO = "positron-ai/tron"; PR = 5015
HEAD = "5061623a346ba5e8d22a6de8b3ab4cc058023214"
reviews = json.load(open(sys.argv[1]))
dry = "--dry-run" in sys.argv
for r in reviews:
    payload = {"commit_id": HEAD, "event": "COMMENT", "body": r["review_body"],
               "comments": [{"path": c["path"], "line": int(c["line"]), "side": "RIGHT", "body": c["body"]} for c in r["comments"]]}
    print(f"== {r['reviewer']}: {len(payload['comments'])} inline comments, body {len(r['review_body'])} chars")
    if dry:
        continue
    p = subprocess.run(["gh", "api", f"repos/{REPO}/pulls/{PR}/reviews", "--input", "-"],
                       input=json.dumps(payload), text=True, capture_output=True)
    if p.returncode != 0:
        print("FAILED", p.stderr[:2000]); print(p.stdout[:2000])
        sys.exit(1)
    out = json.loads(p.stdout)
    print("posted review id", out.get("id"), out.get("html_url"))
