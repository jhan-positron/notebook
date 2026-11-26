#!/usr/bin/env python3
"""Watch tron PR 5022 for review activity.

One run takes a snapshot of the PR through the `gh` CLI: reviews, inline
comments, conversation comments, review threads, timeline events, PR state and
the checks of the head commit. It compares the snapshot with the one of the
previous run and prints one line per difference.

  watch_pr.py                compare, print, store the new snapshot, append to log.txt
  watch_pr.py --peek         compare and print, store nothing
  watch_pr.py --state FILE   use FILE as the stored snapshot (for tests)

Exit code 0: the snapshot was taken. Exit code 2: GitHub could not be read, or
the stored snapshot is unreadable. Nothing is stored then.
The script only reads from GitHub.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

OWNER, NAME, PR = "positron-ai", "tron", 5022
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "log.txt")
API = f"repos/{OWNER}/{NAME}"
PULL = f'repository(owner:"{OWNER}",name:"{NAME}"){{pullRequest(number:{PR})'

# Timeline events that repeat a review or a comment the snapshot already holds,
# or that say nothing about the review.
SKIP_EVENTS = {"reviewed", "commented", "line-commented", "subscribed", "unsubscribed", "mentioned"}
# Fields that are stored for the printed line and are not compared.
DISPLAY_ONLY = {"where", "url"}
KINDS = ("pr", "review", "inline", "conversation", "thread", "event", "check")
TEXT_KINDS = ("review", "inline", "conversation")

Q_PR = (
    "query{" + PULL + "{"
    "state isDraft headRefOid baseRefName reviewDecision mergeStateStatus mergeable "
    "mergeQueueEntry{state position} autoMergeRequest{enabledBy{__typename login}} "
    "title body lastEditedAt editor{__typename login} "
    "labels(first:50){nodes{name}} assignees(first:20){nodes{login}} "
    "reviewRequests(first:50){nodes{requestedReviewer{__typename "
    "... on User{login} ... on Team{slug} ... on Bot{login} ... on Mannequin{login}}}} "
    "commits(last:1){nodes{commit{statusCheckRollup{state contexts(first:100){pageInfo{hasNextPage} "
    "nodes{__typename ... on CheckRun{name status conclusion checkSuite{workflowRun{workflow{name}}}} "
    "... on StatusContext{context state}}}}}}}"
    "}}}"
)
REVIEW_FIELDS = (
    "databaseId author{__typename login} state submittedAt body url commit{oid} "
    "reactionGroups{content reactors{totalCount}}"
)
THREAD_FIELDS = "isResolved resolvedBy{__typename login} path originalLine comments(first:1){nodes{databaseId}}"
REST_REACTIONS = ("+1", "-1", "laugh", "confused", "heart", "hooray", "rocket", "eyes")


def gh(args, stdin=None):
    """Run one read-only gh command and return its JSON. Three attempts."""
    error = ""
    for attempt in range(3):
        if attempt:
            time.sleep(10 * attempt)
        try:
            p = subprocess.run(["gh"] + args, input=stdin, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            error = "no answer within 120 s"
            continue
        if p.returncode == 0:
            return json.loads(p.stdout)
        error = " ".join((p.stderr or p.stdout).split())[:400]
    raise RuntimeError(f"gh {' '.join(args[:2])}: {error}")


def gql(query, **variables):
    data = gh(["api", "graphql", "--input", "-"], stdin=json.dumps({"query": query, "variables": variables}))
    return data["data"]["repository"]["pullRequest"]


def gql_all(connection, fields):
    """All nodes of one connection of the PR, 100 per page."""
    query = (
        "query($after:String){" + PULL + "{" + connection
        + "(first:100,after:$after){pageInfo{hasNextPage endCursor} nodes{" + fields + "}}}}}"
    )
    nodes, after = [], None
    while True:
        page = gql(query, after=after)[connection]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        after = page["pageInfo"]["endCursor"]


def rest_all(path):
    """All items of one REST list, 100 per page."""
    items, page = [], 1
    while True:
        chunk = gh(["api", f"{API}/{path}?per_page=100&page={page}"])
        items += chunk
        if len(chunk) < 100:
            return items
        page += 1


def gql_login(actor):
    if not actor:
        return "nobody"
    return actor["login"] + ("[bot]" if actor.get("__typename") == "Bot" else "")


def rest_login(user):
    return (user or {}).get("login") or "nobody"


def rest_reactions(r):
    return " ".join(f"{k}:{r[k]}" for k in REST_REACTIONS if r and r.get(k))


def event_entry(e):
    kind = e.get("event")
    author = e.get("author") or {}
    actor = rest_login(e.get("actor") or e.get("user")) if (e.get("actor") or e.get("user")) else author.get("name", "nobody")
    at = e.get("created_at") or e.get("submitted_at") or author.get("date")
    if kind in ("review_requested", "review_request_removed"):
        detail = (e.get("requested_reviewer") or {}).get("login") or "team " + (e.get("requested_team") or {}).get("slug", "?")
    elif kind in ("labeled", "unlabeled"):
        detail = (e.get("label") or {}).get("name", "")
    elif kind == "committed":
        detail = f"{e['sha'][:10]} {(e.get('message') or '').splitlines()[0] if e.get('message') else ''}"
    elif kind == "cross-referenced":
        issue = (e.get("source") or {}).get("issue") or {}
        detail = f"{issue.get('html_url', '')} {issue.get('title', '')}"
    elif kind == "review_dismissed":
        dismissed = e.get("dismissed_review") or {}
        detail = f"review {dismissed.get('review_id')}: {dismissed.get('dismissal_message') or ''}"
    elif kind == "renamed":
        detail = f"{(e.get('rename') or {}).get('from')} -> {(e.get('rename') or {}).get('to')}"
    else:
        detail = (e.get("commit_id") or "")[:10]
    key = str(e.get("id") or e.get("sha") or f"{kind}/{at}/{detail}")
    return key, {"type": kind, "by": actor, "at": at, "detail": detail.strip()}


def take_snapshot():
    pr = gql(Q_PR)
    for _ in range(3):  # GitHub answers UNKNOWN while it recomputes the merge check
        if pr["mergeable"] != "UNKNOWN":
            break
        time.sleep(10)
        pr = gql(Q_PR)

    rollup = pr["commits"]["nodes"][0]["commit"]["statusCheckRollup"]
    checks = {}
    if rollup:
        if rollup["contexts"]["pageInfo"]["hasNextPage"]:
            raise RuntimeError("the head has more than 100 checks; the script reads 100")
        for c in rollup["contexts"]["nodes"]:
            if c["__typename"] == "CheckRun":
                workflow = ((c.get("checkSuite") or {}).get("workflowRun") or {}).get("workflow") or {}
                name = c["name"] + (f" [{workflow['name']}]" if workflow.get("name") else "")
                result = f"{c['status']}/{c['conclusion']}"
            else:
                name, result = c["context"], c["state"]
            checks.setdefault(name, []).append(result)

    queue = pr["mergeQueueEntry"]
    body_digest = hashlib.sha256((pr["body"] or "").encode()).hexdigest()[:12]
    snap = {
        "pr": {
            "": {
                "state": pr["state"],
                "draft": pr["isDraft"],
                "head": pr["headRefOid"],
                "base branch": pr["baseRefName"],
                "review decision": pr["reviewDecision"],
                "merge state": pr["mergeStateStatus"],
                "mergeable": pr["mergeable"],
                "merge queue": f"{queue['state']}, position {queue['position']}" if queue else "not queued",
                "auto merge": "on, by " + gql_login(pr["autoMergeRequest"]["enabledBy"]) if pr["autoMergeRequest"] else "off",
                "title": pr["title"],
                "description": f"digest {body_digest}, last edit {pr['lastEditedAt']} by {gql_login(pr['editor'])}",
                "labels": sorted(n["name"] for n in pr["labels"]["nodes"]),
                "assignees": sorted(n["login"] for n in pr["assignees"]["nodes"]),
                "requested reviewers": sorted(
                    ("team " + r["slug"]) if r["__typename"] == "Team" else gql_login(r)
                    for r in (n["requestedReviewer"] for n in pr["reviewRequests"]["nodes"])
                    if r
                ),
                "checks": rollup["state"] if rollup else None,
            }
        },
        "review": {},
        "inline": {},
        "conversation": {},
        "thread": {},
        "event": {},
        "check": {name: {"result": " + ".join(sorted(results))} for name, results in checks.items()},
    }
    for r in gql_all("reviews", REVIEW_FIELDS):
        snap["review"][str(r["databaseId"])] = {
            "by": gql_login(r["author"]),
            "state": r["state"],
            "submitted": r["submittedAt"],
            "commit": ((r["commit"] or {}).get("oid") or "")[:10],
            "body": r["body"] or "",
            "reactions": " ".join(
                f"{g['content'].lower()}:{g['reactors']['totalCount']}" for g in r["reactionGroups"] if g["reactors"]["totalCount"]
            ),
            "url": r["url"],
        }
    for c in rest_all(f"pulls/{PR}/comments"):
        snap["inline"][str(c["id"])] = {
            "by": rest_login(c["user"]),
            "created": c["created_at"],
            "where": f"{c['path']}:{c['original_line']}" if c.get("original_line") else c["path"],
            "reply to": c.get("in_reply_to_id"),
            "body": c["body"] or "",
            "reactions": rest_reactions(c.get("reactions")),
            "url": c["html_url"],
        }
    for c in rest_all(f"issues/{PR}/comments"):
        snap["conversation"][str(c["id"])] = {
            "by": rest_login(c["user"]),
            "created": c["created_at"],
            "body": c["body"] or "",
            "reactions": rest_reactions(c.get("reactions")),
            "url": c["html_url"],
        }
    for t in gql_all("reviewThreads", THREAD_FIELDS):
        first = t["comments"]["nodes"][0]["databaseId"]
        snap["thread"][str(first)] = {
            "resolved": "yes, by " + gql_login(t["resolvedBy"]) if t["isResolved"] else "no",
            "where": f"{t['path']}:{t['originalLine']}" if t.get("originalLine") else t["path"],
        }
    for e in rest_all(f"issues/{PR}/timeline"):
        if e.get("event") not in SKIP_EVENTS:
            key, entry = event_entry(e)
            snap["event"][key] = entry
    return snap


def one_line(text, limit=160):
    flat = " ".join((text or "").split())
    return flat if len(flat) <= limit else flat[:limit] + "..."


def subject(kind, key, e):
    if kind == "review":
        return f"review {key} by {e['by']}"
    if kind == "inline":
        return f"inline comment {key} by {e['by']} at {e['where']}"
    if kind == "conversation":
        return f"conversation comment {key} by {e['by']}"
    if kind == "thread":
        return f"thread of comment {key} at {e['where']}"
    if kind == "event":
        return f"{e['type']} by {e['by']} at {e['at']}" + (f": {e['detail']}" if e["detail"] else "")
    return key


def describe(kind, key, e):
    """The longer form, for an item that is new or gone."""
    text = subject(kind, key, e)
    if kind == "review":
        text += f": {e['state']}, submitted {e['submitted']}, on commit {e['commit']}, body of {len(e['body'])} characters"
    elif kind == "inline":
        text += f", reply to comment {e['reply to']}" if e["reply to"] else ", starts a thread"
    elif kind == "check":
        text += f": {e['result']}"
    return text


def compare(old, new):
    """Return the printed lines and the full texts of new or edited items."""
    lines, texts = [], []
    head_moved = old["pr"][""]["head"] != new["pr"][""]["head"]
    order = lambda k: (len(k), k)  # numeric ids in numeric order
    for kind in KINDS:
        o, n = old.get(kind, {}), new.get(kind, {})
        if kind == "check" and head_moved:
            counts = Counter(e["result"] for e in n.values())
            lines.append("[check] checks of the new head: " + ", ".join(f"{c} x {r}" for r, c in sorted(counts.items())))
            continue
        if kind != "thread":  # the first comment of a new thread is listed as an inline comment
            for key in sorted(n.keys() - o.keys(), key=order):
                e = n[key]
                line = f"[{kind}] NEW {describe(kind, key, e)}"
                if kind in TEXT_KINDS:
                    line += f': "{one_line(e["body"])}" {e["url"]}'
                    texts.append(f"## NEW {describe(kind, key, e)}\n\n{e['url']}\n\n{e['body']}\n")
                lines.append(line)
            for key in sorted(o.keys() - n.keys(), key=order):
                lines.append(f"[{kind}] GONE {describe(kind, key, o[key])}")
        for key in sorted(o.keys() & n.keys(), key=order):
            for field, value in n[key].items():
                was = o[key].get(field)
                if was == value or field in DISPLAY_ONLY:
                    continue
                name = subject(kind, key, n[key])
                if isinstance(value, list):
                    added, removed = sorted(set(value) - set(was or [])), sorted(set(was or []) - set(value))
                    parts = [f"{word} {', '.join(names)}" for word, names in (("added", added), ("removed", removed)) if names]
                    lines.append(f"[{kind}] {field}: {'; '.join(parts)}")
                elif field == "body":
                    lines.append(f"[{kind}] EDITED {name}: the text changed {n[key]['url']}")
                    texts.append(f"## EDITED {name}\n\n{n[key]['url']}\n\n### Before\n\n{was}\n\n### After\n\n{value}\n")
                else:
                    lines.append(f"[{kind}] {name + ': ' if name else ''}{field}: {was!r} -> {value!r}")
    return lines, texts


def state_line(snap):
    pr = snap["pr"][""]
    resolved = sum(1 for t in snap["thread"].values() if t["resolved"] != "no")
    return (
        f"State: {pr['state']}, review decision {pr['review decision']}, merge state {pr['merge state']}, "
        f"mergeable {pr['mergeable']}, checks {pr['checks']}, head {pr['head'][:10]}; "
        f"{len(snap['review'])} reviews, {len(snap['inline'])} inline comments, "
        f"{len(snap['conversation'])} conversation comments, {resolved} of {len(snap['thread'])} threads resolved."
    )


def log(text):
    with open(LOG, "a") as f:
        f.write(text + "\n")


def failures_in_a_row():
    if not os.path.exists(LOG):
        return 0
    count = 0
    for line in reversed(open(LOG).read().splitlines()):
        if "FETCH FAILED" not in line:
            break
        count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--peek", action="store_true", help="store nothing")
    ap.add_argument("--state", default=os.path.join(HERE, "state.json"), help="the stored snapshot")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    stamp = f"{now:%Y-%m-%d %H:%M} UTC ({now.astimezone(ZoneInfo('America/Los_Angeles')):%Y-%m-%d %H:%M %Z})"
    try:
        stored = json.load(open(args.state)) if os.path.exists(args.state) else None
        new = take_snapshot()
    except Exception as error:  # report every failure; a silent watch looks like a quiet PR
        if args.peek:
            print(f"FETCH FAILED at {stamp}: {error}")
        else:
            log(f"{stamp} | FETCH FAILED: {error}")
            print(f"FETCH FAILED at {stamp}, {failures_in_a_row()} run(s) in a row: {error}")
        return 2

    if stored:
        # UNKNOWN is no information. Keep the last known value so a real change still shows later.
        for field in ("mergeable", "merge state"):
            if new["pr"][""][field] == "UNKNOWN":
                new["pr"][""][field] = stored["snap"]["pr"][""][field]
        lines, texts = compare(stored["snap"], new)
        since = f"previous snapshot {stored['taken']}"
    else:
        lines, texts, since = [], [], "no previous snapshot"

    if not stored:
        print(f"BASELINE STORED at {stamp}")
    elif lines:
        print(f"CHANGES: {len(lines)} at {stamp}, {since}")
        print("\n".join(lines))
    else:
        print(f"NO CHANGE at {stamp}, {since}")
    print(state_line(new))

    if args.peek:
        return 0
    if texts:
        os.makedirs(os.path.join(HERE, "changes"), exist_ok=True)
        path = os.path.join(HERE, "changes", f"{now:%Y%m%dT%H%MZ}.md")
        with open(path, "w") as f:
            f.write(f"# PR {PR}: new and edited texts seen at {stamp}\n\n" + "\n".join(texts))
        print(f"Full texts: {path}")
    log(f"{stamp} | " + (f"{len(lines)} change(s)" if lines else "no change" if stored else "baseline stored"))
    for line in lines:
        log("    " + line)
    tmp = args.state + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"taken": stamp, "snap": new}, f, indent=1)
    os.replace(tmp, args.state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
