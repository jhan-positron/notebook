---
name: tron-code-review
description: Review pull requests and diffs in positron-ai/tron for execution-path coverage, stats/counter semantics, forward-pass bookkeeping, asynchronous ownership, cost on per-token paths (hidden zero fills, copies, work done before the test that needs it), meaningful tests, and tests that a build option keeps out of the required CI lane. Use when reviewing Tron code changes, including a change that adds a model shape or enlarges a size on an existing path.
---

# Tron code review

Short version: Review the change across the execution paths and ownership boundaries that determine its behavior and its cost. Support each finding with a concrete condition or quantity and evidence from the revision under review.

## Scope and terms

Review the supplied base and head commits. If reviewing local changes instead, identify the revision and working-tree diff examined. Read the applicable repository instructions and project term definitions.

- Tron is the inference program under test. runtron is its command-line tool. rinzler is the production server.
- A token is a unit of text processed by the model. A token job is one token's scheduled model work. A forward pass is one model execution over the scheduled token jobs.
- A stats/counter value counts work or measures execution, such as elapsed time.
- FPGA means a programmable hardware accelerator. FPGA-assisted attention can include software work too.
- A listener receives a token job's output scores when available. Listener presence is not an exact marker of whether the token came from a prompt or from generation.
- Wall time is elapsed time between the operation's start and end, including waits within that interval.
- A hot path is code that runs once per token, once per KV page or once per layer. A KV page is a 64-token block of the key/value cache.
- A size parameter is a value that sets how much work one call does, such as the number of query heads that share one key/value head.
- A view is an object that points at memory it does not own, such as `tron::const_view`.

## Review the changed behavior

First identify the intended behavior and the system boundaries it crosses.

Do not stop at the diff. Trace relevant unchanged callers, callees, model eligibility, worker mappings, generated code, and consumers.

For each new or changed stats/counter, check:

- Does it count or time the intended work? Are the units clear?
- Which code updates it? Can any execution path omit or double-count work?
- Which component owns its initialization, aggregation, and reset? Does the value cover one operation or accumulate across operations as intended?
- Does the classification describe the work being counted? Do worker or layer indices keep the meaning that readers expect across operations?
- Do the exported values and documentation answer the reader's intended question? Could missing collection be mistaken for no work?
- Forward-pass example:
  - Trace every entry point through completion. Check normal exits, early returns, and failure paths.
  - Cover software-only and FPGA-assisted attention.
  - Check that each completed pass contributes exactly one pass count when statistics collection is enabled.
  - Check that its wall time covers the documented start and end points.
  - Verify that its job counts, timing, and execution-path counts all use that pass's class: `decode_like` or `prompt_or_mixed`.
  - Inspect every caller for missing bookkeeping.
  - Flag a path that could count jobs without counting the pass, or assign timing to the previous pass's class.
  - Propose tests that exercise those paths through the model entry point.

The example uses the categories from [PR4596](https://github.com/positron-ai/tron/pull/4596). In that revision, `decode_like` means every token job has a listener. `prompt_or_mixed` means at least one job lacks a listener. These are forward categories, not software-only versus FPGA execution paths. Verify the category names and rules in the revision under review. Check the intended treatment of interrupted passes before treating incomplete accounting as a defect.

For every asynchronous operation (work that may finish after the initiating call returns), trace allocation, reservation, submission, completion, release, and cancellation. Check which owner keeps the data alive until completion. Identify the event that permits reuse or release.

## Check relevant conditions

Check the changes under different conditions that can select different code paths. Choose the conditions relevant to this change:
- Software-only / FPGA-assisted attention. FPGA means a programmable hardware accelerator.
- The feature enabled / disabled.
- Pure / mixed serving batches. A pure batch contains only prompt processing or only output-token generation. A mixed batch contains both.
- Empty / singleton. Check cases with no work or exactly one item of work. The item depends on the changed code: a queued task, a memory transfer, or an attention page, for example. These cases may take different code paths from larger workloads.
- Boundary model shapes. "Shape" means model dimensions, such as the number of attention heads or the number of values in each head. An attention head is one attention computation channel. Check dimensions at supported limits and just outside them. Unsupported dimensions should trigger the intended rejection or an alternative supported execution path.

State which conditions were checked and which were not checked. Distinguish code inspection from tests actually run.

## Review the cost on per-token paths

Start from the path, not from the diff. When a change lets a size parameter take a larger value on an existing path, every line on that path whose cost grows with the parameter is part of the change. That includes lines the diff does not touch.

1. Name the parameter, its old value and its new value.
2. Read every function on that path at the reviewed revision, unchanged lines included.
3. For each line whose cost grows with the parameter, state the cost per call at both values, in bytes or in instructions.
4. State how often the function runs: per token, per KV head, per page or per layer.

Then look for these patterns on the path:

- A declaration that fills memory before a full overwrite. Does a local object zero-fill its storage in its default constructor, just before another writer sets every element? Read the constructor of the type, because the declaration line shows no work. The default constructor of `tron::tensor` zero-fills, and `tensor<...> s{uninitialized};` skips the fill. Confirm that every element is written before any read, for every value of the size parameter. Do not flag an accumulator, or a buffer whose untouched elements are read later as zeros.
- A copy made only to change the type. Is an owning local filled by `memcpy`, `std::copy` or assignment, and then only read? Read the signature of the function that reads it. If that function accepts a view, the copy can go. Check three conditions first: the source stays alive and unchanged while it is read, the source and the destination do not overlap, and the address meets the alignment that the view type claims. Do not flag a snapshot of memory that is about to change, or a conversion between number formats.
- Work done before the test that decides whether it is needed. Does a preparation step (pack, convert, gather, look up, allocate) run before a condition, where one branch never reads the result? Find how often that branch runs from counters, not from a guess. Search the tests for an assertion that pins the order. An order with a stated and measured reason is a design choice. Then ask whether the new parameter value changes that measurement.
- A scalar loop inside a vector kernel. Does a loop move or convert one element per iteration, at a new or larger instantiation? A cost that grows faster than the parameter is the signal. Compile the file with the project's compiler and flags, count the function's instructions by name, and compare the instantiations. Time one call on the target CPU.
- The same intermediate value computed once per lane. Does a helper that is called once per index recompute a stage that depends on only part of the index? Count the distinct results against the computed ones. Confirm the count in the object code, because compilers differ in what they merge.

Do not rely on the optimizer to remove a fill or a copy. The optimizer removes a fill only when it can see the overwrite, and a call into another source file hides it.

Report a cost finding with its quantity, its unit and its frequency, in the form "`<N>` bytes copied per `<page visit>`". Name a remedy that the code base already offers. Name the compiler, the flags and the CPU behind every instruction count and every time, because a count from another compiler or a time from another CPU is only a hint. State what was not measured. A change of cost needs its own measurement before it merges. Without one, the pull-request description must say that its benchmarks predate the change.

These patterns come from the review of [PR5022](https://github.com/positron-ai/tron/pull/5022#pullrequestreview-5623855297). That change let the AMX attention path serve 16 query heads per key/value head, where it had served 4. AMX is Intel's matrix instruction set. Three of its five cost findings concerned code that the change did not touch. The five comments: [zero fill](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061865), [row copy](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062246), [pack before its test](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062294), [scalar pack](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061055), [repeated shuffle stage](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062057).

## Review the tests

For each important test, ask:

- Does it call the changed production boundary?
- Does its fake retain the information that could be wrong?
- What deliberate semantic break would make the assertion fail?

For example, directly adding cycles to a stats/counter tests accumulation. It does not prove that the real wait path records elapsed time. A fake memory-transfer function that discards destination addresses cannot establish that the transfer writes to the right destination.

Apply these deliberate breaks to each new test section, and name the assertion that fails. A break with no failing assertion is a finding. Name the assertion in a build that a required lane makes. A required lane is a CI workflow that every pull request starts by itself and that must pass before the merge. An assertion does not count when only a build with some option turned on compiles it, and no required lane turns that option on.

- Shrink a loop bound in the production code. A test that counts calls and never reads the outputs still passes.
- Shift a base index or a stride. A test that uses only index 0 still passes, because the wrong term is multiplied by zero.
- Enlarge a loop bound past the buffer. A test that checks only the rows the code should write still passes. Give the input extra rows that hold a sentinel value, and require the rows the code must not touch to stay unchanged. Keep the broken code inside the test's own buffers, so that the failure is deterministic.

Check that a new parameter value runs on every arm the old value runs on, such as the full case, the partial case and the disabled case.

Check which code the tests reach without special hardware. Code that needs no special hardware must not sit behind a hardware gate. One such gate is a source file that only one instruction-set build compiles and that only a skipping test case reaches. Check the exit code of the test program as well. Catch2 is the C++ test framework. A Catch2 program returns 0 when some cases pass and the others skip, so the lane reports a pass although the new code never ran. It returns 4 when every selected case skips.

Check where each new test section executes. A build option is a switch of the build that reaches the code as a macro, such as a CMake `option()` that the code reads with `#ifdef`. A build option can keep a test out of a lane, as missing hardware can. A workflow that only a person or another workflow starts (`workflow_dispatch`, `workflow_call`) is not a required lane. This holds even when the repository's documents call its check names required, and even when a run of it passed at the reviewed revision.

For each test file that gains a section or an assertion, read three places:

- the options that each required lane passes to CMake, and the default of each option that the lane does not pass.
- the registration of the test in `t/CMakeLists.txt`, which is the line that declares the test program. It can give the program a definition of its own.
- every guard around the section. A guard is an `#ifdef`, `#ifndef` or `#if` block on the macro of a build option.

Read the guards in the whole file, not only in the diff. A guard that is older than the change still covers the sections that the change adds inside it. Work out the condition of each guard in the lane's build of the test program. When the condition is false there, the lane does not compile the guarded sections. The lane still reports a pass in two cases. In the first case the `#else` branch of the guard holds a placeholder case, which is a case that only calls `SUCCEED`. In the second case another case of the program passes.

Report the finding in the form "`<test>` runs `<N>` assertions with `<OPTION>` off and `<M>` with it on, and `<lane>` builds with it off". Do not flag these:

- a guard on a macro that the lane's build defines for the test program. The definition can come from the lane's options, from the default of the option, or from the registration of the test.
- a section that a second registration of the same file compiles with the macro defined.
- a section that another required lane builds and runs.
- a guard on a compiler or platform condition that no definition of the project sets, such as a sanitizer check.
- a manual switch. A manual switch is a macro that no build file defines and that the source tells the developer to set by hand. A CMake `option()` is never a manual switch.

Then find what the sections outside the lane need, and name the remedy with the smallest scope that the code base already offers.

1. The sections need only the macro. This holds when the code under test is in headers, and the test defines its own fakes for every function that the option adds to the library. Then give the one test program the definition. Search `t/CMakeLists.txt` for a registration that already passes a definition for its own program (`DEFINES` in `add_catch_test`, or `target_compile_definitions` on a test target), and copy its form. First check every other translation unit of the test program: each library it links, and each object file that the build compiles once and shares between test programs. They are built without the definition. None of them may compile an entity that the macro changes and that this test also uses: a class, an instance of a template for the same types, an inline function or an inline variable. Then delete the guard and its placeholder case. Check that a section fails without the definition. If none fails, put an `#error` for the missing macro at the top of the file, as `t/t_llama_unit.cpp` does.
2. A section needs neither the option nor special hardware. Move the section outside the guard. When the code under test sits in a source file that only a build with the option compiles, the remedy also moves that code to a header or a source file that every build compiles.
3. The sections need code that only a build with the option holds: a source file, a region of a library source file under the same macro, a class whose layout the macro changes, or a file built with a special compile flag. First look for a way to give that code to the one test program. The check of remedy 1 holds for such a way too. Do not propose a definition for the one program when the macro changes a class, or a region of a source file, that a library of the program also compiles. The library is built without the macro, and the program would then hold two versions of that code. A registration can name a source file under `src/` in its `FILES`, as `t_memperf` does. That file is in no library, and that registration passes no definition. Only a build can confirm the same way for another file. Until a build confirms it, name it as a question. If no such way works, two choices remain. The required lane turns the option on, or the user approves an exception to the test policy. State what else the option changes in that lane.
4. The sections need hardware that the machines of the lane lack. They stay behind the guard, and they report a skip. State which run executed them.

Rate the finding by its remedy. When remedy 1 applies, or when remedy 2 moves only test code, the finding is a current defect. Ask for the fix before the merge. Name the runs that the fix needs: the test passes in a build with the options of the required lane, a deliberate break makes it fail there, and the test still passes with the option on. Name also what the fix changes besides the test: its run time and memory in the lane, its rows in `config/test-benchmarks.json`, and each sentence that says the test is compiled out. The test policy in the repository's `AGENTS.md` says that a required CI suite must execute every committed test, and that only the user can approve an exception. A run on a developer machine, or a workflow that someone starts by hand, does not close the finding. In every other case, report the finding, the remedy and its cost, and say that an exception needs the user's approval. A move of production code changes object code, so it needs its own check before it merges.

A declined remedy does not close a finding whose facts still hold. First check the author's answer against the code. When the answer shows that a required lane runs the sections, withdraw the finding. Otherwise treat the author's reason as a condition on the fix, and name the next remedy that meets the condition. This also holds when the review request lists the remedy as already decided. Then report the finding with another remedy, and name the declined one.

These test checks also come from the review of PR5022: [outputs never read](https://github.com/positron-ai/tron/pull/5022#discussion_r4356060801), [index 0 only](https://github.com/positron-ai/tron/pull/5022#discussion_r4356060971), [unchecked rows](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061782), [one arm only](https://github.com/positron-ai/tron/pull/5022#discussion_r4356062178), [hardware gate](https://github.com/positron-ai/tron/pull/5022#discussion_r4356060885), [exit code](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969).

## Report findings

Return each finding with a concrete trigger, consequence, source location, evidence strength, and suggested discriminating check (a check that distinguishes correct behavior from the suspected defect).

Separate design choices and future risks from current defects. Verify that the suspected condition is reachable before calling it a current failure. Do not claim the absence of a bug outside the paths actually checked.
