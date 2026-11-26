# Review checks distilled from the review of tron PR 5022 (draft)

Short version: The review of PR 5022 found five avoidable costs on the per-token attention path, and three of them concern code the PR did not change. The search step of our present hot-path check covers only added lines and a keyword list, so none of the five matches it. This draft holds 6 cost checks, 5 test checks, 4 claim checks, one proof method and one form for a finding, each with its precedent.

Status on 2026-11-19, after jhan's decision:

- Section A (cost) and section B (tests) are in the skill `tron-code-review`.
- The three rules for writing code are in the skill `cpp-coding-guide`, section "Hot paths".
- Checks A2 and A3 are also in check 30 of the skill `folks-code-review` (named Wade-code-review until 2026-11-19), as its "raised size" trigger.
- Sections C, D, E and F are in no skill. C1, C2 and C4 overlap checks 7, 17 and 6 of `folks-code-review`. C3 (control rows) is new.

Card numbers such as I5 are the card numbers of the reply page `/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html`.

## Words used here

- Hot path: code that runs once per token, once per KV page or once per layer.
- KV page: a 64-token block of the key/value cache. A dense page is a full page inside the attention window. Only dense pages use the AMX kernels.
- AMX: Intel's matrix instruction set. AVX-512: Intel's 512-bit vector instruction set.
- kv_mul: the number of query heads per KV head. It is 4 for llama-3.1-8b and 16 for Muse Glimmer.
- Size parameter: a value that sets how much work one call does, for example kv_mul.
- Opaque call: a call to a function the compiler cannot see into, for example a function defined in another source file.
- View: an object that points at memory it does not own, for example `tron::const_view` or `std::span`.
- Opcode census: a count of the instructions of one compiled function, grouped by instruction name.
- Object compare: compile one source file at two commits with the same compiler and flags, then compare the instruction listings function by function.
- Mutation: a small deliberate break of the code, made to see whether a test fails.
- Control row: a benchmark row whose code path the PR does not touch.
- HEAD: the reviewed commit. BASE: the merge base of HEAD and the target branch.

## A. Cost on per-token paths

### A1. Follow the size parameter, not the diff

Look for: a PR that lets a size parameter take a larger value on an existing path. Examples: a new model shape, a larger template argument, a wider batch.

How to check:

1. Name the parameter, its old value and its new value.
2. Open every function on that path at HEAD. Read the unchanged lines too.
3. For each line whose cost grows with the parameter, write the cost per call at both values, in bytes or in instructions.
4. Write how often the function runs: per token, per KV head, per page, per layer.
5. Compare the growth of the cost with the growth of the parameter. A cost that grows faster than the parameter needs check A5.

Do not flag: a path the new value cannot reach. Read the gate first.

Finding wording: "`<line>` costs `<N>` bytes per `<call>` at `<old value>` and `<M>` bytes at `<new value>`. It runs once per `<unit of work>`."

Seen in: PR 5022 let kv_mul be 16 on the AMX path, where it was 4. Three of its five cost findings concern code the PR did not change (I5, I6, I4). One concerns a loop in which the PR changed one token, `GROUP_HEADS_4` to `group_heads` (I9). One concerns new code (I12) [Ref1][Ref3].

### A2. A declaration that fills memory before a full overwrite

Look for: a local object declared on a hot path, where the next writer sets every element. These types fill their storage on default construction: `tron::tensor`, a `std::array` or a struct written with `{}` or `()`, `std::vector<T>(n)`, `T buf[N] = {}`.

How to check:

1. Read the default constructor of the type. The declaration line shows no work. In tron, `tensor() : data() {}` zero-fills, and the two-dimension form does the same for each row [Ref4].
2. Compute the fill size: element count times element size, in bytes per call.
3. Confirm that every element is written before any read. Read the writer's loop bounds for every value of the size parameter.
4. Look for a constructor that skips the fill. In tron it is `tensor(uninitialized_t)` [Ref4].

Fix:

```cpp
// uninitialized: the QK kernel below writes every element before any read.
tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};
```

Do not flag:

- a buffer that is read before it is fully written, such as an accumulator;
- a buffer whose untouched elements are read later as zeros;
- a few scalars;
- cold code: startup, teardown, tests.

Do not rely on the optimizer. It removes the fill only when it can see the overwrite. Before an opaque call the fill stays [Ref7].

Seen in: I5. The declaration zero-filled 4,096 bytes per dense page visit at kv_mul 16, and 1,024 bytes at kv_mul 4. The QK kernel, in another source file, then wrote every element. Accepted [Ref1][Ref2].

### A3. A copy made only to change the type

Look for: inside a loop on a hot path, an owning local (tensor, array, vector, string) that is filled by `memcpy`, `std::copy` or assignment and is then only read.

How to check:

1. Ask why the copy exists. Read the signature of the function that reads the copy.
2. Look for a view type that satisfies the same signature.
3. Check the three conditions of a view. The source stays alive and unchanged while the view is read. Source and destination do not overlap. The base address and every offset meet the alignment that the view type claims.
4. Compute the copy size: bytes per iteration times iterations per call.

Fix:

```cpp
// before: 512 bytes copied per head
tensor<operation_head_size> scratch;
std::memcpy(&scratch[0], amx_o + offset * operation_head_size,
    operation_head_size * sizeof(float));
head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));

// after: a view over the same row, no copy
tron::const_view<float, true, false, tron::seq<operation_head_size>> row{
    amx_o + offset * operation_head_size};
head_sp.v_star.set(fma(head_sp.v_star, corr_, row));
```

Remove an include that only the copy needed.

Do not flag:

- a snapshot: the source is overwritten while the copy is still read;
- a conversion, for example bf16 to fp32;
- a copy that provides an alignment the reader requires.

Seen in: I6. 16 copies of 512 bytes each, 8,192 bytes per dense page visit at kv_mul 16. `fma` accepts any `expression`, and `const_view` is one. The reviewer also checked the alignment: the buffer is 64-byte aligned and each row offset is a multiple of 512 bytes. Accepted [Ref1][Ref2][Ref5].

### A4. Work done before the test that decides whether it is needed

Look for: a preparation step (pack, convert, gather, look up, allocate) that runs before a condition, where one branch never reads the result.

How to check:

1. List the readers of the result on each branch.
2. Find how often the branch without a reader runs. Use counters or an exit report. Do not guess.
3. Search the tests for an assertion that pins the order. A pinned order needs a stated reason.
4. Compute the wasted cost: cost per call times the share of calls that take the branch without a reader.

Fix: do the work at first use, inside the branch that reads it.

Do not flag: an order with a stated and measured reason. Then ask whether the new value of the size parameter changes that measurement.

Seen in: I4. The query group is packed before the dense-page check, and a test requires one pack on a partial page. The order was deliberate at kv_mul 4: the pack cost 63 ns on a Xeon 6962P, and 21 to 24 % of the AMX-on page-range calls had no AMX page at prompt 2048 and at prompt 8192. The reviewer reports about 660 ns for the 16-head pack on an AMD EPYC 9654. Deferred to a follow-up issue that starts with a measurement [Ref1][Ref2].

### A5. A scalar loop inside a vector kernel

Look for: a loop in kernel code that moves or converts one element per iteration, at a new or larger instantiation.

How to check:

1. Compile the file to assembly with the project's compiler and flags.
2. Count the instructions of the function and find its most frequent instruction. Compare the instantiations.
3. Time one call of each instantiation on the target CPU.
4. Name the compiler, the flags and the CPU in the finding. A count from another compiler is a hint. A time from another CPU is a hint.

Seen in: I9. `pack_q_group_128x4<16>` compiled to 512 `vpextrw` stores. The reviewer measured 660 ns per call against 71 ns for 4 heads (clang 19, `-O3`, AMD EPYC 9654). The element count grew 4 times and the time grew 9.3 times. We confirmed the scalar loop by reading. We did not reproduce the two times. Deferred [Ref1][Ref2].

### A6. The same intermediate value computed once per lane

Look for: a helper with an index as template parameter that is called once per index, where an early stage depends on only part of the index.

How to check:

1. Count the distinct intermediate results. Count the computed ones.
2. Confirm the count in the object code of the project's compiler. Compilers differ here.

Fix: compute the shared stage once, then finish each lane from it.

Seen in: I12. The 16-head store emits 48 shuffle instructions per 16-token block where 32 are enough. clang 19.1.7, the project's compiler, emits the 48. g++ 11.4 merges the duplicates without a source change. Deferred [Ref1][Ref2].

### How to word a cost finding

- State the quantity with its unit and its frequency: "8,192 bytes of memcpy per dense page visit".
- Name a fix that uses something the code base already has.
- Say what was not measured: "I did not check whether thin LTO removes the fill."
- Say whether it blocks the merge. The reviewer marked the two larger rewrites "not a blocker" and "fine as a follow-up".
- A change of cost needs its own number before it merges. Without one, the PR body says that the benchmarks predate the change.

### The same points as rules for writing code

- On a hot path, declare a scratch buffer with `{uninitialized}` when the next writer sets every element. Add one comment line that names the writer.
- Pass a view when the reader accepts any expression. Do not copy into a temporary to change the type.
- Test the condition first. Prepare for a branch inside that branch.

## B. Tests: which mutation survives?

For each new test section, apply these mutations and name the assertion that fails. A mutation with no failing assertion is a finding.

### B1. Shrink a loop bound

The test counted calls and never read the outputs. "An epilogue that only merged 4 of the 16 heads would still pass." Fix: read every output the code writes. Require the exact value when the fake kernels make it exact. Seen in: I19 [Ref1].

### B2. Shift a base index or a stride

The test called with index 0 only. So the term `kv_head * kv_mul * head_size` was always 0, and a wrong base could not fail. Fix: add one section with a nonzero index. Seen in: I17 [Ref1].

### B3. Enlarge a loop bound past the buffer

The test checked only the rows the code should write. A bound that is too large would read past the buffer, and the test would pass. Fix: give the input extra rows that hold a sentinel value. Require the rows the code must not touch to stay unchanged. Keep the mutated code inside the test's own buffers, because a read of stack garbage gives no deterministic failure. Seen in: I24, with the fix changed by us in that last point [Ref1][Ref2].

### B4. Run the new value on every arm

The new 16-head value ran only on a full page. The partial-page arm and the kill-switch arm ran with the old value. Fix: add the new value to each arm. Seen in: I21 [Ref1].

### B5. Code that needs no special hardware must not sit behind a hardware gate

Three AVX-512 lanes were reachable only through a test case that skips on a host without AMX. They had run in no CI lane. Fix: move the code to a place that a normal build reaches, and test it without the gate.

Check the exit codes as well. Catch2 returns 0 when some cases pass and others skip. It returns 4 when every selected case skips. Seen in: I10 and I26 [Ref1][Ref2].

## C. Claims

### C1. "CI covers this"

Search the build log of the required lane for the build option. Zero matches means that the lane did not build the code.

```
gh run view --job <job id> --log | grep -c <OPTION_NAME>
```

Seen in: I7. A source comment said that the CMake CI lane configures with the option on. No lane that runs on pull requests did [Ref1].

### C2. Documentation outside the diff

After a change of behavior, search the documentation for sentences that describe the old behavior. Seen in: I8. `README.ci.md` still said "skip with a warning" [Ref1].

### C3. Control rows in a benchmark table

A row whose path runs no PR code must fall inside the noise band. When it does not:

1. Say so in the table.
2. Read the sign of the difference in each repetition. The same sign in every repetition means a constant offset between the two binaries.
3. More repetitions do not remove a constant offset. An A/A pair (two builds of one commit) measures its size.

Seen in: I13. A row without PR code on its path showed +0.56 tokens per second against a band of 0.33. The difference was positive in all four repetitions. The reviewer's fix was more repetitions. We changed it to a statement in the PR body [Ref1][Ref2].

### C4. A sentence in templated code names the arguments it holds for

A warning that is true only for fewer than 16 heads was written without that condition. A `static_assert` message claimed a limit that the code does not have. Seen in: I3 and I14 [Ref1].

## D. Proof that a refactor changes nothing

Compile the function at BASE and at HEAD with the same compiler and flags. Compare the instruction counts and the listings. The reviewer's result for the 4-head kernel: 204 against 204 instructions, 0 different lines. Name the compiler, because the result holds for that compiler only. Seen in: I11 [Ref1].

## E. Form of a finding

1. The claim, at a line.
2. The scenario or the quantity: which wrong code would pass, or how many bytes per call.
3. The fix, with code.
4. The severity.
5. The evidence line: `Checked by: <command> -> <output>`.
6. What was not checked.

All 26 comments of the review carry parts 1 and 5 [Ref1].

## F. On the author's side: check the fix separately from the finding

In PR 5022 we confirmed 24 of the 26 findings and partly confirmed 2. None was wrong. We changed the fix in 9 comments before we accepted it. Details were off in 4 confirmed comments (I7, I8, I24, I26) [Ref2].

So a correct finding does not make its fix correct. Re-run the evidence line first. Then test the fix as if it were a new change.

## References

- [Ref1] Review 5623855297 of tron PR 5022 by `ishapira-positron`, at commit 4c4b7b8864: https://github.com/positron-ai/tron/pull/5022#pullrequestreview-5623855297. Comment ids: I3 r4356062368, I4 r4356062294, I5 r4356061865, I6 r4356062246, I7 r4356060700, I8 r4356061170, I9 r4356061055, I10 r4356060885, I11 r4356062875, I12 r4356062057, I13 r4356062436, I14 r4356061630, I17 r4356060971, I19 r4356060801, I21 r4356062178, I24 r4356061782, I26 r4356061969.
- [Ref2] Our checks and decisions: `/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html`, cards I1 to I26 and card D2, state of 2026-11-19. Nothing is posted yet.
- [Ref3] `git diff -U0 6198824246 4c4b7b8864 -- h/tron/models/self_attention.hpp src/tron/kernels/amx_attn.cpp`: no changed line at 1755 or at 1795-1797 of `self_attention.hpp`. In the pack loop of `amx_attn.cpp` one token changed.
- [Ref4] `h/tron/tensor/tensor.hpp` at 4c4b7b8864: lines 40-42 (`tensor() : data() {}`), 46 and 260 (`tensor(uninitialized_t) noexcept {}`), 254-256 (`std::construct_at(&data)`).
- [Ref5] `h/tron/models/self_attention.hpp` at 4c4b7b8864: line 1755 (`s_pages`), lines 1787-1807 (PV output and the per-head copy). `h/tron/kernels/expr.hpp:537-542` (`fma`). `h/tron/tensor/view.hpp:361-362` (`const_view`).
- [Ref6] `/home/jhan/.claude/skills/Wade-code-review/references/procedures.md:351`: the search of check 30 reads added lines only. Its keyword list has `std::memset` and `std::fill`. It has no `memcpy`, and a default constructor has no keyword.
- [Ref7] Probe of 2026-11-19 on reduced code, not on tron: g++ 11.4.0, `-O3 -march=x86-64-v4`, AMD Ryzen 9 9950X. A default-constructed buffer of 16 x 64 floats before an opaque writer keeps a zero fill of 4,096 bytes (`rep stosq`). With the `uninitialized` constructor there is no fill. With a visible overwrite the compiler removes the fill. A 512-byte copy into a stack row stays in the code (`rep movsq`).
