# round2-tools: tools of the second reply to Isaac on tron PR 5022

Short version: these files built and patched the page `../round2-respond-2-issac.html` on 2026-11-23 and
2026-11-24. The page answers the follow-up of the reviewer Isaac on PR 5022 and his draft PR 5606. After jhan's
go of 2026-11-24, `post_after_go.py` saved the new PR description and posted the reply. Do not run its write
modes again.

Words used here:
- The page: `../round2-respond-2-issac.html`.
- The description: the text of PR 5022 on GitHub. Its saved copy is
  `/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/inputs/pr5022-body-live.md`.

| File | What it does |
|---|---|
| `diff2html.py` | Renders `git diff A B -- PATH` as a diff block with old and new line numbers. `fragments/` holds the four blocks of the page. |
| `apply_body.py` | Applies the seven replacements to the saved description and prints the word count after each one. Usage: `python3 -B apply_body.py LIVE.md OUT.md`. |
| `pr5022-body-after-5606.draft.md` | The description draft that `apply_body.py` wrote: 1,998 words, with seven names in capitals that stand for CI results. |
| `apply_page_patch1.py`, `apply_page_patch2.py` | The two patches of the page after the review rounds. Each replacement asserts that its old text occurs once. They are kept as a record. Do not run them again. |
| `apply_page_patch3.py` | The patch of the page after the go: the section "After your go" and the references R26 to R28. A record. Do not run it again. |
| `apply_page_patch4.py` | The patch of the page for the review request to Isaac of 2026-11-24 19:46 UTC. A record. Do not run it again. |
| `make_reply_template.py`, `reply.template.md` | Turns the reply block of the page into GitHub markdown, with the names in capitals kept. |
| `fill_ci_results.py` | Fills the seven CI values (`values.json`) into the description draft and the reply template. It stops at a left-over name or at 2,000 words. |
| `post_after_go.py` | `check` runs every check and writes nothing. `save-body` saved the description and `post-reply` posted the reply on 2026-11-24, each with a read-back. Done. |

Checks of the page:
- Structure: `python3 -B ../pr5022-post/page-tools/check_html.py ../round2-respond-2-issac.html`
- Sentence and paragraph sizes: `python3 -B ~/.claude/skills/plain-english-experiment/scripts/check_lengths.py ../round2-respond-2-issac.html`

Records of the steps after the go (CI logs, the texts as sent, the read-backs):
`/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/after-go/` (README there).

Test records of this round: `/home/jhan/workspace/intel-AMX/exec/results/pr5606-check-20261123/` and the README in
`/home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/`.
