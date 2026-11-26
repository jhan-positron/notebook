# Measurement scripts for the GDN/AMX split: facts for the handoff

## Short version
- Every shell script of the old campaign runs on delphi-3b35 only and writes into one hard-wired result folder, `gdn-impl-20261121`. Three scripts skip a run whose output file exists, so a campaign over new commits needs a new folder name.
- `build.sh` takes the commit and the model list as parameters. Only its default model list (Qwen3.5 4B) assumes the model's branch. No build of a main-based commit with it is recorded.
- The arm table names the build tags `ctr`, `pa`, `pab`. After the split no commit on the model's branch holds Part B, and Qwen3.5 4B is not registered at PR #5022's head, so the arm table, the cell table and the analysis scripts need edits.

## Words and conventions
- tron = the inference program. runtron = its command-line tool. GDN = GatedDeltaNet. AMX = Intel tile-matrix instructions.
- arm = one build with one set of switches. cell = one user count with one prompt length. tag = name of a build tree `/var/tmp/jhan/b35-gdn-<tag>` on delphi-3b35.
- IMPL = `/home/jhan/workspace/intel-AMX/exec/gdn-impl-20261121`. G20 = `/home/jhan/workspace/intel-AMX/exec/gdn-20261120`. RES = `/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121`. LOGS = `/home/jhan/workspace/intel-AMX/exec/logs`.
- Script line numbers refer to the files on disk as read on 2026-11-22 (these folders are not inside a git repository from this shell; newest edit: `build.sh` and `models.e4b.yaml` 2026-11-22 15:27 PST, `e4b-tests.sh` 15:47 PST). Line numbers of tron files name their commit.
- Every `.sh` below except `build-all.sh` and `load-snapshot.sh` exits unless `hostname` = `delphi-3b35`. The `.py` files have no host check; they read the shared-home paths. The host they ran on is not verified.

## 1. Files: purpose, inputs, outputs, hard-wired values

### IMPL/build.sh (88 lines)
- Purpose: build tron targets at one commit in a tree on 3b35's local disk. Details in section 2.
- Inputs: `TAG` (required), `SHA` (required), `REG` (default `G20/models.gdn.yaml`), `CPUS` (96-135), `JOBS` (36), `CONF_FLAGS` (default `-DTRON_AMX_DISPATCH=ON`), `TARGETS` (default `runtron t_gated_delta_net`) [build.sh:16-31].
- Outputs: `RES/build-$TAG.txt`, `RES/build-$TAG.done`, `LOGS/gdn-impl-20261121-build-$TAG.log` (appended) [build.sh:20-21,36,86].
- Hard-wired: `NAME=gdn-impl-20261121` [19]; tree prefix `/var/tmp/jhan/b35-gdn-` [23]; repository `/home/jhan/workspace/tron` [22]; copied model list is always named `models.gdn.yaml` [30,54]; record counts the literals `TRON_GDN_STATS` and `ingested-qwen-3\.5-4b` [84]; `TAG=base` is refused [39].

### IMPL/build-all.sh (14 lines)
- Purpose: three `build.sh` calls in a row. No host check of its own.
- Inputs: `CTR`, `PA`, `PAB` (commit ids, required), `CPUS` (96-143), `JOBS` (44) [11-13].
- Outputs: `RES/build-all.done` with `ctr=.. pa=.. pab=..` [14].
- Hard-wired: tags `ctr`, `pa`, `pab` [11-13]; target list `runtron t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype t_llama_unit t_tronstats_convention` [10]; result folder [8].

### IMPL/campaign.sh (88 lines)
- Purpose: timed runtron runs, cells x arms x repetitions, each through `G20/run-one.sh`. Tables in section 4.
- Inputs: `CELLS` (all 6), `ARMS` (`base p0 b ab a0 a`), `REPS` (3), `FIRST_REP` (1), `CELLS_ALL` (overridable table) [31-33,43-49].
- Outputs: `RES/rt/<run>.log`, `RES/load/<run>.txt`, `RES/rt-results.txt`, `LOGS/gdn-impl-20261121-campaign.log`, marker `LOGS/gdn-impl-20261121-campaign.done` [22-23,29-30].
- Hard-wired: `NAME` [27]; `STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"` [34]; arm table with tags `ctr pab pa base` and the switches `TRON_AMX_DISABLE=1`, `TRON_AMX_GDN_DISABLE=1` [35-42]; cell table with model slug `ingested-qwen-3.5-4b-tp4` and cell keys `q35-tp4-*` [43-48]; tree prefix `b35-gdn-` [62]. It ends after 3 consecutive failed runs [81].

### IMPL/unit-tests.sh (49 lines)
- Purpose: run the unit-test programs of the build trees and write one table.
- Inputs: `OUT` (`RES/unit-tests.txt`), `TAGS` (`ctr pa pab`), `TESTS` (`t_gated_delta_net t_amx_numerics t_amx_dispatch_dtype t_llama_unit t_tronstats_convention`) [16-18].
- Outputs: `$OUT` (overwritten), `RES/unit/<tag>__<test>__<switch>.txt` [22,49].
- Command per test: `SYSTEM_CONFIG="--instance 1,2" [switch] taskset -c 96-143 ./gen/<test> --skip-benchmarks` [24].
- Hard-wired: result folder [15]; tree prefix [22]; four extra rows always run tag `pab` with `TRON_AMX_DISABLE=1` and `TRON_AMX_GDN_DISABLE=1` [45-48].

### IMPL/token-check.sh (71 lines)
- Purpose: same prompt, temperature 0, compare the generated tokens of each arm with the arm `base`.
- Inputs: `PROMPTS` (`1024 4096`), `LEN` (256), `ARMS` (`orig base p0 a0 a b ab`) [18-19,36]. It passes no `MODEL`, so `run-one.sh` takes its default Qwen slug unless `MODEL` is in the environment [45-47; run-one.sh:24].
- Outputs: `RES/tokens/p<prompt>__<arm>.txt`, `RES/tokens/summary.txt` (overwritten by every call with the prompts and arms of that call) [42,71].
- Hard-wired: `NAME` [15]; `STATS` with `TRON_GDN_STATS=1` [20]; 12-row arm table with tags `base ctr pab pa partb` [21-32]; run name `tok-q35-tp4-1u-p...` [45]; reference arm `base` [55]; an existing token file is skipped [43].

### IMPL/logit-margin.sh (67 lines) and IMPL/logit_summary.py (52 lines)
- See section 5.

### IMPL/collect.py (286 lines)
- Purpose: parse `rt/*.log` (decode rate, time to first token, `[attn-stats]`, `[gdn-stats]`), `load/*.txt`, `rt-results.txt` into one JSON file.
- Inputs: results folder as argument 1 (default RES) [32]; `REPS_RANGE` (`11-19`), `SUFFIX` (empty) [36-37].
- Output: `<folder>/collected<SUFFIX>.json` [259].
- Hard-wired: arm set `{base,p0,b,ab,a0,a,orig,nost}` [35]; session rule by repetition number (1-9, 11-19, 21-29) [16-18]; 128 prompt tokens per prefill pass and the rule `prompt % 128 == 0` [93-109]; run names starting `trace-` or `tok-` are dropped [208]; label text `q35-tp4-` [270].

### IMPL/compare.py (221 lines)
- Purpose: campaign medians against the prediction file, plus the pass rules of the plan.
- Inputs: results folder as argument 1 (default RES) [27]; `SUFFIX` [32].
- Output: `<folder>/comparison<SUFFIX>.json` [190].
- Hard-wired: prediction file `exec/results/gdn-20261120/predictions.json` [28] (it holds the six `q35-tp4-*` cells only, checked with python); `CELLS` list of six `q35-tp4-*` keys [29]; arm-to-scenario map `p0, a, b, ab` [31]; a cell without arm `base` is skipped [70]; `pred["cells"][cell]` is read without a check [73].

### IMPL/report_data.py (401 lines)
- Purpose: one dict with every number of the result page.
- Inputs: none (paths in the file). Output: none (imported by `gen_report.py`, `gen_pr_body.py`).
- Hard-wired: `RES` [21]; `PRED` [23]; `CELLS` [24]; `understand/review-result.json` opened without a check [213]; arm order and arm pairs of the token check [241,250-251]; campaign log path [290]; side runs `q35-tp4-1u-p1024__q-a__rep1` and others [306-307]; score compare with `prompt = 1024` and the files `logits-p1024-l4__base.txt`, `logits-p1024-l190__*.txt` [347-350]; tags `ctr pa pab` [381]; `session_times(11, 19)` [391]; `bench/*.txt` files read by `task1()`, `task3()`, `task4()` [40-197].

### IMPL/gen_report.py (1621 lines) and IMPL/decode_why.py (604 lines)
- Purpose: write `/home/jhan/workspace/intel-AMX/GDN/gdn-amx-results.html`. `decode_why.py` builds section 5 and part of section 3 for it.
- Inputs: output path as argument 1 [gen_report.py:17]. It imports `pagelib` from G20 [13].
- Hard-wired in `gen_report.py`: arm names and labels [79-80,598-602,783-790]; tags `ctr pa pab noamx` [547-548,793]; cell `q35-tp4-1u-p1024` [287,1223]; text naming branch `jhan-gdn-amx`, commit `72e1191804`, PR #5572, PR #3696, `TRON_GDN_STATS`, `TRON_AMX_GDN_DISABLE` [709-759,1251-1282,1431].
- Hard-wired in `decode_why.py`: arms [18]; 32 layers, every 4th is attention [19-20]; `assert n_gdn == {24}` on `r["gdn"]["summary"]["n_operations"]` of every run [50-52].

### IMPL/gen_pr_body.py (352 lines)
- Purpose: write `pr-body.md`, the body of draft PR #5572.
- Inputs: output path as argument 1 (default `IMPL/pr-body.md`) [24].
- Hard-wired: `RES` [22]; worktree `/home/jhan/workspace/ai-runs/tron-gdn-amx` [23]; `CELLS` [31]; commit list `72e1191804..HEAD` with `assert len(commits) == 3` [39-40]; diff base `72e1191804` [42,185,211-214]; cells `q35-tp4-1u-p1024`, `q35-tp4-8u-p1024` [97,103]; tags `pab ctr pa` and the count of 5 tests [130-137]; text naming PR #3696 and PR #5022 [344].

### IMPL/pr-prep.sh (40 lines)
- Purpose: `build-all.sh`, `unit-tests.sh`, a Debug build without AMX dispatch (tag `noamx`) with its tests, then `make lint-notes`.
- Inputs: `CTR`, `PA`, `PAB` (required) [21].
- Outputs: `RES/unit-tests.txt`, `RES/unit-tests-noamx.txt`, `RES/lint-notes.txt`, `LOGS/gdn-impl-20261121-pr-prep.{log,done}`.
- Hard-wired: paths [13-16]; `noamx` build from `$PAB` with `CONF_FLAGS='-DCMAKE_BUILD_TYPE=Debug'` and three targets [27]; lint runs in `/var/tmp/jhan/b35-gdn-pab` [37].

### IMPL/final-chain.sh (48 lines)
- Purpose: unit tests, token check, campaign repetitions 11-13, control arms repetitions 21-23, stand-alone kernel timing.
- Inputs: `SKIP_UNIT` (unset) [28].
- Outputs: `LOGS/gdn-impl-20261121-final-chain.{log,done}`, `RES/campaign-session2.done`, `RES/campaign-controls.done`.
- Hard-wired: paths [18-21]; tags `ctr pa pab` [27]; `FIRST_REP=11 REPS=13` [37]; controls `ARMS="base nost orig" CELLS="q35-tp4-1u-p1024 q35-tp4-8u-p1024 q35-tp4-1u-p4096" FIRST_REP=21 REPS=23` [41]; `bench/task3.sh`, `bench/task3_burst.sh` [45-46]. `bench/task3.sh` compiles `IMPL/bench/amx_gdn_bench.cpp`, not the tron tree [bench/task3.sh:17-24].

### IMPL/post-chain.sh (39 lines)
- Purpose: wait for the final chain, repeat the token check with second runs and tag `partb`, copy `unit-tests.txt` to `unit-tests-measured.txt`, then `build-all.sh` and `unit-tests.sh` at the head commits.
- Inputs: `CTR`, `PA`, `PAB` (required) [30].
- Hard-wired: paths [14-17]; arm lists [26-27].

### IMPL/e4b-check.sh (107 lines)
- Purpose: token check of Gemma 4 E4B with AMX on, off, on again, plus the attention kernel per layer from `[attn-stats]`.
- Inputs: `TAG` (`e4b`), `MODELS` (`ingested-gemma-4-e4b-it-tp4 ingested-gemma-4-e4b-it-permuted`), `PROMPTS` (`1024`), `LEN` (128), `ARMS` (`on off on2`) [24-32].
- Outputs: `exec/results/gdn-e4b-20261122/{rt,load,tokens}/`, `tokens/summary.txt`, `e4b-check.done`.
- Hard-wired: `NAME=gdn-e4b-20261122` [21]; two-field arm table `on|TRON_ATTN_STATS=1`, `off|TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1`, `on2|...` [29-31]; reference arm `on` [61]; header text "at the Part B head" [56].

### IMPL/e4b-tests.sh (74 lines)
- Purpose: run the four tests `t_generate_ingest_1_gemma_4_e4b_{fpga,tp2_fpga,tp4_fpga,permuted_fpga}` with AMX on and with `TRON_AMX_DISABLE=1`. It takes its own load snapshot and applies the two refusal rules of `run-one.sh` [54-61].
- Inputs: `TAG` (`e4b`), `TESTS`, `ARMS` (`on off`), `TMO` (1200 s) [22-28].
- Outputs: `exec/results/gdn-e4b-20261122/tests/<test>__<arm>.txt`, `tests/summary.txt`, `load/test-*.txt`, `e4b-tests.done`.
- Hard-wired: `NAME` [21]; tree prefix [23]; our cards [29]; lock `/var/tmp/jhan/gdn-e4b-20261122.run.lock` [34].

### IMPL/models.e4b.yaml (49 lines)
- Model list with three entries: `qwen_3p5_4b` [6-18], `gemma_4_e4b_it` [20-33], `gemma_4_e4b_it_permuted` [35-49]. Header: copies of `config/models.yaml` at 882e5322f1.
- Lines 20-49 are identical to `config/models.yaml` lines 843-872 at ddf843ad97 (diff run).

### G20/run-one.sh (82 lines)
- See section 3.

### G20/build-3b35.sh (87 lines)
- Purpose: the first build recipe; built the tree `b35-gdn-base` (the arm `orig`).
- Inputs: `TAG` (`base`), `SHA` (`72e1191804ecb7591b23230439786a6a1ca784b8`), `JOBS` (40), `TARGETS` [18-19,28,30].
- Outputs: `exec/results/gdn-20261120/build-$TAG.{txt,done}`, `LOGS/gdn-20261120-build-$TAG.log`.
- Hard-wired: `REG` is not a parameter [26]; CPUs 96-143 [27]; it always runs the dependency and configure steps [56-62]; it fails when the Qwen slug is missing from `gen/runtron` [86].

### G20/models.gdn.yaml (18 lines)
- Model list with one entry, `qwen_3p5_4b`, slug `ingested-qwen-3.5-4b`, executors `tp1, tp2, tp4` [6,15-16]. Header: copy of the entry at 72e1191804.

### exec/3b35-inspect-20261112/load-snapshot.sh (108 lines)
- Purpose: read-only load record on stdout (about 12 s). No host check.
- Inputs: `SAMPLE_S` (10), `OUR_APP` (`96-143,223-230`), `OUR_DEV` (`75-78`), `OUR_NODE` (1) [19-22].
- Output lines used by other scripts: rows `socket0`, `socket1`, `our-app-cores`, `our-dev-cores` with `busy_pct` in column 3 [64-66].
- Nothing to change while the runs stay on `--instance 1,2`.

## 2. build.sh step by step
1. Check `TAG` (lowercase letters and digits, not `base`) and the host [38-40].
2. Take the lock `/var/tmp/jhan/gdn-impl-20261121.build-$TAG.lock`; remove the old marker [41-43].
3. Resolve `SHA` in `/home/jhan/workspace/tron` [44].
4. Tree `/var/tmp/jhan/b35-gdn-$TAG`: when absent, `git -C /home/jhan/workspace/tron worktree add --detach`. When present, fail on local changes to tracked files, then `git checkout --detach $SHA` in it [46-52]. Line 53 checks that HEAD equals `SHA`.
5. Copy `$REG` to `$WT/models.gdn.yaml` [54].
6. Under `nice -n10 taskset -c $CPUS` [35,58]: only when `gen/CMakeCache.txt` is absent, run `make TOKENIZER_PYTHON_VERSION=3.12.7 ingest-deps`, `make ... gen/tokenize_py`, and `cmake --preset native -DBUILD_INGEST_MODELS=ON ${CONF_FLAGS:--DTRON_AMX_DISPATCH=ON} -DDEV_MODEL_CONFIG=$WT/models.gdn.yaml -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 -DCMAKE_CXX_COMPILER_LAUNCHER=ccache` [60-66].
7. `cmake --build gen --target $TARGETS -j$JOBS`; only error and warning lines reach the log [68].
8. Fail when a target file `gen/<target>` is missing [74].
9. Write the record `RES/build-$TAG.txt`: tag, tree, full commit with date and subject, configure line, cache values, compiler, targets with build seconds, CPUs and jobs, sha256 of each target, and for runtron the counts of `tdpbf16ps`, `TRON_ATTN_STATS`, `TRON_GDN_STATS` and the Qwen slug [75-86]. The counts cause no failure.
10. Marker `build-$TAG.done` = `ok` or `failed: <reason>` [36-37,88].

Consequence of step 6: a tree that already has a cache keeps its old options. A new `CONF_FLAGS` is ignored there [60]. Whether a changed model list file is picked up in an existing tree is not verified.

Does it assume the model's branch?
- Default `REG` names `qwen_3p5_4b` [models.gdn.yaml:6]. `config/models.yaml` at ddf843ad97 has no `qwen_3p5_4b`; it has `gemma_4_e4b_it` at line 843 and `gemma_4_e4b_it_permuted` at line 858 (git grep).
- `make ingest-deps` and `gen/tokenize_py` exist at ddf843ad97 [GNUmakefile:463, :545 at ddf843ad97].
- Preset `native` and the options exist at ddf843ad97 [CMakePresets.json:31; cmake/model_selection.cmake:6, :17; CMakeLists.txt:46, all at ddf843ad97].
- `t/t_gated_delta_net.cpp` exists at ddf843ad97, so the default targets exist there.
- ddf843ad97 is visible in `/home/jhan/workspace/tron` (git cat-file).
- `TRON_GDN_STATS` and `TRON_AMX_GDN_DISABLE` occur in 0 files at ddf843ad97, so the record line 84 would print 0 there.

Answer: the script text needs no edit for a main-based commit when `REG=<list whose models exist at that commit>` is passed. With the default `REG` it asks for a model that is not registered there. Not verified by a run: all 8 records `RES/build-*.txt` are commits on top of 72e1191804. The E4B export itself ran on 3b35 only at 882e5322f1 (`LOGS/gdn-impl-20261121-build-e4b.log`: "Exporting torch trace to traces/gemma-4-e4b-it", first build 749 s).

Measured build times (records `RES/build-*.txt`): 294 to 311 s for the six-target Qwen builds with `-j44`; 20 to 21 s for a rebuild of an existing tree.

Comparison with `exec/pr5022-final-20261119/`:
- `build-3b35.sh` there is the script that builds a main-based tree on delphi-3b35 [README.md:36].
- It makes a worktree of main at `BASE_SHA=3bea58b788...` in `/var/tmp/jhan/b35-pr5022-$TAG`, and for `TAG=final` copies the uncommitted prepared files over it and checks the tree hash [build-3b35.sh:28-29,53-63]. `TAG` must be `final` or `main` [40].
- It configures `-DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON` and builds `runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit` [32-33]. So that tree holds no model plugin.
- `tests-3b35.sh` there runs 14 unit-test runs in `/var/tmp/jhan/b35-pr5022-final` [tests-3b35.sh:25,65-78]. README line 113: throughput, token identity and runs with a real FPGA card are not covered.
- The tested tree c114b85944 is the tree of commit ddf843ad97 [README.md:119-120].

## 3. run-one.sh
Inputs [23-32]: `RUN` (required), `MODEL` (`ingested-qwen-3.5-4b-tp4`), `USERS` (1), `PROMPT` (1024), `LEN` (256), `ARMENV` (`TRON_ATTN_STATS=1`), `EXTRA` (empty), `TAG` (`base`), `TMO` (2400 s), `NAME` (`gdn-20261120`).

Checks before the run, in order:
1. Host is delphi-3b35 [39]. Binary `/var/tmp/jhan/b35-gdn-$TAG/gen/runtron` exists [40].
2. If `rt/$RUN.log` already holds "average tok/s", exit 0 without a run [43].
3. Lock `/var/tmp/jhan/$NAME.run.lock`; exit 1 when held [44-45].
4. Load snapshot (10 s sample) into `load/$RUN.txt` [54].
5. Our cards `0000:90:00.0 0000:93:00.0 0000:b9:00.0 0000:bc:00.0` [37]: when one has sysfs `enable` = 1, write `RUN-REFUSED` and exit 3 [58,62].
6. Our CPUs: when the snapshot row `our-app-cores` (CPUs 96-143 and 223-230, load-snapshot.sh:20) is above 5.0 % busy, write `RUN-REFUSED` and exit 3 [63]. When the value is missing or not a number, this rule is skipped [63].
7. Unmount a stale FUSE mount `$WT/stats/instance-*` when no runtron of ours runs [65-67].

Command [70-71]:
```
cd /var/tmp/jhan/b35-gdn-$TAG && env -u TRON_AMX_DISABLE -u USE_HW_ATTN \
  SYSTEM_CONFIG="--instance 1,2" $ARMENV TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
  timeout -k 60 $TMO gen/runtron stream-generate-text -m $MODEL -o \
  --prompt-length $PROMPT -l $LEN -u $USERS --dont-stop $EXTRA
```
- There is no `taskset`. tron takes its CPUs from `SYSTEM_CONFIG`. One run log shows "App CPU list: 223-224,96-101,120-125,..." (`RES/rt-results.txt`, run `q35-tp4-8u-p8192__a__rep13`).
- All runtron flags used here and in the token scripts occur in the sources at ddf843ad97 (git grep: `prompt-length`, `dont-stop`, `pay-for-determinism`, `output-token-file`, `intermediates-file`).

What it writes:
- `exec/results/$NAME/rt/$RUN.log.attempt`, renamed to `rt/$RUN.log` on success [71,80].
- `exec/results/$NAME/load/$RUN.txt` [54].
- A block in `exec/results/$NAME/rt-results.txt`: header `### run=... model=... users=... prompt=... len=... armenv=[...] extra=[...] bin=... tip=<short commit>`, a `load:` line, the kept result lines, then `RUN-OK`, `RUN-FAILED` or `RUN-REFUSED` [59-62,75-81].
- After the run it removes our own unmapped files `/dev/hugepages/slice-*-of-8` [46-52,74].
- Exit code: 0 only when the output holds "average tok/s"; 1 on failure; 3 on refusal.

Old campaign: `RES/rt-results.txt` holds 223 `RUN-OK`, 2 `RUN-REFUSED` (8.5 % and 7.3 % busy) and 1 `RUN-FAILED` (the 2-token trial of `logit-margin.sh`).

## 4. campaign.sh tables and timing
Source lines 34-48, verbatim:
```
STATS="TRON_ATTN_STATS=1 TRON_GDN_STATS=1"
ARMS_ALL=$'base|ctr|'"$STATS"$'
p0|pab|'"$STATS"$' TRON_AMX_DISABLE=1
b|pab|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
ab|pab|'"$STATS"$'
a0|pa|'"$STATS"$' TRON_AMX_GDN_DISABLE=1
a|pa|'"$STATS"$'
orig|base|'"$STATS"$'
nost|ctr|TRON_ATTN_STATS=1'
CELLS_ALL=${CELLS_ALL:-$'q35-tp4-1u-p1024|ingested-qwen-3.5-4b-tp4|1|1024|256
q35-tp4-8u-p1024|ingested-qwen-3.5-4b-tp4|8|1024|256
q35-tp4-1u-p4096|ingested-qwen-3.5-4b-tp4|1|4096|256
q35-tp4-8u-p4096|ingested-qwen-3.5-4b-tp4|8|4096|256
q35-tp4-1u-p8192|ingested-qwen-3.5-4b-tp4|1|8192|256
q35-tp4-8u-p8192|ingested-qwen-3.5-4b-tp4|8|8192|256'}
```
- Arm fields: name | build tag | environment. Cell fields: key | model | users | prompt length | generated tokens. Run name: `<key>__<arm>__rep<N>` [74].
- Rotation: for repetition `rep`, the arm order is the `ARMS` list shifted left by `(rep - 1) % number_of_arms` positions [69-70]. Log check: repetition 11 ran `[a0 a base p0 b ab]`, repetition 13 ran `[base p0 b ab a0 a]`.
- Loop order: repetition, then cell, then arm; 5 s sleep after each run [67-83].

Sessions in `LOGS/gdn-impl-20261121-campaign.log` (178 "start" lines, 177 "end" lines, all `rc=0`, 178 `RUN-OK`):

| Session | Start (UTC) | End (UTC) | Duration | Runs | Commits (ctr / pa / pab) |
|---|---|---|---|---|---|
| 1, reps 1-2 | 2026-11-21 23:24:26 | no finish line; last "end" 23:48:22 | rep 1: 21 min 22 s | 36 + 7 of rep 2 | 50b5a9c4ef / 28c5dda93d / cbcb771f61 |
| 2, reps 11-13 | 2026-11-22 00:13:35 | 01:17:45 | 64 min 10 s (21 min 23 s per rep) | 108 | d5093e07c2 / 8351e4ad52 / aacdd287c0 |
| 3, controls, reps 21-23 | 2026-11-22 01:17:45 | 01:30:30 | 12 min 45 s | 27 | ctr d5093e07c2; base 72e1191804 |

- Wall time of one run (`RUN-OK wall=`): 9 s minimum, 13 s median, 49 s maximum.
- The whole final chain ran from 00:07:42 to 01:32:56 UTC, 85 min 14 s (`LOGS/gdn-impl-20261121-final-chain.log`).
- Why session 1 stopped is not in the log. `collect.py` lines 16-18 say it was stopped.
- The timed runs used the commits of the branch `jhan-gdn-amx-measured`, not the head commits 0d69ef3ce8 / 775bba7661 / 882e5322f1 (`rt-results.txt` tips: 18 runs per arm at aacdd287c0 or 8351e4ad52, 27 `base` at d5093e07c2). Between aacdd287c0 and 882e5322f1 the files under `h/` and `src/` differ in comment lines only; tests and READMEs differ too (git diff).

## 5. logit-margin.sh and a run for ingested-gemma-4-e4b-it-tp4 at generated token 63
What the script does: one runtron run per arm with `--temperature 0 --pay-for-determinism --intermediates-file /var/tmp/jhan/gdn-impl-20261121-intermediates.txt`, keeps the lines "Top-k Logits of token N" and "Top-k Token IDs for Logits of token N", deletes the big file, then calls `logit_summary.py` [26,38-39,61-66].

Hard-wired to the Qwen arms:
- `NAME=gdn-impl-20261121` is a plain assignment, so output goes to `RES/tokens/` [20-22].
- Arm table `base|ctr`, `b|pab` with `TRON_AMX_GDN_DISABLE=1`, `a|pa`, `ab|pab`, all with `TRON_GDN_STATS=1` [27-31]. Default `ARMS="base b"` [32].
- No `MODEL` is passed [38-39], so the Qwen default of `run-one.sh` applies unless `MODEL` is in the environment.
- The trial run uses arm `base` (tag `ctr`, a Qwen-only build), prompt 64, 2 tokens, and divides the file size by 66 [45-47].
- Run name `logit-q35-tp4-1u-p...` [60]. Output name `logits-p<prompt>-l<len>__<arm>.txt` has no model in it, and an existing file is skipped [58-59]. `RES/tokens/` already holds `logits-p1024-l4__{base,b,ab}.txt` and `logits-p1024-l190__{base,a}.txt`.
- `logit_summary.py` maps a log label to a generated token with `generated = N - (prompt - 1)` [logit_summary.py:47]. For Qwen, generated token 0 is "token 1023" at prompt 1024 (`RES/tokens/logits-p1024-l4__base.txt`).

Measured on Qwen: 9,133,727 bytes of intermediates per token; 9.44 GB and 220 s for prompt 1024 with 4 tokens; 11.7 GB and 272 s with 190 tokens; 3,145 GB free on `/var/tmp/jhan` at that time (`LOGS/gdn-impl-20261121-logit-margin*.log`).

Why token 63: in `exec/results/gdn-e4b-20261122/tokens/summary.txt` the arm `off` of `ingested-gemma-4-e4b-it-tp4` at prompt 1024 equals the arm `on` at 65 of 128 positions, first difference at generated token 63. The arm `on2` equals `on` at 128 of 128. Build: tag `e4b` at 882e5322f1.

What an E4B run needs to change:
1. A new `NAME` or a model part in the output file names [20,58].
2. An arm table for E4B: an AMX-on arm and an arm with `TRON_AMX_DISABLE=1`, both on a tag whose build holds the E4B plugin (today `e4b`), without `TRON_GDN_STATS` and `TRON_AMX_GDN_DISABLE` [27-32].
3. `MODEL=ingested-gemma-4-e4b-it-tp4` passed to `run-one.sh` in `one_run` [38-39].
4. `LEN` of at least 64, so that generated token 63 is produced (default 4) [24].
5. A trial arm that exists for E4B [45], and no `PER_TOKEN` (the 9,133,727 bytes are a Qwen value) [43-44]. The disk rule stops the script above `MAX_GB` = 60 GB or above half of the free space [56].
6. The index rule of `logit_summary.py` line 47. For `--prompt-length 1024` the E4B log says "Request with 1025 tokens in" and "1026 context"; the Qwen log says "1024 tokens in" and "1025 context" (`gdn-e4b-20261122/tokens/summary.txt`; campaign log). Which "token N" label holds generated token 63 for E4B is not verified. A check is to compare the best token id of the step with position 63 of `tokens/ingested-gemma-4-e4b-it-tp4__p1024__on.txt`.
7. Not verified: whether the E4B plugin writes the "Top-k Logits" lines, and the intermediates size per token for E4B.
8. `report_data.score_compare()` reads fixed Qwen file names with `prompt = 1024` [report_data.py:347-350].

## 6. Result files of the old commits
Folder RES:
- `unit-tests.txt`: head commits ctr 0d69ef3ce8, pa 775bba7661, pab 882e5322f1; run 2026-11-22T06:29:52Z; 15 rows plus 4 switch rows, all "passed".
- `unit-tests-measured.txt`: the session-2 commits d5093e07c2, 8351e4ad52, aacdd287c0; run 2026-11-22T00:07:17Z; 19 rows, all "passed".
- `unit-tests-session1.txt`: the session-1 commits 50b5a9c4ef, 28c5dda93d, cbcb771f61; 15 rows, all "passed"; one comment line for `t_gated_delta_net` at 72e1191804.
- `unit-tests-noamx.txt`: Debug build without AMX dispatch at 882e5322f1, 3 rows "passed", plus the 4 `pab` switch rows.
- `unit/<tag>__<test>__<switch>.txt`: 22 files, full output of the latest run only.
- `tokens/summary.txt`: now holds only the prompt 4096 table (8 arms, all equal, 2026-11-22T01:35:30Z). The prompt 1024 table was overwritten. It is in `LOGS/gdn-impl-20261121-post-chain.log`: `orig base p0 a0 base2` all equal; `a a2 ab ab2` first difference at generated token 185; `b b2 bonly` first difference at generated token 1.
- `tokens/p1024__<arm>.txt` (12 arms), `tokens/p4096__<arm>.txt` (8 arms): token files from the session-2 commits, tag `base` at 72e1191804 and tag `partb` at 8376a86d8a (`rt-results.txt` tips).
- `tokens/logits-p1024-l4__{base,b,ab}.txt`, `logits-p1024-l190__{base,a}.txt`, `logits-summary-p1024-l{4,190}.txt`: kept score lines and summaries; binaries at ced2366229 (ctr), 0254d6f713 (pa), 5346490a4a (pab).
- `build-ctr.txt` 0d69ef3ce8; `build-pa.txt` 775bba7661; `build-pab.txt` 882e5322f1; `build-noamx.txt` 882e5322f1 (Debug, `TRON_AMX_DISPATCH=OFF`); `build-e4b.txt` 882e5322f1 (runtron plus the four E4B tests); `build-p0.txt` a72caf7e40 (work in progress); `build-partb.txt` 8376a86d8a; `build-stats.txt` 4e509c7f9f. Each has a `.done` marker with `ok`. `build-all.done` = `ctr=ok pa=ok pab=ok`.
- The build records of the session-2 commits were overwritten by later builds of the same tags. Their commits remain in the `tip=` field of `rt-results.txt` and in the "arm ... = build ... at ..." lines of the campaign log.
- `rt-results.txt`, `rt/` (223 logs and 1 `.attempt`), `load/` (226 files): every run.
- `collected.json`, `comparison.json` (session 2), `collected-session1.json`, `comparison-session1.json`, `collected-controls.json`, `comparison-controls.json`.
- `campaign-session2.done`, `campaign-controls.done`: both `ok`. `lint-notes.txt`: ends with `lint-notes rc=0`.
- `bench/` (42 files, stand-alone kernel timing), `trace/` (4 files), `results-page-text-v*.txt` (page text drafts).

Folder `exec/results/gdn-e4b-20261122/`:
- `tokens/summary.txt`: per E4B model and arm, kernel per layer and token comparison. With AMX on, 35 of 42 layers read K tokens with AMX kernels.
- `tests/summary.txt`: 8 rows (4 tests x on/off), all `rc=0`, 178 assertions each, at 882e5322f1.
- `rt-results.txt`, `e4b-check.done`, `e4b-tests.done`.

Logs in LOGS: `gdn-impl-20261121-build-<tag>.log`, `-campaign.log`, `-final-chain.log`, `-post-chain.log`, `-pr-prep.log`, `-logit-margin{,-ab,-l190}.log`, `gdn-e4b-20261122-{check,tests}.log`.

## 7. Worktrees (`git -C /home/jhan/workspace/tron worktree list`, 177 entries in all)
| Path | Commit | Branch |
|---|---|---|
| /home/jhan/workspace/ai-runs/pr5022-final/tron | 4c4b7b8864 | detached |
| /home/jhan/workspace/ai-runs/pr5022-final/tron-mergeonly | 4c4b7b8864 | detached |
| /home/jhan/workspace/ai-runs/pr5022-isaac/tron-head | 4c4b7b8864 | detached |
| /home/jhan/workspace/ai-runs/tron-gdn-amx | 882e5322f1 | jhan-gdn-amx |
| /home/jhan/workspace/ai-runs/tron-gdn-amx-review | cbcb771f61 | detached |
| /home/jhan/workspace/ai-runs/tron-gdn-partb | 8376a86d8a | jhan-gdn-partb |
| /home/jhan/workspace/ai-runs/tron-gdn-stats | 4e509c7f9f | jhan-gdn-stats |
| /home/jhan/workspace/ai-runs/tron-glimmer-amx | ddf843ad97 | jhan-amx-kvmul16 |
| /home/jhan/workspace/ai-runs/tron-glimmer-planner | 7ce44251c0 | jhan-amx-kvmul16-planner |
| /home/jhan/workspace/ai-runs/tron-glimmer-prefetch | 0ce944a9de | jhan-amx-kvmul16-prefetch |
| /home/jhan/workspace/ai-runs/tron-qwen35-4b | 72e1191804 | detached |
| /var/tmp/jhan/b35-gdn-base | 72e1191804 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-ctr | 0d69ef3ce8 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-e4b | 882e5322f1 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-noamx | 882e5322f1 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-p0 | a72caf7e40 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-pa | 775bba7661 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-pab | 882e5322f1 | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-partb | 8376a86d8a | detached, "prunable" |
| /var/tmp/jhan/b35-gdn-stats | 4e509c7f9f | detached, "prunable" |
| /var/tmp/jhan/b35-pr5022-final | 3bea58b788 | detached, "prunable" |

- "prunable" is shown because `/var/tmp/jhan` is the local disk of delphi-3b35 and is absent on the agent's machine. Never run `git worktree prune`.
- Other heads checked: `origin/jhan-amx-kvmul16` = ddf843ad97; `origin/rbjarnason/qwen35-native-4b-registry` = 72e1191804; `origin/jhan-gdn-amx` = 882e5322f1; `jhan-gdn-amx-measured` = aacdd287c0. ddf843ad97 is not an ancestor of `origin/main` (7eddde7895); their merge base is 3bea58b788. The model's branch holds 21 commits that are not on main (merge base 54476c6581).
- Tags in use on 3b35: `base ctr pa pab p0 partb stats noamx e4b`.

## Not verified
- A `build.sh` run on a main-based commit, and an E4B export at ddf843ad97.
- Whether an existing build tree picks up a changed model list file.
- The "token N" label of generated token 63 for E4B, the E4B intermediates size, and whether E4B writes "Top-k Logits" lines.
- The host on which the `.py` scripts ran.
- That `compare.py`, `report_data.py` and `decode_why.py` fail on other cells or models. This is read from the code (compare.py:73, report_data.py:62 and 213, decode_why.py:50-52), not run.

## What the new campaign must change
1. All scripts: a new folder name in place of `gdn-impl-20261121`. It is hard-wired in `build.sh:19`, `build-all.sh:8`, `campaign.sh:27`, `unit-tests.sh:15`, `token-check.sh:15`, `logit-margin.sh:20`, `pr-prep.sh:13-16`, `final-chain.sh:18-21`, `post-chain.sh:14-17`, `collect.py:32`, `compare.py:27`, `report_data.py:21,290,303`, `gen_pr_body.py:22`. Reason: `run-one.sh:43`, `token-check.sh:43` and `logit-margin.sh:58-59` skip a run whose output exists, and `build.sh` and `unit-tests.sh` overwrite `build-<tag>.txt`, `unit-tests.txt` and `unit/*`.
2. `build.sh`: keep the tree prefix `b35-gdn-` (it is also in `run-one.sh:35`, `campaign.sh:62`, `unit-tests.sh:22`, `e4b-tests.sh:23`, `pr-prep.sh:37`, `final-chain.sh:27`). Pick tags that are free, or accept that a reused tag moves that tree to the new commit and removes the old binary [build.sh:49-51]. A reused tree keeps its old configure options [build.sh:60].
3. `build.sh`, record line 84: the slug pattern `ingested-qwen-3\.5-4b` and the `TRON_GDN_STATS` count, for a build without that model or without the counters.
4. New model list file for a main-based build of Part B: the two E4B entries of `models.e4b.yaml` lines 20-49 without the `qwen_3p5_4b` entry of lines 6-18, passed as `REG=`.
5. `build-all.sh`: the tags `ctr pa pab`, the variables `CTR PA PAB` and the target list [10-14]. The new stack has three commits on the model's branch (counters, Part 0, Part A) and one on another branch with another model list.
6. `campaign.sh` arm table [35-42]: rows `p0`, `b`, `ab` name tag `pab`. Rows `b` and `a0` set `TRON_AMX_GDN_DISABLE=1`, which exists only from the Part A commit on. `STATS` [34] sets `TRON_GDN_STATS=1`, which no main-based build reads. Default `ARMS` [33].
7. `campaign.sh` cell table [43-48]: slug and keys are Qwen. A Part B campaign off PR #5022's branch needs cells with a model registered there, for example `ingested-gemma-4-e4b-it-tp4`.
8. `unit-tests.sh`: `TAGS` [17], `TESTS` [18], and the four fixed `pab` switch rows [45-48].
9. `token-check.sh`: arm table [21-32], default `ARMS` [36], run name prefix [45], `MODEL` not passed [45-47], reference arm `base` [55]. For E4B, `e4b-check.sh` does this job: change `NAME` [21], `TAG` default [24], header text [56].
10. `e4b-tests.sh`: `NAME` [21], `TAG` default [22].
11. `logit-margin.sh` and `logit_summary.py`: the eight points of section 5.
12. `final-chain.sh`: tag loop [27], `FIRST_REP`/`REPS` [37], control arms and cells [41]. `post-chain.sh`: arm lists [26-27]. `pr-prep.sh`: `noamx` build from `$PAB` [27], lint tree `b35-gdn-pab` [37].
13. `collect.py`: arm set [35], `REPS_RANGE` default [36], the prefill-pass rule [93-109] (E4B logs 1025 prompt tokens for prompt 1024, so `prompt % 128` is not 0).
14. `compare.py`: `PRED` [28], `CELLS` [29], `DIRECT` [31]. The prediction file has no cell outside the six `q35-tp4-*` keys.
15. `report_data.py`: `CELLS` [24], tags [381], token arm order and pairs [241,250-251], side runs [306-307], score compare files [347-350], session repetitions [391], and the unconditional reads of `bench/*.txt` and `understand/review-result.json` [40-197,213].
16. `gen_report.py` and `decode_why.py`: arm labels, tag names, the cell `q35-tp4-1u-p1024`, the page text that names `jhan-gdn-amx`, `72e1191804`, PR #5572 and PR #3696, and `assert n_gdn == {24}` [decode_why.py:50-52].
17. `gen_pr_body.py`: worktree [23], base `72e1191804` [39,42,185,211-214], `assert len(commits) == 3` [40], tags and test count [130-137], text on PR #3696 and PR #5022 [344]. One body per PR needs its own base and commit range.
18. `G20/run-one.sh` and `load-snapshot.sh`: no edit while runs stay on `--instance 1,2`. Callers must pass `MODEL`, `TAG` and `NAME`, since the defaults are the Qwen slug, `base` and `gdn-20261120` [run-one.sh:24,30,32].
