#!/usr/bin/env python3
"""Apply version 3 of the candidate edits to a copy of the skills (version 2 plus the fixes of the final check).

Usage: apply_candidate_v3.py <skills dir> [--blind]

Each old text must occur exactly once. With --blind the texts that name the
fix of tron PR 5022 (worked example, precedent notes) are left out, so that a
replay on that pull request tests the rule and not the worked example.
"""
import sys, pathlib

root = pathlib.Path(sys.argv[1])
BLIND = "--blind" in sys.argv


def edit(rel, old, new):
    p = root / rel
    t = p.read_text()
    n = t.count(old)
    assert n == 1, f"{rel}: expected 1 occurrence, found {n}: {old[:70]!r}"
    p.write_text(t.replace(old, new))


def prov(text):
    """Text that names the PR 5022 fix. Dropped in the blind variant."""
    return "" if BLIND else text


# ====================================================================== tron-code-review
T = "tron-code-review/SKILL.md"

edit(T,
     "work done before the test that needs it), and meaningful tests. Use when",
     "work done before the test that needs it), meaningful tests, and tests that a build option keeps out of the required CI lane. Use when")

edit(T,
     "Apply these deliberate breaks to each new test section, and name the assertion that fails. A break with no failing assertion is a finding.\n",
     "Apply these deliberate breaks to each new test section, and name the assertion that fails. A break with no failing assertion is a finding. "
     "Name the assertion in a build that a required lane makes. A required lane is a CI workflow that every pull request starts by itself and that must pass before the merge. "
     "An assertion does not count when only a build with some option turned on compiles it, and no required lane turns that option on.\n")

TRON_LANE = """
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
"""
edit(T,
     "It returns 4 when every selected case skips.\n",
     "It returns 4 when every selected case skips.\n" + TRON_LANE)

edit(T,
     "[exit code](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969).\n",
     "[exit code](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969)."
     + prov(" The lane check and its remedies come from the same pull request: [option off in every pull-request lane](https://github.com/positron-ai/tron/pull/5022#discussion_r4356060700), [definition for one test target](https://github.com/positron-ai/tron/pull/5022#issuecomment-7118448228).")
     + "\n")

# ====================================================================== cpp-coding-guide
C = "cpp-coding-guide/SKILL.md"
p = root / C
t = p.read_text()
assert t.rstrip().endswith("```"), "cpp-coding-guide: unexpected end of file"
CPP_SECTION = """
## Tests behind a build option

A build option is a switch of the build that reaches the code as a macro, such as a CMake `option(...)` that the code reads with `#ifdef`. A guard is the `#ifdef` block on that macro. The registration of a test is the line of the build file that declares the test program. A fake is a stand-in that the test defines in place of a real function. The examples use Catch2, the C++ test framework. Its `SUCCEED` macro records a pass. Its `SKIP` macro ends a test case and reports it as skipped.

These rules apply to a test file with such a guard. They also apply when you add a case or a section inside a guard that is already there. When the guard or the registration is older than your change, tell the user what the guard leaves out, and propose the change. Do not change them without the user's decision.

- Do not write a placeholder case. A placeholder case is a test case that only reports success in the build without the option, such as an `#else` branch that calls `SUCCEED`. The test program then passes in a build that compiled none of the real cases, and the report shows the same pass for both builds.
- Give the macro to the one test program when the test supplies everything else. This holds when the code under test is in headers, and the test defines its own fakes for every function that the option adds to the library. Let the registration pass the definition of the macro to that one program. Search the registrations for a test that already does this, and copy its form. In tron this is the `DEFINES` argument of `add_catch_test`.
- Before you give the macro to one test program, check the code that the definition does not reach. That code is each library that the program links, and each object file that the build compiles once and shares between test programs. It must not compile an entity that the macro changes and that this test also uses. Such an entity is a class, an instance of a template for the same types, an inline function or an inline variable.
- After the registration passes the definition, remove the guard and the placeholder case. The real cases then run in every build. Check that a case fails without the definition. If none fails, put an `#error` for the missing macro at the top of the test file.
- Keep a guard only around the cases that need something a definition cannot supply. Examples are a source file that only the option adds to the library, a compiler feature, and hardware that the test host may lack. Put every other case outside the guard. When a case needs hardware, the case tests for the hardware at run time. Without the hardware it calls `SKIP`. The report then says "skipped".
- When every case of a file must stay behind the guard, the build without the option still needs one case. A Catch2 program without a test case exits with code 2, and the test fails. Make that case call `SKIP`, and register the test so that the exit code for "every case skipped" is reported as skipped. In tron this is `SKIP_RETURN_CODE 4` with the label `skip_return_code_4`.
- Do not widen a guard to remove a warning about an unused helper in the build without the option. The warning says that this build compiles the helpers and none of the cases that use them. Ask first whether the cases can run in that build.

```cpp
// A build without the option compiles only the second case. It passes,
// so the report shows a pass for checks that did not run.
#ifdef PROJECT_FAST_PATH
TEST_CASE("the dispatch calls each fake kernel once") { check_dispatch(); }
#else
TEST_CASE("dispatch test skipped (not compiled)") {
  SUCCEED("build without PROJECT_FAST_PATH - nothing to test");
}
#endif

// The test defines the fake kernels itself, so it needs only the macro.
// Its registration passes the definition to this one program:
//   add_catch_test(NAME t_dispatch DEFINES PROJECT_FAST_PATH ...)
// No guard and no placeholder case. The case runs in every build.
TEST_CASE("the dispatch calls each fake kernel once") { check_dispatch(); }

// The transpose needs nothing from the option, so it sits outside the guard.
// The kernel case needs the kernel source file and the instruction set.
// It stays inside the guard. A build without the option does not compile it.
// With the option, it reports a skip on a host without the instruction set.
TEST_CASE("the transpose writes every row") { check_transpose(); }
#ifdef PROJECT_FAST_PATH
TEST_CASE("the kernel matches the reference") {
  if (!fast_path::available()) SKIP("this host lacks the instruction set");
  check_kernel();
}
#endif
```
"""
p.write_text(t.rstrip("\n") + "\n" + CPP_SECTION)

# ====================================================================== folks-code-review
S = "folks-code-review/SKILL.md"
P = "folks-code-review/references/procedures.md"

# Setup step 3: the first clause of the repository test policy.
edit(S,
     '("Tests": assertions about values or structure need an identifiable consumer, no duplicate coverage, extend the closest existing test)',
     '("Test policy": a required CI suite must execute every committed test, a local run does not count, and an agent may not decide that an exception applies; assertions about values or structure need an identifiable consumer; no duplicate coverage; extend the closest existing test)')

# Setup step 5: two checks reach lines outside the diff.
edit(S,
     'A hunk outside the diff gets at most an informational "fwiw" line.',
     'A hunk outside the diff gets at most an informational "fwiw" line. Two checks reach lines outside the diff. Check 30 reads unchanged lines on a path where the PR raises a size. Check 3A form (f) reads the guard around a test unit that the diff adds or widens.')

# Setup step 6: a declined remedy.
edit(S,
     "Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified.",
     'Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified. When you or the author decline a remedy for a concern that the checks confirm, the concern stays open. Look for another remedy that fixes it (section "When a remedy is declined").')

# Index line of check 3A.
edit(S,
     "3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, without hardware, on a second run?",
     "3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, with that lane's build options, without hardware, on a second run?")

# Check 3A: the old severity line covers forms (a) to (e) only.
edit(S,
     "Severity and precedent: no 'nit'. Questions, non-blocking, except form (d), which opens with 'Coverage gap:' and asks in the must-change form 'Please extend an existing CI suite' (3960538177). n = 5 comments over 4 PRs (tron 1920, 2011, 4128, 4557), 2026-01-28 to 2026-10-05.\n",
     "Severity and precedent for forms (a) to (e): no 'nit'. Questions, non-blocking, except form (d), which opens with 'Coverage gap:' and asks in the must-change form 'Please extend an existing CI suite' (3960538177). n = 5 comments over 4 PRs (tron 1920, 2011, 4128, 4557), 2026-01-28 to 2026-10-05. Form (f) is must-change and has its own severity line below.\n"
     + "@@FORM_F@@")

FORM_F = """
Widening from PR 5022 (2026-11-23): form (f), a compile-time gate.

Trigger: in t/, the diff adds or widens a test unit (TEST_CASE, SECTION, GENERATE arm, or an assertion in a helper that such a unit calls) that at HEAD sits inside a region, and a CMake option of the project switches the region's macro. A region is the lines between an `#if`, `#ifdef` or `#ifndef` line (the guard) and its `#endif`, the `#else` arm included. The option switches the macro through a `target_compile_definitions` line under `if(<option>)`, or through a `#cmakedefine` header, where the macro can have another name than the option. The guard and its `#else` arm may be unchanged since BASE. The trigger is the unit, not the guard. Highest priority when the `#else` arm holds a placeholder case, which is a case that only passes (`SUCCEED`, an empty body). The binary then reports a pass on a lane that compiled none of the added assertions.

Procedure:
1. Read the whole test file at HEAD, not the diff. List its regions. Map each added or widened unit to its region and to the `#else` arm.
2. Find every place that defines the macro (the option and its default, each `target_compile_definitions` line, a `DEFINES` argument or a `target_compile_definitions` call on the test's own target, each preset, each workflow). Take the gating lane from check 7, steps 1 to 4. Only a workflow that a `pull_request` or `merge_group` event starts counts as gating here. A workflow that a person dispatches does not count, even when README.ci.md lists its check names as required and a run of it passed at HEAD. Work out whether the gating lane compiles each added or widened unit. State how many assertions the binary runs there.
3. Sort each guarded unit into one of four classes. Class (i) calls only code that every build compiles. Class (ii) needs header code under the same macro, and the test file supplies the rest itself (its own fakes, the stand-in functions that it defines). Class (iii) needs option-only code, which is code that a library holds only in a build with the option: a source file or a compiler flag that the build adds only under the option, a region of a library source file under the same macro, or a class that a library source file also compiles and whose layout the macro changes. A class inside a template that only the test instantiates does not make a unit class (iii). Step 5 checks that case. Class (iv) needs an instruction set that the lane's runners lack.
4. Pick the remedy by class. A class (i) unit moves above the guard. When every other guarded unit of the target is class (ii), the test target can pass the define itself. A define is a macro that the build file gives to the compiler for one target, and it reaches every unit of that target. Search t/CMakeLists.txt for a test that already does this (`DEFINES` in `add_catch_test`, or `target_compile_definitions` on a test target), and quote it. Do not propose the define when a unit of the same target is class (iii) or (iv). With the option off the binary would then not link, or the test and the library would compile two layouts of one class.
5. Check that the define is safe for one target. Grep h/ and src/ for the macro. List the other translation units of the test program: its linked libraries, and the object files that the registration adds (`testlog_objects`, `testfake_objects`, `testmain_objects`, support objects in FILES). They are built without the define. Three kinds of hit are unsafe. The first is a hit in a .cpp file of a linked library. The second is a hit in a non-template type, an inline function or an inline variable that such a unit also compiles. The third is a hit in a template that such a unit instantiates for a type the test also uses. In each case ask, do not prescribe.
6. Quote the lines of the AGENTS.md test policy on CI execution at HEAD.
7. Name the runs that the fix needs before the author takes it. The test passes in a build with the gating lane's options. A deliberate break of the changed path makes it fail there. The test still passes in a build with the option on.

Question: with the option at the gating lane's value, which added assertion executes, and can this one test target pass the define itself?

Do not fire on:

- a unit of class (iii) or (iv). Say what it needs, name the run under 3B, and say that the exception needs the user's approval. A hardware probe stays with forms (a) and (b).
- a macro that no CMake option of the project switches (compiler, platform and standard-library macros).
- a unit that the gating lane compiles. Under a guard that asks for the macro (`#ifdef <NAME>`, `#if defined(<NAME>)`), that holds in three cases: the lane sets the option, or the option's default defines the macro, or the test's own registration defines the macro outside every `if(<option>)` block (`DEFINES <NAME>`, or `target_compile_definitions` on the test target). Under `#ifndef <NAME>` and in an `#else` arm, it holds when the lane's build of the test leaves the macro undefined.
- a manual switch, which is a macro that no build file defines and that the source tells the developer to set by hand.
- a unit outside the region that asserts the same contract on the gating lane (name it).
- a file in which the diff neither adds nor widens a unit ("fwiw" at most).
- fpga/DISABLED binaries.

A change of the gating lane's global build flags is never the first remedy. It changes what every other test of that lane exercises. A run of another workflow is the remedy of 3B, not of this form.

Finding shape, class (ii): "Every unit this PR adds to `<file>` sits under `#ifdef <NAME>` (:<line>). <gating workflow> leaves `<NAME>` off (<configure file:line>). So there the binary runs <K> assertions (<the `#else` case at :<line>, or the cases outside the region>), none of the new ones, and a break of <changed path> passes the required checks. The units call <header entry point> and the file's own fakes, so they need neither <hardware> nor <option-only source>. `<sibling test>` (<CMake file:line>) passes its own define. Please register `<test>` with `DEFINES <NAME>` and drop the `#else` case, so that a lost define fails instead of passing." Class (i): "`<unit>` (:<line>) sits under `#ifdef <NAME>` (:<line>), and <gating workflow> leaves `<NAME>` off (<configure file:line>). The unit calls only <header entry point>, which every build compiles. Please move it above the guard."

Severity and precedent: must-change, in the "Please <verb>" form, before the merge. The repository test policy requires a required CI suite to execute every committed test, and it does not let an agent grant the exception. The author decides whether the fix enters this PR or an exception applies. After the fix, rerun checks 7 and 8. Each sentence that says the test is compiled out is then wrong. Also refresh the test's rows in config/test-benchmarks.json (the run time and memory that the test scheduler plans with). t/AGENTS.md asks for that after a material change of a test.""" + prov(""" Not from Wade's record. It comes from ishapira-positron on PR 5022 (output of a multi-agent review pipeline). Comment 4356060700 (2026-10-23) asked for the option in the Nix build. claude[bot] thread 4645384802 (2026-11-20) asked for the sections in a required suite, and it gave the Nix option as an example. The author declined the Nix option. It changes every model test of the lane. Comment 7118448228 with PR 5606 (2026-11-24 UTC) gave the per-target define, the way `t_page_share_counters` does it (t/CMakeLists.txt:276 at ddf843ad97).""") + """
"""
edit(S, "@@FORM_F@@", FORM_F)

# Check 7: a true lane sentence does not close the coverage question.
edit(S,
     "README text is a claim to check, never evidence.",
     "README text is a claim to check, never evidence. A true lane sentence closes this check only. When the sentence says that the gating lane leaves a setting off, check 3A form (f) asks which added test units that setting compiles out.")

# Check 35: any bot, a coverage bin, the severity of a confirmed claim.
edit(S,
     "Trigger: a cursor[bot] (automated reviewer) thread (unresolved, unanswered)",
     "Trigger: a thread whose first author is an automated reviewer (a login that ends in `[bot]`, such as cursor[bot] or claude[bot]; unresolved, unanswered)")
edit(S,
     "2. Bin: SENTINEL (`-1` default reaches a callee), UNREACHABLE, UNUSED, DUPLICATE-CONSTANT, CONCURRENCY.",
     "2. Bin: SENTINEL (`-1` default reaches a callee), UNREACHABLE, UNUSED, DUPLICATE-CONSTANT, CONCURRENCY, COVERAGE (a test or a path does not execute on a lane; owning checks 3A, 3B and 7).")
edit(S,
     "6. Verdict with the deciding file:line.\n",
     "6. Verdict with the deciding file:line.\n"
     "7. For a CONFIRMED claim, take the severity from the severity line below. If you or the author decline the bot's fix, go to \"When a remedy is declined\".\n")
edit(S,
     "optional forwarded agent items, never a blocker.",
     "optional forwarded agent items that the checks do not confirm (never a blocker).")
edit(S,
     'Severity and precedent: none for a refutation; a confirmed claim is "a legit concern" (3156090573). n = 14 comments over 11 PRs, 2026-03-11 to 2026-09-09, attributed (3970590653, 4800935083).',
     'Severity and precedent: none for a refutation. A confirmed claim is "a legit concern" (3156090573). When it rests on a written repository rule, it has the severity of its owning check, and the bot\'s own label does not lower that severity. Such a label is the word "optional", or a mark such as the yellow circle of claude[bot]. Quote the rule by file:line. A confirmed claim that rests on no written rule keeps the bot\'s label. n = 14 comments over 11 PRs, 2026-03-11 to 2026-09-09, attributed (3970590653, 4800935083).'
     + prov(" The COVERAGE bin, the claude[bot] login and the rule on the bot's label are not from Wade's record. They come from claude[bot] thread 4645384802 on PR 5022 (2026-11-20)."))

# Replying: a pointer, and a new subsection.
DECLINED = """
### When a remedy is declined

This rule covers any reviewer and any bot. It applies to a finding that the checks confirm, in three cases: its owning check rates it must-change, or the reviewer marked it with one of the four signals above or with a CHANGES_REQUESTED review, or it rests on a written repository rule. The wording of the remark does not decide it. A must-change finding can arrive as a question ("Could we add ...?"). The rule does not apply to a claim that the checks refute. It does not apply to a declined preference ("nit", "trivial", "pedantic", "maybe"), which keeps the rule above. Apply it in two situations: you are about to recommend against a proposed fix, or the author declines one.

1. A declined remedy does not close the finding. Write the finding without the fix, and mark whether the change at HEAD closes it. Write the reason for declining as a condition on any fix ("must not change what the other tests of the lane exercise").
2. Search for a fix that meets the condition. Try the same change at a narrower scope (one test target, one file, one call site). Try the way a sibling in the same file already solved it (`git grep` the neighboring registrations, guards and helpers).
3. Test every sentence of the form "X needs Y" in the draft. Search for one way to reach X without Y. Keep the sentence only when the search finds none.
4. Show the author one narrower fix next to the draft reply. Name the runs that the fix needs and what else it changes. The author decides whether it enters the PR.
5. A reply with words only is the last choice for such a finding. The reply stays short. The record of the fixes that were tried, and why each fails, goes to the author, not into the reply.
6. Do not pass the finding on as settled. A list of decided points for a later review or a handoff names the declined remedy and, next to it, the finding that is still open.
""" + prov("""
Not from Wade's record. Precedent: PR 5022. Threads 4356060700 and 4645384802 were answered with one reason and a run started by hand. The reviewer kept the changes-requested state and supplied the narrower fix himself (comment 7118448228, PR 5606).
""")
edit(S,
     "- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write \"LGTM\", resolve a thread for him, or post without the author's approval.\n",
     "- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write \"LGTM\", resolve a thread for him, or post without the author's approval. When the checks confirm the finding, also follow \"When a remedy is declined\" below.\n"
     + DECLINED)

# ---------------------------------------------------------------------- procedures.md
edit(P,
     "A compile-time `#if` is not a runtime exit; a `min_slices_N` label in t/CMakeLists.txt is test selection, listed separately.",
     "A compile-time `#if` is not a runtime exit. It is form (f), steps 16 to 20. A `min_slices_N` label in t/CMakeLists.txt is test selection, listed separately.")

STEPS = """16. Regions (f): `grep -n -E '^[[:space:]]*#[[:space:]]*(if|ifdef|ifndef|elif|else|endif)\\b|SUCCEED\\(' full/<file>`. Added units: `git -C WT diff -U0 BASE HEAD -- t/<file> | grep -E '^\\+.*(TEST_CASE|SECTION\\(|GENERATE\\()'`, mapped to HEAD lines. Widened units: `git -C WT diff -U0 BASE HEAD -- t/<file> | awk '/^@@/{split($3,a,/[,+]/); n=a[2]-1} /^\\+/ && !/^\\+\\+\\+/{n++; if ($0 ~ /(REQUIRE|CHECK)[_A-Z]*\\(/) print n": "substr($0,2)}'` prints each added assertion with its HEAD line. Take the unit of each line with the owner-line command of step 10. An assertion added to a helper widens every unit that calls the helper. The guard can predate the PR: `git -C WT show BASE:t/<file> | grep -n -E '^[[:space:]]*#[[:space:]]*(if|ifdef|ifndef|elif|else|endif)\\b'`.
17. Macro and lanes: `git -C WT grep -n '<NAME>' HEAD -- '*CMakeLists.txt' '*.cmake' '*.in' CMakePresets.json nix flake.nix .github GNUmakefile`. Sort the hits: the `option(` line and its default; each `target_compile_definitions` call (the name can sit on a continuation line); a `DEFINES <NAME>` argument, a `PROPERTIES <NAME> ON` setting or a `target_compile_definitions_if_target` call on a test target; a `#cmakedefine <NAME>` line (the option then has another name: read the `if(...)` around `set(<NAME>`); each preset and each workflow. A definition on the test's own target, outside every `if(<option>)` block, means that every lane compiles the units under `#ifdef <NAME>`: stop, form (f) does not fire on those units. Gating lane: check 7, steps 2 to 4. No hit in the gating lane's recipe = the default of the `option(` line holds there. An `#ifndef` region and an `#else` arm compile when the macro is absent. Assertions on that lane: read the lane's test log, or count the REQUIRE, CHECK and SUCCEED lines that the lane compiles: the lines outside every region, and the lines in the arms that the lane compiles. That is a count of source lines, not of executed assertions.
18. Needs: `git -C WT grep -n -A40 -E 'if *\\((NOT +)?<NAME>[ )]' HEAD -- '*CMakeLists.txt' '*.cmake'`. Read each block to its `endif()` and list its `target_sources`, `add_library`, `target_link_libraries` and `COMPILE_OPTIONS` lines. They are what the build adds only under the option. For each production symbol the guarded units call: `git -C WT grep -n '<symbol>' HEAD -- h src` and `grep -n '<symbol>' full/<file>`. Defined in a header, with no `#if <NAME>` region around it, in its body or in the header code that it calls (step 19 lists the regions) = class (i), the unit can move above the guard. Defined in a header with such a region = header code under the macro (class (ii) when the test file supplies the rest). Defined in the test file = its own fake (class (ii)). Defined only in an option-only source, or inside an `#if <NAME>` region of a library source = a define cannot run it (class (iii)).
19. Define safety: `git -C WT grep -n -E '^[[:space:]]*#[[:space:]]*(el)?if.*<NAME>' HEAD -- h src`. List the other translation units of the test program. They are the LIBRARIES of the registration with what those link, and the object files that `add_catch_test` adds: `testlog_objects` always, `testfake_objects` for `LABELS fake`, `testmain_objects` for `main`, and every `$<TARGET_OBJECTS:...>` in FILES. None of them gets the define. Hits only in headers, inside templates = one target can pass the define, provided that none of those units instantiates the same templates for the types the test uses. In tron the model instances are in `${TRON_MODEL_OBJECTS}` (tron_model_specializations, full_scheduler, fake_scheduler and their _static forms), not in `tron`. A hit that wraps a whole type, function or variable that exists only with the macro = safe when none of those units names it. A hit in src/*.cpp of a linked library, or in a non-template type, an inline function or an inline variable that such a unit also compiles = ask.
20. Sibling and policy: `git -C WT show HEAD:t/CMakeLists.txt | grep -n -B4 -E 'DEFINES|target_compile_definitions'`; quote the registration and the comment above it. `git -C WT show HEAD:AGENTS.md | grep -n -A6 'Every committed test must run in CI'`.
"""
ON_PR = prov("""
On PR 5022 at ddf843ad97 (BASE 3bea58b788): step 16 t/t_amx_dispatch_dtype.cpp `#ifdef TRON_AMX_DISPATCH` :56, `#else` :400, SUCCEED :402; added SECTIONs :364, :368, :372, :377, all inside the :56 region; the `#else` case was already at BASE (:284-288). Step 17: CMakeLists.txt:46 default OFF; set at .github/workflows/cmake-single-platform.yml:355 and CMakePresets.json:68; no hit under nix/. Step 18: fakes of every entry point at :313-352; option-only source kernels/amx_attn.cpp (src/tron/CMakeLists.txt:221). Step 19: 7 regions in h/tron/models/self_attention.hpp, all inside the `self_attention` class template, none in src/*.cpp; the test links `tron pos_fake`, which hold no model objects. Step 20: t/CMakeLists.txt:273-276 (`t_page_share_counters DEFINES TRON_PAGE_SHARE_COUNTERS`) and :615 (`t_llama_unit DEFINES _GLIBCXX_ASSERTIONS`); AGENTS.md:29-35. Fires on t_amx_dispatch_dtype with the define: its units are class (ii). Fires on t/t_amx_numerics.cpp:148 with the move: the PR widens that case at :171, and the case calls only the constexpr `eligible` and `query_scalar_ok` of h/tron/kernels/amx_attn_iface.hpp, which no macro guards (class (i), by reading, not compiled above the guard). Does not fire on the other cases of that file. The packer case (:369) calls pack_q_group_128x4, which only kernels/amx_attn.cpp defines (class (iii)). The QK and PV cases (:379, :391) also need AMX: they test `available()` (:380, :393) and SKIP without it (:381, :394, class (iv)). So that file cannot take the define. This example is from ishapira-positron (comment 7118448228, PR 5606), not from Wade's record. ishapira-positron did not raise the case at :148.
""")
edit(P,
     "\n\nOn PR 1920: t/t_hwattention.cpp:670 `return;` under :603 TEST_CASE_METHOD",
     "\n" + STEPS + "\nOn PR 1920: t/t_hwattention.cpp:670 `return;` under :603 TEST_CASE_METHOD")
edit(P,
     "PR 4557: existing line stays at 96a6220ab6.\n",
     "PR 4557: existing line stays at 96a6220ab6.\n" + ON_PR)

# Check 35: any bot author, and bots without the cursor[bot] body format.
edit(P,
     "comments(first:3){nodes{databaseId path line author{login}}}}}}}}' -F n=N > threads.json`; keep first author `cursor`, both flags false, one comment node.",
     "comments(first:3){nodes{databaseId path line author{login __typename}}}}}}}}' -F n=N > threads.json`; keep threads whose first author has `__typename` `Bot` (GraphQL prints a bot login without the `[bot]` suffix, such as `cursor` and `claude`), both flags false, one comment node.")
edit(P,
     "| @tsv'`; `git -C WT diff -U0 BASE HEAD -- <path> | grep -n '^@@'`.\n3. SENTINEL:",
     "| @tsv'`; `git -C WT diff -U0 BASE HEAD -- <path> | grep -n '^@@'`. The first command keeps only bodies with the `DESCRIPTION START` marker of cursor[bot]. For a bot without the marker, such as claude[bot]: `gh api repos/positron-ai/tron/pulls/N/comments --paginate --jq '.[] | select(.user.login | endswith(\"[bot]\")) | select(.body | test(\"DESCRIPTION START\") | not) | [.id, .path, .line, .commit_id[0:10], (.body | split(\"\\n\")[0][0:200])] | @tsv'`. claude[bot] opens a finding with a red circle, or with a yellow circle and \"(optional)\".\n3. SENTINEL:")
edit(P,
     "Forward kept items quoted, optional.",
     "Forward kept items quoted. An item is optional unless the checks confirm it and it rests on a written repository rule (SKILL.md check 35, severity line).")

print("candidate v3 edits applied" + (" (blind variant)" if BLIND else ""))
