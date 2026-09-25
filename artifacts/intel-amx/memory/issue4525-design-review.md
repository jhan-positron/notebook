---
name: issue4525-design-review
description: "2026-09-22: four Claude review rounds of the codex design for issue #4525 (typed KV-cache tensors, parent PR for PR 4424). R1 9 major; R2 4 major; R3 1 major (G01); R4 (third revision, ~20:00 UTC): 71/79 resolved, 8 partly, 0 regressed; 47 new (1 major J01 = draft PR runs no Test host job, CI evidence route unstated), verdict accept with minor edits, implementable now (3/3 judges). Pages + pipelines in VNNIed-K-in-place/issue4525/; traps inside"
metadata:
  type: project
---

jhan (input-2-ai/claude-review-add-tensor-type.md, 2026-09-21 PDT evening) asked: confirm
issue #4525 captures the request(s); review codex's design status/design-new-tensor-type.html;
output status/claude-review-design-new-tensor-type.html. Context: Ben's three PR 4424 comments
(worker index r4065141577; typed tensors review 5270587330; API sketch 5765866077 with the
reservation about a separate k_vnni_layout). jhan renamed the issue at 00:10 UTC 09-22
("independent from PR #4424", was "before").

ROUND 1 (2026-09-22 ~03:00 UTC, original design 67,216 bytes): issue captures the request; jhan's
reading of Ben is right; accept with changes, 0 blocker / 9 major / 36 minor / 13 notes (58 kept,
10 rejected). Page archived as status/claude-review-design-new-tensor-type-r1.html (+ -r1-votes);
data in evidence/claude-review/.

ROUND 2 (2026-09-22 04:00-06:20 UTC, codex revision 83,567 bytes, sha ead80325...): jhan asked
"review again and re-generate" the same page. Result: 35 resolved / 20 partly / 3 deferred
(issue-body edits F19-F21, jhan's), 0 unresolved, 0 regressed. 64 new findings: 4 major
(N01 8-lane guidance orders packed bodies + test runs where t_llama_unit/t_heterogeneous_scheduler
do not compile at unmodified main (set_v/get_v exist only under TRON_CHUNK_SIZE==16); N02
TRON_IGNORE_NAN is ON in every non-Debug build (PUBLIC option, src/tron/CMakeLists.txt:292-295) so
the design's NaN rule is Debug-only and test bits are build-dependent; N03 child table never
switches detail::kv_block's K member to k_vnni_tensor under layout_on (child still reinterpret_casts
the array at kv_cache.hpp:1692/1706/1730/1742); N04 definition of done needs recorded reviewer
answers but no record place/fallback), 38 minor, 22 notes. 3 judges: accept with changes, not
yet implementable; questions block misses native-K typing (jhan's request, N08). Page =
status/claude-review-design-new-tensor-type.html (537 KB, 10 sections; anchors for every F/C id);
votes page 1.5 MB. Pipeline: evidence/claude-review-r2/ (workflow-result.json, findings.json,
build_findings.py, gen_review.py, overrides.json, lead-verified-facts-r2.md, r1-findings-compact.md,
design-revised-text.txt). Workflow wf_5a245030-66d: 268 agents, 29.7M tokens, 1h51m.

ROUND 3 (2026-09-22 ~07:00-09:30 UTC, second codex revision 121,774 bytes, sha 5dea1702, finalized 06:24 UTC): jhan
asked again to "review again and re-generate" the same page. 87 open items = 64 round-2 findings + 23 round-1 residuals, in 17
batches x (checker + source/fairness re-graders): 60 resolved / 25 partly / 2 deferred (F20, F21) / 0 unresolved / 0 regressed;
lead lowered M04 to partly (G19: for_each_active_slot visits logical slots). 10 finders + 19 checker new-defects -> 52 merged ->
3 refuters each -> 50 + 4 critic (H..) survived; lead dropped H04 (dup of G18) and G52 (positive check), regraded 9. Final:
52 new findings = 1 major (G01: design deleted the round-2 sentence keeping scaled_v_expr in kv_cache.hpp while forbidding
cache callers to use detail::v_vnni_access; all 3 judges' must-fix), 27 minor (G22 t_amx_numerics PV fixture route, G09
static_assert not requires-clause, G04 D5 "existing alias", G06/G07 issue-text block replaces Scope bullets / no checklist,
G17/G16 header homes, regressions G29/G30/G34/G28/G21/G15/G08, process H01 lint-notes, H02 format-haskell, G24/G25/G26/G49),
24 notes. Judges: implementer implementable now; maintainer + risk not yet. Verdict accept with changes. New ids this round
G.. (finders) H.. (critic) because the design links N../M.. to the live page; the r3 page keeps every N/M/F/C id as a
disposition-row anchor (checked: all 64 design links resolve). Round-2 page archived as -r2.html / -r2-votes.html with links
rewired (sed). Pipeline: evidence/claude-review-r3/ (workflow-result[-inner].json, findings.json, build_findings.py,
gen_review.py, overrides.json, lead-verified-facts-r3.md, batches/, design-round3-text.txt, design-r2-to-r3-wdiff.txt).
Workflow wf_457a1e23-11d: 234 agents, 28.2M tokens, 2h15m. Live main at review time 1400fa4481 (none of the design's
files changed since 2880c3aa9b); issue #4525 and PR 4424 unchanged.

ROUND 4 (2026-09-22 17:00-20:10 UTC; third codex revision 168,971 bytes, sha d2e9dabf, finalized 16:43 UTC): DONE. 79 open items (52
round-3 G/H + 27 round-3 partly/deferred) in 17 batches: 71 resolved / 8 partly (G15 G35 G17 H01 G46 G41 by majority; N11 and G08 lowered
by the lead) / 0 deferred / 0 unresolved / 0 regressed. 10 finders + 16 checker defects -> 46 merged (0 dropped) + 4 critic -> 47 survived,
3 rejected (J29 include already visible via model.hpp->self_attention.hpp; J33 both readings pass; J38 drift line needs -v). Lead regraded
5 to note (J08 J11 J13 J14 L01), dropped none. Final: 1 major (J01: GCP Nix product jobs are draft-gated (gcp-nix.yml:168-171, 294-297,
382-385), so a draft parent has no Test host job, the design forbids Run CI without direction, and names no route (promote to ready for
review, permitted for the PR based on main; user-directed label; user-directed rerun; gh workflow run = separate evidence); J36: 0 of ~31-41
recent Test host jobs ran on delphi-3bda-0, so the :504 log fallback is the usual case), 11 minor (J02 J03 J04 J05 J06 J07 J09 J10 J12 J15
L02), 35 notes. J09 = the design's ":270 model source has dma = false" is WRONG: production V buffer is hardware::btensor = dmatensor<bf16>
(dma = true, dmatensor.hpp:173); only the host executor's tensor is false; MY facts-r4 endorsed the wrong value (copied from the round-3 G41
lead note) and is corrected in a CORRECTIONS block; also :819/:1575 are the bf16 get_v callers, :2038 is float. Judges: 3 x "accept with
minor edits", implementable now, record adequate; must-fix J01 (implementer, risk). Verdict accept with minor edits. New id prefixes J.. / L..
Pipeline: evidence/claude-review-r4/ (build_inputs.py, make_overrides.py -> overrides.json, build_findings.py, gen_review.py,
workflow-result[-inner].json, findings.json, batches/, lead-verified-facts-r4.md, r3-findings.md, design-round4-text.txt, wdiff). Workflow
wf_1f0aef78-f49: 216 agents, 26.3M tokens, 2h07m. Page 608 KB (241 ids: 79 dispo rows + 60 r3-resolved + 35 r2-resolved + 20 rejected +
47 J/L + 3 rejected J), votes 1.37 MB; round-3 pages archived as -r3.html / -r3-votes.html (links rewired) before regeneration; the design
links 75 distinct ids (77 hrefs) on the live page, all kept (gen_review asserts). Live main 0a51385e95 (model.hpp +1 line at 891).

**Why:** codex may revise a third time from this page; jhan may ask for round 4.
**How to apply:** for another round (round 5 would grade 47 J/L + 8 partly = 55 items), rerun the r4 workflow shape (build_inputs.py BATCHES -> batches; make_overrides.py for prose; new id prefixes, e.g. P../R..); archive the live pages as -r4.html/-r4-votes.html FIRST (sed rewire); r4 shape = r3 shape (batches x checker+2 re-graders, 10 finders incl. regression-diff and section-9 audit, merge, 3 refuters, critic, 3 judges); r2 shape was (dispo batches x checker+2 re-graders,
8 finders, merge, 3 refuters, critic, 3 judges); update facts-r2 first (ls-remote main; gh issue/PR).
Traps: (1) the design links "[Fnn]" to claude-review-design-new-tensor-type.html#Fnn -> the review
page MUST keep an anchor per round-1 id (section 3 rows) or codex's links break; (2) the Workflow
tool's output file wraps the script's return in {summary, result, ...}; use ['result']; (3) putting
all disposition vote reasons inline made the page 957 KB; move them to the votes page (dispo-Fnn
anchors); (4) no chromium/playwright on claude-box: structural checks only (ASCII, anchors, links);
(5) verifiers narrowed several finder claims (N12 "factual error" was an omission; N01 alone is
minor, major only with M01/N61) -> always read votes before grading; (7) round-4: a lead facts-file sentence seeded a wrong "RIGHT" (dma=false) -> never copy a prior lead note as a fact; re-derive types from source (executor -> BTensor -> dmatensor::dma); (8) the design links G/H + 23 F/C ids to the LIVE page: keep anchors for every id ever issued. (6) round-1 recommendation
text carried a suggestion (copy_plane, F13) that its own verifiers withdrew and codex implemented
it -> put verifier corrections INTO the recommendation text next time.
See [[vnnied-k-in-place-project]], [[pr4424-description-on-github]], [[no-names-in-github-issues]].
