# Checklist for jhan: PR #4557 round 2 (2026-10-01)

Words used here: W = the tron worktree /home/jhan/workspace/ai-runs/tron-issue4525 (branch jhan-kv-typed-tensors, local head faf8ee42ca, origin still at c73e7fb2f9). E = /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930 (the folder with the final texts).

Precondition, met at 19:37 UTC: the 3bda build and test run at faf8ee42ca is complete and green. The counts in the texts are measured, not predicted: both builds rc 0, t_llama_unit 244522 assertions in 44 cases on each tree, packed-bits case 20755, lint-notes rc 0. Log copy: E/final-3bda.log (source /var/tmp/jhan/tron-issue4525-final.log on delphi-3bda). One check before posting: no placeholder is left in any text.

```
grep -c '<<COUNTS' /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930/final-*.md
```

Every line must end in `:0`. (The counts were filled by hand from the log on 2026-10-01 19:38 UTC. E/fill-counts.py is a helper another step left behind. It is not needed any more.)

## 0. Check the local branch

```
git -C /home/jhan/workspace/ai-runs/tron-issue4525 status --short
git -C /home/jhan/workspace/ai-runs/tron-issue4525 log --oneline c73e7fb2f9..HEAD
```

Expected: no status lines, and 8 commits with faf8ee42ca on top and 63df10cf90 at the bottom.

## 1. Push

```
git -C /home/jhan/workspace/ai-runs/tron-issue4525 push origin jhan-kv-typed-tensors
```

This is a fast-forward of origin (c73e7fb2f9 is an ancestor of faf8ee42ca). No force flag is needed.

## 2. Check that GitHub marks #4697 and #4698 as merged

```
gh pr view 4697 --repo positron-ai/tron --json state,mergeCommit -q '.state + " " + (.mergeCommit.oid // "-")'
gh pr view 4698 --repo positron-ai/tron --json state,mergeCommit -q '.state + " " + (.mergeCommit.oid // "-")'
```

Expected: MERGED for both. If one still says OPEN, close it with a note:

```
gh pr close 4697 --repo positron-ai/tron --comment "Taken into jhan-kv-typed-tensors by fast-forward as 8bbbb7c82d (PR #4557)."
gh pr close 4698 --repo positron-ai/tron --comment "Merged into jhan-kv-typed-tensors as merge commit 8e0cf77bed (PR #4557)."
```

## 3. Update the PR body

Re-fetch the live body first. The edit was made against the snapshot E/pr-body-live.md fetched on 2026-10-01 at about 19:12 UTC.

```
gh pr view 4557 --repo positron-ai/tron --json body -q .body | diff - /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930/pr-body-live.md && echo "live body unchanged"
```

If the diff is empty, apply the new body. If it is not, re-run `python3 E/gen-final-body.py` on the re-fetched E/pr-body-live.md (the script asserts on every line it edits, so a moved line fails loudly) and look at the regenerated E/final-pr-body.diff. The live body uses CRLF line ends and final-pr-body.md keeps them. Do not re-run E/fill-counts.py on it: that script rewrites the file with LF line ends.

```
gh pr edit 4557 --repo positron-ai/tron --body-file /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930/final-pr-body.md
```

## 4. Post the five replies

One file per reply: E/final-reply-b2.md to E/final-reply-b6.md (the same text as E/final-replies.md, without the headings). Use `-F`, not `-f`: `-f body=@file` posts the literal text "@file", and `-F` reads the file and sends the integer id as a number.

```
cd /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930
gh api repos/positron-ai/tron/pulls/4557/comments -F body=@final-reply-b2.md -F in_reply_to=4133643149 -q .html_url
gh api repos/positron-ai/tron/pulls/4557/comments -F body=@final-reply-b3.md -F in_reply_to=4133869073 -q .html_url
gh api repos/positron-ai/tron/pulls/4557/comments -F body=@final-reply-b4.md -F in_reply_to=4134028988 -q .html_url
gh api repos/positron-ai/tron/pulls/4557/comments -F body=@final-reply-b5.md -F in_reply_to=4134076112 -q .html_url
gh api repos/positron-ai/tron/pulls/4557/comments -F body=@final-reply-b6.md -F in_reply_to=4134925164 -q .html_url
```

Each call prints the URL of the posted reply. B1 (4133613638) is already answered by your comment 4158498407.

## 5. Close issue #4588

`gh issue close` has no `--comment-file` flag. Pass the file content as the string:

```
gh issue close 4588 --repo positron-ai/tron --reason completed --comment "$(cat /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/exec/ben-20260930/final-issue-4588-comment.md)"
```

## 6. Ask for the review again

```
gh pr edit 4557 --repo positron-ai/tron --add-reviewer bgamari-positron
```

The reviewer's state is CHANGES_REQUESTED (review 5352791816). A re-request is what clears it on his side.

## 7. Label

The PR carries `Skip benchmarks` (checked 2026-10-01 19:14 UTC). Leave it as it is. The body's Labels section says the same.

## 8. After the push

```
gh pr checks 4557 --repo positron-ai/tron --watch
```

Expected: the GCP Nix lane (AMX-off) builds and tests the new head. The AMX-on tests ran only on delphi-3bda (step 0 precondition).

Housekeeping, not for GitHub:

- Delete the 3bda copy when the log is saved: `ssh delphi-3bda rm -rf /var/tmp/jhan/tron-issue4525-ben` (keep /var/tmp/jhan/tron-issue4525-final.log until it is copied into E).
- Design page status/design-new-tensor-type.html: record Q3 as rejected (B5 option b) and the "Expression reads" row as withdrawn, keep every id anchor.
- Memory note: the 2026-09-24 "paragraph removed" sentence is wrong. The paragraph left with #4698 on 2026-10-01.
