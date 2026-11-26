---
name: declined-fix-leaves-finding-open
description: "Lesson from tron PR 5022 (analysis of 2026-11-23): when we decline a reviewer's fix, the finding stays open; restate the goal, search the same file for a narrower fix and a sibling precedent, and never pass the point on as 'settled, do not report'"
metadata:
  node_type: memory
  type: project
  originSessionId: 5923dad0-d660-4ecb-a1a6-4f80f4865614
  modified: 2026-11-24T06:26:53.826Z
---

Analysis of 2026-11-23 (this is my conclusion from the record, not a rule that jhan stated).

What happened on tron PR 5022: the gap "the new dispatch test sections run in no required CI lane" was reported five times (our own Wade-code-review check 3A on 2026-10-18, twice; Isaac on 2026-10-23; claude[bot] on 2026-11-20; Isaac on 2026-11-24). The first four reports named one fix: turn `TRON_AMX_DISPATCH` ON in the Nix build. We declined that fix for a good reason and treated the point as closed. The fifth report brought a narrower fix that met our reason: `DEFINES TRON_AMX_DISPATCH` on the one test target, the form of `t_page_share_counters` at `t/CMakeLists.txt:276`, which jhan's own PR 4267 had added on 2026-09-04. That line and its README sentence appeared in our tool output more than 10 times and nobody connected them.

**Why:** we judged the fix that the reviewer named, not the goal behind it. The decision card, the pre-review prompt ("Already decided by the author; do not report these as findings") and the handoff ("Do not reopen") each passed the point on as closed. A blind replay of our five skills on the PR head gave 0 of 13 runs that proposed the per-target define, although 8 of 13 reported the gap.

**How to apply:**
- When a reviewer's fix is declined, write the finding without the fix and mark whether our change closes it.
- Write the reason for declining as a condition on any fix. Then search for a fix that meets it: the same change at a narrower scope (one test target, one file), and the way a sibling in the same file solved it (`grep -n -E 'DEFINES|target_compile_definitions' t/CMakeLists.txt` for tron tests).
- Test every sentence of the form "X needs Y" in a reply draft. "Running the cases in required CI needs the Nix flag" was false for the dispatch test.
- Show jhan the narrower fix together with the reply. This is a code option, not a wording option (see [[review-replies-keep-simple]]).
- In a brief for a pre-review agent, list the declined remedy as decided, not the finding.
- A test that uses fakes and needs only a macro must not sit under `#ifdef <OPTION>` with an `#else` placeholder case. tron's `AGENTS.md` test policy requires a required CI suite to execute every committed test.

Same gap, still open on 2026-11-23: draft PR 5572 (`jhan-gdn-amx`, head 882e5322f1) adds two 256-dim dispatch sections under the same guard, and its registration has no `DEFINES`.

Replay material for testing skill edits: [[skill-replay-harness]]. Related: [[isaac-reviews-are-agent-pipeline]], [[changes-need-system-tests]].
