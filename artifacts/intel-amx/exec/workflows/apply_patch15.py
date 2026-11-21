#!/usr/bin/env python3
"""Page pass 15 (main session, 2026-11-20, after jhan's second go at about 10:26 PST): the replies B1 and B2 are
posted and the review is re-requested. Nothing is open. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p, encoding='utf-8').read(); orig = s
PR = 'https://github.com/positron-ai/tron/pull/5022'
def once(old, new):
    global s
    if new in s: return 0
    assert s.count(old) == 1, ('not found exactly once', old[:70], s.count(old))
    s = s.replace(old, new); return 1
todo = 0
# the line under the title
todo += once('pushed and posted on 2026-11-20 (head ddf843ad97, review 5997064669) &middot; two replies to an automated review wait for your go</p>',
             'pushed and posted on 2026-11-20 (head ddf843ad97, reviews 5997064669 and 5997527928) &middot; review re-requested from Isaac at 10:27 PST &middot; nothing is open</p>')
# Short version, last sentence
todo += once('One thing is needed from you: the go for two more replies (cards <a href="#B1">B1</a> and <a href="#B2">B2</a>), which answer an automated review of the new head, and after them I re-request Isaac\'s review.</p></div>',
             'After your second go the two replies to an automated review of the new head are posted as well (cards <a href="#B1">B1</a> and <a href="#B2">B2</a>), and Isaac\'s review is re-requested, so nothing is open on our side.</p></div>')
# status box: head line
todo += once('<div class="open" id="open5"><p><strong>Status 2026-11-20 09:57 PST: pushed, CI passed, replies posted.</strong> One thing is needed from you: the go for two more replies, cards <a href="#B1">B1</a> and <a href="#B2">B2</a>. They answer an automated review that arrived on the new head.</p>',
             '<div class="open done" id="open5"><p><strong>Status 2026-11-20 10:28 PST: every step is done.</strong> The head is pushed, CI passed, all replies are posted, and Isaac\'s review is re-requested. Nothing is needed from you now. The list below was written at 09:57 PST, and its last two points are updated.</p>')
# status box: last bullet
todo += once('<li><strong>Not done: the re-request of Isaac\'s review.</strong> I hold it until the two comments of the automated review are answered.</li>',
             f'<li><strong>Replies to the automated review.</strong> You gave the go at about 10:26 PST, after the rewording of B2. Both replies were posted at 10:27 PST as one review, <a href="{PR}#pullrequestreview-5997527928">review 5997527928</a>. I read both back and compared them with the texts sent. All 28 review threads of the PR now hold a reply <a class="ref" href="#R64">[R64]</a>.</li>\n'
             '<li><strong>Re-request of Isaac\'s review.</strong> Done at 10:27 PST. The timeline of the PR shows the request <a class="ref" href="#R64">[R64]</a>.</li>')
# section heading and its sub line
todo += once('<h2 id="bot">Automated review of the new head: 2 comments, 2 draft replies</h2>', '<h2 id="bot">Automated review of the new head: 2 comments, 2 replies posted</h2>')
todo += once('need no follow-up push." Neither draft reply is posted.</p>', 'need no follow-up push." Both replies were posted on 2026-11-20 at 10:27 PST.</p>')
# reply labels of B1 and B2
n = s.count('<div class="lbl">Reply (draft, not posted)</div>')
if n:
    assert n == 2, n
    s = s.replace('<div class="lbl">Reply (draft, not posted)</div>', '<div class="lbl">Reply (posted 2026-11-20 10:27 PST)</div>'); todo += 1
# reference R64
REF = ('<li id="R64">Review 5997527928 by jhan-positron, submitted 2026-11-20 18:27:33 UTC, with the reply comments 4646192229 (B1) and 4646192533 (B2); record <code>posted-bot-replies.json</code> in the results folder. '
       'The timeline of the PR has the event <code>review_requested</code> for ishapira-positron at 18:27:51 UTC. The texts sent are <code>muse-glimmer/pr5022-post/md/B1.md</code> and <code>B2.md</code>.</li>\n')
if '<li id="R64">' not in s:
    i = s.index('<li id="R63">'); j = s.index('</ol>', i)
    s = s[:j] + REF + s[j:]; todo += 1
# how this was checked: last sentence of the update paragraph
todo += once('Not posted: the two draft replies B1 and B2. Not done: the re-request of the review.</p>',
             'The replies B1 and B2 were posted at 10:27 PST after your go, and the review was re-requested in the same minute.</p>')
if s != orig:
    open(p, 'w', encoding='utf-8').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
