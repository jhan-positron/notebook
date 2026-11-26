# pr5022-post: tools and texts of the posting of review round 2 of tron PR 5022

Short version: on 2026-11-20 the 26 thread replies and the combined reply to the review of PR 5022 were posted
from here as one GitHub review (number 5997064669). Two replies to an automated review (`md/B1.md`, `md/B2.md`) followed as review 5997527928 at 10:27 PST.
The texts in `md/` are what was sent.

Words used here:
- Page: `../respond-2-Isaac.html`, the page that holds every reply draft in a block `<div class="reply">`.
- Card: one comment of the review on that page (I1..I26 inline comments, T0..T13 points of the review body,
  B1 and B2 comments of the automated review).
- Pending review: a GitHub review that only its author sees until it is submitted.

| File | What it does |
|---|---|
| extract_replies.py | Reads the reply blocks of the page into `replies.json` (card, thread id, HTML). |
| to_markdown.py | Turns `replies.json` into GitHub markdown, one file per card in `md/`. The second block of card T13 is the combined reply (`COMBINED.md`). |
| fill_placeholders.py | Fills head, run ids, runner and issue number (`values.json`) into the page and into the PR description draft. |
| check_quotes.py | Checks that every quoted code line of the replies occurs in the pushed head. |
| locate_blocks.py | Prints where each quoted block stands in the pushed head, to check stated line numbers. |
| md_hazards.py | Flags characters that GitHub would read as markup outside code. |
| render_check.py | Renders the texts with the markdown service of GitHub. Nothing is published. |
| count_ins.py | Counts instructions per kernel function in a disassembly listing. |
| post_review.py | Posted the 26 replies and the combined reply as one review (`--dry-run` or `--post`). Done; do not run `--post` again. |
| post_bot_replies.py | Posted `md/B1.md` and `md/B2.md` as one review (`--dry-run` or `--post`). Done; do not run `--post` again. |

Order of use: extract_replies.py, to_markdown.py, the three checks, then the posting script with `--dry-run`,
then with `--post`. Records of what was posted: `posted-review.json` and `posted-bot-replies.json` in
`../../exec/results/pr5022-final-20261119/`.
