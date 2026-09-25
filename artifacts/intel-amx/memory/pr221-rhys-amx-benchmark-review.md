---
name: pr221-rhys-amx-benchmark-review
description: "2026-09-21/22 review of systems_test PR #221 (Rhys, 'Add 32-user, 4096-token Llama 8B performance benchmark' = the AMX benchmark row jhan asked for in Slack 09-21 09:57 PDT): verdict ACCEPTABLE, no review file written (jhan's rule: do nothing if good); 3 optional nits kept here; verified facts about the PR's prompt-selection redesign and Slack rendering"
metadata: 
  node_type: memory
  type: project
  originSessionId: 008e4377-f128-449a-a5d4-19d794f55499
  modified: 2026-09-22T01:04:09.513Z
---

PR: https://github.com/positron-ai/systems_test/pull/221, head 4022d3ef (4 commits), base e4727d5, merges clean onto
main 62c45e3. Review clone: ~/workspace/ai-runs/systems_test-pr221 (branch pr221, own .venv; pytest scratch dirs inside).
Review artefacts: session scratchpad pr221/ (context.md, code.diff, findings.txt, verify_prompts.py). Workflow wf_415124ce-e06
(6 finders, 24 findings, 72 refuter votes): 21 refuted, 3 survive as nit/minor.

What jhan asked (Slack DM to Rhys 2026-09-21 09:57 PDT, NOT the section-9 draft of CI-test/status/llama-3.1-8b.html): the
row llama-3.1-8b-instruct-good-tp2 @ 32 users, prompt 4096, gen 1536; directly after the existing llama-8b entry (no
re-provision); label "AMX benchmark"; sequencing = merge this test first, merge tron PR #4505 (deb preset AMX ON) at least a
day later. No thresholds and no platform gating were requested. The PR meets all four items.

Rhys's design differs from our concatenation patch (exec/l8b-levers-20260919/prompt.py.patch): he APPENDED 320 long ShareGPT
records to testlib/sharegpt_1000.json (now 1320 records; first 1000 byte-identical) with a provenance manifest
testlib/sharegpt_long_manifest.json, and PromptGenerator.prepare() builds an eligible pool (332 records at 4096 = 12 originals +
320 appended) in the parent before the fork; generate() picks eligible[seed % len]. Verified with the real cached tokenizers:
every pre-existing row's prompts are byte-identical to the base code for every nightly seed; the 4096 row gives 320 distinct
prompts, exactly 4096 tokens, no NUL. prepare() adds 2-6 s per config. tps.py: worker openai errors wrapped in RuntimeError
(SDK exceptions cannot unpickle -> BrokenProcessPool before), None sentinel + cancel_join_thread fix the post-failure worker
hang we hit in our campaigns. results.py: a labelled row without threshold shows as
`:memo: llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): N TPS` in BOTH Slack reports, verdict unchanged.

Optional nits NOT posted (jhan can ask for status/review-Rhys-PR.md): (1) a crashed run of the labelled row renders as
`:memo: ... 0.0 TPS` under PASSED in the enforced report (base printed nothing; YAML report already did this for gemma-4);
(2) the 3 fork-based tests add the suite's only 3 DeprecationWarnings (OpenBLAS/jemalloc threads; only a filterwarnings entry
removes them); (3) manifest prompt_sha256 of record 3DGOV17 predates the NUL fix (nothing reads the manifest).
FYI items: the genoa (AMD) nightly also runs the row and prints "(AMX benchmark)"; the ratchet cannot CREATE thresholds, so
(model, 32) entries in get_goal and thresholds/system_ci_perf.yaml must be added by hand after AMX nights accumulate
(section 9.4 proposed 30.6 / 30.0 / 30.3); the full 32-user run was not repeated after Rhys's last commit.

**Why:** jhan will compare AMX-off vs AMX-on nights on this row after #4505 merges; these facts explain what the row shows.
**How to apply:** when the row appears in Slack, remember 0.0 TPS = crash, not a measurement; when setting thresholds use
[[l8b-8u4k-20260920-campaign]] numbers. Related: [[ci-enable-20260917-campaign]], [[ci-amx-test-shapes-recommendation]],
[[l8b-levers-20260919-campaign]].
