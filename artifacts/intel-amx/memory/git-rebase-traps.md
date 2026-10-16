---
name: git-rebase-traps
description: Traps hit when rebasing PR branches of tron (2026-09-15): rebase strips '#'-leading commit-message lines; a clean textual rebase can still fail to compile when main added a caller of a function whose signature the PR changed (incl. new overload FAMILIES and decltype of a constrained call); git 2.34 quirks; a stacked branch's base vanishes when the parent PR is rebased before merging
metadata:
  type: feedback
---

Three traps from the 2026-09-15 rebase of PR 3879 (jhan-amx-p0 onto main 68378c3b48).

1. `git rebase` strips commit-message lines that begin with `#` (its message cleanup
   treats them as comments). A body line starting with `#4338 as the future home ...`
   vanished silently. Compare every rebased message with its original
   (`git log -1 --format=%B`), and restore with `git commit --amend --cleanup=whitespace
   -F msg` (whitespace mode keeps `#` lines; verbatim mode keeps trailing blank lines too).
2. A rebase with no textual conflict can still break the build: main's #3054 added a
   second caller of apply_page_tok with the old arity while the PR had added a parameter
   without a default. Always build the rebased tip (3bda, exec/pr1-rebase-YYYYMMDD/) and
   grep main's added lines for every function whose signature the PR changed
   (`git diff OLD_BASE origin/main | grep '^+' | grep -E 'name1|name2'`).
3. git 2.34 on claude-box: `git cherry-pick -q` is not a valid option; `git merge-tree
   --write-tree` does not exist (simulate the GitHub merge with a detached worktree +
   `git merge --no-ff`, then `git diff <merge> <rebased-tip>`).

4. (2026-09-15, VNNI-K #4424 onto main) When the PR CONSTRAINS an accessor (requires
   clause), main may have added sibling overloads of the same family that the constraint
   must also cover (main's whole-page `page::k(slot, kv_head)` next to the per-token
   `k(slot, kv_head, i)`): a clean auto-merge leaves the new sibling unconstrained and it
   silently reads the wrong layout. Also a non-dependent `decltype(page.k<...>(...)) keys;`
   of a now-constrained call is a hard error, not SFINAE: wrap it in the same
   `if constexpr` lambda pattern as the other layout-dependent locals.
5. A stacked branch (VNNI-K on jhan-amx-p0) loses its base when the parent PR is rebased
   before merging: the old base commit is not in main, so `git rebase main` would replay
   the parent's old commits too. Use `git rebase --onto origin/main <old-base-merge-commit>`
   with the exact merge commit the child was built on (here 544ca05c7a), and keep a backup
   branch of the pre-rebase head. Run a per-file "map main vs branch" workflow first; it
   predicted every conflict and the two hidden compile breaks.

6. (2026-09-30, PR #4596 approved then CONFLICTING) For an already-approved PR, MERGE origin/main into the
   branch instead of rebasing: the reviewed commits keep their ids, the '#'-line trap and the 26-commit
   replay are avoided, and it is the repo's own convention (main's history is full of "Merge branch 'main'
   into <branch>" commits, e.g. f0db4f4e5c the same day). GitHub does NOT dismiss approvals on new pushes
   in positron-ai/tron (PR 3879: Bill's and bgamari's approvals stayed APPROVED through later pushes; no
   DISMISSED review exists), so the approval survives the merge commit. Recipe used: git merge --no-commit
   --no-ff origin/main -> resolve -> lefthook-equivalent checks (git diff --check origin/main HEAD -- ':!lib/**',
   no <cassert>, clang-format in the nix shell) -> ninja + the PR's test binaries -> git push (fast-forward).
   `git merge-tree <base> HEAD origin/main` (3-arg form, git 2.34) previews the conflicts before touching the tree.

**Why:** jhan asked for a plain "rebase and push"; without checks 1-2 the PR would have
shipped a red CI (compile error) and a mangled commit message.
**How to apply:** for every rebase of a reviewed PR: rebase -> message diff vs originals ->
tree diff vs simulated merge -> full build + tests on 3bda -> force-with-lease push.
Related: [[pr3879-split-progress]], [[nfs-attr-cache-build-trap]].

7. (2026-10-05, PR #4557 merge of main) After rsyncing a merged tree to the 3bda worktree, `nix develop` refuses to
   evaluate if main added a file under nix/ that the worktree's git index does not track ("Path 'nix/...' is not
   tracked by Git"); the build steps then silently do nothing and the chain runs stale test binaries. Run
   `git add -A .` in /var/tmp/jhan/tron-issue4525 first (then `git rm -r --cached gen-amxoff gen-avx2 gen-debug`),
   and always require a BUILD-* EXIT line plus fresh binary mtimes before reading test lines.
