# Context: update of the Wade-code-review skill from Wade's whole review record (2026-10-06)

Read this file fully before working.

## What this is
Reviewer Wade (GitHub login Wado-posi) reviews pull requests (PRs) in positron-ai/tron, the inference server
code base. A skill at /home/jhan/.claude/skills/Wade-code-review/SKILL.md (with references/procedures.md and
references/pr4557-misses.md) tells an agent how to review a PR the way Wade does, before Wade sees it.
That skill was derived on 2026-10-05 from ONE review (PR 4557): 13 checks about tests, PR-body claims,
commit history, scope and ownership. The job now: go through ALL of Wade's reviews on PRs he did not author
and update the skill so that it covers what he actually comments on.

## The corpus (read only, never edit)
Directory: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/wade-20261006/corpus/
- corpus.json: 115 PRs (positron-ai repos, 2025-09 to 2026-10) that Wade reviewed and did not author. Per PR:
  title, author, body (live text), file list, commit subjects, Wade's reviews (state + body + commit), Wade's
  inline comments (id, path, line, diff_hunk, parent comment if a reply, replies by others) and his conversation
  comments. 334 reviews (100 APPROVED, 234 COMMENTED, 0 CHANGES_REQUESTED), 243 inline comments, 11 conversation comments. PR list = union of gh search prs --reviewed-by and --commenter (tron 3879 and 2898 have conversation comments only).
- pr/<repo>-<number>.md: one readable digest per PR that has any Wade text (67 files). Use these.
- silent.json: the 48 PRs Wade approved with no text at all (negative space: what he does NOT comment on).
- prs-reviewed.json / prs-authored.json: the PR lists from `gh search prs`.
- Facts counted with code: inline comments by area: h/ 126, src/ 77, t/ 27, docs 8, other 5. 122 of 267 texts
  contain a question mark. 43 texts contain a ```suggestion block. 13 say "nit". 1 says "squash". 0 say "LGTM".
  Wade sometimes pastes text from an AI assistant (9 texts, first on 2026-03-27 in PR 2233: "Claude had this to say about below:"; also PRs 2461, 2872, 2906, 3008, 3490, 4128, 3879, 4191). Treat pasted text as attributed material, not as his own words.

## Code access (read only)
A tron worktree is at /home/jhan/workspace/ai-runs/tron-issue4525 (DO NOT edit, DO NOT run state-changing git:
no checkout, reset, worktree, fetch, pull, prune). Merged PR commits are in its history: use
`git -C /home/jhan/workspace/ai-runs/tron-issue4525 show <commit>:<path>` and `git ... log`. `gh pr diff N --repo positron-ai/tron`
and `gh api` work for PR content. Line numbers in Wade's comments refer to the commit shown next to the comment.

## The existing skill (read it before classifying)
/home/jhan/.claude/skills/Wade-code-review/SKILL.md: 13 checks:
 1 value-pinning test rows need a consumer; 2 structure-only compile-time checks; 3 layout check gated by hardware
 does not run on the CI lane; 4 duplicate test coverage; 5 test name contradicts assertions; 6 guarantee claim vs
 enforcing declaration; 7 CI claims name the lane; 8 result rows cite the reviewed head; 9 PR-body passages a reader
 cannot use; 10 unrelated hunks; 11 commit history / fixup clusters; 12 shared-header change needs owner sign-off;
 13 role-bearing constant names. Plus "How Wade words a finding" and "Report the result".
Procedures: /home/jhan/.claude/skills/Wade-code-review/references/procedures.md.

## Ground rules for every agent
- Quote Wade verbatim (copy from the digest; never paraphrase inside quotation marks) and give the comment id.
- Distinguish what you read from what you infer. Plain English: define a code name or acronym at first use,
  one claim per sentence.
- Return raw data in the schema; no human-facing prose.
