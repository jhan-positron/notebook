# The finding under study: Isaac's comment of 2026-11-24 00:48 UTC on tron PR 5022, and his fix PR 5606

Source: https://github.com/positron-ai/tron/pull/5022#issuecomment-7118448228 (author ishapira-positron). PR 5022 head at that time: ddf843ad97.

## Comment text (verbatim)

Thanks for the careful work on this, and for the detailed replies. Almost everything from our review is done, and we checked it ourselves: the kernels compile to the same instructions as before, and when we broke the new code in 14 different ways, your tests caught every one.

One thing keeps this at changes requested.

**The dispatch test does not run in the required CI lane.** With `TRON_AMX_DISPATCH` off, `t_amx_dispatch_dtype` compiles to its placeholder case. So the new 16-head checks only run when someone starts the legacy workflow by hand.

Your reason for keeping the option out of the Nix build makes sense: it would change what the model tests exercise for every pull request. There is a smaller way that avoids that. The test can pass the define itself, the way `t_page_share_counters` does, so only this one binary sees it.

To save you the work, we made that change in #5606, on top of your head. With the option off the test then runs all 30,747 assertions, and it fails when we break the dispatch code. That is the only thing we are still waiting on.

Two smaller notes:

- The registration line we suggested for `t_amx_numerics` was wrong: it does not configure. What you did instead is right. Sorry for that.
- Everything else is fine with us, including the three items you moved to #5511 and leaving kv_mul 8 out.


## PR 5606 (verbatim description)

Title: 🔧 Apply the #5022 review: run the AMX dispatch test with the option off
Author: ishapira-positron
Base branch: jhan-amx-kvmul16 (the branch of PR 5022)
Head: ishapira/jhan-amx-kvmul16-review-followup at 90a9110be5d2c6552267322c472902984dca8e0f
Created: 2026-11-24T00:47:57Z
Size: +12 -11 lines in 4 files

Here's the one open point from my review of #5022 as code instead of a comment. If you like it, take the two commits: cherry-pick them, or fast-forward your branch to this one. They sit on your head `ddf843ad97`.

## What changes

- **`t_amx_dispatch_dtype` runs its real cases wherever the tests are built.** It passes `TRON_AMX_DISPATCH` itself, the way `t_page_share_counters` passes its own define. With the option off the test was one placeholder case; now its dispatch checks run there too.
- **Nothing else sees the option.** The model tests of the required lane are unchanged, which was your reason for keeping the flag out of the Nix build. The option only changes code inside the `self_attention<model>` template, and no other translation unit in the test binary instantiates that template for the test's models.
- **The placeholder case is gone** (second commit). With the guard in place, a registration that loses the define compiles to the placeholder and passes; without the guard the test fails instead. You can drop this commit, at that cost.
- **The CMake comments and `README.ci.md` say where the test runs.**

## Where my review was wrong

- The registration line I suggested for `t_amx_numerics` (`LABELS "fake;skip_return_code_4"` through `add_catch_test`) does not configure. What you did instead is right.

## Heads-up

- **Your description goes stale in one place.** The Verification row for the default CI build says the AMX checks are compiled out. That no longer holds for this test.
- **The benchmark rows for `t_amx_dispatch_dtype` record 8 MB.** With its real cases the test peaks near 99 MiB by your measurement. `t/AGENTS.md` asks for a `bin/slice bench --update` after a change like this. I did not run it, because it needs a run on each machine class.
- A real-AMX run in required CI (your TODO, #3997) is a separate thing and still open.

## Tested

In the Nix sandbox, in a build with the option off, at this branch's tip: the test passes 30,747 assertions, where before it was one placeholder assertion. Eight one-line faults in the dispatch code each make it fail there, and so does removing the define. It also passes with the option on, and the first commit builds and passes on its own. The sandbox build is not the full CI lane (it leaves out the lane's model flags), and draft CI runs only lint and contract checks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## PR 5606 commits

```
c6cba6b0f8  Run the AMX dispatch test wherever the tests are built

t_amx_dispatch_dtype checks the AMX call sites in self_attention.hpp
against fake kernels that it defines itself, so it needs no AMX
hardware. It was compiled only when TRON_AMX_DISPATCH was ON. The
required CI lane leaves the option OFF, so there the test was a
placeholder case that reported success.

The test now passes the definition itself, as t_page_share_counters does
for its option. The option changes only code inside the
self_attention<model> template, and no other translation unit in this
binary instantiates that template for the test's models, so nothing else
in the binary disagrees about it.

The comment in src/tron/CMakeLists.txt and the paragraph in README.ci.md
now say that this test runs wherever the tests are built.

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
90a9110be5  Drop the placeholder case of the AMX dispatch test

The build now always defines TRON_AMX_DISPATCH for this test, so the
#else branch, a case that only reported success, can no longer be
compiled. Remove the guard and that case.

This also makes a lost definition visible. With the guard, a
registration that drops or misspells the define compiles to the
placeholder and passes. Without the guard, the bf16 sections fail.

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
```

## PR 5606 diff against ddf843ad97 (verbatim)

```diff
diff --git a/README.ci.md b/README.ci.md
index 3fd86635ef0..00872016b08 100644
--- a/README.ci.md
+++ b/README.ci.md
@@ -594,7 +594,10 @@ carries the kernels and selects them at run time only on hosts with AMX. The
 `deb-host` preset inherits the setting from `deb`. Every other preset leaves
 it at its default OFF. The kernel cases of `t_amx_numerics` execute AMX only
 when the test job lands on a Granite Rapids runner; elsewhere Catch2 reports
-them as skipped, and ctest and Slice still report a pass.
+them as skipped, and ctest and Slice still report a pass. `t_amx_dispatch_dtype`
+compiles the dispatch with its own define wherever the tests are built, and
+defines fake kernels, so the call sites in `h/tron/models/self_attention.hpp`
+are tested where the option is OFF too.
 
 `BUILD_INGEST_MODELS=ON` enables the ingest pipeline integration in the C++
 build. GCP Nix also requires the complete test model profile. Developers can
diff --git a/src/tron/CMakeLists.txt b/src/tron/CMakeLists.txt
index d3f09ce3c5a..cb172334c51 100644
--- a/src/tron/CMakeLists.txt
+++ b/src/tron/CMakeLists.txt
@@ -214,7 +214,9 @@ add_library(tron STATIC
 # the deb preset and the legacy CMake workflow (cmake-single-platform.yml) set
 # it ON. In that workflow the kernel tests execute only on a Granite Rapids
 # runner; on other runners they are reported as skipped, and ctest and Slice
-# still report a pass.
+# still report a pass. t_amx_dispatch_dtype passes the definition itself and
+# defines fake kernels, so the call sites are compiled and tested wherever the
+# tests are built.
 # TODO(jhan): make one real-AMX test execution a required CI check
 # (https://github.com/positron-ai/tron/issues/3997).
 if(TRON_AMX_DISPATCH)
diff --git a/t/CMakeLists.txt b/t/CMakeLists.txt
index 32692477e16..f519b4a3cb8 100644
--- a/t/CMakeLists.txt
+++ b/t/CMakeLists.txt
@@ -624,8 +624,11 @@ add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake
   PROPERTIES SKIP_RETURN_CODE 4 LABELS fake)
 set_property(TEST t_amx_numerics APPEND PROPERTY LABELS skip_return_code_4)
 # Defines CPU fakes for every amx_attn_h128g4 entry point in its own TU (see the file
-# header), so it must not be merged with another AMX test.
-add_catch_test(NAME t_amx_dispatch_dtype LIBRARIES tron pos_fake PROPERTIES LABELS fake)
+# header), so it must not be merged with another AMX test. It passes the define
+# itself, as t_page_share_counters does, so the dispatch call sites are compiled
+# and tested wherever the tests are built, whatever the value of the
+# TRON_AMX_DISPATCH option.
+add_catch_test(NAME t_amx_dispatch_dtype DEFINES TRON_AMX_DISPATCH LIBRARIES tron pos_fake PROPERTIES LABELS fake)
 add_catch_test(NAME t_matmul LIBRARIES tron pos PROPERTIES RESOURCE_LOCK fpga LABELS fpga)
 add_catch_test(NAME t_first_result_fault LIBRARIES tron pos PROPERTIES RESOURCE_LOCK fpga LABELS fpga)
 add_catch_test(NAME t_metrics LIBRARIES tron pos PROPERTIES RESOURCE_LOCK fpga LABELS fpga)
diff --git a/t/t_amx_dispatch_dtype.cpp b/t/t_amx_dispatch_dtype.cpp
index 234c850ca84..b0a5e7627b9 100644
--- a/t/t_amx_dispatch_dtype.cpp
+++ b/t/t_amx_dispatch_dtype.cpp
@@ -53,8 +53,6 @@
 
 using namespace tron;
 
-#ifdef TRON_AMX_DISPATCH
-
 namespace {
 
 struct amx_probe {
@@ -397,8 +395,3 @@ TEST_CASE("AMX dispatch rejects non-bf16 queries and partial pages",
     exercise_page<host_fp16>(page_size);
   }
 }
-#else
-TEST_CASE("AMX dispatch dtype test skipped (dispatch not compiled)", "[amx_numerics]") {
-  SUCCEED("build without TRON_AMX_DISPATCH - nothing to test");
-}
-#endif
```
