# Review context for systems_test PR #221 (read fully before reviewing)

## What is being reviewed
- Repo: positron-ai/systems_test (the nightly system-CI harness). PR #221 by Rhys,
  title "Add 32-user, 4096-token Llama 8B performance benchmark".
- Local clone at the PR head: /home/jhan/workspace/ai-runs/systems_test-pr221
  (branch pr221, head 4022d3ef11efe9b99b1ef871a0983892a6dd4868). Base commit
  (merge base with main): e4727d52127113ab6359bf1bf7a2076d4129be56. Use
  `git -C /home/jhan/workspace/ai-runs/systems_test-pr221 show e4727d5:<path>`
  to read base versions and `git -C ... diff e4727d5 pr221 -- <path>` for diffs.
- Code diff without the two large JSON data files:
  /tmp/claude-0/-home-jhan-workspace-intel-AMX-CI-test/008e4377-f128-449a-a5d4-19d794f55499/scratchpad/pr221/code.diff
- Full diff (13.7 MB, includes the data files): same folder, full.diff.
- A venv exists in the clone: `.venv/bin/python`; run tests with
  `cd /home/jhan/workspace/ai-runs/systems_test-pr221 && uv run --offline pytest tests/ -q`.
  Do NOT modify tracked files in the clone; if you need to experiment, copy files to
  your own scratch folder.
- Do NOT run anything against delphi-3bda or any DUT. This is a code review only.

## Files changed (code)
pyproject.toml (+2), scripts/perf.py (+16), testlib/prompt.py (+41/-12),
testlib/results.py (+11/-3), testlib/tps.py (+31/-7), tests/test_perf.py (+19),
tests/test_prompt.py (new, 129), tests/test_results_v2.py (+32), tests/test_tps.py (+137/-1).
Data: testlib/sharegpt_1000.json (1000 -> 1320 records; the first 1000 unchanged, byte-order
preserved), testlib/sharegpt_long_manifest.json (new; provenance of the 320 appended records).

## What jhan (the requester) actually asked Rhys for (Slack DM 2026-09-21 09:57 PDT)
1. Add llama-3.1-8b-instruct-good-tp2 at 32 users (8 per engine behind Caddy), prompt
   length 4096, 1536 generated tokens to system CI. "Today's llama-8b row with 4x the
   users and 4x the prompt." It ran about 11 minutes in jhan's own measurement.
2. No extra provisioning when it sits directly after the existing llama-8b entry.
3. Sequencing: add the test first; after at least a day, merge tron PR #4505 (which
   turns on the AMX kernel in the tron .deb). This lets the nightly show the AMX effect.
4. A label, "something like AMX benchmark", so the CI (Slack) item looks like
   `llama-3.1-8b-instruct-good-tp2 @8u per machine, AMX benchmark`.
jhan did NOT ask for thresholds in the Slack message. (An earlier internal draft had
proposed thresholds 5 % below the AMX values: get_goal tps 30.6 / min_tps 30.0, YAML
average_tps 30.6 / p05_tps 30.3, and a platform-gating decision, but that draft was not
what was sent.) Rhys's PR says the row "displays as informational until a threshold is
available".

## Facts already verified by the lead reviewer (do not re-derive; you may cite them)
- Unit tests: 1622 passed (uv run pytest tests/), ruff check on the changed files: clean,
  `git diff --check`: clean. PR CI (lint, unit_test, Cursor Bugbot, Graphite) all pass.
- Real-tokenizer check (all 13 configs of scripts/perf.py, cached HF tokenizers,
  transformers 5.15.0): for EVERY pre-existing config, PromptGenerator.generate at the PR
  head returns byte-identical prompts to the base code for every seed the nightly uses
  (seeds 0 .. n_users*10-1). For the new 4096 row: 332 eligible records (12 original +
  320 appended), 320 distinct prompts for seeds 0..319 after removing the timestamp
  line, re-encoded token totals exactly 4096, no NUL bytes. With the base code 315 of
  the 320 seeds would have raised "Prompt length ... too short".
- prepare() (the new eligibility scan) costs 2-6 s per config at start (about 40 s more
  per nightly in total).
- Dataset: 15 content-duplicate pairs exist, ALL within the original 1000 records
  (pre-existing, not introduced by the PR). One appended record (index 1186, id
  3DGOV17) contains 3 NUL characters in a human turn; the PR strips NULs before token
  counting because the inference server rejects them (HTTP 400).
- Seeds: tps.py passes seed = round_index * n_users + index, so 32 users x 10 rounds
  gives seeds 0..319, contiguous.
- Nightly durations: granite (delphi-3bda) runs 03:30 UTC, about 9.5 h of an 11 h
  timeout; genoa (AMD, no AMX) runs 03:00 UTC, about 9.5 h of a 12 h timeout. The
  configs list has no platform gate, so the genoa nightly will also run the new row
  (about 13 min there, est.). The new cell measured 10.6 min (AMX) / 13.1 min (no AMX)
  on delphi-3bda in jhan's campaign.
- Precedents in the base code: the configs list already has two entries with the same
  "name" (llama_3_3_70b_instruct_good_tp2 at 8 and 4 users); results are keyed by
  (model, nominal_users). ingested-gemma-4-31b-it-tp2 has a placeholder 1.00 in get_goal
  and NO YAML row, so the YAML comparison report is already marked incomplete every night
  by a "performance threshold unavailable" warning; the new row adds the same kind of
  warning (suppressed as a line when mean TPS exists, but still sets incomplete=True).
- KNOWN and DECIDED (do not raise as a finding): the deployed llama-3.1-8b weights on
  delphi-3bda carry a tokenizer.json with truncation max_length 4096, so the server
  silently truncates prompts above 4096 tokens. jhan decided on 2026-09-19 to do nothing
  about it. The new row's prompts are exactly 4096 tokens before the chat template, so
  the server sees exactly 4096 after truncation of the template overhead. Not a PR issue.
- The PR body says the full 32-user benchmark was NOT rerun after the last commit
  (NUL fix + worker error handling); only the failing round-7 prompt was replayed.

## Repo conventions (systems_test CLAUDE.md)
- Medium/High severity fixes need a regression test that fails before and passes after.
- Any code change must keep docs accurate (docstrings, comments, README, workflow docs).
- Tests in tests/, pytest; lint with ruff; 4-space indent, 88-char max line length
  (ruff passes, so long lines are not lint failures; the base code has many long lines).
- diff-cover threshold 70 % of new/changed lines.

## Base-code behaviour worth knowing (testlib/tps.py at e4727d5)
- benchmark_tps builds n_users Worker objects (global list `workers`), runs
  run_tps_worker(index) in a ProcessPoolExecutor(max_workers=n_users) (fork start
  method on Linux), synchronises rounds with per-worker ingress/egress Queues, and drains
  a shared group_queue until every worker's final sample of the round has arrived.
- Worker.sync polls egress with timeout 1 and re-raises the future's exception.
- Known trap from jhan's campaigns: after a failed cell the ProcessPool workers blocked
  forever (the PR's None sentinel + cancel_join_thread target this).
- concurrent.futures.process pickles a worker exception as _ExceptionWithTraceback;
  in the parent the rebuilt exception's __cause__ is a _RemoteTraceback holding the
  worker's formatted traceback text (which includes chained causes as text). The base
  code's `raise exc from None` discarded that; the PR uses `raise exc from exc.__cause__`.
  openai SDK APIStatusError subclasses cannot be unpickled (constructor needs response),
  which turned worker API failures into BrokenProcessPool before the PR.

## Output expectations
Report only findings you can tie to a specific line of the diff or a specific verified
behaviour, with the concrete failure scenario. Severity scale: blocker (breaks the
nightly or produces wrong numbers), major (wrong behaviour in a realistic path, or a
clear deviation from what jhan asked), minor (quality/clarity), nit. Also report
explicitly "checked and fine" items so the lead can see coverage. Plain English: define
project terms at first use, one claim per sentence.

## Merge state
- PR base e4727d5 is one merge behind main (62c45e3 = PR #220, threshold YAML changes
  only). A trial merge of pr221 onto origin/main is CLEAN (verified by the lead).
- ruff ignores E501 (line length), so long lines are not lint failures in this repo.
