#!/usr/bin/env python3
"""Apply the candidate edits to a copy of the skills. Each old text must occur exactly once."""
import sys, pathlib

root = pathlib.Path(sys.argv[1])

def edit(rel, old, new, count=1):
    p = root / rel
    t = p.read_text()
    n = t.count(old)
    assert n == count, f"{rel}: expected {count} occurrence(s), found {n}: {old[:70]!r}"
    p.write_text(t.replace(old, new))

# ---------------------------------------------------------------- tron-code-review
T = "tron-code-review/SKILL.md"
edit(T,
 "cost on per-token paths (hidden zero fills, copies, work done before the test that needs it), and meaningful tests. Use when",
 "cost on per-token paths (hidden zero fills, copies, work done before the test that needs it), meaningful tests, and tests that a build option hides from the required CI lane. Use when")

edit(T,
 "Apply these deliberate breaks to each new test section, and name the assertion that fails. A break with no failing assertion is a finding.\n",
 "Apply these deliberate breaks to each new test section, and name the assertion that fails. A break with no failing assertion is a finding. Name the assertion in the build configuration of a required lane. An assertion that only an option-on build compiles does not count when no required lane sets the option.\n")

LANE = """
Check where each new test section executes. A build option can hide a test, as hardware can. A required lane is a CI workflow that must pass before a pull request merges. For each test file that gains a section, read three places: the configure flags of each required lane, the registration of the test in `t/CMakeLists.txt`, and every preprocessor guard (`#ifdef`, `#if`) around the section. Read the guards in the whole file, not only in the diff. A guard that is older than the change still hides the sections that the change adds behind it. A guard on an option that the lane leaves off removes the guarded sections from that lane. The lane still reports a pass when the other arm of the guard holds a placeholder case that only calls `SUCCEED`, or when another case of the program passes. Report the gap in the form "`<test>` runs `<N>` assertions with `<OPTION>` off and `<M>` with it on, and `<lane>` builds with it off". Do not flag a guard on a macro that the lane defines, a section that another required lane builds and runs, or a manual switch that the source declares as one.

Then find what the hidden sections need, and name the narrowest remedy that the code base already offers.

1. The sections need only the macro. This holds when the code under test sits in headers, and the test defines its own fakes for every function that the option adds to the library. Then give the one test target the definition. Search `t/CMakeLists.txt` for a registration that passes a definition for its own target (`DEFINES` in `add_catch_test`, or `target_compile_definitions` on a test target), and copy its form. First check that no library the test links, built without the definition, compiles a class, a template instance or an inline function that the macro changes and that this test also uses. Then delete the guard and its placeholder arm, so that a registration that loses the definition fails instead of passing.
2. Part of the code needs neither the option nor special hardware. Move that part to a header or a source file that every build compiles, and test it outside the guard.
3. The sections need a source file or a compile flag that only the option-on build has. Then the choices are the option in the required lane, or an exception. State what else the option changes in that lane.
4. The sections need hardware that the runners of the lane lack. They stay gated, and they report a skip. State which run executed them.

Rate the gap by its remedy. When remedy 1 or 2 applies, the gap is a current defect: ask for the fix before the merge. The test policy in the repository's `AGENTS.md` says that a required CI suite must execute every committed test, and that only the user can approve an exception. A run on a developer machine, or a workflow that someone starts by hand, does not close the finding. When only remedy 3 or 4 applies, report the gap, the remedy and its cost, and say that the exception needs the user's approval.

A declined remedy does not close the finding. When the author declines one remedy and gives a reason, treat that reason as a condition on the fix. Name the next remedy that meets the condition.
"""
edit(T,
 "It returns 4 when every selected case skips.\n",
 "It returns 4 when every selected case skips.\n" + LANE)

edit(T,
 "[exit code](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969).\n",
 "[exit code](https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969). The lane check and its remedies come from the same pull request: [option off in every pull-request lane](https://github.com/positron-ai/tron/pull/5022#discussion_r4356060700), [definition for one test target](https://github.com/positron-ai/tron/pull/5022#issuecomment-7118448228).\n")

# ---------------------------------------------------------------- cpp-coding-guide
C = "cpp-coding-guide/SKILL.md"
p = root / C
t = p.read_text()
assert t.rstrip().endswith("```"), "cpp-coding-guide: unexpected end of file"
SECTION = """
## Tests behind a build option

A build option is a switch of the build that reaches the code as a macro, such as a CMake `option(...)` that the code reads with `#ifdef`. A guard is the `#ifdef` block on that macro. These rules apply to a test file with such a guard. They also apply when you add a case or a section inside a guard that is already there.

- Do not write a placeholder case. A placeholder case is a test case that only reports success in the build without the option, such as an `#else` arm that calls `SUCCEED`. The test program then passes in a build that compiled none of the real cases, and the report shows the same pass for both builds.
- Pass the definition to the one test target when the test supplies everything else. This holds when the option only switches on code in headers, and the test defines its own fakes for the functions that the option adds to the library. Then remove the guard and the placeholder case. The real cases run in every build, and a lost definition fails the test. Search the test registrations for a test that already passes its own definition, and copy its form. In tron this is the `DEFINES` argument of `add_catch_test`. First check that no library the test links, built without the definition, compiles a class, a template instance or an inline function that the macro changes and that this test also uses.
- Keep a guard only around the cases that need something a definition cannot supply. Examples are a source file that only the option adds to the library, a compiler feature, and hardware that the test host may lack. Put every other case outside the guard. A case that needs hardware checks for it at run time and calls `SKIP`, so that the report says "skipped".
- Do not widen a guard to silence a warning about an unused helper in the build without the option. The warning says that this build compiles the helpers and none of the cases that use them. Ask first whether the cases can run in that build.

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
// It stays inside the guard, and it reports a skip on a host without them.
TEST_CASE("the transpose writes every row") { check_transpose(); }
#ifdef PROJECT_FAST_PATH
TEST_CASE("the kernel matches the reference") {
  if (!fast_path::available()) SKIP("this host lacks the instruction set");
  check_kernel();
}
#endif
```
"""
p.write_text(t.rstrip("\n") + "\n" + SECTION)

# ---------------------------------------------------------------- folks-code-review
S = "folks-code-review/SKILL.md"
P = "folks-code-review/references/procedures.md"

# Setup step 3: the first clause of the repository test policy.
edit(S,
 '("Tests": assertions about values or structure need an identifiable consumer, no duplicate coverage, extend the closest existing test)',
 '("Test policy": a required CI suite must execute every committed test, a local run does not count, and an agent may not decide that an exception applies; assertions about values or structure need an identifiable consumer; no duplicate coverage; extend the closest existing test)')

# Setup step 5: the guard of an added test unit may sit outside the diff.
edit(S,
 'A hunk outside the diff gets at most an informational "fwiw" line.',
 'A hunk outside the diff gets at most an informational "fwiw" line. One exception: check 3A form (f), where the added test unit is in the diff and the guard around it is not.')

# Setup step 6: a declined remedy.
edit(S,
 "Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified.",
 'Concede the substance, correct the detail, and never post a replacement sentence the checks have not verified. When the author declines a remedy, the concern stays open: look for another remedy that fixes it (last bullet of "Replying to Wade").')

# Index line of check 3A.
edit(S,
 "3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, without hardware, on a second run?",
 "3A. Gated or blind test: were the code wrong as the test claims, which assertion fails on the gating lane, with that lane's build options, without hardware, on a second run?")

FORM_F = """
Widening from PR 5022 (2026-11-23): form (f), a compile-time gate.

Trigger: in t/, the diff adds or widens a test unit (TEST_CASE, SECTION, GENERATE arm) that at HEAD sits inside an `#if` or `#ifdef` region, and a CMake `option()` of the project defines the region's macro. The guard line and its `#else` arm may be unchanged since BASE: the trigger is the added unit, not the guard. Highest priority when the `#else` arm holds a case that only passes (`SUCCEED`, an empty body). The binary then reports a pass on a lane that compiled none of the added assertions.

Procedure:
1. Read the whole test file at HEAD, not the diff. List its preprocessor regions. Map each added unit to its region and to the `#else` arm.
2. Find every place that defines the macro (the option, the `target_compile_definitions` line, each preset, each workflow). Take the gating lane from check 7, steps 1 to 4. State how many assertions the binary runs on the gating lane.
3. List what the guarded units need: header code under the same macro; definitions the test file supplies itself (its own fakes); a source file, library or compiler flag that the build adds only under the option; an instruction set that the lane's runners lack.
4. If the units need only the first two, search the same CMake file for a test that passes a define for its own target (`DEFINES` in `add_catch_test`, or `target_compile_definitions` on a test target). Quote it.
5. Check that the define is safe for one target. Grep h/ and src/ for the macro. A hit in a .cpp file of a linked library, or in a non-template type or an inline function that such a library also compiles, means that the test and the library would disagree. Then ask, do not prescribe.
6. Quote the lines of the AGENTS.md test policy on CI execution at HEAD.

Question: with the option at the gating lane's value, which added assertion executes, and can this one test target pass the define itself?

Do not fire on: units that need an option-only source file, library or flag, or instructions the runners lack (say so, name the run under 3B, and say that the exception needs the user's approval; a hardware probe stays with forms (a) and (b)); a macro that no CMake option of the project defines (compiler, platform and standard-library macros); an option that the gating lane sets; a manual switch that the source declares as one; a unit outside the region that asserts the same contract on the gating lane (name it); a file to which the diff adds no unit ("fwiw" at most); fpga/DISABLED binaries. A change of the gating lane's global build flags is never the first remedy: it changes what every other test of that lane exercises. A run of another workflow is the remedy of 3B, not of this form.

Finding shape: "Every unit this PR adds to `<file>` sits under `#ifdef <NAME>` (:<line>). <gating workflow> leaves `<NAME>` off (<configure file:line>). So there the binary is the `#else` case (:<line>): 1 assertion, none of the new ones, and a break of <changed path> passes the required checks. The units call <header entry> and the file's own fakes, so they need neither <hardware> nor <option-only source>. `<sibling test>` (<CMake file:line>) passes its own define. Please register `<test>` with `DEFINES <NAME>` and drop the `#else` case, so that a lost define fails instead of passing."

Severity and precedent: must-change, in the "Please <verb>" form, before the merge. The repository test policy requires a required CI suite to execute every committed test, and it does not let an agent grant the exception. After the fix, rerun checks 7 and 8: sentences and registry rows that describe the placeholder build go stale. Not from Wade's record. It comes from ishapira-positron on PR 5022 (output of a multi-agent review pipeline). Comment 4356060700 (2026-10-23) and claude[bot] thread 4645384802 (2026-11-20) named the gap with the remedy "set the option in the Nix build". The author declined that remedy, because it changes every model test of the lane. Comment 7118448228 with PR 5606 (2026-11-24 UTC) gave the per-target define, the way `t_page_share_counters` does it (t/CMakeLists.txt:276 at ddf843ad97).
"""
edit(S,
 "n = 5 comments over 4 PRs (tron 1920, 2011, 4128, 4557), 2026-01-28 to 2026-10-05.\n",
 "n = 5 comments over 4 PRs (tron 1920, 2011, 4128, 4557), 2026-01-28 to 2026-10-05.\n" + FORM_F)

# Check 7: a true lane sentence does not close the coverage question.
edit(S,
 "README text is a claim to check, never evidence.",
 "README text is a claim to check, never evidence. A true lane sentence closes this check only. When the sentence says that the gating lane leaves a setting off, check 3A form (f) asks which added test units that setting compiles out.")

# Check 35: any bot, a coverage bin, severity of a confirmed claim.
edit(S,
 "Trigger: a cursor[bot] (automated reviewer) thread (unresolved, unanswered)",
 "Trigger: a thread whose first author is an automated reviewer (a login that ends in `[bot]`, such as cursor[bot] or claude[bot]; unresolved, unanswered)")
edit(S,
 "2. Bin: SENTINEL (`-1` default reaches a callee), UNREACHABLE, UNUSED, DUPLICATE-CONSTANT, CONCURRENCY.",
 "2. Bin: SENTINEL (`-1` default reaches a callee), UNREACHABLE, UNUSED, DUPLICATE-CONSTANT, CONCURRENCY, COVERAGE (a test or a path does not execute on a lane; owning checks 3A, 3B and 7).")
edit(S,
 "6. Verdict with the deciding file:line.\n",
 "6. Verdict with the deciding file:line.\n7. A CONFIRMED claim keeps the severity of its owning check. The bot's own label (\"optional\", a colour) does not lower it when the claim rests on a written repository rule. If the author declines the bot's fix, go to the last bullet of \"Replying to Wade\".\n")
edit(S,
 "optional forwarded agent items, never a blocker.",
 "optional forwarded agent items (never a blocker, unless step 7 applies).")

# Replying: a declined remedy.
edit(S,
 "- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write \"LGTM\", resolve a thread for him, or post without the author's approval.\n",
 "- Answer a must-change with a fact at the reviewed head (file:line, commit id). Never write \"LGTM\", resolve a thread for him, or post without the author's approval.\n"
 "- A declined remedy does not close a confirmed finding. This holds for any reviewer and for a bot. When the checks confirm the fact and the author declines the proposed fix, write the finding without the fix, and write the reason for declining as a condition on any fix (\"must not change what the other tests of the lane exercise\"). Before drafting the reply, search for a fix that meets the condition: the same change at a narrower scope (one test target, one file, one call site), or the way a sibling in the same file already solved it (`git grep` the neighbouring registrations, guards and helpers). Test every sentence of the form \"X needs Y\" in the draft before it is posted. Put the narrower fix before the author together with the reply. An \"answer only\" reply to a must-change signal (the four signals above, or a CHANGES_REQUESTED review) is the last choice. It then lists the narrower fixes that were tried and why each fails. Do not pass the finding on as settled: a list of decided points for a later review names the declined remedy, not the finding. Not from Wade's record. Precedent: PR 5022. Threads 4356060700 and 4645384802 were answered with one reason and a run started by hand. The reviewer kept the changes-requested state and supplied the narrower fix himself (comment 7118448228, PR 5606).\n")

# procedures.md, check 3 step 2 and the new steps.
edit(P,
 "A compile-time `#if` is not a runtime exit; a `min_slices_N` label",
 "A compile-time `#if` is not a runtime exit. It is form (f), steps 16 to 20; a `min_slices_N` label")

STEPS = """16. Regions (f): `grep -n -E '^[ \\t]*#[ \\t]*(if|ifdef|ifndef|elif|else|endif)\\b|SUCCEED\\(' full/<file>`. Added units: `git -C WT diff -U0 BASE HEAD -- t/<file> | grep -E '^\\+.*(TEST_CASE|SECTION\\(|GENERATE\\()'`, mapped to HEAD lines. The guard can predate the PR: `git -C WT show BASE:t/<file> | grep -n -E '^#(if|ifdef|ifndef|else|endif)'`.
17. Macro and lanes: `git -C WT grep -n -E 'option\\(<NAME>|compile_definitions\\([^)]*<NAME>|-D<NAME>|"<NAME>"' HEAD -- CMakeLists.txt '*/CMakeLists.txt' CMakePresets.json nix flake.nix .github GNUmakefile`. Gating lane: check 7, steps 2 to 4. No hit in the gating lane's recipe = off there. Assertions on that lane: read the lane's test log, or count the REQUIRE lines outside the region.
18. Needs: `git -C WT grep -n -A4 'if(<NAME>)' HEAD -- '*CMakeLists.txt' | grep -E 'target_sources|target_link_libraries|COMPILE_OPTIONS'` lists what the build adds only under the option. For each production symbol the guarded units call: `git -C WT grep -n '<symbol>' HEAD -- src` and `grep -n '<symbol>' full/<file>`. Defined in the test file = its own fake. Defined only in an option-only source = a define cannot run it.
19. Define safety: `git -C WT grep -n -E '#if.*<NAME>' HEAD -- h src`. Hits only in headers, inside templates = one target can pass the define, provided that no library on the test's link line instantiates the same templates for the types the test uses (read LIBRARIES in the registration). A hit in src/*.cpp of a linked library, or in a non-template type that such a library compiles = ask.
20. Sibling and policy: `git -C WT show HEAD:t/CMakeLists.txt | grep -n -B4 -E 'DEFINES|target_compile_definitions'`; quote the registration and the comment above it. `git -C WT show HEAD:AGENTS.md | grep -n -A6 'Every committed test must run in CI'`.
"""
ON_PR = """
On PR 5022 at ddf843ad97 (BASE 3bea58b788): step 16 t/t_amx_dispatch_dtype.cpp `#ifdef TRON_AMX_DISPATCH` :56, `#else` :400, SUCCEED :402; added SECTIONs :364, :368, :372, :377, all inside the :56 region; the `#else` case was already at BASE (:284-288). Step 17: CMakeLists.txt:46 default OFF; set at .github/workflows/cmake-single-platform.yml:355 and CMakePresets.json:68; no hit under nix/. Step 18: fakes of every entry point at :313-352; option-only source kernels/amx_attn.cpp (src/tron/CMakeLists.txt:221). Step 19: 7 regions in h/tron/models/self_attention.hpp, all inside the `self_attention` class template, none in src/*.cpp; the test links `tron pos_fake`, which hold no model objects. Step 20: t/CMakeLists.txt:273-276 (`t_page_share_counters DEFINES TRON_PAGE_SHARE_COUNTERS`) and :615 (`t_llama_unit DEFINES _GLIBCXX_ASSERTIONS`); AGENTS.md:29-35. Fires on t_amx_dispatch_dtype. Does not fire on t/t_amx_numerics.cpp :82-404: its units call the kernels of amx_attn.cpp, and the QK and PV cases SKIP without AMX (:380, :393). This example is from ishapira-positron (comment 7118448228, PR 5606), not from Wade's record.
"""
edit(P,
 "\n\nOn PR 1920: t/t_hwattention.cpp:670 `return;` under :603 TEST_CASE_METHOD",
 "\n" + STEPS + "\nOn PR 1920: t/t_hwattention.cpp:670 `return;` under :603 TEST_CASE_METHOD")
edit(P,
 "PR 4557: existing line stays at 96a6220ab6.\n",
 "PR 4557: existing line stays at 96a6220ab6.\n" + ON_PR)

# procedures.md, check 35: any bot author.
edit(P,
 "keep first author `cursor`, both flags false, one comment node.",
 "keep first authors that are bots (GraphQL prints the login without the `[bot]` suffix: `cursor`, `claude`), both flags false, one comment node.")
print("candidate edits applied")
