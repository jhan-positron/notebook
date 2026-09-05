# Handoff: token-30 / step-22 AMX numerics investigation

Written 2026-08-30 by the session that ran the campaign. Audience: the next agent (or person)
taking this further. Read the two pages first; this file adds state, machine rules, and the
open work items with exact starting points.

**Short version.** An AMX-off vs AMX-on greedy run of qwen on delphi-3bda picks a different
word at one step; the campaign showed that step is an exact bf16 tie in the AMX-off scores,
that a non-AMX perturbation flips it identically, and that no test found an AMX defect.
Open: prove-or-refute work that testing so far cannot see (same-input replay, ON/ON repeat,
page-id trace), the unresolved 2026-08-18 event, and instrumentation fixes.

## Reading list (in order)

1. `definitive-decode/index.html` - how to make two runtron runs comparable at all
   (flags, traps, per-layer data). The glossary there defines every term used here.
2. `definitive-decode/debug-plan.html` - the executed plan v2: hypotheses H0-H6,
   decision tree, run matrix R1-R9, predeclared thresholds.
3. `definitive-decode/token30-results.html` - results, plain-English conclusions,
   response to codex's review, technical verdict. Regenerate it any time with:
   `python3 exec/dd/dd_report.py --res exec/results/dd --out definitive-decode/token30-results.html --mark 22`
4. `definitive-decode/codex-review/review.html` - codex's independent review of the plan;
   the results page answers it point by point. Its still-open demands are work items below.
5. Auto-memory (loaded each session): `token30-campaign`, `runtron-determinism-recipe`,
   `debug-code-new-branch`, `plain-english-default`.

## Established (do not re-derive)

- Verdict: the step-22 word change (today's build) is an exact bf16 tie (margin 0.0000)
  broken one way by AMX-off (lower id wins ties) and the other way by any one-notch
  perturbation; the add-order control (AMX off, two fewer cores) flips it identically.
  No test found an AMX defect. Evidence table: results page, "What we found, and how".
- Gates that held: A/A OFF/OFF byte-identical outside the broken `Attn out` label
  (0 of 304,176 records); forced replay exact; forced-vs-free ON agree at the flip;
  mirror build == canonical build (0 of 304,176); kernel tests 6158/6414/6157 assertions,
  none skipped; engagement counters ON 9.4M-11.3M work items, OFF 0.
- Historical 2026-08-18 step-30 event: unresolved. Its binary (sha 787342cf...) is gone;
  today's build AND the preserved `tron-amx/gen/runtron.inc1b` both produce a different AMX-off sequence
  from the archived logs starting at token 4, while agreeing with each other exactly
  (`exec/results/dd/inc1b/`). Suspects: weights/tokenizer/machine state of that day, or
  code older than inc1b.
- Numbers you will want: flip steps under forcing = 22 (0 ulp), 37 (0 ulp), 145 (3 ulp,
  pair moved 6 ulp); non-flip pair movement median 1 ulp, p95 4 ulp (256 steps); mean
  |delta| over the vocabulary: median 0.031, p95 0.066 (64 steps); truncation build ratio
  0.89; WO per-record relative change on the prompt: control 0.0165 vs AMX 0.0162 (median).
  Note on the pair-movement units: 1 ulp median / 4 ulp p95 are computed per step in that
  step's notch size (steps-r4x.json rows); the absolute p95 is 0.75. The 64-step statistics
  on the results page (median 0, p95 1 notch) are a different population - do not mix them.
- Source-level split (answered 2026-08-30, from existing logs; results page section
  "rounding vs addition order"): at the cascade-free seam (WO layer 0, tokens 128-2047),
  rounding only = median relative change 0.00222 (100% of values), addition order only =
  0.00007 (32%), both = 0.00222, non-AMX control = 0.00202. Rounding dominates locally
  (~30x); downstream both saturate. Point (b) of the results-page Q&A is thereby answered;
  no separate work item remains for it.

## Machines, repos, rules (must follow)

- Machine: delphi-3bda only (user rule). CI holds it nightly: busy only if
  `/run/lock/systems-test-ci.lease` exists AND state=="busy" AND now < expires_at_epoch.
  Before ANY runtron launch: `source ~/workspace/intel-AMX/exec/lib-guard.sh` then
  `campaign_guard_acquire || stop`; re-check `ci_took_dut` between runs; release with a trap.
  Rinzler policy: after CI, stop leftover rinzler@{0..3} ONLY when idle for 10 min
  (SYSTEM_STATS lines all `Open=0 ... Busy=0` AND `sudo -n ss` shows 0 established
  connections on :13000-13003); never start them back. Builds while the machine is busy:
  `nice -n19 taskset -c 23,24,36,167,168,180` with `-j6`.
- Repos (NFS-shared alpha <-> 3bda; build only on 3bda inside `nix develop`):
  - `~/workspace/tron-amx` = branch `jhan-amx-p0` = PR #3879. NEVER put debug code here
    (user directive 2026-08-30).
  - `~/workspace/tron-dd` = branch `jhan-dd-debug` (commits bd68d5cb50, 2f268298e7):
    engagement counters (`AMX-DEBUG pages_amx=... pages_fallback=... arena_absent=...`
    printed at exit), `TRON_INTERMEDIATES_FILTER=<regex>`, cmake `TRON_AMX_PV_TRUNC`,
    the broken `Attn out` label (see work item 3). Not pushed.
  - Binaries in `tron-dd/gen/`: `runtron.canon` (043d7bb5...), `runtron.mirror`
    (d56f459e...), `runtron.trunc` (cc99ff5b...), plus `t_amx_numerics.{canon,mirror,trunc}`
    and `t_amx_logit_ab`. All contain the qwen model. `tron-amx/gen/runtron` (99ea7a06)
    does NOT (BUILD_INGEST_MODELS=OFF) - do not use it for qwen.
  - Build recipe: `cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON
    -DTRON_AMX_DISPATCH=ON -DCMAKE_CXX_FLAGS= [-DTRON_AMX_K_MIRROR=ON|-DTRON_AMX_PV_TRUNC=ON]`.
    A fresh worktree needs `cp -r ~/workspace/tron-amx/ingest/traces ingest/` first
    (git-ignored; plain cp, not cp -a).
- Scripts: `exec/dd/` - `dd-campaign-v3.sh` (the corrected campaign; v2 = `dd-campaign.sh`, what actually ran),
  `dd-inc1b-check.sh`, `dd-phase3-hf.sh` (r8/r9, untested end to end), analysis:
  `dd_tokens.py`, `dd_logits_step.py`, `dd_first_divergence.py`, `dd_bin_score.py`,
  `dd_report.py` (`--ignore-labels "Attn out"` is the default). All tested except dd-phase3-hf.
- Data: summaries `exec/results/dd/` (JSON per comparison; `campaign.txt` is the full run
  log; `verdict.html` + `codex-response.html` are included into the results page).
  Raw runs (12 GB logs etc., 69 GB total) on 3bda local disk `/var/tmp/jhan/dd/` - safe to
  delete after archiving anything you need.
- Standard run flags (one prompt; NEVER add `-u` next to a token file - `-u N` APPENDS
  N Moby Dick prompts): `stream-generate-text -m ingested-qwen-3-4b-instruct-2507-tp2
  --instance 0,4 --devices 10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59
  --dev-cores 3,4 --numa 0 --hugepage_file /dev/hugepages/dd --nr_hugepages 128 -o
  --temperature 0 --pay-for-determinism -u 1 --prompt-length 2048`, env `USE_HW_ATTN=0`,
  arm via `TRON_AMX_DISABLE=1` (exact string) vs unset. The archived 2026-08-18 runs and
  the inc1b check also passed `-s 42` (inert at temperature 0, but include it when
  reproducing them, e.g. for work item 6).

## Open work items (highest value first)

1. **Same-input replay at the flip's attention call** (codex C2; closes the "admissible
   numerics" gap). Goal: show the AMX kernel output for the REAL tensors at step 22 is
   within a declared bound of an fp64 reference, or find it is not. Method: on jhan-dd-debug,
   add a one-shot dump in `apply_page_tok` (self_attention.hpp ~1560) gated by env
   (e.g. TRON_AMX_DUMP_CALL="token,layer,page"): write Q-pack, K page, V page, exp rows to
   files; then extend `t/t_amx_numerics.cpp` with a mode that loads those files and runs
   kernel-vs-fp64-reference (the envelope logic is already there, lines ~255-295).
   Decision rule: outside `1e-4 x abs product mass + 1e-6` per element = defect; inside = gap
   closed. Cost: one code change + one forced ON run + one test run.
2. **ON/ON repeat of one binary** (codex C4). Two forced ON runs with `runtron.canon`,
   compare with `dd_first_divergence.py --threshold 0`; expect 0 outside `Attn out`.
   ~30 min including the guard dance. Add it to dd-campaign-v3.sh afterwards.
3. **Fix the `Attn out` label** (instrumentation bug). Symptom: differs between identical
   OFF runs while WO (computed from it) is identical. Current placement: after
   `attn_done_barrier` reading `output[ix]` (self_attention.hpp, commit 2f268298e7).
   Suspect: `output` is a channel buffer already released/reused after
   `output_channel.finish_writing` + `post_attention()`. Try logging inside `run_joins`
   per kv-head slice (each worker logs the slice it wrote, before finish_writing), or copy
   the vector to a scratch before the barrier. Verify with an OFF/OFF pair: 0 differing
   `Attn out` records = fixed.
4. **Page-id trace** (codex C3/H4 hardening). Replace the aggregate counters with a
   per-(token, layer) record of dispatched page ids for one chosen layer (env-gated),
   assert against the expected set (all complete 64-token pages from earlier passes).
   Positive discriminator for/against dispatch bugs.
5. **HF arbiter with exact ids** (quality-regression measurement, not tie arbitration).
   Fix Phase 1c: `nix develop --command python3 bin/tokenize_py ...` prints the nix banner
   on stdout - take the LAST line of stdout as the JSON. Then `exec/dd/dd-phase3-hf.sh r8`
   (round-trip id check is built in; needs `$D/prompt.ids` and `$D/forced.tok`; prompt.ids
   does NOT exist yet - the fixed Phase 1c must be rerun on 3bda first to create it). Compare
   per-step TVD OFF-vs-HF and ON-vs-HF; "equal" = the per-step TVD distributions of the two
   arms overlap with no predeclared-threshold excess (declare the threshold before running).
   Prior record: max TVD 0.7139 both arms, argmax agreement 126/148 both
   (rampup/04-amx-action-plan.html:311; also exec/QUEUE.md row 14).
6. **Historical 2026-08-18 event** (only if jhan wants it). Paths: (a) `git reflog` /
   `git log --all` in tron-amx on 3bda for the pre-squash commits around 2026-08-18 22:41Z,
   rebuild, rerun `exec/t1-quick.sh` flags; (b) check weights/tokenizer file mtimes under
   the model weights dir vs that date (find the dir with
   `grep -iE "weights|model path" /var/tmp/jhan/dd/r1a.log` on 3bda; the HF-side copy is
   `~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507`). If (a) reproduces
   step 30, diff builds; else declare
   environmental and close.
7. **Fail-closed campaign marker** (codex C8). dd-campaign-v3.sh: make the final `ok`
   depend on: A/A values == 0 (outside ignored labels), engagement ON>0/OFF==0, all rc==0,
   kernel tests parsed with assertions>0 and no "skipped". Currently only run-completeness
   and A/A tokens stop it.
8. **Optional breadth**: more prompts / ctx lengths for tie statistics; the same ladder on
   llama-3.1-8b (has goldens; also head 128 / kv_mul 4); mixtral-8x7b for the MoE variant
   (expert-flip reading: `WFF1 expert {e}` keys, see the MoE section of
   `definitive-decode/index.html`). Needs decisions from jhan first: model list, prompts,
   run flags per model (the flag set above is qwen-tp2-specific); geometry starting points
   in exec/QUEUE.md rows 17-18.

## Traps that already bit once (do not rediscover)

- `-u N` appends N Moby Dick prompt files; it never limits users.
- `nix develop --command` prints a banner on stdout: never parse a command's stdout run
  that way without stripping it.
- `ctest` hides Catch2 WARN/skip lines of passing tests: run test binaries directly and
  parse "All tests passed (N assertions".
- `--intermediates-file` is DELETED and recreated at model construction (help text says
  "append"); one distinct path per run; compare by 50-char key, never by diff;
  the generated plugin's plain `WQ`/`WK` labels are duplicated 32x/8x per (token, layer) -
  use the shared labels (WQ roped, WK roped, WV, WO) or add head indices first.
- `extract_logits` writes tokens AND logits as bare sha256 filenames; parse the
  "Saved tokens to:"/"Saved logits to:" stdout lines; `--max-tokens` (default 40) truncates;
  `--max-layers` defaults to 2.
- Test binaries (t_amx_*) take instance/cores/hugepages from the `SYSTEM_CONFIG` env string,
  not flags. Hugepage files are `/dev/hugepages/slice-*-of-8`; remove only after `fuser`.
- Logits and activations are bf16; text logs print them exactly at 8 significant digits on
  tp executors; every delta is a whole number of ulps (ulp = 2^(floor(log2 x) - 7)).
- The console's generated text is green ANSI chunks; extract with
  `\x1b\[38;2;000;128;000m(.*?)\x1b\[0m`, never by line filtering.
- First AMX-affected token with a 2048-token prompt and 128-token prefill chunks is
  token 128 (pages filled in the same pass are not dense-dispatched) - not 63.

## Style requirement for anything you write

Plain English always, per `~/.claude/CLAUDE.md` (# English): define every project term at
first use, one claim per sentence (test -> observation -> meaning), numbers with units and
plain meaning, citations after the sentence, a 3-sentence "Short version" first. Project
term list: `~/workspace/intel-AMX/CLAUDE.md`.
