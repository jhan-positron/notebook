# Wade's review record: corpus boundary, counts and method

Short version: This file records where the skill's checks come from. The 2026-10-06 refresh read every review Wade (GitHub login Wado-posi) left on 115 pull requests he did not author, classified all 273 texts, and derived or widened the checks in SKILL.md from the clusters. Counts below are computed with code over the saved corpus, not estimated.

## Words used here

- PR: pull request. Inline comment: a comment attached to a diff line. Conversation comment: a comment in the PR's discussion tab. Review: a submitted review with a state (APPROVED, COMMENTED, CHANGES_REQUESTED) and an optional body.
- Silent PR: a PR Wade approved with no text at all (no comment, no review body).
- Corpus: the saved JSON of all the above, plus each PR's title, body, file list and commit subjects.

## Corpus boundary

- Collected 2026-10-06 with the GitHub command-line tool `gh`. PR set = union of `gh search prs --reviewed-by Wado-posi --owner positron-ai` (182 PRs) and `--commenter Wado-posi` (191 PRs). PRs Wade authored (69 in the reviewed-by set, 76 in the union) were dropped: replies on his own PRs are not reviews. Result: 115 PRs by other authors, created 2025-09-23 to 2026-10-03, last record 2026-10-06.
- Per PR, three paginated endpoints were read: `pulls/N/reviews`, `pulls/N/comments` (inline, with the diff hunk, the parent comment and every reply), `issues/N/comments`. No fetch failed.
- Records by Wade: 334 reviews (100 APPROVED, 234 COMMENTED, 0 CHANGES_REQUESTED), 243 inline comments (37 of them replies to someone else), 11 conversation comments. Only 15 review bodies carry text. 67 PRs have some text from Wade. 48 PRs are silent.

| Repository | PRs | Reviews | Inline | Conversation | Silent PRs |
|---|---:|---:|---:|---:|---:|
| positron-ai/tron | 102 | 316 | 238 | 10 | 38 |
| positron-ai/aps-claude-files | 6 | 6 | 0 | 0 | 6 |
| positron-ai/asimovsw-docs | 2 | 6 | 4 | 1 | 0 |
| positron-ai/asim | 2 | 3 | 1 | 0 | 1 |
| positron-ai/asimov-os | 2 | 2 | 0 | 0 | 2 |
| positron-ai/terminus | 1 | 1 | 0 | 0 | 1 |

- Inline comments by file area: h/ 126, src/ 77, t/ 27, docs 8, other 5. Test files draw 11 percent of his inline comments.
- Inline comments by month: 2025-09 2, 2025-12 6, 2026-01 23, 2026-02 25, 2026-03 52, 2026-04 22, 2026-05 37, 2026-06 33, 2026-07 2, 2026-08 11, 2026-09 23, 2026-10 7.
- What the corpus cannot show: deleted comments, repositories the account cannot read, reviews never submitted, and activity after collection. An empty approval establishes no preference.

## Pasted assistant text

Nine texts contain analysis Wade attributes to an AI assistant. They are attributed material, not his own words, and a check derived only from them says so in its precedent note.

| PR | Id | Date | Opening words |
|---|---|---|---|
| tron 2233 | 3002297607 | 2026-03-27 | "Claude had this to say about below:" |
| tron 2461 | 4131374395 | 2026-04-17 | "I think CC is onto something with that `attn_launchers` finding." |
| tron 2872 | 3342904643 | 2026-06-02 | "which I let Claude summarize for me below" |
| tron 2906 | 4674512577 | 2026-06-10 | "So I asked Claude to summarize my concern" |
| tron 3008 | 3437517809 | 2026-06-18 | "GPT had this to say about `first_desc`:" |
| tron 3490 | 4800935083 | 2026-07-28 | "I did ask claude to do a review as well." |
| tron 4128 | 5498556672 | 2026-09-01 | "So I prompted Claude with that (and told it to look at the PR overall)." |
| tron 3879 | 5544513215 | 2026-09-04 | "below is Claude's evaluation of this PR:" |
| tron 4191 | 3970590653 | 2026-09-09 | "I asked GPT to evaluate this... it agrees:" |

The six dense inline comments on PR 4128 (3907183627, 3907185740, 3907214892, 3960506641, 3960538177, 3960538961) carry no disclosure but were posted minutes after the disclosed paste and share its form. The PR 4557 review (5420005787 and seven inline comments) has the same form and no disclosure. Whether it was assisted is Insufficient data.

## Method of the refresh

1. One classifier agent per PR batch read the digest of every PR with Wade text and labelled each of the 273 texts: the concern, the existing check it maps to (full, partial, none), a candidate label, a detection sketch, the evidence Wade had to read, the form, the severity and the author's response. 202 texts mapped to none of the 13 checks of the 2026-10-05 skill.
2. Three taxonomists (by mechanism, by evidence read, by delta to the existing skill) clustered the 273 rows; a judge merged them into 35 clusters: 1 non-review cluster (35 answers, praise and self-notes), 22 new checks, 11 widenings of existing checks, 2 existing checks kept as they were.
3. One drafter per cluster wrote the check in the house form from the member comments and the code at the cited commits. Three refuters per draft tested precision (the trigger run on the diffs of silently approved PRs), facts (verbatim quotes, code at the commit, later replies) and executability (the commands run on an originating PR). A tightener folded the verdicts. A critic checked overlap and the codex cross-check coverage.
4. Codex's parallel refresh of its own copy of the skill (~/.codex/skills/wade-code-review, 2026-10-06 10:26) was cross-checked: 8 of its claims that contradict the Claude skill were fact-checked (4 hold, 4 partly), and its 65 guidance bullets were mapped to corpus evidence (58 backed by Wade comments, 2 by pasted assistant text only, 5 by none).

Inputs and outputs: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006/ (corpus/, classified.json, merged-taxonomy.json, items/, codex-factcheck.md, codex-map.json, the workflow scripts).
