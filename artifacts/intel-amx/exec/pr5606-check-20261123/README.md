# pr5606-check-20261123: build and test of the two commits of tron PR 5606 on delphi-3b35

## Short version

Both commits of PR 5606 build with 0 compiler warnings on delphi-3b35, and all 20 test runs exit with code 0.
With the build option OFF the dispatch test now checks 30,747 assertions instead of 1, and its loaded program
is byte-identical to the option-ON build apart from the 20-byte build ID.
Of 10 one-line faults in the dispatch code, the option-OFF test catches 9, and the one it misses is missed by
the option-ON build too.

## Words used here

- tron: the inference program under test. rinzler: the production server.
- PR 5022: the pull request that lets the AMX attention kernels serve 16 query heads per KV head.
- PR 5606: the reviewer's draft pull request with two commits on top of the head of PR 5022.
- AMX, AVX: CPU instruction sets. AMX works on "tiles" (small matrices in the CPU).
- TRON_AMX_DISPATCH, "the option", "the define": the CMake option (default OFF) that compiles the AMX kernels
  and their call sites. With the option ON, the compiler gets `-DTRON_AMX_DISPATCH`.
- Dispatch code: the call sites in `h/tron/models/self_attention.hpp` that choose AMX or AVX for one KV page.
- Dispatch test: `t_amx_dispatch_dtype`. It replaces the AMX kernels with fakes (plain C++ functions that count
  their calls). So it needs no AMX hardware.
- Kill switch: the environment variable `TRON_AMX_DISABLE=1`. It turns AMX off at run time.
- Fake device: a software stand-in for the FPGA cards, linked into the unit tests.
- S0, S1, S2: the three source states. S0 is the head of PR 5022 (`ddf843ad97`). S1 is the first commit of
  PR 5606 (`c6cba6b0f8`). S2 is both commits (`90a9110be5`, git tree `d6c77bd315`).
- OFF tree: `/var/tmp/jhan/b35-pr5606-off`, configured with the option OFF. ON tree: `/var/tmp/jhan/b35-pr5606-on`,
  configured with the option ON.
- Placeholder: at S0 and S1 the test file has an `#else` branch with one case that only reports success.
- Catch2: the test framework. Assertion: one `REQUIRE` check. Test case, section: a test and its sub-parts.
  Catch2 exits with 42 when an assertion fails.
- KV page: a block of 64 tokens. Dense page: a full page that the query sees completely. Only a dense page
  takes the AMX path.
- bf16: the 16-bit bfloat16 number format. kv_mul: query heads per KV head (4 or 16 here).
- Pack: the copy of one token's query heads into the layout the AMX kernel reads. QK kernel: scores queries
  against keys. PV kernel: multiplies the attention weights with the values.
- Weak symbol: a function that several object files may define (an inline function or a template instance).
  The linker keeps one copy. `nm` prints such symbols with type W or V.
- One-definition rule: the C++ rule that all copies of such a function in one program come from the same text.
- Linker map: a file the linker writes. It names the object file that each part of the binary comes from.
- Loaded section: a part of a binary that the system maps into memory (code, constants, data). Debug
  information is not loaded.
- Registry: `config/test-benchmarks.json`. Per machine class it holds the run time and peak memory of every
  test. Slice (`bin/slice`): the test scheduler that reads it.
- Mutation: a deliberate one-line fault, used to check that a test fails when the code is wrong.

## Rules for the shared machine

- delphi-3b35 is shared. Other users run servers on the first half of the machine.
- Every command here is pinned to our CPUs 96-143 with `nice -n10 taskset -c 96-143`. Builds use `-j40`.
- Every test run sets `SYSTEM_CONFIG="--instance 1,2"`. The tests link the fake device. They open no FPGA
  card and take no huge page.
- No runtron, no rinzler, no benchmark. `bin/slice bench` ran only with `--check` and `--check-platform`.
- Never run `git worktree prune` on that machine. The trees `/var/tmp/jhan/b35-pr5022-final` and
  `/var/tmp/jhan/b35-gdn-stats` were not touched.
- GitHub was not written to.

## Files

| File | What it does |
|---|---|
| common.sh | Settings that every script sources: paths, the three commits, the CPU pin. |
| build-3b35.sh | Moves one tree to one state and builds the test targets. Creates the tree on the first call. |
| tests-3b35.sh | Runs the three tests, each plain and with the kill switch. |
| chain-off-3b35.sh | Steps 2 and 3 in the OFF tree, one after the other. |
| compile-commands-3b35.sh, compile-commands.py | Record which compile commands carry the define. |
| extras-3b35.sh | Counts AMX instructions in the test binary. With `WALL=1` it measures wall time and peak memory. |
| symbols-3b35.sh, symbols.py | Symbol check for the one-definition rule. Links a second time to get the linker map. |
| includers-3b35.sh | Lists the objects compiled from the dispatch header, and which of them the test binary holds. |
| bincmp-3b35.sh, bincmp.py, secthash.py, symbols-compare.py | Compare the test of the OFF tree with the test of the ON tree. |
| mutations-3b35.sh, mutate.py, mutations.tsv, catch-failures.py | Apply each fault, rebuild, run, record, restore. |
| registry-check-3b35.sh | Read-only checks of the registry. |

## How to run

All scripts run on delphi-3b35. The order below is the order of the run.

```
ssh delphi-3b35 'bash ~/workspace/intel-AMX/exec/3b35-inspect-20261112/load-snapshot.sh'
D=~/workspace/intel-AMX/exec/pr5606-check-20261123
ssh delphi-3b35 "OPT=off STATE=S0 bash $D/build-3b35.sh"          # step 1: build, about 2.5 minutes
ssh delphi-3b35 "OPT=off STATE=S0 bash $D/tests-3b35.sh"          # step 1: 6 runs
ssh delphi-3b35 "nohup bash $D/chain-off-3b35.sh >/dev/null 2>&1 &"   # steps 2 and 3, about 3 minutes
ssh delphi-3b35 "OPT=off STATE=S2 WALL=1 WALL_STATES='S0 S1 S2' bash $D/extras-3b35.sh"   # wall times
ssh delphi-3b35 "OPT=off STATE=S2 bash $D/symbols-3b35.sh"        # step 4
ssh delphi-3b35 "nohup bash $D/mutations-3b35.sh >/dev/null 2>&1 &"   # step 5, about 16 minutes
ssh delphi-3b35 "OPT=on STATE=S2 TARGETS='t_amx_dispatch_dtype t_amx_numerics t_llama_unit' bash $D/build-3b35.sh"   # step 6
ssh delphi-3b35 "OPT=on STATE=S2 bash $D/tests-3b35.sh"
ssh delphi-3b35 "OPT=on STATE=S2 bash $D/compile-commands-3b35.sh; OPT=on STATE=S2 bash $D/extras-3b35.sh"
ssh delphi-3b35 "OPT=on STATE=S2 bash $D/symbols-3b35.sh"
ssh delphi-3b35 "bash $D/includers-3b35.sh; OPT=on bash $D/includers-3b35.sh"
ssh delphi-3b35 "bash $D/bincmp-3b35.sh"                          # needs both trees at S2, unchanged
ssh delphi-3b35 "bash $D/registry-check-3b35.sh"                  # step 7
# extra mutation runs
ssh delphi-3b35 "ONLY='m12-dense-tokhi-dropped m04-dense-end-relaxed+m12-dense-tokhi-dropped' PART2=0 SUFFIX=-extra bash $D/mutations-3b35.sh"
ssh delphi-3b35 "OPT=on ONLY=m04-dense-end-relaxed PART2=0 SUFFIX=-on bash $D/mutations-3b35.sh"
```

- Records: `exec/results/pr5606-check-20261123/`. Logs: `exec/logs/pr5606-check-20261123-*.log`.
- Markers: `build-<opt>-<state>.done`, `tests-<opt>-<state>.done`, `chain-off.done`, `mutations*.done`.
- A build must not run in a tree while `mutations-3b35.sh` or `bincmp-3b35.sh` uses that tree.
- Do not edit a script while a copy of it runs. bash reads a script from the shared disk piece by piece.

## Results

All times are UTC on 2026-11-24, from 04:49 to 05:29. That is 2026-11-23, 20:49 to 21:29 PST.

### Machine load

| Snapshot | Our CPUs (96-143 and 223-230) | Second socket (144 CPUs) | First socket | FPGA cards 4-7 |
|---|---|---|---|---|
| Before, 04:49:22 | 0.0 % busy | 0.0 % busy | 42.4 % busy, 61.57 CPUs used by user `disagg` | not open |
| After, 05:26:11 | 0.0 % busy | 0.0 % busy | 42.5 % busy, 61.55 CPUs used by user `disagg` | not open |

- The first half runs three rinzler servers of user `disagg`: two with 15 busy threads each (llama-3.1-8b)
  and one with 31 busy threads (gpt-oss-120b). The process IDs are the same before and after [R1].
- The load average is 62.8 before and 62.4 after. It comes from those three servers [R1].
- The 256 huge pages of 1 GiB on our memory node are free before and after [R1].
- A direct sample of CPUs 96-143 over 2 s shows 0.0 % busy before each test set of the OFF tree [R3].
  The ON-tree test set shows 2.1 %, because a mutation build ran in the OFF tree at that time [R3].

### Builds

Recipe: clang 19.1.7, preset `native`, RelWithDebInfo, `BUILD_INGEST_MODELS=OFF`, ccache [R2].

| Tree | State | Targets | Wall time | Build steps | Compiler warnings |
|---|---|---|---|---|---|
| OFF | S0 | t_amx_dispatch_dtype, t_amx_numerics, t_llama_unit, t_page_share_counters | 143 s | 312 | 0 |
| OFF | S1 | t_amx_dispatch_dtype | 82 s | 10 | 0 |
| OFF | S2 | the same four as S0 | 53 s | 8 | 0 |
| ON | S2 | t_amx_dispatch_dtype, t_amx_numerics, t_llama_unit | 125 s | 311 | 0 |

- "Compiler warnings" counts the lines with `warning:` in the full build log [R2].
- The first configure of each tree prints one CMake warning: the variable `CMAKE_COLOR_DIAGNOSTICS` is not
  used by the project. It is not a compiler warning [R2].
- At S2 the git tree hash of both trees is `d6c77bd315c556ebf78556450562f2427ee660c7`, as expected [R2].
- In the OFF tree, `t_amx_numerics`, `t_llama_unit` and `t_page_share_counters` have the same sha256 at S0
  and at S2. So PR 5606 changes none of these three binaries [R2].

### Test runs

Every run uses `--skip-benchmarks`. Every run ended with the wanted exit code 0 [R3].

| # | State | Option | Run | Exit code | Result |
|---|---|---|---|---|---|
| 1 | S0 | OFF | t_amx_dispatch_dtype | 0 | 1 assertion in 1 test case passes (the placeholder) |
| 2 | S0 | OFF | t_amx_dispatch_dtype, kill switch | 0 | 1 assertion in 1 test case passes |
| 3 | S0 | OFF | t_amx_numerics | 0 | 2,560 assertions in 1 test case pass |
| 4 | S0 | OFF | t_amx_numerics, kill switch | 0 | 2,560 assertions in 1 test case pass, 0 cases skip |
| 5 | S0 | OFF | t_llama_unit | 0 | 265,564 assertions in 75 test cases pass |
| 6 | S0 | OFF | t_llama_unit, kill switch | 0 | 265,564 assertions in 75 test cases pass |
| 7 | S1 | OFF | t_amx_dispatch_dtype | 0 | 30,747 assertions in 1 test case pass |
| 8 | S1 | OFF | t_amx_dispatch_dtype, kill switch | 0 | 30,747 assertions in 1 test case pass |
| 9 | S2 | OFF | t_amx_dispatch_dtype | 0 | 30,747 assertions in 1 test case pass |
| 10 | S2 | OFF | t_amx_dispatch_dtype, kill switch | 0 | 30,747 assertions in 1 test case pass |
| 11 | S2 | OFF | t_amx_numerics | 0 | 2,560 assertions in 1 test case pass |
| 12 | S2 | OFF | t_amx_numerics, kill switch | 0 | 2,560 assertions in 1 test case pass, 0 cases skip |
| 13 | S2 | OFF | t_llama_unit | 0 | 265,564 assertions in 75 test cases pass |
| 14 | S2 | OFF | t_llama_unit, kill switch | 0 | 265,564 assertions in 75 test cases pass |
| 15 | S2 | ON | t_amx_dispatch_dtype | 0 | 30,747 assertions in 1 test case pass |
| 16 | S2 | ON | t_amx_dispatch_dtype, kill switch | 0 | 30,747 assertions in 1 test case pass |
| 17 | S2 | ON | t_amx_numerics | 0 | 21,521 assertions in 5 test cases pass |
| 18 | S2 | ON | t_amx_numerics, kill switch | 0 | 6,671 assertions pass; 3 cases pass, 2 cases skip ("AMX unavailable") |
| 19 | S2 | ON | t_llama_unit | 0 | 265,564 assertions in 75 test cases pass |
| 20 | S2 | ON | t_llama_unit, kill switch | 0 | 265,564 assertions in 75 test cases pass |

- Rows 1 and 7 confirm the reviewer's numbers: 1 placeholder assertion before, 30,747 assertions after [R3].
- Rows 3-6 and 11-14 are equal. `t_amx_numerics` and `t_llama_unit` give the same counts at S0 and at S2 [R3].
- Rows 15-20 equal the numbers of the earlier round at the head of PR 5022 [R13].
- `t_page_share_counters` was built, as the task says. It was not run.

### Compile commands

The build writes one compile command per source file to `gen/compile_commands.json` [R4].

| Tree, state | Commands in the build | Define in the command of `t/t_amx_dispatch_dtype.cpp` | Commands of the library tron with the define | Commands with the define in the whole build | Command for `src/tron/kernels/amx_attn.cpp` |
|---|---|---|---|---|---|
| OFF, S1 | 524 | 1 time | 0 of 17 | 1 | none |
| OFF, S2 | 524 | 1 time | 0 of 17 | 1 | none |
| ON, S2 | 525 | 1 time | 18 of 18 | 204 in 145 targets | 1 |

- In the OFF tree the kernel file is not compiled: the build has no build statement, no object file and no
  member of `libtron.a` for it [R4].
- In the ON tree the define appears once in the test's command, not twice [R4].
- With the define removed from the registration line, the count for the test is 0 [R10].

### AMX instructions in the test binary

`objdump -d --no-show-raw-insn gen/t_amx_dispatch_dtype`, 1,457,966 lines of disassembly [R5].

| Tree, state | tdpbf16ps | tileloadd | tilestored | tilezero | ldtilecfg | tilerelease |
|---|---|---|---|---|---|---|
| OFF, S2 | 0 | 0 | 0 | 0 | 0 | 0 |
| ON, S2 | 0 | 0 | 0 | 0 | 0 | 0 |

The count is 0 in the ON tree too, because the test's fakes replace the kernels [R5].

### Wall time and peak memory

5 runs of each kept binary of the OFF tree, with `/usr/bin/time -f "%e s %M KiB"`. Load average 65.8, our
CPUs 0.0 % busy over 2 s, no build running [R6].

| Binary | Wall time, 5 runs | Peak resident memory, 5 runs |
|---|---|---|
| S0 (placeholder), 24,389,992 bytes | 0.65 to 0.67 s | 6,912 KiB (6.75 MiB) in all 5 runs |
| S1, 36,623,048 bytes | 0.78 to 0.79 s | 99,072 to 101,376 KiB (96.75 to 99.0 MiB) |
| S2, 36,623,024 bytes | 0.76 to 0.78 s | 99,072 to 101,376 KiB (96.75 to 99.0 MiB) |

- With its real cases the test takes about 0.11 s longer and 90 to 92 MiB more memory than the placeholder [R6].
- The S2 numbers equal the option-ON numbers of the earlier round: 0.77 to 0.79 s and 99,072 to 101,376 KiB [R13].
- The first attempt of this step failed with exit code 127. The kept copies were in `gen/keep/`, and the
  binary finds two shared libraries relative to its own folder. The copies now sit in `gen/`.

### Symbol check for the one-definition rule

Question: the test's own object is compiled with the define, and everything it links is compiled without.
Does any other linked object hold a second, different copy of a function of the dispatch code?

Link line of the test in the OFF tree at S2: 4 object files, 10 static libraries, 6 shared libraries. The
test's object is the fourth object file, after `fake.cpp.o`, `testlog.cpp.o` and `mwaitx.cpp.o` [R7].

| Count | OFF tree, S2 | ON tree, S2 |
|---|---|---|
| Symbols defined in the test's object | 9,788 | 9,788 |
| Weak symbols among them (nm types W, V, u) | 4,777 (4,263 W, 514 V, 0 u) | 4,777 |
| Other objects on the link line that define a symbol | 356 | 357 |
| Objects that the linker really used (linker map) | 153 | 153 |
| A. Weak symbols of the test that another object on the link line also defines | 598 | 600 |
| A. Of those, with a different size | 387 | 389 |
| B. The same against the 153 objects the linker used | 588 | 588 |
| B. Of those, with a different size | 383 | 383 |
| Of the 588, taken by the linker from the test's object / from another object | 578 / 10 | 578 / 10 |
| Common symbols whose name contains self_attention, apply_page, apply_dense or amx_attn | 0 | 2 |
| Symbols with one of those words in any other object | 0 | 15, in `libtron.a(amx_attn.cpp.o)` |
| Symbols of the template `tron::self_attention<...>` in the test's object / in other objects | 68 / 0 | 68 / 0 |
| Undefined symbols of the test's object that contain self_attention, attn_accum or amx_attn | 0 of 278 | 0 of 278 |

The 598 common symbols of the OFF tree, by library [R7]:

| Library | Common symbols | With a different size |
|---|---|---|
| C++ standard library | 285 | 208 |
| nlohmann (JSON library) | 177 | 80 |
| fmt (formatting library) | 111 | 86 |
| Other | 13 | 8 |
| Names that mention `tron::` | 12 | 5 |

- The 5 `tron::` symbols with a different size are tracing templates of the perfetto library and two inline
  functions of `tron::fuse::stats`. None belongs to the dispatch code [R7].
- The 2 common symbols of the ON tree are the PV kernel for 4 and for 16 heads. The real kernel object
  `libtron.a(amx_attn.cpp.o)` defines them too (680 and 1,269 bytes; the fakes have 1,082 bytes each).
  The linker does not use that object: the linker map shows 0 sections from it [R7].

Symbols of namespace `tron::amx_attn_h128g4` in the final binary (the same 5 in both trees) [R7]:

| Symbol | Type, size | Taken from |
|---|---|---|
| `available()` | strong, 13 bytes | the test's object |
| `begin_region()` | strong, 6 bytes | the test's object |
| `end_region()` | strong, 6 bytes | the test's object |
| `weights_times_v_128x4<4>` (PV fake) | weak, 1,082 bytes | the test's object |
| `weights_times_v_128x4<16>` (PV fake) | weak, 1,082 bytes | the test's object |

The pack fake and the QK fake have no symbol. The compiler inlined them into their callers [R7].

Who is compiled from the dispatch header `h/tron/models/self_attention.hpp` [R8]:

- 5 of the 197 built objects of the OFF tree: three members of `libtron.a` (`gof.cpp.o`, `models/cache.cpp.o`,
  `scheduler/token_tree.cpp.o`), the test's object, and the object of `t_llama_unit`.
- The linker takes 0 sections from each of the three library members for this test.
- So the test's object is the only object inside `gen/t_amx_dispatch_dtype` that is compiled from the header.

OFF tree against ON tree, both at S2 [R9]:

| Compare | Result |
|---|---|
| The test's own object, instructions and relocation targets (`objdump -dr`) | same sha256 `759999e83f244366` in both trees |
| The linked binary, instruction listing with addresses masked | 0 of 1,442,554 lines differ; 15,400 functions in both |
| The linked binary, loaded sections byte by byte | 28 of 29 sections are identical, with the same addresses |
| The one section that differs | `.note.gnu.build-id`, 20 of its 36 bytes |
| The code section `.text` | 5,556,388 bytes, identical |
| Sections with a different size | only debug sections (`.debug_info`, `.debug_str`, `.debug_line`, `.debug_str_offsets`, `.debug_line_str`) |
| Sizes of the 4,777 weak symbols of the test's object | 0 differ |
| Sizes of the 2,327 definitions in other objects | 0 differ |
| Output of the plain test run, 202 lines, time stamps and counters masked | 0 lines differ |

What this shows:

- No other object on the link line defines a function of the dispatch template. The linker has no second copy
  that could disagree [R7].
- The size differences sit in template functions of the standard library, fmt and the JSON library. The ON
  tree has the same 383 differences. So they come from other compile flags, not from the define [R7][R9].
- The test built in the OFF tree is the same loaded program as the test built in the ON tree. Only the build
  ID differs [R9].

What this cannot show:

- A symbol check sees only functions that have a symbol. It cannot see a class layout, or a function that
  the compiler inlined.
- It covers one build recipe: clang 19.1.7, RelWithDebInfo, preset `native`, `BUILD_INGEST_MODELS=OFF`. The
  required lane builds with Nix and with the lane's model flags. That build was not made here.
- It covers this test binary only. Every other test still compiles the header without the define.

### Mutations (OFF tree, S2)

Each fault changes one line inside an `#ifdef TRON_AMX_DISPATCH` region of `h/tron/models/self_attention.hpp`.
The script checks that the line lies inside such a region. Line numbers after "check" are lines of
`t/t_amx_dispatch_dtype.cpp` at S2. The test has 9 sections. The unchanged test exits with 0 and passes
30,747 assertions [R10].

| Fault | Line | Change | Exit code | Assertions: passed, failed | Sections that fail | First failed check |
|---|---|---|---|---|---|---|
| m01 eligibility inverted | 1538 | `amx_eligible && available()` to `!amx_eligible && available()` | 42 | 7,371 passed, 5 failed | 5 of 9 | line 224: `pack_calls`, 0 instead of 1 |
| m02 `available()` dropped | 1538 | `amx_on = amx_eligible;` | 42 | 25,515 passed, 2 failed | 2 of 9 | line 224: `pack_calls`, 1 instead of 0 |
| m03 window test flipped | 1720 | `<` to `>=` in the sliding-window clause of the dense-page test | 42 | 15,166 passed, 3 failed | 3 of 9 | line 225: `qk_calls`, 0 instead of 1 |
| m04 full-page test relaxed | 1718 | `end == page::page_size` to `end <= page::page_size` | 0 | 30,747 passed | 0 of 9 | none: NOT caught |
| m05 pack skipped | 1694 | `if (!packed.test(...))` to `if (packed.test(...))` | 42 | 7,371 passed, 5 failed | 5 of 9 | line 224: `pack_calls`, 0 instead of 1 |
| m06 PV call skipped | 1789 | `if (false)` in front of the PV kernel call | 42 | 15,169 passed, 3 failed | 3 of 9 | line 226: `pv_calls`, 0 instead of 1 |
| m07 wrong group offset | 1696 | `kv_head * operation_kv_mul * head_size` to `kv_head * head_size` | 42 | 26,618 passed, 1 failed | 1 of 9 | line 292: packed value 1.0625 instead of 2.0 |
| m08 16 heads sent to the 4-head QK kernel | 1761 | `qk_rowmajor_128x4<operation_kv_mul>` to `<GROUP_HEADS_4>` | 42 | 18,307 passed, 2 failed | 2 of 9 | line 229: `qk_group_heads`, 4 instead of 16 |
| m09 every head reads PV row 0 | 1798 | `row{amx_o + offset * head_size}` to `row{amx_o}` | 42 | 15,604 passed, 3 failed | 3 of 9 | line 281: `v_star`, 1.0 instead of 2.0 |
| m10 merge dropped | 1802 | `s_star = s_star * corr + sum` to `s_star = sum` | 42 | 24,499 passed, 3 failed | 3 of 9 | line 276: `s_star`, 64 instead of 128 |
| m11 compile-time gate inverted | 1629 | `if constexpr (amx_eligible)` to `if constexpr (!amx_eligible)` | - | does not compile | - | static assertion "the AMX query packer reads q.data as bf16". Not counted. |

Totals: 10 faults compile. The test catches 9. It does not catch m04. One more fault does not compile [R10].

Why m04 is not caught, with three extra runs [R10]:

| Extra run | Tree | Exit code | Result |
|---|---|---|---|
| m12: line 1719, the clause `pg.at_offset(page_size - 1) < range.tok_hi` replaced by `true` | OFF | 0 | 30,747 assertions pass: NOT caught |
| m04 and m12 together (a two-line control, not a one-line fault) | OFF | 42 | 22,957 passed, 2 failed; the 2 partial-page sections fail at line 225 (`qk_calls`, 1 instead of 0) |
| m04 alone | ON | 0 | 30,747 assertions pass: NOT caught |

- The dense-page test has two clauses that both reject the 63-token page of this test: the count of active
  tokens (line 1718) and the position of the last token against the end of the visible range (line 1719) [R12].
- The test builds its page so that the visible range ends at the last token [R12]. So each clause alone still
  rejects the page.
- The test does catch the removal of both clauses together.
- The ON tree misses m04 too. So this gap is a property of the test at the head of PR 5022. PR 5606 does not
  cause it.

The define itself [R10]:

| Case | State | Build | Define in the compile command | Exit code | Result |
|---|---|---|---|---|---|
| m-define-S2: `DEFINES TRON_AMX_DISPATCH` removed from the registration line | S2 | compiles and links, 84 s | 0 times | 42 | 7,371 passed, 5 failed; 5 of 9 sections fail at line 224 (`pack_calls`, 0 instead of 1) |
| m-define-S1: the same | S1 | compiles and links, 4 s | 0 times | 0 | 1 assertion in 1 test case passes (the placeholder) |

- At S2 the five failing sections are the five that expect a pack: every bf16 section with AMX available.
- At S1 the binary without the define has the sha256 of the S0 binary (`cd1ded79fbabafa4`).
- So the second commit does what its message says: without the guard, a lost define makes the test fail.

After every run the tree is back at S2, `git status --porcelain` prints nothing, and each rebuilt binary has
the sha256 it had before [R10].

### Registry

Read-only, in the OFF tree at S2 [R11].

| Machine class | Row of `t_amx_dispatch_dtype` |
|---|---|
| genoa96 | times 0.419 s, 0.422 s, 0.416 s for 1, 2, 4 slices; `max_rss_mb` 8, 8, 8 |
| granite_rapids_6962p (the class of delphi-3b35) | times 0.834 s, 0.847 s, 0.602 s for 1, 2, 4 slices; `max_rss_mb` 8, 8, 8 |

- The classes genoa32 and granite_rapids_6960p have no row for this test.
- PR 5606 does not change `config/test-benchmarks.json`.
- `bin/slice bench --check-platform`: exit code 0, output "bench --check-platform: ok".
- `bin/slice bench --check`: exit code 0, output "bench --check: ok", with two warnings. One names 126 CTest
  entries without a command (tests that this tree did not build). One names `t_proxy_gptoss` as missing from
  this machine class.
- The scheduler's drift warning for this test: none. That check compares labels, minimum slices and skip codes.
  It does not compare memory.
- Both rows say 8 MB. The measured peak at S2 is 96.75 to 99.0 MiB on this machine [R6].
- `bin/slice bench --update` was not run. It measures on both halves of the machine.

## Claims of PR 5606 against these records

| Claim (comment or PR body) | Result here |
|---|---|
| With the option off the test runs 30,747 assertions | Confirmed at S1 and S2 (rows 7-10) |
| Before, it was one placeholder assertion | Confirmed at S0 (rows 1-2) |
| The first commit builds and passes on its own | Confirmed (S1 build, rows 7-8) |
| It passes with the option on | Confirmed (rows 15-16) |
| Eight one-line faults each make it fail | Insufficient data: the PR does not list the eight faults. Of our own 10 faults, 9 fail the test. |
| Removing the define makes it fail | Confirmed at S2 (m-define-S2, exit code 42) |
| With the guard, a lost define compiles to the placeholder and passes | Confirmed at S1 (m-define-S1, exit code 0, 1 assertion) |
| Nothing else sees the option | Confirmed for this build: 1 of 524 compile commands carries the define, and three other test binaries are unchanged |
| No other translation unit in this binary instantiates the template for the test's models | Confirmed: 0 symbols of the template in the 356 other objects; the test's object is the only linked object compiled from the header |
| The registry rows say 8 MB, and the test peaks near 99 MiB | Confirmed: 8 MB in both rows; 96.75 to 99.0 MiB measured at S2; 6.75 MiB for the placeholder |
| The test registers the define the way `t_page_share_counters` does | Confirmed: `t/CMakeLists.txt` line 276 has `DEFINES TRON_PAGE_SHARE_COUNTERS`; that line is on main since commit `f6794a7c15` [R15] |

## Not covered

- The required lane itself. No Nix build was made, and no GitHub workflow was started.
- A build with `BUILD_INGEST_MODELS=ON` or with the model flags of the required lane.
- Any other compiler or build type than clang 19.1.7, RelWithDebInfo.
- The machine class genoa96 (AMD). All runs are on one Intel Xeon 6962P host.
- `t_page_share_counters` was built at S0 and S2. It was not run.
- The filtered runs of `t_amx_numerics` (per section, JUnit report, `[kv_data]`) of the earlier round.
- State S1 with the option ON. The ON tree was built at S2 only.
- The rest of PR 5022. Only the three tests named above ran.
- Throughput, token identity, and any run with a real FPGA card.
- The registry update. `bin/slice bench --update` needs a run on each machine class.
- The reviewer's eight faults. They are not listed, so they could not be repeated.
- The reviewer's note that his earlier registration line for `t_amx_numerics` does not configure.
- A dense-page case where the page has fewer than 64 active tokens but the visible range goes on, and a full
  page that the visible range covers only partly. No section of the test builds either case (see m04, m12).

## State left on delphi-3b35

- `/var/tmp/jhan/b35-pr5606-off` and `/var/tmp/jhan/b35-pr5606-on`: both at S2, `git status --porcelain` prints
  nothing. Sizes: 2.3 GiB and 2.2 GiB.
- Files that git ignores exist beside `gen` in both trees: `.cargo/`, `.rustup/` and `rust/rustenv`. The
  configure step of the project creates them.
- `gen/` of the OFF tree also holds the kept test binaries `t_amx_dispatch_dtype.S0`, `.S1`, `.S2`. `gen/keep/`
  of both trees holds the second link and its map. `gen/` of the ON tree holds `t_amx_dispatch_dtype.S2`.
- Git added the two worktree entries to `/home/jhan/workspace/tron/.git/worktrees/`.

## References

Paths are relative to `/home/jhan/workspace/intel-AMX/exec/` unless they start with `/`.

- [R1] `results/pr5606-check-20261123/load-snapshot-before.txt`, `load-snapshot-after.txt`
- [R2] `results/pr5606-check-20261123/build-off-S0.txt`, `build-off-S1.txt`, `build-off-S2.txt`, `build-on-S2.txt`;
  full logs `logs/pr5606-check-20261123-build-*-ninja.log` and `-configure.log`
- [R3] `results/pr5606-check-20261123/tests-off-S0.txt`, `tests-off-S1.txt`, `tests-off-S2.txt`, `tests-on-S2.txt`;
  one log per run in `results/pr5606-check-20261123/tests/`
- [R4] `results/pr5606-check-20261123/compile-commands-off-S1.txt`, `compile-commands-off-S2.txt`, `compile-commands-on-S2.txt`
- [R5] `results/pr5606-check-20261123/amx-insn-off-S2.txt`, `amx-insn-on-S2.txt`
- [R6] `results/pr5606-check-20261123/wall-times-off.txt`
- [R7] `results/pr5606-check-20261123/symbols-off-S2.txt`, `symbols-on-S2.txt`; lists and linker maps in
  `symbols-off-S2/` and `symbols-on-S2/`
- [R8] `results/pr5606-check-20261123/includers-off-S2.txt`, `includers-on-S2.txt`
- [R9] `results/pr5606-check-20261123/bincmp-off-on-S2.txt`
- [R10] `results/pr5606-check-20261123/mutations.txt`, `mutations-extra.txt`, `mutations-on.txt`; one test log per
  case in `results/pr5606-check-20261123/mutations/`
- [R11] `results/pr5606-check-20261123/registry-check.txt`, `registry-check--check.out`, `registry-check--check-platform.out`
- [R12] `h/tron/models/self_attention.hpp` lines 1710-1721 (the dense-page test) and
  `t/t_amx_dispatch_dtype.cpp` lines 139-140 and 156-157 (page and visible range), both at commit `90a9110be5`
- [R13] `results/pr5022-final-20261119/tests.txt`, `wall-times.txt` (the earlier round, head of PR 5022, option ON)
- [R14] `results/pr5606-check-20261123/inputs/comment-7118448228.md`, `pr5606-body.md`, `pr5606.diff`
- [R15] `t/CMakeLists.txt` line 276 at commit `90a9110be5`; `git merge-base --is-ancestor f6794a7c15 3bea58b788`
  succeeds in `/home/jhan/workspace/ai-runs/tron-glimmer-amx`
