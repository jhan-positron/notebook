#!/usr/bin/env python3
"""Post the replies to the review of tron PR 5022 as ONE review of kind "comment".

The review holds 26 thread replies (cards I1..I26 of respond-2-Isaac.html, as markdown files) and the combined
reply as the review body. GitHub keeps a review "pending" (visible to its author only) until it is submitted, so
nothing is visible to anybody else before the last step.

Usage: post_review.py --dry-run   print what would be sent; sends nothing
       post_review.py --post      1. create the pending review   2. add the 26 replies   3. read them back and
                                  compare with what was sent     4. submit the review with the combined reply
If a step after 1 fails, the pending review is deleted, so no partial state stays on GitHub.
"""
import json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.environ.get('POST_MD_DIR', os.path.join(HERE, 'md'))   # the override serves the dry-run test only
RECORD = '/home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/posted-review.json'
OWNER, REPO, NUMBER = 'positron-ai', 'tron', 5022
EXPECT_HEAD = 'ddf843ad97f8602fc1171458e42036ef03b6e4c4'
REVIEWER_REVIEW = 5623855297          # the review that is answered
CARDS = [f'I{i}' for i in range(1, 27)]


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
    assert mode == '--dry-run' or 'POST_MD_DIR' not in os.environ, 'POST_MD_DIR is for --dry-run only'
    replies = {r['card']: r for r in json.load(open(os.path.join(HERE, 'replies.json'))) if r['card'] in CARDS}
    assert sorted(replies) == sorted(CARDS), 'cards missing'
    bodies = {c: open(os.path.join(MD, c + '.md'), encoding='utf-8').read().strip() + '\n' for c in CARDS}
    combined = open(os.path.join(MD, 'COMBINED.md'), encoding='utf-8').read().strip() + '\n'
    for name, b in list(bodies.items()) + [('COMBINED', combined)]:
        assert '⟦' not in b and '⟧' not in b, f'{name}: a placeholder is left'
        assert 200 < len(b) < 60000, f'{name}: unexpected length {len(b)}'

    state = gql('''query($owner: String!, $repo: String!, $number: Int!) {
      viewer { login }
      repository(owner: $owner, name: $repo) { pullRequest(number: $number) {
        id headRefOid state
        reviews(first: 100) { nodes { id databaseId state author { login } } }
        reviewThreads(first: 100) { totalCount nodes { id isResolved comments(first: 50) { totalCount nodes { databaseId author { login } } } } }
      } } }''', {'owner': OWNER, 'repo': REPO, 'number': NUMBER})
    viewer = state['viewer']['login']
    pr = state['repository']['pullRequest']
    assert pr['state'] == 'OPEN', pr['state']
    assert pr['headRefOid'] == EXPECT_HEAD, f'the PR head moved: {pr["headRefOid"]}'
    mine = [r for r in pr['reviews']['nodes'] if r['author']['login'] == viewer and r['state'] == 'PENDING']
    assert not mine, f'{viewer} already has a pending review on this PR: {mine}'
    threads = {t['comments']['nodes'][0]['databaseId']: t for t in pr['reviewThreads']['nodes']}
    # Threads of other reviews may exist (an automated review of the new head added 2 on 2026-11-20). Only the
    # 26 threads of the answered review get a reply; each must still hold exactly its first comment.
    missing = [c for c in CARDS if int(replies[c]['discussion']) not in threads]
    assert not missing, f'threads missing for {missing}'
    others = sorted(set(threads) - {int(replies[c]['discussion']) for c in CARDS})
    print(f'threads on the PR: {pr["reviewThreads"]["totalCount"]}; not answered by this review: {others}')
    plan = []
    for c in CARDS:
        t = threads[int(replies[c]['discussion'])]
        assert t['comments']['totalCount'] == 1, f'{c}: the thread has new comments ({t["comments"]["totalCount"]})'
        plan.append((c, int(replies[c]['discussion']), t['id'], bodies[c]))
    print(f'viewer {viewer}; PR head {pr["headRefOid"][:10]}; {len(plan)} thread replies + review body '
          f'({sum(len(b) for _, _, _, b in plan)} + {len(combined)} characters)')
    for c, disc, tid, b in plan:
        print(f'  {c:4} r{disc} {tid}  {len(b):5} chars  "{b[:70].strip()}..."')
    if mode == '--dry-run':
        print('dry run: nothing sent'); return

    review = gql('''mutation($pr: ID!, $oid: GitObjectID!) {
      addPullRequestReview(input: {pullRequestId: $pr, commitOID: $oid}) { pullRequestReview { id databaseId state } } }''',
                 {'pr': pr['id'], 'oid': EXPECT_HEAD})['addPullRequestReview']['pullRequestReview']
    rid = review['id']
    print(f'pending review created: {rid} (state {review["state"]})')
    try:
        assert review['state'] == 'PENDING', review['state']
        sent = {}
        for c, disc, tid, b in plan:
            com = gql('''mutation($review: ID!, $thread: ID!, $body: String!) {
              addPullRequestReviewThreadReply(input: {pullRequestReviewId: $review, pullRequestReviewThreadId: $thread, body: $body}) {
                comment { id databaseId state } } }''', {'review': rid, 'thread': tid, 'body': b})['addPullRequestReviewThreadReply']['comment']
            sent[disc] = {'card': c, 'comment': com['databaseId'], 'state': com['state']}
            time.sleep(0.7)
        back = gql('''query($id: ID!) { node(id: $id) { ... on PullRequestReview { state
              comments(first: 100) { totalCount nodes { databaseId body state replyTo { databaseId } } } } } }''', {'id': rid})['node']
        assert back['state'] == 'PENDING', back['state']
        assert back['comments']['totalCount'] == 26, back['comments']['totalCount']
        for n in back['comments']['nodes']:
            disc = n['replyTo']['databaseId']
            c = sent[disc]['card']
            assert sent[disc]['comment'] == n['databaseId'], f'{c}: comment id differs'
            assert norm(n['body']) == norm(bodies[c]), f'{c}: the stored text differs from the text sent'
        print('read back: 26 pending replies, each on its thread, each text equal to the text sent')
        done = gql('''mutation($review: ID!, $body: String!) {
          submitPullRequestReview(input: {pullRequestReviewId: $review, event: COMMENT, body: $body}) {
            pullRequestReview { id databaseId state url submittedAt } } }''', {'review': rid, 'body': combined})['submitPullRequestReview']['pullRequestReview']
    except BaseException as err:
        print(f'FAILED: {err}\ndeleting the pending review {rid}')
        try:
            gql('mutation($id: ID!) { deletePullRequestReview(input: {pullRequestReviewId: $id}) { pullRequestReview { id state } } }', {'id': rid})
            print('pending review deleted; nothing is visible on GitHub')
        except Exception as err2:
            print(f'could NOT delete the pending review: {err2}')
        raise SystemExit(1)
    print(f'submitted: review {done["databaseId"]} state {done["state"]} at {done["submittedAt"]}\n{done["url"]}')
    json.dump({'review': done, 'replies': sent, 'answers_review': REVIEWER_REVIEW}, open(RECORD, 'w'), indent=1)
    print('record:', RECORD)


if __name__ == '__main__':
    main()
