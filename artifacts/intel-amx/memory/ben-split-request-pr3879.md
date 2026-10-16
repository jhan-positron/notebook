---
name: ben-split-request-pr3879
description: "2026-09-04 Ben asked to split PR3879 in the order counters -> AMX kernel without mirror -> K mirror (DM 13:28 PDT), plus topical commits; CHANGES_REQUESTED w/ 10 inline comments; response doc PR3879/response-Ben-breaking-up-PR.md follows his order (3-PR stack)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 42803215-f20d-4e0a-8810-8dea42380d02
  modified: 2026-09-05T00:14:25.429Z
---

On 2026-09-04 Ben Gamari (bgamari-positron, requested reviewer) posted in #intel-amx that
PR3879 is a "2.5kLoC monolith", named two cut points (AMX kernel vs K mirror; page-share
instrumentation) and at 11:58 PDT asked to "squash and rebuild the history with a slightly
more topical structure". He also submitted CHANGES_REQUESTED (11:56 PDT, 10 inline comments:
7 on kernel/dispatch lines, 2 on page_share_counters.hpp, 1 on pre-existing kv_cache.hpp:487)
asking for a shape-specific kernel namespace and the name `amx_k_mirror`. jhan replied on
Slack at 12:00 "looking into separating it to individual concerns", then asked Ben by DM
(13:24) to write down what he had proposed in the gpt-oss meeting. Ben's DM (13:28 PDT,
D0B7WC0FZLY): "First introduce the page sharing counters / Then introduce the AMX kernel
without the K mirror / Then introduce the K mirror". That order is the operative request.
Wade posted a Claude agent review the same morning (issuecomment-5544513215): blocking = no
CI on head, AGENTS.md test policy, ungoverned mirror arena RAM; should-fix = move
page_share_counters.hpp out of tree (conflicts with Ben's counters-first PR; the doc resolves
it by giving PR 0 a CMake option + small host test + purpose statement).

Verified facts used in the response (PR3879/response-Ben-breaking-up-PR.md, has a
"Context for a reviewer" block at top because jhan will have another agent review it):
- Concern map (non-blank added lines, hunk-verified): mirror 600 code + 572 tests (49%),
  kernel 347 + 156, dispatch 242 + 306, page-share 101, build 28, shared test lines 42.
- Dependencies: dispatch -> kernel; mirror -> dispatch (kv_cache.hpp #error); nothing depends
  on the mirror; page-share is fully independent (hooks anchor on main-unchanged lines).
  Mirror kernel = amx_attn.cpp lines 43, 232-269 + header mirror section.
- Rebase onto main: 4 files with real conflicts; only scheduler/full.hpp is semantic
  (main's try_create_book_with_retry, commit 9076993a); main also requires
  llm_configuration::attention_scale (two new test configs need it).
- CI test pool has 3 Granite Rapids AMX runners (delphi-17cf, 3bd6, 3bda); issue #3997's
  "no CI host has AMX" is out of date; option 1 = -DTRON_AMX_DISPATCH=ON at
  cmake-single-platform.yml:365.
- Repo norms: merged-PR median +105 lines, p95 1798; Ben's own stacked PRs median +112;
  AGENTS.md supports stacks (descendants stay draft); Bill's AMX PR #2934 (+2911) has had
  no human review since June with Ben as sole requested reviewer.

Recommendation given: 3-PR stack in Ben's order by subtraction from the rebased tree:
PR0 counters (~101 lines + CMake option + host test, base main); PR1 = #3879 retitled,
kernel+dispatch+build+tests ~1,050 lines in topical commits, carries the CI flag (base main
recommended so PR0 does not gate it; decision open); PR2 draft mirror ~1,185 lines stacked
on PR1 with the amx_k_mirror rename. Park t_amx_logit_ab (DISABLED test violates AGENTS.md).
Open decisions for jhan in section 10 of the doc. Status: doc written, nothing posted, no
split performed.

**How to apply:** before any split work, re-read the doc's section 9 steps and section 10
decisions; check #intel-amx, the DM with Ben, and the PR for newer messages; keep the
"mirror" lineage note ([[mirror-naming-convention]]); use [[debug-code-new-branch]]
(jhan-dd-debug) for the parked logit tool. Related: [[amx-tron-softattn-project]],
[[more-testing-round1]], [[jeremy-comments-replies]].
