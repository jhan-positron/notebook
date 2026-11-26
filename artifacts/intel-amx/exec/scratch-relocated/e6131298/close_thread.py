#!/usr/bin/env python3
"""Post one reply on a review thread of tron PR 5022 and resolve the thread.

Steps: check the thread, create a pending review, add the reply, read it back, submit, resolve, read back.
On a failure before the submit step the pending review is deleted, so nothing becomes visible.
Usage: close_thread.py <text file> --dry-run | --post
"""
import json
import subprocess
import sys

OWNER, REPO, PR = "positron-ai", "tron", 5022
THREAD = "PRRT_kwDOKStajs6veIrN"          # registry thread, first comment r4356061343
FIRST_COMMENT = 4356061343
HEAD = "187da02163fe97db837dca6443983986f20c0ef8"


def gql(query, **variables):
    p = subprocess.run(["gh", "api", "graphql", "--input", "-"], input=json.dumps({"query": query, "variables": variables}),
                       capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"gh failed: {p.stdout} {p.stderr}")
    d = json.loads(p.stdout)
    if d.get("errors"):
        sys.exit(f"GraphQL errors: {d['errors']}")
    return d["data"]


def main():
    text_file, mode = sys.argv[1], sys.argv[2]
    body = open(text_file, encoding="utf-8").read().rstrip("\n")
    d = gql("""query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
      id headRefOid state reviewThreads(first:100){totalCount nodes{id isResolved viewerCanResolve viewerCanReply
        comments(first:20){totalCount nodes{databaseId author{login}}}}}
      reviews(states:PENDING,first:5){nodes{id}}}}}""", o=OWNER, r=REPO, n=PR)["repository"]["pullRequest"]
    threads = d["reviewThreads"]["nodes"]
    t = next(x for x in threads if x["id"] == THREAD)
    print(f"PR state {d['state']}, head {d['headRefOid'][:10]}, threads {d['reviewThreads']['totalCount']}, "
          f"unresolved {sum(not x['isResolved'] for x in threads)}, my pending reviews {len(d['reviews']['nodes'])}")
    print(f"thread {THREAD}: resolved={t['isResolved']} comments={t['comments']['totalCount']} "
          f"first={t['comments']['nodes'][0]['databaseId']} last author={t['comments']['nodes'][-1]['author']['login']} "
          f"canReply={t['viewerCanReply']} canResolve={t['viewerCanResolve']}")
    assert d["state"] == "OPEN" and d["headRefOid"] == HEAD, "the PR head or state changed"
    assert t["comments"]["nodes"][0]["databaseId"] == FIRST_COMMENT, "this is not the registry thread"
    assert not t["isResolved"] and t["viewerCanReply"] and t["viewerCanResolve"]
    assert t["comments"]["totalCount"] == 2, "the thread gained a comment since it was read: read it first"
    assert not d["reviews"]["nodes"], "a pending review of mine exists already"
    print(f"reply text: {len(body)} characters, {len(body.split())} words")
    if mode != "--post":
        print("dry run: nothing posted")
        return
    rid = gql("""mutation($p:ID!,$c:GitObjectID!){addPullRequestReview(input:{pullRequestId:$p,commitOID:$c}){
      pullRequestReview{id state}}}""", p=d["id"], c=HEAD)["addPullRequestReview"]["pullRequestReview"]["id"]
    try:
        gql("""mutation($v:ID!,$t:ID!,$b:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewId:$v,
          pullRequestReviewThreadId:$t,body:$b}){comment{id}}}""", v=rid, t=THREAD, b=body)
        back = gql("""query($id:ID!){node(id:$id){... on PullRequestReview{state comments(first:5){nodes{body
          replyTo{databaseId}}}}}}""", id=rid)["node"]
        c = back["comments"]["nodes"]
        assert back["state"] == "PENDING" and len(c) == 1, back
        assert c[0]["body"] == body and c[0]["replyTo"]["databaseId"] == FIRST_COMMENT, "read-back differs from the text sent"
    except BaseException:
        gql("mutation($id:ID!){deletePullRequestReview(input:{pullRequestReviewId:$id}){pullRequestReview{id}}}", id=rid)
        print("pending review deleted; nothing was posted")
        raise
    sub = gql("""mutation($id:ID!){submitPullRequestReview(input:{pullRequestReviewId:$id,event:COMMENT}){
      pullRequestReview{databaseId state url submittedAt}}}""", id=rid)["submitPullRequestReview"]["pullRequestReview"]
    print(f"review submitted: {sub}")
    res = gql("mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{id isResolved resolvedBy{login}}}}",
              t=THREAD)["resolveReviewThread"]["thread"]
    print(f"thread resolved: {res}")
    after = gql("""query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
      reviewDecision mergeStateStatus reviewThreads(first:100){nodes{id isResolved comments(last:1){nodes{url
      author{login} body}}}}}}}""", o=OWNER, r=REPO, n=PR)["repository"]["pullRequest"]
    t = next(x for x in after["reviewThreads"]["nodes"] if x["id"] == THREAD)
    last = t["comments"]["nodes"][0]
    print(f"read-back: resolved={t['isResolved']} last comment by {last['author']['login']} {last['url']} "
          f"equals the text sent: {last['body'] == body}")
    print(f"PR now: reviewDecision={after['reviewDecision']} mergeStateStatus={after['mergeStateStatus']} "
          f"unresolved threads={sum(not x['isResolved'] for x in after['reviewThreads']['nodes'])}")


main()
