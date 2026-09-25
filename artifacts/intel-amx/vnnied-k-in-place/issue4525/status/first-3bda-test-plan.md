# First 3bda machine test plan: typed KV-cache tensors (issue #4525 parent)

Written 2026-09-22 21:00 UTC. Branch `jhan-kv-typed-tensors`, base main `0a51385e95`,
first branch commit `85084e937c` (21:05 UTC; equals the peer's snapshot `48ab31f7` plus
the test fix of section 7), second commit `682064f8fb` (removes the bulk-route bounds
assert found by Step F), third commit `c2efd73ff6` (review fixes: tests and comments
only, plus one 8-lane-only deleted member), fourth commit `c3c368d298` (21:20 UTC; test
extensions from the review's completeness critic). The branch head is `c3c368d298`. Its
16-lane production code is byte-identical to `682064f8fb`.

## Short version

The branch replaces raw `bf16*` cache arguments with typed views and moves the packed-V
row operations into one header, without changing a stored byte or an arithmetic step.
The unit tests already pass on delphi-3bda with real AMX (section 2). This plan lists the
machine tests that still have to show the refactor changed nothing: every build
configuration, the broad host test gate, a token-identical runtron A/B, a
performance A/B inside the run-to-run band, and an instruction comparison of the moved
loops.

## Words used here

- tron: the inference program under test. runtron: its command-line tool. rinzler: the
  production server, running on 3bda as the systemd units `rinzler@0..3`.
- delphi-3bda (3bda): the Intel Xeon 6 (Granite Rapids) test server with AMX. It runs
  the nightly CI at about 03:30-13:20 UTC and is shared with Bill (see section 3).
- AMX: Intel Advanced Matrix Extensions, the tile instructions of the fast attention
  path. AVX-512: the 512-bit vector instructions of the normal attention path.
- 16-lane build / 8-lane build: a build with 16 fp32 values per vector register
  (AVX-512, `TRON_CHUNK_SIZE == 16`) or 8 (AVX2). Only the 16-lane build stores V
  packed; the 8-lane build keeps V row-major.
- TRON_AMX_DISPATCH: the CMake option that compiles the AMX kernels and their dispatch
  (default OFF; the required CI build has it OFF). AMX-on / AMX-off below name that
  compile-time option.
- TRON_AMX_DISABLE=1: the runtime kill switch. The binary keeps the AMX code but takes
  the AVX-512 path. "kill switch" arm below.
- K, V, KV cache: a token's key and value vectors, and the store of earlier tokens'
  keys and values that attention reads.
- native K: K stored row-major, one token's 128 dims consecutive. packed V: V stored
  with the values of two adjacent tokens interleaved per dim (Note [Packed V layout] in
  h/tron/tensor/v_vnni.hpp).
- v_vnni_tensor / v_vnni_view / v_vnni_row: the new packed-V owner, matrix view and row
  expression. const_native_k_view: the new alias of the existing row-major K plane view.
- page: 64 tokens of KV cache. book: the owner of a run of pages and their memory.
  slot: the K/V storage of one layer. kv_block: K and V for one head of one page.
  arena: one allocated memory region of a book.
- FPGA attention (USE_HW_ATTN=1): attention computed on the FPGA cards; the CPU still
  stages K and V rows for it through the GOF (group of four tokens) callbacks.
- TPS: generated tokens per second, summed over users. TTFT: time to first token in
  seconds. A/A: the same binary run twice. A/B: base binary against branch binary.
- CI lease: the file `/run/lock/systems-test-ci.lease` on 3bda; CI holds the host when
  the file exists, says `busy`, and has not expired.
- lib-guard: `~/workspace/intel-AMX/exec/lib-guard.sh`, the shell library whose
  `campaign_guard_acquire` refuses to start when CI, another user, a blackout, another
  campaign, a runtron, or active serving is present.
- our half: socket 1 of 3bda (CPUs 72-143 and 216-287, cards 90/93/b9/bc,
  `runtron --instance 1,2`). Bill's marker file `/bill-has-instance-0,2` reserves the
  first half for him.
- base binary / branch binary: the same cmake configuration built from main
  `0a51385e95` and from the branch.
- objdump: the GNU tool that prints the compiled instructions of a binary.
- Slice: the repository's test scheduler (`bin/slice`). Its logs are under
  `logs-<hostname>/run-NNNN/` in the checkout.

## 1. What is under test

The branch implements the parent of PR #4424 as designed in
status/design-new-tensor-type.html (codex, revision d2e9dabf) and reviewed in four rounds
(status/claude-review-design-new-tensor-type.html).

Changed files (10 modified, 2 new):

- h/tron/tensor/kv_cache_fwd.hpp (new): forward declarations only, no intrinsics.
- h/tron/tensor/v_vnni.hpp (new): owner, view, row expression, `append_v_row`,
  `load_row`, `copy_token`, Note [Packed V layout].
- h/tron/models/kv_cache.hpp: `kv_block::v` is now the owner; `set_v` takes an aligned
  read-only source row, `get_v` an aligned destination row; new `page::v_packed`;
  `page::append_v` forwards to `copy_token`; `scaled_v_expr` takes the packed view;
  `book::allocate_kv_group` default-initializes the kv_block arrays in place
  (Note [KV block lifetime]); `v_data` and `v_base` are gone.
- h/tron/models/model.hpp: `save_v_impl` wraps the executor's V row as a typed view.
- h/tron/kernels/amx_attn_iface.hpp and src/tron/kernels/amx_attn.cpp: the QK kernel
  takes `const_native_k_view<64, 128>`, the PV kernel `v_vnni_view<const bf16, 64, 128>`.
- h/tron/models/self_attention.hpp: passes the whole K plane and the packed V plane.
- h/tron/scheduler/full.hpp: the GOF V callback unpacks into a typed destination row.
- t/t_llama_unit.cpp, t/t_amx_numerics.cpp, t/t_amx_dispatch_dtype.cpp,
  t/heterogeneous_scheduler_compile.cpp: migrated callers, typed-boundary checks, one
  new bit-exactness case, and the apply_page_range call that main had left stale.

What must not change (the pass rules of every step below follow from this list):

- The bytes stored in the cache for the same inputs.
- The generated tokens of a greedy run, per attention path (AVX-512, AMX, FPGA).
- TPS and TTFT, within the run-to-run band.
- The instruction mix of the moved loops, and no memory clearing on the allocation or
  restore path.

## 2. State at the time of writing

Done on 3bda in `/var/tmp/jhan/tron-issue4525` (local disk, 16-lane, AMX on,
RelWithDebInfo, clang-19 from the Nix shell, build pinned to socket 1):

| Check | Result | Evidence |
|---|---|---|
| Build of runtron, t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype, t_heterogeneous_scheduler | 0 errors, 0 compiler warnings | /var/tmp/jhan/tron-issue4525-build2.log, -build3.log |
| clang-format-19 dry run on the 12 changed files | clean | same logs ("FORMAT CLEAN") |
| t_llama_unit | all 43 test cases pass, 176462 assertions | /var/tmp/jhan/tron-issue4525-tests/t_llama_unit.log |
| new case "packed V rows keep their bits ..." alone | 1 case, 4 sections, 20621 assertions pass | run by hand 20:40 UTC |
| t_amx_numerics with real AMX | 4 cases pass, 12301 assertions, no "AMX unavailable" warning | .../t_amx_numerics.log |
| t_amx_numerics with TRON_AMX_DISABLE=1 (control) | 4 cases pass, 2060 assertions, both QK and PV cases print "AMX unavailable" | .../t_amx_numerics.disabled.log |
| t_amx_dispatch_dtype (CPU fakes) | 4 sections pass | .../t_amx_dispatch_dtype.log |
| t_heterogeneous_scheduler | passes | .../t_heterogeneous_scheduler.log |

Baseline facts measured on unmodified main `0a51385e95` in the same configuration:

- runtron, t_llama_unit, t_amx_numerics, t_heterogeneous_scheduler build in about
  10 minutes with a warm ccache [build1 log].
- t_amx_dispatch_dtype does not compile on main with AMX on: its `apply_page_range`
  call passes 8 arguments and the function takes 9 [build0 log,
  self_attention.hpp:1374]. The branch adds the missing query-mask argument.

Queued at 20:35 UTC on 3bda (script /var/tmp/jhan/tron-issue4525-chain.sh, log
/var/tmp/jhan/tron-issue4525-chain.log); results go into section 7 when they land:

- every target of the 16-lane AMX-on tree (`cmake --build gen`);
- `make lint-notes`;
- the 16-lane AMX-off tree (`gen-amxoff`, the required CI feature set) with the four
  tests run;
- a Debug 16-lane AMX-off tree (`gen-debug`) running the `[kv_data]` cases without
  `TRON_IGNORE_NAN`;
- the 8-lane tree (`gen-avx2`) building `tron` and `t_amx_dispatch_dtype`.

Not run anywhere yet: the broad host gate, any runtron run (the section-2 trees have
no model plugin, see Step D), any performance measurement, any instruction comparison,
CI.

## 3. Rules for every step on 3bda

- Read the lease first. CI holds the host only when `/run/lock/systems-test-ci.lease`
  exists, says `busy`, and has not expired. The nightly runs about 03:30-13:20 UTC.
  Between long runs, recheck with `ci_took_dut` from lib-guard.
- Source lib-guard and call `campaign_guard_acquire` before any runtron step. It
  refuses a busy lease, another active user, a blackout, an occupied campaign lock, a
  running runtron, or active serving. Builds and Catch2 unit tests need no guard; keep
  them on socket 1 with `taskset -c 72-143,216-287` and at most `-j 48`.
- Keep Bill's marker `/bill-has-instance-0,2`. Our runtron runs use `--instance 1,2`.
  Do not touch socket 0.
- Serving must be down for every runtron step, and only jhan authorizes that. platformd
  0.11 restarts units stopped with systemctl within about a minute, so use the API:
  `POST http://localhost:8080/api/inference/down` before and `.../up` after
  (`rinzler_stop_serving` in lib-guard, `dut.sh serving-down/up` in
  exec/q4b-fpga-20260921/). The takeover hold window 01:40-04:30 UTC is off limits.
- Build inside `nix develop --accept-flake-config`; never run cmake outside it (it
  invalidates the cache). ninja's `-k 0` goes after `--`.
- Two worktrees on local disk: `/var/tmp/jhan/tron-issue4525` (branch) and
  `/var/tmp/jhan/tron-issue4525-base` (main `0a51385e95`; create it with
  `git -C ~/workspace/tron worktree add --detach ... 0a51385e95` ON 3bda). Configure
  both with the same options. Never `git worktree prune` from claude-box.
- Sync from the editing worktree with `rsync -rlc` and the excludes recorded in the
  memory note; never `--delete`.
- Every command below writes its log under `/var/tmp/jhan/tron-issue4525-tests/`;
  copy the logs to `issue4525/evidence/3bda-first-test/` at the end.

## 4. Steps

### Step A. Build configurations (design section 8, "Build configurations")

| Config | cmake options (preset `native`, plus `-DBUILD_INGEST_MODELS=OFF -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF`) | Build | Run | Pass rule |
|---|---|---|---|---|
| A1 16-lane, AMX on | `-DAVX512=ON -DTRON_AMX_DISPATCH=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo` | all targets | t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype, t_heterogeneous_scheduler | 0 errors; every case passes; `AVX512:BOOL=ON` in CMakeCache.txt and no "Disabling AVX512" line |
| A2 16-lane, AMX off (the CI feature set) | `-DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo` | all targets | same four tests | same; t_amx_numerics and t_amx_dispatch_dtype print their "not compiled" placeholder |
| A3 8-lane, AMX off | `-DAVX512=OFF -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo` | `tron`, `t_amx_dispatch_dtype`, on base AND branch | none counted (placeholder only) | both trees build the same target set; t_llama_unit and t_heterogeneous_scheduler fail on both (record the first error of each) |
| A4 Debug 16-lane, AMX off | `-DAVX512=ON -DTRON_AMX_DISPATCH=OFF -DCMAKE_BUILD_TYPE=Debug` | t_llama_unit | `t_llama_unit "[kv_data]" --skip-benchmarks` | passes; the t_llama_unit compile command in compile_commands.json has no `-DTRON_IGNORE_NAN` |

Record for each tree: the compiler version line, the three cache values above, and the
`-O` flag from compile_commands.json (the build adds `-O3` after the preset's `-O2`).

### Step B. Real AMX execution proof (design section 8, "Prove real AMX execution")

Already done at 20:30 UTC (section 2). Repeat on the final commit:

```
cd /var/tmp/jhan/tron-issue4525
taskset -c 72-143 gen/t_amx_numerics            > $T/t_amx_numerics.log
taskset -c 72-143 env TRON_AMX_DISABLE=1 gen/t_amx_numerics > $T/t_amx_numerics.disabled.log
```

Pass rule: the first log has 4 passed cases and no "AMX unavailable" line. The second
has 4 passed cases and two "AMX unavailable" lines (QK and PV). A pass line alone is
not enough; the early-return path also passes.

### Step C. Broad host gate (run-tron-tests skill: build-test, then test-host)

In the A2 tree (the CI feature set), on the branch and then on base:

```
make build-test      # cmake --build gen, every test target
make test-host       # bin/slice run --filter=host --exclude-tag=slow
```

`bin/slice route` said `local-legacy` on 3bda, so plain local commands apply. Run it
while serving is down and no runtron is active; Slice may use hugepages and cards.
Pass rule: the set of passing and failing binaries is the same for base and branch,
and every test that touches the KV cache passes on the branch. Keep the Slice
`logs-<hostname>/run-NNNN/` directory of both runs; Slice keeps only 10.

Duration est.: 1-2 hours per tree, depending on ccache.

### Step D. Functional A/B: token-identical greedy runs

Prerequisite for Steps D and E: runtron binaries that contain the ingested qwen3-4b
plugin. The unit-test trees of section 2 were configured with
`-DBUILD_INGEST_MODELS=OFF`, so their `gen/runtron` has no model plugin. Configure the
two runtron trees (base and branch) like the earlier campaign trees
(`/var/tmp/jhan/tron-p0perf13/gen/CMakeCache.txt`: `BUILD_INGEST_MODELS=ON`,
`BUILD_TEST_MODELS=OFF`, `BUILD_PRODUCTION_MODELS=OFF`, `TRON_AMX_DISPATCH=ON`,
`AVX512=ON`, RelWithDebInfo) and check the plugin is present:
`strings gen/runtron | grep -c ingested-qwen-3-4b-instruct-2507` must print a number
above 0 (the campaign script exec/vnnik-20260914/campaign.sh:203 makes the same check).
The ingest step exports model traces (`ingest/traces/`); a fresh tree takes est. 1-2 h
for that step, and gated google/gemma exports need `HF_TOKEN`. The earlier trees on
3bda hold complete traces; whether their `ingest/traces` can be reused depends on the
ingest input stamps and is checked at build time, not assumed.

Model: qwen3-4b (`ingested-qwen-3-4b-instruct-2507-tp2`), the AMX shape (128-dim
heads, 4 query heads per KV head), served with `runtron --instance 1,2`. Recipe from the determinism memory: `--pay-for-determinism`,
temperature 0, one prompt from a forced text token file (never `-u N` with token
files), `--output-token-file`, compared with `exec/vnnik-20260914/compare_tokens.py`.

| Arm | Binary | Environment | Purpose |
|---|---|---|---|
| D1 | base | AMX on (default) | reference |
| D2 | branch | AMX on | typed QK and PV views |
| D3 | base | TRON_AMX_DISABLE=1 | reference for the AVX-512 path |
| D4 | branch | TRON_AMX_DISABLE=1 | append_v_row / scaled_v_expr path |
| D5 | base | USE_HW_ATTN=1 (FPGA attention) | reference for the GOF V callback |
| D6 | branch | USE_HW_ATTN=1 | typed get_v in full.hpp |
| D7 | branch | AMX on, second run | A/A control |

Pass rule: D2 == D1, D4 == D3, D6 == D5, D7 == D2, token for token over the whole
generation (256 tokens). The change touches no arithmetic and no addition order, so a
single differing token is a defect, not noise. Prompt lengths: 1024 and 8192 tokens
(one page-aligned, one with many full pages for the AMX dense path).

Duration est.: 30 minutes including model load.

### Step E. Performance A/B (refactor: expect no change)

Same model and instance. 8 users per run, prompt lengths 1024 / 2048 / 8192 tokens,
256 generated tokens, 3 repetitions interleaved across arms, TPS and TTFT recorded.

| Arm | Binary | Environment |
|---|---|---|
| E1 | base | AMX on |
| E2 | branch | AMX on |
| E3 | base | TRON_AMX_DISABLE=1 |
| E4 | branch | TRON_AMX_DISABLE=1 |

Template: exec/vnnik-20260914/{campaign.sh,summarize.py} (same shape, same arms
pattern); point it at the two runtron binaries and name the result directory
exec/results/typedkv-<date>/.

Pass rule: for every prompt length, |E2 - E1| and |E4 - E3| are inside the
run-to-run band of the three repetitions (the 2026-09-14 campaign measured a standard
deviation of at most 0.4 TPS and 0.15 s TTFT at this shape). The refactor may not cost
or gain anything; a shift larger than the band in either direction is investigated
with Step F before anything else.

Duration est.: 2 hours for the 4 arms x 3 lengths x 3 repetitions.

### Step F. Instruction comparison (design section 8, "Instruction comparison")

On the A1 base and branch t_llama_unit binaries:

```
objdump -d -l --no-show-raw-insn -C gen/t_llama_unit > $T/objdump.<tree>.txt
```

Locate, through the source lines of the Catch2 cases, the loops of even and odd
`set_v`, `append`/`copy_token`, `get_v` unpack (bf16 destination:
`_mm512_cvtepi32_epi16`; float destination), and the `scaled_v_expr` weighted sum.
Count per body: `vmovdqa64`/`vmovdqu64` loads and stores, `vdpbf16ps`, `vpternlogd`,
`vpslld`/`vpsrld`, `vpmovzxwd`, `vpmovdw`, calls, and `rep stos`/`memset`.

Pass rule: the same counts base and branch for each body; no new call, no destination
load on an even append, no scalar dimension loop, no memory clearing in
`book::allocate_kv_group` or `restore_reclaimable_kv_storage` (the in-place array
construction must compile to nothing). fp16 append has no baseline body (main never
instantiates it): record "Insufficient data: no baseline fp16 body".

### Step G. Evidence to keep

- The commit shas of base and branch, `git status` of both trees (clean), the three
  cache values and the compiler line of every tree.
- Every log named above, plus `run.log`-style index files with exit codes.
- runtron command lines and the token files of Step D; the summarize.py table of
  Step E; the objdump excerpts of Step F.
- Copy to `issue4525/evidence/3bda-first-test/` and reference them from the PR
  description.

## 5. Order and timing

1. Now (serving up, no guard needed): finish Step A (chain running), Step B on the
   final commit, and the `make build-test` half of Step C on both trees.
2. After jhan authorizes the takeover, before 01:40 UTC or after 13:20 UTC: serving
   down through the platformd API, Step D (30 minutes), Step E (2 hours), the
   `make test-host` half of Step C (1-2 hours per tree), serving up.
3. Any time: Step F (offline, needs only the two binaries).

Total est.: 5-7 hours of machine time, of which 3-4 hours need serving down.

## 6. Not covered by this plan

- The review of the implementation (workflow of 8 finder lenses, 3 refuters per finding,
  one completeness critic) confirmed 15 findings, none major; all code and comment fixes
  are in commit `c2efd73ff6`. Two items were recorded rather than changed: the QK kernel's
  `const_native_k_view` argument is passed by hidden reference (the rank-2 `const_view`
  has user-provided copy and move constructors), one store and one load per kernel call,
  a design-mandated signature; and the PR description must say that the internal
  KV-cache API changed under issue #4525 while the public API (h/libtron.hpp and the
  headers it exports) is untouched.
- The review's completeness critic found every design step 1-6 implemented and named
  three test-contract gaps. Two are closed in the branch (all four token-copy parities
  under the NaN-poison observation; exact bits after token copies). The third is
  recorded as a deferral: the design asked for a generic-conversion NaN expectation
  selected by `#ifdef TRON_IGNORE_NAN`; this change does not touch the generic
  `fp32s_to_bf16s` conversion, so the new case tests the packed path's policy
  independence only, and the Debug run confirms it (section 7).

- CI evidence. A draft PR runs no Test host job; the GCP Nix product jobs need the PR
  to be ready for review (allowed for the PR based on main) or a user-directed
  `Run CI` label or rerun (round-4 finding J01).
- The test-cost record. `bin/slice bench --update t_llama_unit` measures the whole host
  and needs jhan's direction; until then the PR records the deferral.
- The 8-lane full test suite: t_llama_unit and t_heterogeneous_scheduler do not
  compile at 8 lanes on main either.
- PR #4424: its rebase onto this parent is the next PR order item, not this test.

## 7. Results of the queued configurations (20:35-20:55 UTC)

Chain log: /var/tmp/jhan/tron-issue4525-chain.log. Test logs:
/var/tmp/jhan/tron-issue4525-tests/.

| Step | Result | Reading |
|---|---|---|
| A1 all targets, branch, 16-lane AMX on | every target builds except t_rinzler (t/t_rinzler.cpp:5316, `read_stats_counter` undeclared) | pre-existing: main `0a51385e95` fails identically in the same tree configuration [/var/tmp/jhan/tron-issue4525-basebuild.log]; the branch does not touch t_rinzler.cpp. Cause: the helper (line 4628) is defined only under `TRON_GPT_OSS_20B_INGEST_MODEL_ENABLED`, its use at 5316 is not, so the error follows from `BUILD_INGEST_MODELS=OFF`, not from AMX. t_rinzler is fpga-labelled (t/CMakeLists.txt:643), so the host suite never builds it |
| make lint-notes | exit 0 | the two new Notes and every cross reference resolve |
| A2 16-lane AMX off (CI feature set), branch | builds; t_llama_unit 43 cases / 176462 assertions pass; t_amx_numerics and t_amx_dispatch_dtype run their "not compiled" placeholder (1 assertion each); t_heterogeneous_scheduler 1852 assertions pass | `AVX512:BOOL=ON`, `TRON_AMX_DISPATCH:BOOL=OFF`, RelWithDebInfo confirmed in gen-amxoff/CMakeCache.txt |
| A4 Debug 16-lane AMX off, branch | builds; t_llama_unit `[kv_data]` first run: 28 of 29 cases pass, 1 failure in the new case; after the test fix below: 29 of 29 pass, 48958 assertions [c4.t_llama_unit.kv_data.rerun.log] | `CMAKE_BUILD_TYPE:STRING=Debug`; the t_llama_unit compile command has no `-DTRON_IGNORE_NAN` (0 occurrences) |
| A3 8-lane AMX off | the `tron` library itself does not compile at 8 lanes: h/tron/simd/fp32.hpp:749 `cast_fp32`, :807 `mask1x16`/`fp32x16` unknown, and more | pre-existing: main fails the same way in /var/tmp/jhan/tron-issue4525-base/gen-avx2 [BASEAVX2 EXIT 1]; the 8-lane comparison of Step A3 is not applicable on this main |
| A1 rerun after the test fix, branch | t_llama_unit 43 cases / 176462 assertions pass [t_llama_unit.rerun.log] | the "Aborting" lines in that log are forked death-test children of an existing case, not failures |
| A1 rerun at the branch head `c2efd73ff6` (review fixes) | t_llama_unit 43 cases / 176594 assertions pass [t_llama_unit.rev.log, 21:12 UTC]; clang-format clean | the 132 new assertions are the partner-zero checks after the bf16 and fp16 even appends; the Debug tree was not rebuilt for this commit (its earlier run covered the same bit checks minus those 132) |
| A1 rerun at the branch head `c3c368d298` (test extensions) | t_llama_unit 43 cases / 199125 assertions pass [t_llama_unit.rev2.log, 21:20 UTC]; clang-format clean | "append_v preserves poison" ran for dst_tokens 2 and 3 (all four copy parities under the NaN poison); the new "token copies keep bits" section ran for both destination parities; the Debug tree was not rebuilt for this commit |

The Debug failure and its fix: the new case wrote the bf16 denormal bit pattern 0x0001 as
a special value and read back 0. A standalone program compiled with the tree's clang-19
showed that a plain `bf16` struct copy at `-O0` flushes that denormal to zero, with
DAZ and FTZ both off (MXCSR 0x1f80), while `-O3` keeps the bits
[/var/tmp/jhan/tron-issue4525-tests/denorm/denorm.cpp]. The packed path is integer-only
and never flushed anything; the test harness did. The special value is now 0x8000
(negative zero), and the comment in the test says why.

Step F, done 20:59-21:15 UTC by a subagent (files under
/var/tmp/jhan/tron-issue4525-tests/objdump/: out/report.txt, out/vector_mix.txt,
out/diff_*.txt, harness_*.objdump.txt, build.py, analyze.py, *.o.cmd.txt, md5.txt).
Method: 19 noinline wrapper functions compiled against the base tree and the branch
tree with t_llama_unit's exact clang-19 command, then `objdump -d -r` and a normalized
instruction diff.

| Body | Base | Branch | Verdict |
|---|---|---|---|
| set_v even/odd for bf16, float, fp16 (constant token) | 63-83 instructions each | same | identical sequences |
| get_v even/odd for float, bf16 (constant token) | 63-64 | same | identical |
| scaled_v weighted sum | 130 (8 vdpbf16ps, 31 vmovaps) | 130 | identical |
| book::append closure (copy_token bodies) | 409 | 432 | vector mnemonics equal; + one compare-and-branch per token for the new bounds assert (see below) |
| book construction and reclaimable restore | 274 / 137 | 202 / 108 | allocate_kv_group now out of line (called, not inlined); no store to the arena, no rep stos, no memset, no loop |
| set_v / get_v with a runtime token | 87-103 | 96-113 | vector mix identical; + cmp, jae and one spill for the new bounds assert |

Reading: the moved bodies are the same instructions; the in-place array construction
compiles to nothing; even append reads only the source row in both trees. The one
behavior addition was `TRON_ASSERT_LT(token, Rows)` in `detail::v_vnni_access::pair_base`
(TRON_ASSERT stays active in release builds), which main never had on the bulk path. It
was removed from the bulk route in commit `682064f8fb` (21:30 UTC); `operator[]` and
`at()` keep their asserts. The snapshot the peer session measures still contains that assert,
so its Step E numbers are an upper bound on the refactor's cost. Not covered by the
harness: the heterogeneous-geometry `construct_kv_blocks` loop and the AMX kernel argument
path (Insufficient data at the instruction level; the unit tests cover both).

Execution of Steps C-F: session issue4525-40 started the run at 20:55 UTC on 3bda from
the snapshot commit `48ab31f7` (ref `i4525-snap-20260922T2047Z`, my working tree at
20:47 UTC; the only later change is the test fix above). Its log is
exec/logs/i4525-20260922-chain.log, results exec/results/i4525-20260922/, later copied
to issue4525/evidence/3bda-first-test/. Its results belong in that evidence directory
and in the PR description; this section stays the record of the unit-level checks.

Its report is issue4525/status/first-3bda-test-results.html (generator
exec/i4525-20260922/gen_report.py; published at https://claude.ai/artifact/FfE8Vi3weawiQ5VQnmxCJF): per cell and arm the TPS and TTFT mean with the
standard deviation over the repetitions, the head-vs-base and headoff-vs-baseoff
differences, the paired per-repetition delta with its t statistic, and an inside/OUTSIDE
verdict against a band of 2 x the larger arm sd, next to this plan's reference spread.

Reported by that session so far (its message of 21:3x UTC; its logs are the record):

- Step D done, four verdicts ok. CPU attention at prompt 1024 and 8192, five arms each
  (base, head snapshot `48ab31f7`, head A/A, base with the kill switch, head with the
  kill switch): every pair identical for 256 generated tokens, including head with the
  kill switch against head (AMX against AVX-512 path). FPGA attention at 1024 and 8192:
  head identical to base for 256 tokens.
- Step E started about 21:35 UTC on the binary of commit `682064f8fb` (version string
  2026.09.22-682064f8), arms base / head / base+kill switch / head+kill switch, 8 users,
  prompt 1024 / 2048 / 8192, 3 repetitions; expected to end 00:00-00:30 UTC, then
  `make test-host` in the AMX-off tree (Step C).
- Serving went down at 21:14 UTC through the platformd API (`dut.sh serving-down`); the
  lib-guard idle takeover refused because the engines' last journal line after each idle
  SYSTEM_STATS burst is "0 history events", not the stats line (a guard gap to fix).
- Chain finished 22:30 UTC, serving back up (4 engines, Bill's marker present).
- Step E (`682064f8fb` against main, 36 runs, 0 failures): all 12 comparisons inside the
  run-to-run band; largest differences +0.72 % TPS and -0.73 % TTFT, both with the head
  faster; per-arm standard deviation at most 0.35 TPS and 0.23 s. Reading: the refactor
  costs nothing measurable, as the plan's pass rule requires.
- Step C, branch tree, 16-lane AMX off: `make build-test-host` rc 0 (669 host targets;
  t_rinzler is fpga-labelled and not among them), `make test-host` rc 0: 88 passed, 1
  skipped, 0 failed, makespan 110 s. The base half of the pass rule (same pass/fail set on main `0a51385e95`) runs
  from exec/i4525-20260922/stepc-base.sh, expected done about 23:15 UTC.
- Step F: full objdump of both A1 t_llama_unit binaries kept under
  /var/tmp/jhan/tron-issue4525-tests/; the harness report above is the analysed result,
  copied to issue4525/evidence/3bda-first-test/stepF-peer/.
- Final (22:49 UTC): 3bda released, serving up (default-0..3 healthy), Bill's marker
  present, CI lease free. Step C control on main `0a51385e95` in the same AMX-off
  configuration: `make build-test-host` rc 0 (816 s), `make test-host` rc 0 with 88
  passed / 0 failed / 1 skipped (t_proxy_lib), the identical status set to the branch (89
  test lines each). Final tally: Step D 4 of 4 identical; Step E 12 of 12 inside the
  band; Step C same pass/fail set. Report issue4525/status/first-3bda-test-results.html;
  evidence issue4525/evidence/3bda-first-test/ (175 files). Trees left on 3bda:
  /var/tmp/jhan/tron-main0922, tron-i4525rt (snapshot), tron-i4525rt2 (`682064f8fb`),
  tron-i4525c (branch, AMX off), tron-i4525cbase (main, AMX off).

Step F re-run on the final production code (22:52 UTC; the branch tree held commit
`c3c368d298`, whose 16-lane production code equals `682064f8fb`; only the branch harness
was recompiled, against the unchanged base object). Files: out/report_final.txt,
out/diff_final_*.txt, harness_branch_final.o and its .cmd.txt, all under
/var/tmp/jhan/tron-issue4525-tests/objdump/.

| Body | Base | Final | Verdict |
|---|---|---|---|
| set_v even/odd for bf16, float, fp16; get_v even/odd for float, bf16 (constant token) | 63-83 | same | identical |
| set_v / get_v with a runtime token | 87-103 | 87-102 | vector instructions identical and in the same order; one fewer scalar `add` (scaled-index addressing instead of a pre-added pointer); the compare-and-branch of the earlier run is gone, and its abort symbol no longer exists |
| book::append closure (copy_token bodies) | 409 | 417 | vector mnemonics unchanged; no compare-and-branch per token any more; the remaining delta is scalar bookkeeping for the indexed addressing (moves, lea, sub/add, nop padding); no new call, no memcpy/memset change |
| book construction, reclaimable restore, scaled_v | 274 / 137 / 130 | 202 / 108 / 130 | allocate_kv_group stays out of line (83 instructions, called twice from the constructor and once from restore) with the `bytes % sizeof(kv_block_t)` assert; no store through the arena pointer, no rep stos, no memset, no loop |

Reading against the pass rule: every moved body has the same instruction mix; no
destination read was added on even appends; no scalar dimension loop; no clearing in
allocation or restore. The compiler differences are explained: address mode and register
allocation, plus one cold-path outlining with a once-per-arena assert.

## 8. Rebase onto main 996f58ec82 and the draft PR (2026-09-23)

Words used here: chunk = the page-aligned reclaimable KV storage unit that PR #4455
introduced on `main` (it replaced the one reclaimable arena per book).

- 04:57 UTC, on jhan's "push the branch and create PR": `main` had moved from
  `0a51385e95` to `996f58ec82` (68 files). Two textual conflicts (kv_cache.hpp
  allocate path, heterogeneous_scheduler_compile.cpp includes) and one hidden break
  (main's new t_llama_unit case "Sliding KV chunks reserve and restore transactionally"
  called the pointer forms of set_v/get_v). Rebased with `git rebase --no-verify
  origin/main`; backup branch jhan-kv-typed-tensors-pre-rebase-20260923 = `c3c368d298`.
- Resolution (all in commit 1): `construct_kv_blocks(base, bytes, pages, reclaimable)`
  is called from `allocate_retained_storage` and from `allocate_reclaimable_chunk`
  (offset `pages * byte_offset` = slot_page's); Note [KV block lifetime] reworded; the
  new test uses v_source_row / v_destination_row. Commit messages of commits 2-4
  byte-identical; commit 1's bullet now names the two allocation functions.
- Review (workflow, 3 lenses x 2 refuters, 25 agents): no code defect; one Note
  sentence and the commit-1 bullet reworded (above). Body verification (4 lenses):
  corrections applied to the PR text (Step D placement `--instance 2,4` on cards
  90:00.0 / 93:00.0 and runtron's built-in prompt, not a forced token file; packed-V
  wording; PR #4455 alone for the chunks; Step F method = 19 noinline wrappers;
  per-result commit attribution; cost-data deferral names the four platform blocks).
- Light check on 3bda during the nightly CI lease (jhan's standing rule: light work
  only): `-fsyntax-only` of amx_attn.cpp, t_amx_dispatch_dtype.cpp, t_amx_numerics.cpp,
  heterogeneous_scheduler_compile.cpp, t_llama_unit.cpp with the tree's 16-lane AMX-on
  compile commands, 2 CPUs at nice 19: all rc 0 (2-16 s each); clang-format-19 dry run
  on the 12 files rc 0; `make lint-notes` rc 0 [evidence/3bda-first-test/rebase/
  rebase-syntax-9bd53996cb.log; the later comment-only reword of kv_cache.hpp was
  format-checked again: OK].
- Final commits: `b951ba9b4c` `daf227de13` `959d1ae229` `707159b9ef` (tip). Pushed
  jhan-kv-typed-tensors and the pre-rebase branch. Draft PR #4557
  (https://github.com/positron-ai/tron/pull/4557), label Skip benchmarks, assignee
  jhan-positron; first comment = the evidence tables of sections 7 and this section.
- Pending: the 3bda chain /var/tmp/jhan/tron-issue4525-rebase-chain.sh (waits for the
  lease + 10 min grace, then builds gen (all targets) and gen-amxoff (four tests) on our
  half and runs the four tests plus the sliding-chunk and packed-bits cases; log
  /var/tmp/jhan/tron-issue4525-rebase-chain.log). Then the PR's Verification table gets
  the rebased-tip row and the PR leaves draft (`gh pr ready 4557`).
- Not re-run on the rebased tip: Steps D and E (the 16-lane production code differs
  from the measured code only by the chunk-construction call sites), the host suite
  (the required CI test-host job covers it once the PR is ready), `make lint`, the
  toolchain lint.
- 06:10-06:25 UTC (jhan: apply the C++ coding guide to the PR's code and the plain-English
  rules to its description): 61 guide findings in the PR-added lines (54 unnamed fixed
  values, 7 brace-less loop bodies; 5 finders, 2 refuters each, none refuted) fixed in the
  fifth commit `1c87d66926` (named constants such as V_PLANE_ALIGNMENT_64 and
  PV_TILES_PER_HALF_4, test rows aligned with chunk_alignment, braces); light checks on
  3bda rc 0 (-fsyntax-only of the five translation units, clang-format-19, lint-notes).
  Description rewritten from two independent plain-English checks (about 60 distinct
  violations, mostly undefined terms, semicolons and multi-point paragraphs); report
  status/pr4557-guide-checks.html. The build chain's GO marker now names `1c87d66926`.
- 13:09-13:45 UTC: the CI lease cleared at 13:09; the chain built the AMX-on tree (all
  targets, 308 s; only `t_rinzler` fails, as on main) and the AMX-off tree (274 s) on our
  half and ran the tests on `1c87d66926`: t_llama_unit 44 cases / 252718 assertions in
  both trees (the sliding-chunk case alone 53593, the packed-V bit case alone 28947),
  t_amx_numerics 12301 (real AMX) and 2060 (kill switch, two "AMX unavailable" lines),
  t_amx_dispatch_dtype 1559, t_heterogeneous_scheduler 1900: all pass. Allocation-path
  check of the rebased binary (objdump of gen/t_llama_unit, script
  evidence/3bda-first-test/rebase/alloc_path_check.py): every allocate_retained_storage
  and allocate_reclaimable_chunk instantiation is 68-92 instructions with no backward
  jump, no rep stos and no memset. Logs: evidence/3bda-first-test/rebase/. PR #4557 marked
  ready for review; the GCP Nix CI links go into the PR body when the jobs finish.
  Trap: Catch2 splits a test name on commas; a single-case run needs `\,`.
- ~14:40 UTC: the GCP Nix CI run 35868511322 on `1c87d66926` completed with success (Build
  Tron, Test host, Test FPGA, Test ingest and every lint/contract job pass; the Benchmark
  jobs were skipped by the Skip benchmarks label); Debian smoke passed. The draft-time run
  35826452601 had skipped Build Tron and the test jobs, as round-4 finding J01 predicted.
  The PR body's CI section carries the links. Plan complete.
- ~16:30 UTC: the PR description gained the section "Response to the reviewer's comments on
  #4424": every point of the maintainer's review and API sketch (44 points, verified by one
  mapper and two refuters each), with what PR #4557 does and whether it follows the sketch
  (35 sketch rows: 17 same, 6 same rule with another shape, 6 different for a recorded
  reason, 1 different without a recorded reason, 5 deferred to #4424). Sources and the
  mapping summary are in the session scratchpad; the section itself is on the PR.
