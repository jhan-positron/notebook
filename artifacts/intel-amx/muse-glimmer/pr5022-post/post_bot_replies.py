#!/usr/bin/env python3
"""Post the two replies to the automated review of tron PR 5022 (cards B1 and B2 of respond-2-Isaac.html) as ONE
review of kind "comment" without a review body. Same method as post_review.py: the review stays "pending"
(visible to its author only) until the last step.

Usage: post_bot_replies.py --dry-run | --post
The texts are md/B1.md and md/B2.md next to this script. Make them with extract_replies.py and to_markdown.py.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = '/home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/posted-bot-replies.json'
OWNER, REPO, NUMBER = 'positron-ai', 'tron', 5022
EXPECT_HEAD = 'ddf843ad97f8602fc1171458e42036ef03b6e4c4'
TARGETS = {'B1': 4645384790, 'B2': 4645384802}      # card -> first comment of its thread


def gql(query, variables):
    p = subprocess.run(['gh', 'api', 'graphql', '--input', '-'],
                       input=json.dumps({'query': query, 'variables': variables}), capture_output=True, text=True)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise RuntimeError(f'gh api graphql: exit {p.returncode}: {p.stdout[:300]} {p.stderr[:300]}')
    if p.returncode != 0 or out.get('errors'):
        raise RuntimeError(f'GraphQL error: {json.dumps(out.get("errors"))[:600]} {p.stderr[:300]}')
    return out['data']


def norm(text):
    return '\n'.join(l.rstrip() for l in text.replace('\r\n', '\n').strip().split('\n'))


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode not in ('--dry-run', '--post'):
        raise SystemExit(__doc__)
    bodies = {c: open(os.path.join(HERE, 'md', c + '.md'), encoding='utf-8').read().strip() + '\n' for c in TARGETS}
    for c, b in bodies.items():
        assert '⟦' not in b and 200 < len(b) < 60000, f'{c}: placeholder or unexpected length'
    state = gql('''query($owner: String!, $repo: String!, $number: Int!) {
      viewer { login }
      repository(owner: $owner, name: $repo) { pullRequest(number: $number) {
        id headRefOid state
        reviews(first: 100) { nodes { databaseId state author { login } } }
        reviewThreads(first: 100) { nodes { id comments(first: 50) { totalCount nodes { databaseId } } } }
      } } }''', {'owner': OWNER, 'repo': REPO, 'number': NUMBER})
    viewer = state['viewer']['login']; pr = state['repository']['pullRequest']
    assert pr['state'] == 'OPEN' and pr['headRefOid'] == EXPECT_HEAD, f'PR state or head changed: {pr["state"]} {pr["headRefOid"]}'
    assert not [r for r in pr['reviews']['nodes'] if r['author']['login'] == viewer and r['state'] == 'PENDING'], 'a pending review exists'
    threads = {t['comments']['nodes'][0]['databaseId']: t for t in pr['reviewThreads']['nodes']}
    plan = []
    for c, first in TARGETS.items():
        t = threads[first]
        assert t['comments']['totalCount'] == 1, f'{c}: the thread has new comments ({t["comments"]["totalCount"]}); read them first'
        plan.append((c, first, t['id'], bodies[c]))
        print(f'  {c} r{first} {t["id"]} {len(bodies[c])} chars "{bodies[c][:70].strip()}..."')
    if mode == '--dry-run':
        print('dry run: nothing sent'); return
    review = gql('''mutation($pr: ID!, $oid: GitObjectID!) {
      addPullRequestReview(input: {pullRequestId: $pr, commitOID: $oid}) { pullRequestReview { id state } } }''',
                 {'pr': pr['id'], 'oid': EXPECT_HEAD})['addPullRequestReview']['pullRequestReview']
    rid = review['id']
    try:
        sent = {}
        for c, first, tid, b in plan:
            com = gql('''mutation($review: ID!, $thread: ID!, $body: String!) {
              addPullRequestReviewThreadReply(input: {pullRequestReviewId: $review, pullRequestReviewThreadId: $thread, body: $body}) {
                comment { databaseId } } }''', {'review': rid, 'thread': tid, 'body': b})['addPullRequestReviewThreadReply']['comment']
            sent[first] = {'card': c, 'comment': com['databaseId']}
            time.sleep(0.7)
        back = gql('''query($id: ID!) { node(id: $id) { ... on PullRequestReview { state
              comments(first: 100) { totalCount nodes { databaseId body replyTo { databaseId } } } } } }''', {'id': rid})['node']
        assert back['state'] == 'PENDING' and back['comments']['totalCount'] == len(plan)
        for n in back['comments']['nodes']:
            c = sent[n['replyTo']['databaseId']]['card']
            assert norm(n['body']) == norm(bodies[c]), f'{c}: the stored text differs from the text sent'
        done = gql('''mutation($review: ID!) {
          submitPullRequestReview(input: {pullRequestReviewId: $review, event: COMMENT}) {
            pullRequestReview { databaseId state url submittedAt } } }''', {'review': rid})['submitPullRequestReview']['pullRequestReview']
    except BaseException as err:
        print(f'FAILED: {err}\ndeleting the pending review {rid}')
        try:
            gql('mutation($id: ID!) { deletePullRequestReview(input: {pullRequestReviewId: $id}) { pullRequestReview { id } } }', {'id': rid})
            print('pending review deleted; nothing is visible on GitHub')
        except Exception as err2:
            print(f'could NOT delete the pending review: {err2}')
        raise SystemExit(1)
    print(f'submitted: review {done["databaseId"]} state {done["state"]} at {done["submittedAt"]}\n{done["url"]}')
    json.dump({'review': done, 'replies': sent}, open(RECORD, 'w'), indent=1)


if __name__ == '__main__':
    main()
