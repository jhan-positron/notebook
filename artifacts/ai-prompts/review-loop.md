# to claude, worker

After the updating, please work a review loop with codex:
- codex is monitoring your updates of ./asimov-c1nano-perf.html, after you are done, it will write review comments to ./codex-review-asimov-c1nano-perf.md
- you monitor ./codex-review-asimov-c1nano-perf.md for codex update, and append your replies to it
- update ./asimov-c1nano-perf.html if you agree with codex
- monitor ./codex-review-asimov-c1nano-perf.md again for the next review iteration
- The review loop ends when codex informs you there is no further comments in ./codex-review-asimov-c1nano-perf.md. If there is no explicit message stating so, please keep monitoring.


# to codex, reviewer
Please start a review loop with claude:
- claude is updating ./asimov-c1nano-perf.html, monitor the file
- after the claude updating is done, review it and write your comments to ./codex-review-asimov-c1nano-perf.md
- claude will update ./asimov-c1nano-perf.md, monitor the file
- after claude update, review again and append review comments again to ./codex-review-asimov-c1nano-perf.md, and 
- continue the review loop until you have no further comments. At that time, append a message to ./codex-review-asimov-c1nano-perf.md to inform claude so
