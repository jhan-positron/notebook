#!/usr/bin/env python3
# Builds respond-2-Isaac.html from the content below. Run with python3 -I.
import html, re, sys

OUT = sys.argv[1]

# ---------- tiny markdown -> html ----------
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s

def md(text):
    out = []
    lines = text.strip("\n").split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            i = j + 1; continue
        if ln.strip() == "":
            i += 1; continue
        if re.match(r"^- ", ln):
            items = []
            while i < len(lines) and re.match(r"^- ", lines[i]):
                item = lines[i][2:]
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and not re.match(r"^- ", lines[i]):
                    item += " " + lines[i].strip(); i += 1
                items.append("<li>" + inline(item) + "</li>")
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        if re.match(r"^\d+\. ", ln):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                item = re.sub(r"^\d+\. ", "", lines[i]); i += 1
                while i < len(lines) and lines[i].startswith("  ") and not re.match(r"^\d+\. ", lines[i]):
                    item += " " + lines[i].strip(); i += 1
                items.append("<li>" + inline(item) + "</li>")
            out.append("<ol>" + "".join(items) + "</ol>"); continue
        if ln.startswith("### "):
            out.append("<h4>" + inline(ln[4:]) + "</h4>"); i += 1; continue
        # paragraph
        buf = [ln]; i += 1
        while i < len(lines) and lines[i].strip() != "" and not lines[i].startswith("```") and not re.match(r"^(- |\d+\. |### )", lines[i]):
            buf.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out)

# ---------- content ----------
SHORT = """
Isaac requested changes on PR 5022 with one review body and 26 inline comments. Every claim he makes about the code checks out at the head commit (4c4b7b8864); the drafts below accept 20 of the 26 inline requests outright, modify 4, and answer the rest. Six decisions are yours before anything is posted: the CI-lane flag, the three hot-path edits, the landing shape, kv_mul 8, issue numbers in source, and how to close the benchmark-provenance gap.
"""

WORDS = [
 ("tron", "the inference program under test. runtron is its command-line tool, rinzler the production server."),
 ("AMX / AVX-512", "Intel CPU instruction sets. AMX multiplies 16-row tiles; AVX-512 works on 512-bit vectors. The AMX attention kernels live in src/tron/kernels/amx_attn.cpp."),
 ("kv_mul / group_heads / GQA", "query heads per KV head (grouped-query attention). llama-3.1-8b has 4, Muse Glimmer 30B has 16. The kernels take it as the template parameter group_heads; group_heads_ok lists the served values."),
 ("bf16", "bfloat16, the 2-byte float format K, V and (for eligible executors) Q are stored in."),
 ("TRON_AMX_DISPATCH", "the CMake option (default OFF) that compiles the AMX kernels and their dispatch. With it OFF, both AMX test binaries hold one placeholder case that reports SUCCEED."),
 ("kill switch", "TRON_AMX_DISABLE=1: the same binary with AMX turned off at run time."),
 ("GCP Nix lane", "gcp-nix.yml, the required pull-request CI workflow. It builds through nix/cmake-tron-test-build.nix, which never sets TRON_AMX_DISPATCH."),
 ("CMake lane", "cmake-single-platform.yml, the legacy workflow. It passes -DTRON_AMX_DISPATCH=ON but runs only on manual dispatch or when publish-deb.yml calls it on a tag push."),
 ("Catch2 SKIP", "a test-case result that Catch2 counts as skipped, not passed. Catch2 exits with code 4 only when every selected case was skipped."),
 ("Slice", "bin/slice, the test runner CI uses. It maps exit code 0 to passed and a code listed under the label skip_return_code_N to skipped."),
 ("delphi-3bda", "the Granite Rapids (Intel Xeon 6962P) test host with AMX. The PR's own test and benchmark records come from it."),
 ("merge base / head", "merge base 6198824246 is the shared ancestor of main and the branch. head 4c4b7b8864 is the commit Isaac reviewed. 5061623a34 is the commit the benchmarks were measured at."),
 ("KV page / dense page", "a 64-token block of the KV cache. A page is dense when the query sees all 64 tokens inside the sliding window; only dense pages take the AMX path."),
 ("Q pack", "the copy of one token's query group into the tile B-operand layout (pack_q_group_128x4). Today it runs before the dense-page check."),
 ("transposing store / lanes", "the AVX-512 code after the QK tile multiply that writes score rows into the caller's buffer. One lane is 4 rows; 16 heads use 4 lanes, 4 heads use 1."),
 ("PR body", "the pull-request description. Its Verification section holds the test and benchmark tables."),
 ("#5021 / #3997", "#5021 tracks the kernel rename and making a new shape a minimal change; it excludes adding a shape and kernel performance. #3997 tracks making one real-AMX test execution a required CI check."),
 ("request-for-change / request-for-response / informational", "how each of Isaac's points is marked below. request-for-change: he asks for a code, comment, test, doc, CI or PR-body change. request-for-response: he asks a question, for evidence, or for a decision. informational: a statement that needs neither."),
]

DECISIONS = [
 ("D1", "The required CI lane",
  "Isaac asks to add -DTRON_AMX_DISPATCH=ON to the GCP Nix build (inline I7, top T1). On 2026-10-19 you deferred that line to issue #3997 with the CI owner, because on a Granite Rapids runner it routes every bf16 head-128 attention in every test of the required lane, including the model tests, through the AMX kernels.",
  "**Recommended:** open the one-line change as its own PR under #3997 with the CI owner as reviewer, and rebase this PR on it if it merges first. Alternative: put the line in this PR, which clears Isaac's blocker directly but changes what the required lane exercises without a separate sign-off. The drafts assume the recommendation."),
 ("D2", "Three hot-path edits in self_attention.hpp",
  "Isaac proposes three dispatch-path changes: move the Q pack after the dense-page check (I4), tag s_pages uninitialized (I5), and replace the per-head memcpy with a view (I6). All three change code on the path the benchmarks measured.",
  "**Recommended:** accept I5 and I6 here (two small edits Isaac wrote out), and move I4 into one kernel-performance follow-up issue together with the vectorised pack (I9) and the stage-3 hoist (I12), so the pack change lands with a Granite Rapids measurement. Alternative: accept I4 here too; the draft for that case is in the I4 card. Either way D6 applies."),
 ("D3", "Landing shape of the branch",
  "I2 asks that the comment-only commit travel with the gate change, I11 proposes three refactor-first commits, I18 warns that his hunk slices proved nothing. The repository allows squash, merge and rebase merges; your PR 5098 landed as a merge commit with its branch commits.",
  "**Recommended:** squash-merge this PR and say so in the PR body. That answers I2, I11 and I18 with one sentence each and avoids a force-push on a reviewed branch. Alternative: rebase into three commits at the end of the review (I11's shape, with the SKIP guards, the CMake comment and the README fix as step 2)."),
 ("D4", "kv_mul 8 in this PR",
  "Isaac's next-decision question: does any served head-128 model with kv_mul 8 run CPU attention in production? If so, he wants 8 added here. Facts found: llama-2-70b, llama-3-70b, llama-3.1-70b and qwen-3-32b have 64 query heads over 8 KV heads and are support_level production [h/tron/plugins/llama.hpp:1601-1617; config/models.yaml:162, 236, 293, 542]. Their hand-written plugin defines no force_hw_attn, so with USE_HW_ATTN unset the FPGA path is 'default off for this model' and every layer runs CPU attention [h/tron/models/model.hpp:744-764, :1630-1632]. qwen-3-30b-a3b also has kv_mul 8 but is an ingested model (FPGA attention by default, support_level working). Whether the production fleet sets USE_HW_ATTN=1 for the 70b models is not visible from the repository: Insufficient data; a production host's /etc/rinzler/instance-N.env or its rinzler journal line 'HW attention ... for model' would resolve it.",
  "**Recommended:** keep 8 out of this PR, write the reason into the group_heads_ok comment (the set is what has been validated on AMX hardware, not what the loops could serve), and open a follow-up issue for kv_mul 8 (not #5021, which excludes adding a shape). Alternative: add 8 here, which needs one more delphi-3bda round before merge: numerics sections for 8, token identity and 8-user throughput for llama-3.1-70b and qwen-3-32b."),
 ("D5", "Issue numbers in source comments",
  "Isaac's suggestion for amx_attn_iface.hpp:16 ends with '(#5021)'. On PR 5015 you rejected an issue number at this same line ('Issue# should not appear in source code', 2026-10-18) and noted the rule for later reviews. The tree is not consistent either way (wide.hpp:1263 and bf16.hpp:127 cite issue numbers).",
  "**Recommended:** keep your rule. The draft takes Isaac's reason clause and leaves the number out; #5021 stays linked from the PR body. Alternative: take his line verbatim."),
 ("D6", "Closing the benchmark-provenance gap",
  "The benchmarks were measured at 5061623a34; the head is 4c4b7b8864. Between the two, the kernel and call-site code changed only in type aliases, a hoisted constexpr and an equivalent if-constexpr ladder (checked with git diff). An object compare of the kernel translation unit would close that gap. But if I5 and I6 land (D2), the dispatch epilogue changes after the measurement, and the kernel compare no longer covers it.",
  "**Recommended:** do the object compare of all six instantiations (no hardware needed) and rerun one Glimmer cell (tp2, prompt 1024, 8 users, 2 repetitions per arm) plus the llama-3.1-8b token-identity cell at the final head on delphi-3bda. Keep the PR body sentence 'Benchmarks are not rerun at the current head' and add the new facts after it. Alternative: object compare only, if I5 and I6 are deferred as well."),
]

TOP = [
 dict(id="T0", title="Opening assessment, 'Architecture: Ideal', 'Not verified: none', 'Purpose: Justified', 'Event: REQUEST_CHANGES'",
      cls="informational", quote="The shape here is right: one predicate shared by the gate and the kernel signature, the 4-head object code unchanged, and the kernel-case skip now visible instead of a WARN that passed.",
      verdict="No ask. His description of the design matches the code.",
      reply="One acknowledging line in the top-level reply is enough. No separate response."),
 dict(id="T1", title="Blocker: no pull-request lane sets TRON_AMX_DISPATCH, so both AMX binaries run as stubs",
      cls="request-for-change", quote="none of it runs in CI at this head: no PR lane sets TRON_AMX_DISPATCH, so both AMX binaries run as their stubs",
      verdict="Confirmed. nix/cmake-tron-test-build.nix:79-101 never sets the option; CMakeLists.txt:46 defaults it OFF; Build Tron job 117831672410 has no compile line for kernels/amx_attn.cpp; Test host job 117835534166 lists both binaries as passed in under 1 s (the SUCCEED stubs). Same ask as I7 and I8. Decision D1.",
      reply="""
You are right on the facts. The required pull-request lane is `gcp-nix.yml`. It builds through `nix/cmake-tron-test-build.nix`, whose cmake arguments never set `TRON_AMX_DISPATCH` [nix/cmake-tron-test-build.nix:79-101], and the option defaults OFF [CMakeLists.txt:46]. I reproduced your check on Build Tron job 117831672410: no line mentions `TRON_AMX_DISPATCH` or `amx_attn`, and the log has no compile line for `kernels/amx_attn.cpp`, which CMake adds only with the option on [src/tron/CMakeLists.txt:219-220]. The Test host job 117835534166 lists both AMX binaries as passed in under 1 s. That is the `SUCCEED` placeholder case in each.

The comment at src/tron/CMakeLists.txt:214 was true when I wrote it on 2026-09-07 [f4889f8072]. The GCP Nix cutover on 2026-09-10 [9a5e03687a] removed the `pull_request` trigger from `cmake-single-platform.yml`, and I did not update the sentence. README.ci.md:581-588 has the same drift.

Will do in this PR: rewrite the CMake comment and the README paragraph so they name the lanes that exist at this head (text under your inline comments at src/tron/CMakeLists.txt:216).

The one-line `-DTRON_AMX_DISPATCH=ON` for `nix/cmake-tron-test-build.nix` I will open as its own PR under #3997, with the CI owner as reviewer. Reason: the required lane's test job can land on a Granite Rapids runner (this head's Test host job ran on delphi-3af6, a Xeon 6962P). With the option on, every bf16 head-128 attention with kv_mul 4 or 16 in every test of that lane, including the model tests that `-DTRON_REQUIRE_ALL_MODEL_TESTS=ON` requires, then goes through the AMX kernels. That change in what the required lane exercises needs its own sign-off. I recorded the lane facts and this consequence on #3997 on 2026-10-19. If that PR merges first, I will rebase this one so its own GCP Nix run is the in-repo evidence you ask for.
"""),
 dict(id="T2", title="Blocker: the 16-head epilogue has no assertion on its softmax state",
      cls="request-for-change", quote="the 16-head epilogue has no assertion on its softmax state",
      verdict="Confirmed. grep for v_star, s_star, m_star, is_valid_for in t/t_amx_dispatch_dtype.cpp returns nothing; the assertions stop at call counts, group sizes, stats and the packed input [t/t_amx_dispatch_dtype.cpp:203-244]. Same ask as I19.",
      reply="Agreed. Will do: the per-head state check, in every section of `exercise_page`. Text and expected values are under your inline comment at t/t_amx_dispatch_dtype.cpp:209."),
 dict(id="T3", title="Blocker: the new transpose lanes have no host-testable path",
      cls="request-for-change", quote="the new transpose lanes have no host-testable path",
      verdict="Confirmed. store_transposed_rows sits in the anonymous namespace of the only -mamx translation unit [src/tron/kernels/amx_attn.cpp:142-170]; its only caller is qk_rowmajor_128x4; the only test reaching it is check_qk<16> behind the SKIP guard [t/t_amx_numerics.cpp:317-324]. Same ask as I10.",
      reply="Agreed. Will do: `transpose_scores<group_heads>` in an AVX-512-only header, and an ungated case for 4 and 16 heads that runs on every host, including the required lane. Details under your inline comment at src/tron/kernels/amx_attn.cpp:156."),
 dict(id="T4", title="Coverage gap: real-AMX execution of check_qk<16> and check_pv<16> at 4c4b7b8864",
      cls="request-for-response", quote="Still needed: per-section Catch2 output from a Granite Rapids host at this head, or a CI run with the option on landing on a delphi runner.",
      verdict="Confirmed that no in-repo record exists. The PR body's counts (17,425 assertions with AMX, 4,111 under the kill switch) come from round3.log on delphi-3bda, outside the repository. A CI dispatch alone would not produce per-section output: Slice sends each binary's output to a per-test log that is uploaded only on failure [cmake-single-platform.yml:485-490; bin/slice:4680, :4743-4745], and its runners include AMD Genoa hosts without AMX. Needs a delphi-3bda run at the final head.",
      reply="""
Agreed. No pull-request lane sets `TRON_AMX_DISPATCH` [nix/cmake-tron-test-build.nix:79-101]. The one workflow that sets it ON runs on manual dispatch or `workflow_call` only [.github/workflows/cmake-single-platform.yml:5-13, :355].

I will attach per-section Catch2 output from delphi-3bda (a Granite Rapids host with AMX) at the final head of this PR, in the Verification section. One command per section, with Catch2's `-c` section filter, so each section reports its own assertion count. The test executables sit in the build root [CMakeLists.txt:66]:

```
gen/t_amx_numerics "AMX QK does not digress from the AVX dotter" -c "4 heads: rows 0..3 match the dotter, rows 4..15 untouched"
gen/t_amx_numerics "AMX QK does not digress from the AVX dotter" -c "16 heads: all 16 rows match the dotter"
gen/t_amx_numerics "AMX PV stays inside the AVX weight-rounding envelope" -c "4 heads"
gen/t_amx_numerics "AMX PV stays inside the AVX weight-rounding envelope" -c "16 heads"
```

The record will also carry a JUnit report (`-r junit`, one `<testcase>` per section), the full run, the kill-switch run (`TRON_AMX_DISABLE=1`, expected `test cases: 4 | 2 passed | 2 skipped`), `gen/t_amx_dispatch_dtype`, the commit hash, the hostname and the host's AMX cpuinfo flags.

A CI dispatch alone would not close this gap. The build and test-host jobs of `cmake-single-platform.yml` land on any runner labelled `[self-hosted, fpga, test, avx512]` [cmake-single-platform.yml:151, :381]. That label set includes the AMD Genoa hosts, which have no AMX [README.ci.md:447-452]. The job log also shows one pass line per binary and nothing else: Slice writes each binary's output to a per-test log and uploads it only on failure [bin/slice:4680, :4743-4745; cmake-single-platform.yml:485-490]. I will still dispatch that workflow for the linked build (your second gap).

The required-lane change stays on #3997, as recorded there on 2026-10-19.
"""),
 dict(id="T5", title="Coverage gap: AMX-on compile and link at this head",
      cls="request-for-response", quote="Still needed: one linked build of both binaries, for example a manual cmake-single-platform.yml dispatch at the head.",
      verdict="Confirmed. gh run list on the branch shows only GCP Nix and Debian smoke runs. cmake-single-platform.yml:353-356 configures with -DTRON_AMX_DISPATCH=ON and links libtron with the kernel TU, rinzler, runtron and all test binaries. Its log proves compile and link, not kernel execution.",
      reply="""
Agreed. No CI job at 4c4b7b8864 compiled the option on. The Build Tron log of GCP Nix run 39179018918 (job 117831672410) links `t_amx_numerics` and `t_amx_dispatch_dtype` but has no line for `kernels/amx_attn.cpp`, the one translation unit compiled with the AMX flags. My AMX-on linked build is the plain-shell build on delphi-3bda (`round3.log`), outside the repository.

I will dispatch the CMake lane at the final head of this PR:

```
gh workflow run cmake-single-platform.yml --ref jhan-amx-kvmul16 -F skip_benchmarks=true
```

That job configures `--preset native -DTRON_AMX_DISPATCH=ON` with tests enabled [cmake-single-platform.yml:353-356, CMakeLists.txt:36]. It links libtron with the kernel translation unit, rinzler, runtron and the three test binaries, and its `test-host` job runs both AMX binaries through `bin/slice run --filter=host` [cmake-single-platform.yml:468-471]. I will add to the Verification table: the run id, the Build Tron job id with its `kernels/amx_attn.cpp` compile line and the two link lines, the Test Host job id with its two `passed` status lines, and the test-host runner name.

One limit. This closes the compile-and-link gap only. The status line reads `passed` whether the two kernel cases ran or skipped, because Catch2 exits 0 on `SKIP` and `t_amx_numerics` has no `skip_return_codes` entry [bin/slice:1208-1213; config/test-benchmarks.json:152]. Real-AMX execution evidence is the delphi-3bda per-section record above.

One caveat on the dispatch itself. The last runs of that workflow (2026-09-28 to 2026-09-30) were `pull_request` events from before the trigger change, with build and test-host skipped, and the 2026-10-30 `publish-deb` dispatch also skipped its call into it. Whether a manual dispatch runs end to end after the GCP Nix cutover is unknown until tried.
"""),
 dict(id="T6", title="Closed: TRON_AMX_DISPATCH=OFF build at the head",
      cls="informational", quote="Build Tron job 117831672410 compiled both test TUs with the option off and Test host ran them.",
      verdict="Confirmed. Run 39179018918 is a pull_request run on head 4c4b7b8864 (started under PR 5015, now listed under 5022). The later run 39181654178 reused the cached build (same source hash c168a39) and skipped its Test host step, so the pair Isaac cites is the only OFF-arm record at this head. The PR-body edit belongs to I16.",
      reply="Agreed. I checked the run myself. I will replace the 'Insufficient data' OFF row of the PR body with these two job ids and the stub-only result (text under your inline comment at t/t_amx_dispatch_dtype.cpp:51)."),
 dict(id="T7", title="Reports resting on a false CI premise (his own sub-reviewers)",
      cls="informational", quote="…stated that CI built with the option on and that the 16-head sections executed. The build log contradicts this.",
      verdict="Statement about Isaac's review tooling, not about the PR. The likely root cause is in the tree: README.ci.md:581-583 says the option is on 'so CI covers that code' and src/tron/CMakeLists.txt:214 says 'The CMake CI lane configures with the option ON'. Both are fixed under I7 and I8.",
      reply="Optional one line: 'Two sentences in the tree probably fed that premise, README.ci.md:581-583 and src/tron/CMakeLists.txt:214. Both are rewritten in this PR.'"),
 dict(id="T8", title="Coverage gap: Granite Rapids timing for the 16-head pack and transpose",
      cls="request-for-response", quote="Findings 5 and 13 were measured on Zen 4 and via instruction counts. The PR-level Glimmer A/B exists in the author's record only.",
      verdict="Confirmed. No per-kernel timer exists: the attention-path stats time one attention job, not one kernel [h/tron/models/attn_stats.hpp:229-233]; no Catch2 BENCHMARK covers the AMX kernels. The whole-job numbers on Granite Rapids are in glimmer-20261016/attn-stats-compare.md (busy time per attention job 0.102 ms with the kill switch, 0.060 ms with AMX; per worker per forward 5.3 ms to 3.1 ms). He names no 'still needed' item, so the response is an offer, not a promise he asked for.",
      reply="""
You are right. No per-kernel timing of the 16-head pack or the transposing store exists on Granite Rapids, and the Glimmer A/B records are outside the repository.

What exists on Granite Rapids is whole-job level. The attention-path stats (`TRON_ATTN_STATS=1`) time one attention job, both software passes and the join, not one kernel [h/tron/models/attn_stats.hpp:229-233]. For Glimmer tp2, FPGA attention, prompt 1024, 8 users, decode, the busy time per attention job is 0.102 ms with the kill switch and 0.060 ms with AMX, in both repetitions [`glimmer-20261016/attn-stats-compare.md`, section 7]. Per worker per forward that is the PR body's 5.3 ms to 3.1 ms. The nightly comparison's 20-second hardware-counter probe recorded 5.52 to 5.56 billion AMX busy cycles in each AMX-on pass and 0 in the others [`glimci-20261017/summary.md`]. These numbers bound the pack and transpose cost. They do not isolate it.

Two things I can add:

1. The A/B record files, attached to this PR as a comment: `glimmer-20261016/rt-results.txt` and `attn-stats-compare.md`, `glimext-20261018/rt-results.txt` and `identity.txt`, `glimci-20261017/summary.md`.
2. A per-kernel timing on delphi-3bda at the head: ns per call for `pack_q_group_128x4`, `qk_rowmajor_128x4` and `weights_times_v_128x4`, each at 4 and 16 heads, on a dense 64-token page fixture, median over at least 1,000 calls. I would make that the baseline of the kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack), so each of those lands with a before-and-after number. Until then your Zen 4 figures are the only per-kernel numbers, and I do not dispute them.

Say if you want only one of the two.
"""),
 dict(id="T9", title="Next decision: does a served head-128 model with kv_mul 8 run CPU attention in production? If so, add 8 here",
      cls="request-for-response", quote="whether any served head-128 model with kv_mul 8 runs CPU attention in production (if so, add 8 here rather than in a follow-up)",
      verdict="Partly confirmed. Yes at tron's defaults: llama-2-70b, llama-3-70b, llama-3.1-70b and qwen-3-32b (64 query heads over 8 KV heads, support_level production) have no force_hw_attn in their hand-written plugin, so with USE_HW_ATTN unset every layer runs CPU attention [h/tron/plugins/llama.hpp:1601-1617; h/tron/models/model.hpp:744-764]. The production fleet's USE_HW_ATTN setting is Insufficient data (not in the repository). Decision D4; the draft declines the 'add 8 here' branch with the reason.",
      reply="""
Your condition is met at tron's defaults, and I still take the second branch of your Architecture gap 1 (write why not, in `group_heads_ok`) rather than adding 8 here.

The facts:

- The served head-128 models with kv_mul 8 (kv_mul = query heads per KV head) are llama-2-70b, llama-3-70b, llama-3.1-70b and qwen-3-32b: 64 query heads over 8 KV heads, all `support_level: production` [h/tron/plugins/llama.hpp:1601-1617; config/models.yaml:162, 236, 293, 542]. qwen-3-30b-a3b has kv_mul 8 too, but it is an ingested model and gets FPGA attention by default.
- The hand-written plugin defines no `force_hw_attn`. With `USE_HW_ATTN` unset the FPGA path is therefore "default off for this model", and every layer runs CPU attention [h/tron/models/model.hpp:744-764, :1630-1632; h/tron/models/hw_attn_config.hpp:12-14].
- The closest record to production I have is the CI machine delphi-3bda, provisioned by platformd. Its `/etc/rinzler/instance-1.env` of 2026-09-13, written while llama-3.3-70b-instruct-good-tp4 was provisioned, sets no `USE_HW_ATTN`, and its rinzler journal of 2026-09-22 reads "HW attention disabled for model 'llama-3.3-70b-instruct-good-tp4': default off for this model". Whether the production fleet sets `USE_HW_ATTN=1` for these models I cannot see from the repository.

Why not add 8 in this PR: the kernels for 8 have never run on AMX hardware. The code change is small (`group_heads_ok`, the instantiation list at amx_attn.cpp:316-326, test sections). The validation is a full hardware round: numerics sections for 8, plus token identity and 8-user throughput for llama-3.1-70b and qwen-3-32b on delphi-3bda. This PR's measurements cover 4 and 16 only, and it is held to a minimum change (#5021 records that, and excludes adding a shape).

Will do: write the reason into the `group_heads_ok` comment (text under Architecture gap 1), replace "No measurements remain pending" in the PR body with the kv_mul-8 item, and open a follow-up issue for kv_mul 8, ordered after #5021.
"""),
 dict(id="T10", title="Next decision: benchmark provenance, object compare of the <16> instantiation between 5061623a34 and head, or one Glimmer rerun",
      cls="request-for-response", quote="whether to close the benchmark provenance gap with an object compare of the <16> instantiation between 5061623a34 and head or one Glimmer rerun",
      verdict="Confirmed gap. git diff 5061623a34..4c4b7b8864 on the kernel and call-site files shows comments, two type aliases (same types), an unpacked_tile alias, two static_asserts, s + r * TILE_ROWS_16 for s + r * 16, the if-constexpr ladder (same three stores in the same order for 16 heads), and a hoisted constexpr operation_kv_mul at the call site. Decision D6.",
      reply="""
Both. The object compare closes the kernel side. Because this review also changes the dispatch epilogue (the `s_pages` tag and the row view, under your inline comments at self_attention.hpp:1755 and :1788), one rerun closes the call-site side.

Between 5061623a34 (the measured commit) and head, the kernel and call-site files changed in comments and compile-time spellings only:

- Two type aliases replace the spelled-out K and V view types in the kernel signatures and instantiations [h/tron/kernels/amx_attn_iface.hpp:140-141; src/tron/kernels/amx_attn.cpp:317-326].
- An `unpacked_tile` alias, two `static_assert`s and a `constexpr lanes` value were added [src/tron/kernels/amx_attn.cpp:150, :213-216].
- The single `if constexpr (group_heads == 16)` block became three `if constexpr (lanes > N)` blocks. For 16 heads they emit the same three lane stores in the same order [src/tron/kernels/amx_attn.cpp:245-253].
- The pack call site reads `geometry.kv_mul()` into a `constexpr` local before use [h/tron/models/self_attention.hpp:1693-1696].

Will do:

1. Compile `amx_attn.cpp` at 5061623a34 and at the final head with the same clang 19.1.7 flags, and diff the disassembly of all six instantiations. The result goes into the Verification section as a new row, with its file (`glimext-20261018/preservation3.txt`). No AMX hardware is needed for this.
2. Rerun the Glimmer tp2 / prompt 1024 production-attention cell (8 users, 2 repetitions per arm) and the llama-3.1-8b tp2 / prompt 1024 token-identity cell at the final head on delphi-3bda, because the epilogue edits are on both models' dispatch path.
3. Keep the sentence "Benchmarks are not rerun at the current head" for the other cells and add the two new facts after it.
"""),
 dict(id="T11", title="Architecture gap 1 (his label: follow-up): the set {4, 16} has no written reason; replace the first static_assert with the real constraint",
      cls="request-for-change", quote="Either instantiate 8 or write why not, in group_heads_ok. While there, the first static_assert at amx_attn.cpp:213 is a third copy of the set; the real transpose constraint is % 4 == 0 && <= 16.",
      verdict="Confirmed. The pack and PV loops are bounded by group_heads [src/tron/kernels/amx_attn.cpp:132, :271]; the store ladder derives its lane count from group_heads [:215-216, :244-253]. A standalone AVX-512 run of the ladder with 4, 8, 12 and 16 heads at strides 64 and 80 gave 0 mismatches in 9,216 positions. No written reason for {4, 16} exists in the PR body, #5021 or the PR 5015 annotations. Same as I14 and I23. Decision D4.",
      reply="""
You are right on both points. Will do, in this PR: write the reason into the `group_heads_ok` comment, and replace the first `static_assert` with the real constraint. I will not instantiate 8 here (reason under your "next decision" question).

The kernels do serve any multiple of 4 up to 16 as written. The pack loop and the PV conversion loop are bounded by `group_heads` [src/tron/kernels/amx_attn.cpp:132, :271]. The QK store ladder derives its lane count from `group_heads` [amx_attn.cpp:215-216, :244-253]. I ran the store ladder (pure AVX-512, no AMX needed) with 4, 8, 12 and 16 heads at row strides 64 and 80 floats, with your constraint in place of the first assert. Every written row matched the transpose, and every row above `group_heads` kept its sentinel: 0 mismatches in 9,216 positions. The call-site buffers also fit 8 and 12 [h/tron/models/self_attention.hpp:260, :1755, :1787].

The first `static_assert` was a tripwire I added when the store still tested `group_heads == 16` by name [7e7f52d761]. The same commit made the ladder generic, so the tripwire now guards nothing. Replacement (your form), under your inline comment at amx_attn.cpp:213.

The reason for {4, 16}: the set is what has been validated on AMX hardware, not what the loops could serve. Proposed comment for `group_heads_ok` [h/tron/kernels/amx_attn_iface.hpp:143-145]:

```
// The group sizes the kernels are compiled for: 4 (llama-3.1-8b, qwen3-4b)
// and 16 (Muse Glimmer 30B). The set is the sizes validated on AMX hardware
// (t_amx_numerics sections, token identity and throughput runs), not the
// sizes the code could serve: the pack, the PV conversion and the QK store
// ladder are written for any multiple of 4 up to 16. kv_mul 8 (the llama-70b
// family, qwen-3-32b) has no AMX run yet and is left out. To add a size: add
// it here, add its explicit instantiations at the end of amx_attn.cpp, add
// its t_amx_numerics sections, and run them on an AMX host.
```

The test comment at t_amx_numerics.cpp:117-118 takes your wording from the inline comment there, so it stops saying "above 16" for 8.
"""),
 dict(id="T12", title="Architecture gap 2 (his label: follow-up): the names amx_attn_h128g4 / _128x4 now lie; 'kept' without a why; rename in a separate mechanical PR",
      cls="request-for-change", quote="Comments describe what is. Rename to amx_attn_h128 / _128 in a separate mechanical PR.",
      verdict="Confirmed. The names occur 87 times in 8 files at head. Issue #5021 (open, created 2026-10-18) already tracks the rename and gives the reason (minimum-change requirement) but fixes no spelling. Same as I1. Decision D5.",
      reply="""
Agreed on both. The rename stays out of this PR and goes to #5021, which is open and names the target family (head 128, `group_heads` as the parameter). I will add your spelling, `amx_attn_h128` and the `_128` suffix, to the issue. The names occur 87 times in 8 files at this head, so the rename is its own mechanical PR. #5021 also carries one requirement beyond the rename: adding a third group size must be a minimal code change.

The comment is the part I fix here. "are kept" records the decision and not the reason. Text under your inline comment at amx_attn_iface.hpp:16, without an issue number in the source (the rule I applied on #5015); the PR body links #5021.
"""),
 dict(id="T13", title="Architecture gap 3 (his label: accepted): two homes for the group set are fine; README.ci.md has already drifted",
      cls="request-for-change", quote="README.ci.md:586-587 still says 'skip with a warning' after the CMake comment moved to 'reported as skipped' -- same sentence, two homes, already drifted.",
      verdict="The two-homes half is informational (accepted by him). The README half is confirmed: README.ci.md is untouched on the branch, and lines 581-588 still say 'so CI covers that code' and 'skip with a warning'. The flags block at README.ci.md:563-568 is a third unnamed home for the same flag. Same as I8.",
      reply="""
Agreed on both.

On the group set: no change. The predicate (`group_heads_ok`, amx_attn_iface.hpp:146-148) and the instantiation list (amx_attn.cpp:316-326) stay as two homes joined by the comment at amx_attn.cpp:316. A single declared list that generates the gate, the instantiations and the test shape lists is already a candidate in #5021, so I will evaluate the `index_sequence` spelling there.

On README.ci.md: you are right. "skip with a warning" is wrong since 4c4b7b8864 switched the QK and PV cases to Catch2 `SKIP` [t/t_amx_numerics.cpp:318, :331], and "so CI covers that code" is wrong for the pull-request lane. Will do: one paragraph (under your inline comment at src/tron/CMakeLists.txt:216), the same sentence in the CMake comment, and a caption on the flags block at README.ci.md:563-568 saying it is the `cmake-single-platform.yml` configure line, so the section has no third unnamed home for the flag.
"""),
]

INLINE = [
 dict(id="I1", path="h/tron/kernels/amx_attn_iface.hpp", line=16, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062116",
      point="'are kept' records the decision but not the reason, and the tracking issue appears only in the PR body; his suggestion adds the reason and '(#5021)'.",
      cls="request-for-change", status="confirmed", action="accept, modified", hw=False, dec="D5",
      verdict="grep for 5021 in the header returns 0. Issue #5021 records the reason verbatim ('minimum-change requirement: keep the names, keep the structure'). On PR 5015 you rejected an issue number at this exact line.",
      reply="""
Agreed on the reason. Will do: lines 14-16 become

```
// 128 with kv_mul 4 or 16 (group_heads_ok). The namespace name
// amx_attn_h128g4 and the _128x4 suffix of every kernel name the first
// shape, kv_mul 4, not the served set. The rename is deferred so that the
// kernel generalization stays a small change.
```

That is your reason without the issue number. I keep issue numbers out of source comments on purpose: a comment describes the design as it is, and a tracker link goes stale once the issue closes. #5021 stays linked from the PR body and records the reason. The names appear in 8 files at this head, which is why the rename is its own mechanical PR.
"""),
 dict(id="I2", path="h/tron/kernels/amx_attn_iface.hpp", line=23, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356063056",
      point="The Note and call-site comment fixes are not separable from the gate change; if the PR lands as several commits they should travel with it.",
      cls="request-for-change", status="confirmed", action="accept (moot under squash-merge)", hw=False, dec="D3",
      verdict="At 393dbc1759 the gate already admits 16 [amx_attn_iface.hpp:160-161 at that commit] while the header still says 'one shape ... kv_mul 4' [:13-14, :22] and self_attention.hpp:1529 says 'kv_mul-4 shape'. The fixes land in 5061623a34, one commit later.",
      reply="""
You are right. At 393dbc1759 the gate already admits kv_mul 16 [h/tron/kernels/amx_attn_iface.hpp:160-161 at that commit], while the file header still says "The kernels serve one shape: head size 128 and kv_mul 4" [:13-14], the Note still says "kv_mul 4 whose executor stores activations as bf16" [:22], and the call-site comment still says "head-128 / kv_mul-4 shape" [h/tron/models/self_attention.hpp:1529 at that commit]. The fixes land one commit later, in 5061623a34.

I plan to squash-merge this PR, so main gets one commit with the gate change and its comments together. I will say so in the PR body. If the branch commits are kept instead, I will fold 5061623a34 into 393dbc1759 before landing.
"""),
 dict(id="I3", path="h/tron/kernels/amx_attn_iface.hpp", line=101, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062368",
      point="The overrun warning in Note [Tile stores write 16 rows] is unconditional, but with 16 heads a buffer sized for the real rows is already 8192 bytes, so it should be scoped to group_heads < TILE_ROWS_16.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="",
      verdict="The merge-base text said 'rows 4..15 are written past its end'; the PR replaced the literals with group_heads and lost the implicit condition. Both callers already allocate 16 rows [self_attention.hpp:1787; t_amx_numerics.cpp:267-268].",
      reply="""
You are right. Will do: scope the sentence to `group_heads < TILE_ROWS_16`.

The merge-base text said "rows 4..15 are written past its end" [6198824246, amx_attn_iface.hpp:98-99]. This PR replaced the literals with `group_heads`, and the condition that was implicit in "4" went unstated. With 16 heads the real rows are all 16 rows, 8192 bytes, so the warning does not apply there [amx_attn_iface.hpp:134-136].

Proposed text for lines 100-105:

```
// (one row per query head) hold real data. When group_heads < TILE_ROWS_16,
// passing a buffer sized for the real rows causes a silent overrun: rows
// group_heads..15 are written past its end, nothing reports an error, and
// whatever follows the buffer in memory is corrupted. Those rows of `o` are
// the products of the kernel's zero padding rows of P (output row i of a tile
// multiply comes from row i of the A operand); callers read rows
// 0..group_heads-1 and ignore the rest.
```

Comment only. The declaration already requires 16 x 128 fp32 for every group size [amx_attn_iface.hpp:243-245], and both callers allocate that [h/tron/models/self_attention.hpp:1787; t/t_amx_numerics.cpp:267-268].
"""),
 dict(id="I4", path="h/tron/models/self_attention.hpp", line=1531, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062294",
      point="The Q group is packed before the dense-page check, so a token whose pages are all partial pays a wasted pack (about 660 ns at 16 heads on his Zen 4). Was the order deliberate? If not, move the pack into apply_page_tok after is_dense_amx_page.",
      cls="request-for-response", status="confirmed", action="answer; defer the move to the performance follow-up", hw=True, dec="D2",
      verdict="Order confirmed [self_attention.hpp:1627-1638, :1880-1882]; the test pins it [t_amx_dispatch_dtype.cpp:178-180, :300-301]. The order predates this PR. Your PR 3879 reply (discussion_r3896108314, 2026-08-31) recorded the measurement at 4 heads and the plan 'pack only when the page is full, and open the region at the first pack'. No Granite Rapids number exists for the 16-head pack.",
      reply="""
The order was deliberate, measured at 4 heads. Codex asked the same question on PR #3879 and I answered it with measurements [https://github.com/positron-ai/tron/pull/3879#discussion_r3896108314]. On the Xeon 6962P the scalar 4-head pack cost 63 ns. In qwen-3-4b decode, 21 to 24 % of AMX-on page-range calls ended with zero AMX pages at prompt 2048 and prompt 8192, and 37 % with a 32-token prompt. The upper bound was 0.5 to 0.8 % of one decode step's CPU time, so I kept the simple order. That reply also recorded the first move if a shape shifts the balance: "pack only when the page is full, and open the region at the first pack". 16 heads is that shape, and your 660 ns is about ten times the 4-head cost. I have no Granite Rapids number for the 16-head pack yet.

I will not move the pack in this PR. The pack cost and the pack placement are one problem: your vectorised pack (your note at amx_attn.cpp:132) cuts the cost of a wasted pack, and the lazy pack removes it. I will put both, with the lazy tile region from the #3879 plan, in one kernel-performance follow-up issue, with a Granite Rapids measurement (pack<16> ns per call, and the share of zero-AMX-page calls for Muse Glimmer) so the change lands with its number. The dispatch test's partial-page expectation stays "one pack" until then.
""",
      alt="""
If you choose to move the pack here (D2 alternative), the plan on record is: `apply_page_range` passes a small lambda instead of the packed pointer; the lambda returns `nullptr` when AMX is off, otherwise opens the tile region on the first pack of the call and calls `packed_amx_query` [self_attention.hpp:1549-1554, :1627-1638]; `apply_page_tok` evaluates `is_dense_amx_page` first and calls the lambda only for a dense page [:1880-1891]; the `finally` at :1557-1559 releases the region only when it was opened; the test caller at t/t_llama_unit.cpp:2952 passes a no-op lambda; in t_amx_dispatch_dtype `packs` becomes equal to `dense` and the partial-page section becomes "no pack, no kernel call" [t/t_amx_dispatch_dtype.cpp:178-180, :300-301]. Then rerun the three AMX tests on delphi-3bda with AMX on and with the kill switch.
"""),
 dict(id="I5", path="h/tron/models/self_attention.hpp", line=1755, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061865",
      point="s_pages is default-constructed, so it zero-fills 4 KB per dense page visit at kv_mul 16 right before the QK kernel overwrites every element; use the tensor's uninitialized constructor.",
      cls="request-for-change", status="confirmed", action="accept, modified (one comment line added)", hw=True, dec="D2",
      verdict="tensor<d0,d1>() calls std::construct_at(&data) and each row's default constructor value-initializes [h/tron/tensor/tensor.hpp:40-42, :254-256]; tensor(uninitialized_t) exists at :260. The QK kernel stores all group_heads rows of all four blocks before the epilogue reads s_pages [amx_attn.cpp:220-253]. All existing uses of the tag are weight tensors.",
      reply="""
Agreed. I will take the suggestion.

What I checked at head: the 2-D tensor default constructor calls `std::construct_at(&data)`, and each row's default constructor is `data()`, so the declaration zero-fills kv_mul x 64 x 4 bytes (4096 bytes at kv_mul 16) [h/tron/tensor/tensor.hpp:40-42, :254-256]. The QK kernel then stores all group_heads rows of all four 16-token blocks before the epilogue reads `s_pages` [src/tron/kernels/amx_attn.cpp:220-253]. The line itself predates this PR. At kv_mul 4 the fill was 1024 bytes; the 16-head shape makes it four times larger, so this PR is the right place to fix it.

On thin LTO: the kernel lives in a separate translation unit, so the fill could only disappear through cross-unit inlining. I did not check whether that happens. With the tag the question does not matter.

Note [Uninitialized Weight Tensors] describes the tag for weight tensors [h/common/util.hpp:289]. This is the first use on a stack scratch buffer, so I will add one line saying why it is safe:

```
      // uninitialized: the QK kernel below writes every element before any read.
      tensor<operation_kv_mul, page::page_size> s_pages{uninitialized};
```

Coverage: `t_amx_dispatch_dtype` drives this path with kernel test doubles that also write every row; the real-value coverage is `t_llama_unit` with the option on and the token-identity runs. I will rerun both on delphi-3bda at the final head, with AMX on and under the kill switch. The change alters no values.
"""),
 dict(id="I6", path="h/tron/models/self_attention.hpp", line=1788, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062246",
      point="Each head's PV row is copied into a stack tensor before fma (16 x 512 B per dense page visit at 16 heads); an aligned const_view over the row in amx_o satisfies fma and set, so the copy can go.",
      cls="request-for-change", status="confirmed", action="accept", hw=True, dec="D2",
      verdict="fma takes any expression [h/tron/kernels/expr.hpp:537-542]; the 1-D const_view derives from expr [h/tron/tensor/view.hpp:360-362]; view::set takes any expr [:186-188]; the aligned view uses the aligned chunk load [h/tron/kernels/chunky.hpp:30-33]. amx_o is alignas(64) [self_attention.hpp:1787] and a row is 512 B, so the aligned view is sound. The block predates this PR. The AVX-path scratch at :1958 is an output buffer and stays.",
      reply="""
Agreed. I will replace the stack copy with an aligned view over the row.

The copy is not needed. `fma` takes any `expression` [h/tron/kernels/expr.hpp:537-542]. The 1-D `const_view` derives from `expr` [h/tron/tensor/view.hpp:360-362], and `view::set` takes any `expr` [h/tron/tensor/view.hpp:186-188]. The aligned view reads with the aligned chunk load [h/tron/kernels/chunky.hpp:30-33]. I checked your soundness claim: `amx_o` is `alignas(64)` [h/tron/models/self_attention.hpp:1787] and each row offset is 512 bytes (128 floats), a multiple of the 64-byte chunk, so the aligned view is sound.

Proposed edit at lines 1795-1803:

```
        tron::const_view<float, true, false, tron::seq<operation_head_size>> row{
            amx_o + offset * operation_head_size};
        if (was_valid) {
          auto corr_ = constant<page::page_size>(corr_arr[offset]);
          head_sp.v_star.set(fma(head_sp.v_star, corr_, row));
          head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
        } else {
          head_sp.v_star.set(row);
          head_sp.s_star = sum_arr[offset];
        }
```

The memcpy at :1796 was the only one in the file, so `<cstring>` goes with it. The values read are the same as before, so I expect no numerics change. I will rerun `t_amx_numerics`, `t_amx_dispatch_dtype` and `t_llama_unit` on delphi-3bda with AMX on and under the kill switch. I have no timing for the saved 8 KB per page visit and will not claim a throughput change without one.

The AVX-path `scratch` at line 1958 stays. There it is the output buffer of `page::scaled_v`, not a copy.
"""),
 dict(id="I7", path="src/tron/CMakeLists.txt", line=216, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356060700",
      point="The comment says a CI lane configures with the option on, but no pull-request lane does. Add -DTRON_AMX_DISPATCH=ON to the Nix cmake_args, and name the lane that really sets the option.",
      cls="request-for-change", status="confirmed", action="accept, modified (comment here; Nix flag as its own PR)", hw=False, dec="D1",
      verdict="Reproduced his grep counts (0 and 0) on job 117831672410. The comment was true for three days: f4889f8072 (2026-09-07) added it, 9a5e03687a (2026-09-10) removed the pull_request trigger. His 'publish-deb dispatch' detail is slightly off: a publish-deb run on main skips its test job (the gate at publish-deb.yml:64-67 needs a tag push or a feature-branch publish); the last two runs show test: skipped.",
      reply="""
You are right on every fact. The required GCP Nix build (`nix/cmake-tron-test-build.nix:79-101`) never sets `TRON_AMX_DISPATCH`, so on this head both AMX test binaries run their `SUCCEED` stubs. I reproduced your counts on Build Tron job 117831672410 (0 and 0; both test objects built in the OFF arm). The comment was true when I wrote it on 2026-09-07 [f4889f8072]. The cutover to GCP Nix removed the `pull_request` trigger from `cmake-single-platform.yml` three days later [9a5e03687a], and I did not update the sentence.

Will do, in this PR: rewrite the comment so it names the lanes that exist at this head, and fix the same drifted sentence in `README.ci.md:581-588`.

```
# fast-path call sites. No pull-request lane sets the option at this head:
# the required GCP Nix build (nix/cmake-tron-test-build.nix) leaves it OFF,
# so t_amx_numerics and t_amx_dispatch_dtype run their SUCCEED stubs there.
# The option is ON only in the deb preset and in the legacy CMake lane
# (.github/workflows/cmake-single-platform.yml, reached by workflow_dispatch
# or by the publish-deb test gate on a tag push); there the kernel cases
# execute only when the job lands on a Granite Rapids runner and are
# reported as skipped elsewhere. ctest and Slice still report a pass when
# those cases skip, because the ungated cases run.
# TODO(jhan): set the option in the required lane and make one real-AMX
# test execution a required check
# (https://github.com/positron-ai/tron/issues/3997).
```

One detail: a `publish-deb` dispatch on `main` does not reach the test job. That job runs only on a tag push or a feature-branch publish [publish-deb.yml:64-70]. In the last two `publish-deb` runs on main (40614582020, 40988310530) the test job was skipped by that gate.

On `-DTRON_AMX_DISPATCH=ON` in the Nix `cmake_args`: agreed that it is the right fix, and agreed on the mechanics. The pack case is scalar [amx_attn.cpp:128-140], the dispatch case uses CPU fakes, the kernel cases `SKIP`, and Catch2 returns 4 only when every case is skipped [catch_session.cpp:351-353]. I will open it as its own one-line PR under #3997 rather than fold it into this one. Reason: the required lane's test job can land on a Granite Rapids host (this head's Test host job ran on delphi-3af6, a Xeon 6962P), and with the option ON every bf16 head-128 attention in the model tests of that lane goes through the AMX kernels, not only the two AMX test binaries. That change in what the required lane exercises should be signed off by the CI owner on its own. If that PR merges first, I will rebase this one so its GCP Nix run is the in-repo evidence you asked for in the review body.
"""),
 dict(id="I8", path="src/tron/CMakeLists.txt", line=216, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061170",
      point="README.ci.md:581-588 still says 'skip with a warning' and 'so CI covers that code'; mirror the new wording there and name cmake-single-platform.yml as the only lane that enables the option.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="",
      verdict="README.ci.md is untouched on the branch. One precision: the publish-deb package job also gets the option ON through the deb preset (make deb runs cmake --preset deb; CMakePresets.json:64, :68 set ENABLE_TESTS OFF and TRON_AMX_DISPATCH ON), so 'only lane' must be worded as 'only workflow that passes the flag and builds the tests with it'.",
      reply="""
You are right. Will do: update README.ci.md:581-588 in this PR so it matches the CMake comment and the test code.

What is stale:

- The tests now call Catch2 `SKIP(...)`, not `WARN(...); return;` [t/t_amx_numerics.cpp:318, :331]. Catch2 counts a `SKIP` as a separate "skipped" result. So "reported as skipped" is the accurate wording.
- "so CI covers that code" overstates it. Only `cmake-single-platform.yml` passes `-DTRON_AMX_DISPATCH=ON` on the configure line [.github/workflows/cmake-single-platform.yml:355]. That workflow runs on manual dispatch or through the `workflow_call` from `publish-deb.yml` [publish-deb.yml:68]. The default `gcp-nix.yml` lane never sets the option.

One precision on "the only lane that enables the option": the package job of `publish-deb.yml` also gets the option ON, through the `deb` preset. `make deb` [publish-deb.yml:113] runs `cmake --preset deb` [GNUmakefile:510], and that preset sets `TRON_AMX_DISPATCH` ON with `ENABLE_TESTS` OFF [CMakePresets.json:64, :68]. So I will word it as "the only workflow that passes the flag and the only one that builds and runs the tests with it ON".

Proposed replacement paragraph:

```
`TRON_AMX_DISPATCH=ON` compiles the AMX software-attention kernels and their
dispatch (see Note [AMX attention dispatch] in
`h/tron/kernels/amx_attn_iface.hpp`). `cmake-single-platform.yml` (manual
dispatch, or the `workflow_call` from `publish-deb.yml` on a tag push) is the
only workflow that passes `-DTRON_AMX_DISPATCH=ON` and the only one that builds
and runs the tests with the option ON; the default `gcp-nix.yml` lane builds
with it OFF, so there `t_amx_numerics` and `t_amx_dispatch_dtype` hold only
their placeholder case. The `deb` preset also sets the option ON, so `make deb`
(the package job of `publish-deb.yml`) and the released package carry the
kernels and select them at run time only on hosts with AMX; that preset builds
no tests. Every other preset leaves it at its default OFF. The kernel cases of
`t_amx_numerics` execute AMX only when the test job lands on a Granite Rapids
runner; elsewhere Catch2 reports them as skipped, and ctest and Slice still
report a pass because the ungated cases run. Making one real-AMX test execution
a required check is tracked in https://github.com/positron-ai/tron/issues/3997.
```

The fenced flags block above it [README.ci.md:563-568] stays and gets one caption line saying it is the `cmake-single-platform.yml` configure command.
"""),
 dict(id="I9", path="src/tron/kernels/amx_attn.cpp", line=132, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061055",
      point="The 16-head pack is a scalar triple loop (512 vpextrw at -O3; about 660 ns per call on his Zen 4 against 71 ns for 4 heads). Not a blocker; a vectorised pack is a contained follow-up.",
      cls="request-for-change", status="partly confirmed", action="defer to a new kernel-performance follow-up issue", hw=True, dec="D2",
      verdict="Scalar loop confirmed [amx_attn.cpp:126-139]; -O3 confirmed [src/tron/CMakeLists.txt:290]. His opcode census and timings are Zen 4 results and are not reproducible here. One refinement: the pack runs once per token per apply_page_range call, which is once per KV section [self_attention.hpp:1169-1172], so 'once per KV head' is a lower bound. #5021 excludes kernel performance, so a new issue is the right tracker.",
      reply="""
Agreed. I will keep the scalar pack in this PR and track the vectorised version on a kernel-performance follow-up issue, linked here once filed. #5021 does not fit, since it excludes performance changes.

What I checked at 4c4b7b8864:

- The loop is a plain scalar copy, two bf16 values per (step, dim pair, head) [src/tron/kernels/amx_attn.cpp:130-137]. The tron target compiles it at `-O3` [src/tron/CMakeLists.txt:290].
- The pack runs once per token per `apply_page_range` call. That is one call per KV section (`run_sections`, h/tron/models/self_attention.hpp:1169), so at least once per KV head per layer, and more when a head is split into several sections [self_attention.hpp:879, :1172]. "Once per KV head" is the lower bound.
- I have not reproduced the `vpextrw` census yet. I will run it on delphi-3bda with the PR's clang 19.1.7 build as the follow-up's baseline, and take the per-call timing on Granite Rapids rather than Zen 4.

Your layout sketch matches the contract [h/tron/kernels/amx_attn_iface.hpp:184-195]. The QK kernel already has the 4-stage 16x16 dword transpose: stages 1-2 at [src/tron/kernels/amx_attn.cpp:218-240], stages 3-4 in `store_transposed_rows` [amx_attn.cpp:150-170]. The follow-up can reuse it. `check_q_pack<4>` and `<16>` test the layout on any host [t/t_amx_numerics.cpp:128-156], so a vectorised pack is covered by the existing test.
"""),
 dict(id="I10", path="src/tron/kernels/amx_attn.cpp", line=156, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356060885",
      point="Lanes 1..3 of the transposing store are pure AVX-512 but only check_qk<16> behind the SKIP guard reaches them, so they have never run in CI. Declare a host-testable transpose_scores<group_heads>, build it without -mamx, add an ungated case against a scalar transpose, and say in the CMake comment that ctest and Slice still pass when the kernel cases skip.",
      cls="request-for-change", status="confirmed", action="accept, modified (header-inline template instead of a separate TU)", hw=False, dec="",
      verdict="The lanes have run in no CI lane at all: the kernel case skips in the option-on lane and the PR lane compiles the file to its stub. A standalone build of stages 1-4 without -mamx on an AVX-512 host gave 0 mismatches over 1024 cells for 4 and for 16 heads and no tile instruction in the binary. ctest registers each case through catch_discover_tests with SKIP_RETURN_CODE 4 by default, so ctest lists the two kernel cases as skipped and the run passes.",
      reply="""
You are right. The three new lanes have run in no CI lane at all. The kernel cases skip in the option-on lane, and the pull-request lane (GCP Nix) does not set `TRON_AMX_DISPATCH` [nix/cmake-tron-test-build.nix:87-93], so there the whole file compiles to the stub case [t/t_amx_numerics.cpp:339-344].

Will do, with one change to the placement:

- Move stages 1-4 into `transpose_scores<group_heads>(const float* s_transposed, float* s, size_t s_stride_floats)`, as an inline template in a new header `h/tron/kernels/amx_attn_transpose.hpp` (AVX-512 intrinsics only, no AMX, the same convention as `dotter.hpp`). `amx_attn.cpp` includes it and calls it after the four tile stores. The interface header stays intrinsics-free and only points to the new header.
- Keep the definition in the header rather than in a separate translation unit, so the compiler can inline it into `qk_rowmajor_128x4<4>`. The PR body states that the 4-head kernels emit the same instructions as on main, and #5021 relies on that compare. After the move I will rerun the object compare (linked runtron, clang 19.1.7, the `preservation2.txt` method). If the `<4>` listing changes, I will mark the function `[[gnu::always_inline]]`.
- Add `"AMX QK transpose writes the group_heads score rows"`, tag `[q_pack]`, sections for 4 and 16 heads. It fills a 64x16 score buffer with distinct values, calls the function, and compares against the scalar transpose `s[q][t] == s_transposed[t * 16 + q]`. Rows `group_heads..15` and a guard column past the stride keep a sentinel. It goes above `#ifdef TRON_AMX_DISPATCH`, so it also runs on the pull-request lane where the option is off. The test TU already gets the AVX-512 flags from the `tron` target [src/tron/CMakeLists.txt:269].
- Local check before pushing: I built stages 1-4 as a standalone program without `-mamx` on an AMD host with AVX-512 and compared with a scalar transpose. Result: 0 mismatches over 1024 cells for 4 heads and for 16 heads, and no tile instruction in the binary.

On the comment text: Slice runs the whole binary and reports it as passed (Catch2 exits 0 because the two host cases pass) [bin/slice:1208-1210]. ctest registers each case through `catch_discover_tests`, which sets `SKIP_RETURN_CODE 4`, so ctest lists the two kernel cases as skipped and the run passes. I will write that in the CMake comment and in README.ci.md:586-588.
"""),
 dict(id="I11", path="src/tron/kernels/amx_attn.cpp", line=156, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062875",
      point="The lane-0 extraction and the WARN-to-SKIP guards are separable from the templating; if the PR is reshaped into commits, those two could go first as pure refactors.",
      cls="request-for-change", status="confirmed", action="answer (moot under squash-merge)", hw=False, dec="D3",
      verdict="Lane 0 uses selectors (0x88, 0x88) and stores at the same addresses as the base loop [amx_attn.cpp:159-167]. His 204-vs-204 compare matches the 4c4b7b8864 commit message. The repository allows squash, merge and rebase merges.",
      reply="""
Your lane-0 identity matches my own compare. Lane 0 uses the selectors (0x88, 0x88) and stores at `s + r * 16 + k * s_stride_floats`, the same addresses as the base loop [src/tron/kernels/amx_attn.cpp:159-167]. My clang 19.1.7 -O3 object compare against the merge base recorded the same 204 instructions for the 4-head QK kernel (commit message of 4c4b7b8864).

I plan to squash-merge this PR, so the three-step history would not survive on main. If the branch commits are kept instead, I will do the split you describe, with step 2 (the WARN-to-SKIP guards) also carrying the CMake comment and the README fix that belong to the same reporting change. One note on step 2 either way: it is a test-reporting change rather than a refactor. On a host without AMX the Catch2 summary then says 2 skipped instead of 4 passed; the exit code stays 0, because the gate and packer cases still pass [t/t_amx_numerics.cpp:90, :306].
"""),
 dict(id="I12", path="src/tron/kernels/amx_attn.cpp", line=164, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062057",
      point="Each lane recomputes stage 3, so the 16-head store emits 48 shuffle-class instructions where 32 would do; hoist stage 3 out of the lane loop, as a follow-up.",
      cls="request-for-change", status="confirmed", action="defer to the kernel-performance follow-up issue", hw=True, dec="D2",
      verdict="Source count confirmed: 3 shuffles per k, 4 k, 4 lanes = 48 [amx_attn.cpp:163-168, :244-253]; pair_sel depends on bit 0 and quad_sel on bit 1 of the lane [:159, :161]. His 40 vshuff64x2 matches your earlier object compare (glimmer-20261016 results page: 0 / 40 lane shuffles for 4 / 16 heads), made before head. A standalone probe of the hoisted form writes identical rows for 4 and 16 heads; g++ 11 already merges the duplicate shuffles, so the saving is specific to clang.",
      reply="""
Agreed. I will track the hoist on the kernel-performance follow-up issue rather than change this PR.

Your count matches the source. The helper emits 3 shuffles per k, 4 k per lane, 4 lanes at 16 heads, so 48 per 16-token block [src/tron/kernels/amx_attn.cpp:163-168, :244-253]. `pair_sel` depends only on bit 0 of the lane and `quad_sel` only on bit 1 [:159, :161]. So stage 3 has 16 distinct results per block and 32 is the floor. Your 40 vshuff64x2 also matches my earlier object compare (clang 19.1.7, qk_rowmajor_128x4: 0 / 40 lane shuffles for 4 / 16 heads, glimmer-20261016). That compare was made before head 4c4b7b8864; at this head I re-compared only `qk<4>`.

I checked the hoisted form in a standalone probe. It writes the same `s` rows as the head code for 4 and 16 heads. With an `if constexpr (lanes > 1)` guard the 4-head path keeps its 3-shuffle sequence at the intrinsic level; whether clang still emits identical object code for `<4>` is for the follow-up's object compare. One note: g++ 11.4 at -O3 already merges the duplicate stage-3 shuffles (32 per block for both forms), so the saving is specific to clang, which is what we ship.

Why not here: the 16-head instruction stream at this head is the reference for the object compare in #5021, which also lists kernel performance as out of scope. The hoist changes that stream, so it needs its own object compare, a Granite Rapids numerics run and a timing. No timing exists for the 16 saved shuffles per block; the follow-up's per-kernel microbenchmark on delphi-3bda would give it.
"""),
 dict(id="I13", path="src/tron/kernels/amx_attn.cpp", line=179, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062436",
      point="The qwen3-4b / tp2 / prompt 1024 row runs no PR code yet shows +0.56 TPS beyond its 0.33 band, so the band understates noise; add repetitions until untouched rows fit, or say the rule gates losses only.",
      cls="request-for-change", status="partly confirmed", action="accept, modified (PR body edit, no new runs)", hw=False, dec="",
      verdict="No PR code on that path: the exit reports show the AMX kernel scored 0 key tokens in both arms [glimext-20261018/exit-reports.txt, q4b-tp2-8u-p1024-fpga blocks]. But the band does measure repeat spread: head minus base is +0.72, +0.31, +0.74, +0.47 in the four repetitions with alternating arm order [rt-results.txt lines 87, 111, 519, 543, 951, 975, 1383, 1407], so this is a systematic between-binary offset, cause unknown. More repetitions would confirm it, not shrink it. The PR body already states the loss-only rule at line 120 and contradicts it at line 78.",
      reply="""
Agreed that the row needs an explanation. I will change the PR body rather than add repetitions.

That row runs no PR code. The attention exit report (`TRON_ATTN_STATS=1`, which counts the key tokens each path scored) shows the AMX kernel scored 0 key tokens in both arms, in decode and in prompt [`glimext-20261018/exit-reports.txt`, `q4b-tp2-8u-p1024-fpga` blocks]. The FPGA scores the ready pages and the AVX loop scores the pending partial page. This PR changes neither path.

The band is not too narrow for repeat spread. The within-arm sd is 0.16 and 0.15 tokens/s per user. Head minus base is positive in all four repetitions, +0.72, +0.31, +0.74 and +0.47 tokens/s per user, with the arm order alternating [`glimext-20261018/rt-results.txt`]. So this is a systematic offset between the two binaries on a path where no PR code runs. I do not know its cause. The band is built from repeat spread and does not cover a binary-level offset. That is why the rule gates losses only, and more repetitions would confirm the offset rather than shrink it. An A/A pair (two builds of the same commit on that cell) is the measurement that would size it; I would rather not spend delphi-3bda time on that for this PR.

Will do, in the Performance section:

- Replace "A change counts when its absolute size exceeds the band." with:

```
The check gates losses only: a configuration fails when its decode loss or its
prefill increase exceeds the band. A gain beyond the band is reported, but it is
claimed as an effect of this PR only where PR code runs on that path.
```

- Relabel the row's cell as `+0.56 / 0.33, beyond, no PR code on path`.
- Add under the merge-base table:

```
The qwen3-4b / tp2 / 1024 row runs no PR code: the AMX kernel scored 0 key
tokens in both arms (exit-reports.txt). Head minus base is positive in all four
repetitions, so the +0.56 TPS is a between-binary offset not caused by code on
that path, cause unknown. The band is built from within-arm repeat spread and
does not cover such an offset. The Glimmer decode gains (2.61 to 5.16 TPS) are
4 to 9 times that offset.
```
"""),
 dict(id="I14", path="src/tron/kernels/amx_attn.cpp", line=213, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061630",
      point="The first static_assert restates the requires clause and its message claims a limitation the lane ladder does not have; replace it with the real upper bound and keep the % 4 assert.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="",
      verdict="The assert can never fire for a size group_heads_ok admits. A constexpr probe over 4, 8, 12, 16, 20, 32 shows his bound passes exactly the sizes the ladder serves and rejects the two it would under-store. The assert came from 7e7f52d761 as a tripwire; the ladder in the same commit removed the failure mode it guarded.",
      reply="""
Agreed. Will do: replace the first `static_assert` with the upper bound and keep the `% 4` assert.

```
  static_assert(group_heads % ROWS_PER_LANE_4 == 0, "a stored lane is 4 rows");
  static_assert(group_heads / ROWS_PER_LANE_4 <= TILE_ROWS_16 / ROWS_PER_LANE_4,
      "at most 4 stored lanes of 4 rows: the ladder below stores lanes 0..3");
```

History, for the record. The first assert was the tripwire Wade asked for on #5015, when the store still keyed on `group_heads == 16` and a third size would have left rows 4..group_heads-1 unwritten. The lane ladder from the same round removed that failure mode for 8 and 12 [amx_attn.cpp:244-253]. After that the assert only repeated `group_heads_ok`, and its message was wrong. Dropping the 8/12 tripwire is intentional: the ladder now serves those sizes.

The new bound catches the case the ladder cannot serve: 20 or 32 heads would store 16 rows and stop. I checked the arithmetic with a small constexpr probe over 4, 8, 12, 16, 20 and 32. The bound passes the first four and rejects the last two.

No tripwire comment. `group_heads_ok` [amx_attn_iface.hpp:146] stays the single list of served sizes. Whether 8 joins that list is answered under your top-level "next decision".
"""),
 dict(id="I15", path="src/tron/kernels/amx_attn.cpp", line=269, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062499",
      point="'keeps unused rows zero' reads as a design reason nobody depends on; the property that matters is per-instantiation thread_local storage, which the Note relies on.",
      cls="request-for-change", status="confirmed", action="accept, modified (split at the semicolon)", hw=False, dec="",
      verdict="Every reader of o is bounded by the group size [self_attention.hpp:1792-1797; t_amx_numerics.cpp:275, :290]; P is the A operand so output row i depends on P row i only [amx_attn.cpp:287-299]. Without per-instantiation storage a 16-head call would leave rows 4..15 nonzero for the next 4-head call.",
      reply="""
You are right. Will do: take your wording, split at the semicolon.

I checked every reader of `o`. The call site reads rows 0..kv_mul-1 only [h/tron/models/self_attention.hpp:1792-1797]. The numerics test reads rows 0..group_heads-1 only [t/t_amx_numerics.cpp:275, :290]. The other two mentions are an unevaluated `requires` probe [t/t_llama_unit.cpp:104] and a dispatch-test stub that writes `o` and reads nothing [t/t_amx_dispatch_dtype.cpp:282-289]. P is the A operand of each `_tile_dpbf16ps`, so output row i depends on P row i only [src/tron/kernels/amx_attn.cpp:287-299]. So the zero padding rows are a description, not a dependency.

The per-instantiation storage is the fact worth keeping. Without it a 16-head call would leave rows 4..15 of a shared P nonzero, and the Note's sentence about rows group_heads..15 of `o` [h/tron/kernels/amx_attn_iface.hpp:103-105] would be false.

Proposed text for line 269:

```
  // A function template's thread_local exists once per instantiation, so a
  // 4-head call never sees a 16-head call's rows. Note [Tile stores write 16
  // rows] relies on that for its zero-row claim.
```
"""),
 dict(id="I16", path="t/t_amx_dispatch_dtype.cpp", line=51, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062738",
      point="The PR body's TRON_AMX_DISPATCH=OFF row says 'Insufficient data' and never mentions the probe guard move; cite jobs 117831672410 and 117835534166 and mention the guard.",
      cls="request-for-change", status="confirmed", action="accept (PR body edit)", hw=False, dec="",
      verdict="Both jobs are real, successful, on head 4c4b7b8864 (run 39179018918). The pre-guard Nix build at 7e7f52d761 (job 117801889954) emitted the -Wunneeded-internal-declaration warning on 'probe'; the head build does not. In the OFF build each binary holds only its SUCCEED placeholder, so the row must say so for both.",
      reply="""
You are right. Both parts of the body are stale. I will edit the PR description, not the code.

The OFF row will cite the Nix lane at the head commit 4c4b7b8864: run 39179018918, Build Tron job 117831672410 (success) and Test host job 117835534166 (success). That lane passes no `-DTRON_AMX_DISPATCH` flag, and the option defaults OFF [nix/cmake-tron-test-build.nix:79-101, CMakeLists.txt:46]. The Test host log shows `t_amx_numerics` and `t_amx_dispatch_dtype` as passed. In the OFF build each file holds only the placeholder case that calls `SUCCEED`, so "passed" there means each binary builds and runs, not that the AMX checks ran [t/t_amx_numerics.cpp:341-347; t/t_amx_dispatch_dtype.cpp:321-325].

I will also add the guard move to the body. The fakes and the `probe` object now sit under `#ifdef TRON_AMX_DISPATCH` [t/t_amx_dispatch_dtype.cpp:51]. The Nix build at 7e7f52d761 (Build Tron job 117801889954) emitted `t_amx_dispatch_dtype.cpp:68:11: warning: variable 'probe' is not needed and will not be emitted [-Wunneeded-internal-declaration]`. The head build emits no such warning.

Proposed row:

```
| `TRON_AMX_DISPATCH=OFF` (option absent, Nix lane default) | Nix lane at `4c4b7b8864`, run 39179018918: Build Tron job 117831672410, Test host job 117835534166 | Build: success, no `probe` warning. Test host: `t_amx_numerics` passed, `t_amx_dispatch_dtype` passed. In this build each binary holds only its placeholder case; the AMX checks are compiled out. |
```
"""),
 dict(id="I17", path="t/t_amx_dispatch_dtype.cpp", line=143, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356060971",
      point="Every section uses one KV head, so the pack base is only ever evaluated with kv_head 0 and the 'starts at the wrong head' failure cannot be observed; add a 32-head / 2-KV-head section called with kv_head 1, or reword.",
      cls="request-for-change", status="confirmed", action="accept (new section and reword)", hw=False, dec="",
      verdict="apply_page_range is called with kv_head 0 only [t_amx_dispatch_dtype.cpp:199]; the pack base term kv_head * operation_kv_mul * head_size [self_attention.hpp:1695-1696] is always 0. Your own PR 5015 annotation said the same. A drafted version of the section exists but was not compiled here (no clang 19 or TBB headers on this host).",
      reply="""
You are right. The fixture calls `apply_page_range` with `kv_head` 0 only [t/t_amx_dispatch_dtype.cpp:199], so the `kv_head * operation_kv_mul * head_size` term of the pack base [h/tron/models/self_attention.hpp:1696] is always 0 here. The comment overstated what the per-head offsets check.

Will do: add the section you propose. It is Glimmer's own shape (32 query heads, 2 KV heads, 128 dimensions per head), and it will be the only check of that base term that runs on a host without AMX. Fixture changes: `n_kv_heads` becomes a template parameter, `exercise_page` takes a `kv_head` argument, the K/V zeroing loop covers every KV head, and the value check compares `probe.q[i]` with `expected[kv_head * group_heads * head_size + i]` over `group_heads * head_size` values. The current loop over `expected.size()` would read past `probe.q`, which holds 16 x 128 values. The softmax-state check from your comment at line 209 indexes the scratchpad with `kv_head * group_heads + offset` for the same reason. I will also reword the comment:

```
    // Per-head offsets make a pack that reads the group from the wrong start
    // or with the wrong stride fail the value check below. The KV-head-1
    // section is the one where the right start is not q.data.
```

One caveat: the new section builds a 32-head model (dim 4096) through the same fixture. If its construction time turns out too long in the test run, I will fall back to your reword alone and say so.
"""),
 dict(id="I18", path="t/t_amx_dispatch_dtype.cpp", line=143, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356063138",
      point="His hunk-by-hunk slices kept the final diff's offsets, so none was a patch against its parent and he never proved any step builds alone.",
      cls="informational", status="confirmed", action="answer only", hw=False, dec="D3",
      verdict="His arithmetic is right: +7 and +2 from the two earlier hunks give the +9 offset. Nothing to change; the answer depends on D3.",
      reply="""
Agreed, the arithmetic is right. The `+140` start of the `-131,7` hunk is the merge-base line 131 plus the +7 and +2 lines that the two earlier hunks of this file add. A hunk-by-hunk slice of the final diff is therefore not a patch against the merge base, and it proves nothing about whether a step builds.

I plan to squash-merge, so no intermediate step needs to build on its own. If I do take up the refactor-first ordering you proposed at `amx_attn.cpp:156`, I will make each step a git commit and run one build with `TRON_AMX_DISPATCH=ON` at each commit before pushing. That build does not need an AMX host.
"""),
 dict(id="I19", path="t/t_amx_dispatch_dtype.cpp", line=209, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356060801",
      point="The 16-head section drives the real epilogue but never reads v_star, s_star, m_star or validity, so an epilogue that merged only 4 of 16 heads would pass; loop over the heads and REQUIRE the exact expected state.",
      cls="request-for-change", status="confirmed", action="accept, modified (in exercise_page, every section)", hw=False, dec="",
      verdict="His expected values match the production epilogue: zero scores give m_page 0, every weight exp(0) = 1, sum = token count; the PV fake zero-fills, so v_star = 0, s_star = token count, m_star = 0 [self_attention.hpp:1766-1806]; the kv head is marked valid [:1646-1661]. token_scratchpad_ref_at<geometry>(0, 0)[head] exists [:381-386, :356-359]. The AVX arm with zero K and V should give the same state; that is a reading, confirmed only by the run.",
      reply="""
You are right. Nothing after `apply_page_range` reads the running-softmax state, so the epilogue's per-head merge is unchecked here. Will do: add the loop you describe, in `exercise_page` after the stats block, so it runs in every section (the 4-head rounds, the 16-head section and the new KV-head-1 section), not only the 16-head one.

Your expected values match the production epilogue. The QK fake writes zero scores, so the scale step leaves 0, `m_page` is 0, every weight is exp(0) = 1 and the sum is the page's token count (64 on a full page, 63 on the partial-page section) [h/tron/models/self_attention.hpp:1766-1785]. The PV fake writes zeros, so `v_star` is set to zeros, `s_star` to the token count and `m_star` to 0 [self_attention.hpp:1790-1806]. `was_valid` is false in every round because the test clears validity before each call [t/t_amx_dispatch_dtype.cpp:155, :189]. The kv head is then marked valid, since the visit returned relevant tokens and `m_star` is not -inf [self_attention.hpp:1646-1661]. The AVX dotter arm sees the same zero K and V, so it should leave the same state; if the run shows otherwise I will restrict the check to the dense sections and report the values.

Proposed block (untested until the build; the index carries `kv_head` for the KV-head-1 section):

```
    // The running-softmax state of every head in the group after the visit.
    // K and V are zero, so each score is 0, each exp is 1, s* is the token
    // count, m* is 0 and v* is 0 on either path. An epilogue that merged
    // fewer than group_heads heads leaves the other heads at their old values.
    {
      auto sp = state.self_attn_state.template token_scratchpad_ref_at<geometry>(0, 0);
      REQUIRE(sp.is_valid_for(kv_head));
      for (size_t offset = 0; offset < group_heads; ++offset) {
        CAPTURE(offset);
        auto head_sp = sp[kv_head * group_heads + offset];
        REQUIRE(head_sp.s_star == static_cast<float>(n_tokens));
        REQUIRE(head_sp.m_star == 0.f);
        for (size_t i = 0; i < head_size; ++i) {
          CAPTURE(i);
          REQUIRE(static_cast<float>(head_sp.v_star[i]) == 0.f);
        }
      }
    }
```

Of the four checks, `s_star == n_tokens` is the one that discriminates a skipped head in every case; the zero checks would also pass on zero-initialised memory. I will rerun `t_amx_dispatch_dtype` with `TRON_AMX_DISPATCH=ON` and refresh the assertion count in the Verification table once, after all test edits of this round.
"""),
 dict(id="I20", path="t/t_amx_dispatch_dtype.cpp", line=272, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062590",
      point="Use the two new page-view aliases at the three test sites that still spell out const_native_k_view<...> and v_vnni_view<const bf16, ...>.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="",
      verdict="The three sites are exactly as he lists. The aliases are plain using-declarations of those types [amx_attn_iface.hpp:140-141]. One more site his grep misses: t/t_llama_unit.cpp:482-485 spells the same types with PAGE_TOKENS_64 namespace-qualified, feeding STATIC_REQUIREs that the kernel accepts exactly those types. The PR 5015 nit that introduced the aliases explicitly scoped the tests out.",
      reply="""
Agreed. Will do: replace the three spelled-out view types with the aliases, so the tests name the layouts the way the kernel does.

The aliases are plain `using` declarations of those exact types [h/tron/kernels/amx_attn_iface.hpp:140-141], so no type changes. The kernel side already uses them in the declarations, the definitions and the explicit instantiations. The nit on #5015 that introduced the aliases said "The test spellings can stay as they are", so I left the tests out then. Your request extends that scope to the tests, and I agree it reads better.

The edits:

```
// t/t_amx_dispatch_dtype.cpp:272
void qk_rowmajor_128x4(const_k_row_major_plane_view,
// t/t_amx_dispatch_dtype.cpp:282
void weights_times_v_128x4(const_v_vnni_plane_view,
// t/t_amx_numerics.cpp:183
    tron::amx_attn_h128g4::const_k_row_major_plane_view{in->k}, q_packed,
```

The fakes sit inside `namespace tron::amx_attn_h128g4`, so the unqualified names resolve there. The numerics call qualifies every name, so it gets the full prefix. I will also shorten the comment above that call, since the alias name now says "the K plane the kernel takes" [t/t_amx_numerics.cpp:181-182].

One more site your grep misses: `k_plane_t` and `v_plane_t` in t/t_llama_unit.cpp:482-485 spell the same two types, with `PAGE_TOKENS_64` namespace-qualified. I plan to leave those. They feed the STATIC_REQUIRE checks that the kernel accepts exactly those layout types and rejects bare pointers [t/t_llama_unit.cpp:490-499]. A spelling independent of the header alias is what that check compares against, and `v_plane_mut_t` next to them has no header alias anyway. Say so if you would rather they go through the aliases too.
"""),
 dict(id="I21", path="t/t_amx_dispatch_dtype.cpp", line=305, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062178",
      point="Only the full-page section runs the 16-head instantiation; add 16-head variants of the partial-page and kill-switch sections.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="D2",
      verdict="Only line 305 passes GROUP_HEADS_16. Both new sections cover more than the predicate: no section today sends a 16-head page through the AVX dotter loop in apply_page_tok. Buffers already fit (probe.q holds 16 x 128). The partial-page expectation stays 'one pack' while the pack order is unchanged (D2).",
      reply="""
Agreed. Will do: add both sections after the 16-head full-page one.

```
  SECTION("host_bf16, 16 heads, partial page: one pack with group_heads 16, no "
          "kernel call") {
    exercise_page<host_bf16, amx_attn_h128g4::GROUP_HEADS_16>(page_size - 1);
  }
  SECTION("host_bf16, 16 heads, full page, available() false: no pack, no kernel "
          "call, one AVX visit that scored the whole page") {
    exercise_page<host_bf16, amx_attn_h128g4::GROUP_HEADS_16>(
        page_size, /*repeat=*/false, /*amx_available=*/false);
  }
```

Both sections cover more than the predicate. Today the only 16-head section is dense, so its page goes to the QK/PV fakes [t/t_amx_dispatch_dtype.cpp:305; h/tron/models/self_attention.hpp:1879-1890]. No section sends a 16-head / 1-KV-head page through the AVX dotter loop in `apply_page_tok`. These two would be the first, and both assert one AVX visit of the whole page [t/t_amx_dispatch_dtype.cpp:218-227].

The partial-page arm also observes the pack. The Q pack runs before the dense predicate, so on a 63-token page the section checks a 16 x 128 pack and `pack_group_heads == 16` [self_attention.hpp:1530-1533; t/t_amx_dispatch_dtype.cpp:207, :239-243]. That is the Muse Glimmer fallback path. The kill-switch arm (available() false, the production `TRON_AMX_DISABLE=1` case) asserts only group-size-independent counters, but runs the 16-head dotter path.

The file header list will name both arms. I will post the new assertion count from a `TRON_AMX_DISPATCH=ON` build and refresh the 3,694 / 1 rows in the Verification table once, after all test edits.
"""),
 dict(id="I22", path="t/t_amx_numerics.cpp", line=37, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356062670",
      point="The trailing comment sits on the GROUP_HEADS_16 line as if it described 16 only; it describes both.",
      cls="request-for-change", status="confirmed", action="accept, modified (trailing comment on both lines)", hw=False, dec="",
      verdict="The current placement was a deliberate edit: 393dbc1759 had an own-line heading above both using-lines; a comment-cleanup pass on PR 5015 objected that the heading also sat above HEAD_SIZE_128, PAGE_TOKENS_64 and TILE_ROWS_16, and a6b93f1f71 moved it onto the 16 line. Isaac's own-line form would reintroduce that.",
      reply="""
Agreed, the trailing comment on the 16 line reads as if it described 16 only. Both constants are the query-heads-per-KV-head count [h/tron/kernels/amx_attn_iface.hpp:133-134].

Some history, so the fix does not undo an earlier cleanup. The first commit on this branch (393dbc1759) had the definition on its own line above both using-lines. A comment-cleanup pass on #5015 objected to that form: with no blank line below, the heading also sat above `HEAD_SIZE_128`, `PAGE_TOKENS_64` and `TILE_ROWS_16`, which are not group sizes. Commit a6b93f1f71 moved the definition onto the `GROUP_HEADS_16` line in response, which created the reading you point out.

Will do: put the trailing comment on both lines instead. Each line then describes itself, and no heading spans the three other names.

```
using tron::amx_attn_h128g4::GROUP_HEADS_16;  // query heads per KV head
using tron::amx_attn_h128g4::GROUP_HEADS_4;   // query heads per KV head
```
"""),
 dict(id="I23", path="t/t_amx_numerics.cpp", line=118, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061465",
      point="The comment's reason ('no kernel above 16') does not explain why 8 is refused; the gate is group_heads_ok, which admits only 4 and 16.",
      cls="request-for-change", status="confirmed", action="accept", hw=False, dec="D4",
      verdict="The 'above 16' sentence was written for the kv_mul 32 row and landed above the 8 row as well (4c4b7b8864). His suggestion replaces line 118 only, giving a three-line comment at 117-119. If D4's alternative is chosen, this comment changes again.",
      reply="""
You are right. Will do: take the suggestion as written.

The "above 16" sentence was written for the kv_mul 32 row (kv_mul = query heads per KV head). I added that row and the sentence together in the last commit. The sentence also sits above the kv_mul 8 row, where it explains nothing. The gate is `group_heads_ok`, which admits only 4 and 16 [h/tron/kernels/amx_attn_iface.hpp:146-148], and the explicit instantiations match that set [src/tron/kernels/amx_attn.cpp:316-326].

New text at t/t_amx_numerics.cpp:117-119:

```
  // llama-70b and qwen-3-32b have 64 query heads sharing 8 KV heads. No
  // kernel is instantiated for any group size other than 4 or 16
  // (group_heads_ok).
```

Whether kv_mul 8 should be served at all is your top-level point. I answer that there, not here.
"""),
 dict(id="I24", path="t/t_amx_numerics.cpp", line=275, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061782",
      point="check_pv checks only rows below group_heads of o_amx, so a P-fill bound regressed to 16 rows would overread s_pages in production yet pass the test; REQUIRE rows group_heads..15 to be zero in the 4-head case.",
      cls="request-for-change", status="confirmed", action="accept, modified (sentinel rows in exp_rows)", hw=True, dec="",
      verdict="The only loop over o_amx is qi < group_heads [t_amx_numerics.cpp:275]; the P-fill loop is at amx_attn.cpp:271; s_pages at kv_mul 4 is 1024 bytes, a 16-row read is 4096. His exact form has a weakness: the test's own exp_rows is also 4 rows, so a regressed bound reads test stack and the garbage is not deterministic. A 16-row exp_rows with 1.0f in rows group_heads..15 keeps the test in bounds and makes the failure deterministic. The PV case runs only on an AMX host.",
      reply="""
You are right. `check_pv` reads only rows 0..group_heads-1 of `o_amx` [t/t_amx_numerics.cpp:275], and the production loop reads only rows 0..kv_mul-1 of `amx_o` [h/tron/models/self_attention.hpp:1792-1797]. So a P-fill bound of 16 rows [src/tron/kernels/amx_attn.cpp:271] would read 3 KiB past the 1024-byte `s_pages` [self_attention.hpp:1755] and no assertion would notice.

Will do: add your zero check, with one change. In the 4-head case the test's own `exp_rows` is also 4 rows [t/t_amx_numerics.cpp:260], so a regressed bound would read the test's stack, and whether that garbage is nonzero is not deterministic. I will give `exp_rows` 16 rows and fill rows group_heads..15 with 1.0f. The correct kernel never reads those rows, so the output rows stay exactly zero (zero P rows times V, Note [Tile stores write 16 rows]). A regressed bound turns each of them into the sum of 64 V values, nonzero for this seed, and the test stays in bounds.

```
  // Rows group_heads..15 hold a nonzero value the kernel must never read.
  alignas(64) float exp_rows[TILE_ROWS_16][PAGE_TOKENS_64];
  for (size_t qi = 0; qi < TILE_ROWS_16; ++qi) {
    for (auto& x : exp_rows[qi]) {
      x = qi < group_heads ? std::exp(ue(gen)) : 1.f;
    }
  }
  ...
  // Rows group_heads..15 of o_amx are zero P rows times V
  // (Note [Tile stores write 16 rows]).
  for (size_t qi = group_heads; qi < TILE_ROWS_16; ++qi) {
    for (size_t d = 0; d < HEAD_SIZE_128; ++d) {
      CAPTURE(qi, d);
      REQUIRE(o_amx[qi * HEAD_SIZE_128 + d] == 0.f);
    }
  }
```

The PV case skips without AMX, so I will run `t_amx_numerics` on delphi-3bda and post the new per-section counts. The 4-head section's name becomes "4 heads: rows 0..3 in the envelope, rows 4..15 zero".
"""),
 dict(id="I25", path="t/t_amx_numerics.cpp", line=311, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061343",
      point="Both tests gained sections but config/test-benchmarks.json was not refreshed; run bin/slice bench --update for both tests after bin/slice route, as t/AGENTS.md asks.",
      cls="request-for-change", status="confirmed", action="accept (one refresh after all test edits)", hw=True, dec="",
      verdict="The file is untouched on the branch and the rule exists verbatim [t/AGENTS.md:23-26]. Caution found while checking: the native preset does not set TRON_AMX_DISPATCH and make build-test never passes it, so a plain build on delphi-3bda would measure the placeholder binary; the configure step must pass -DTRON_AMX_DISPATCH=ON explicitly. The weekly bot refresh measures the Nix OFF binary and its scheduled runs on 2026-10-18 and 2026-10-25 failed.",
      reply="""
Agreed. Will do: run `bin/slice route`, then `bin/slice bench --update t_amx_numerics t_amx_dispatch_dtype` on delphi-3bda, then `bin/slice bench --check`, and commit the refreshed rows. delphi-3bda is the `granite_rapids_6962p` platform, so the update rewrites the two rows in that block [config/test-benchmarks.json:492-493]. I will do it once, after the test edits of this round are in, so the rows match the final binaries.

One note on what the new numbers measure. `TRON_AMX_DISPATCH` defaults to OFF, and the default Nix CI lane does not set it [CMakeLists.txt:46; nix/cmake-tron-test-build.nix:79-100]. In an OFF binary each of these test files contains only its one placeholder case, so the new sections do not exist there. The bot refresh of 2026-10-11 measured that binary [ec1864fe24]. I will measure with a `--preset native` build configured with `-DTRON_AMX_DISPATCH=ON` passed explicitly (the preset itself leaves the option OFF, and `make build-test` does not pass it) [CMakePresets.json:31-39; GNUmakefile:548], which is the build where the sections run, and say so in the commit message. The genoa96 row of `t_amx_numerics` gets `"skip_return_codes":[4]` by hand unless a Genoa host is available for the update, and I will say so in the PR body.

When the weekly bot refresh next succeeds for the 2x72core class (its scheduled runs on 2026-10-18 and 2026-10-25 failed), it re-measures every row on the Nix OFF binary and will overwrite these two. The per-slice-count deltas between the last two refreshes were up to 0.33 s, so I expect the change to stay inside that spread; the update run gives the measured values.
"""),
 dict(id="I26", path="t/t_amx_numerics.cpp", line=317, url="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061969",
      point="With Catch2 SKIP, a filtered run such as t_amx_numerics \"[kv_data]\" on a non-AMX host exits 4, and the registration at t/CMakeLists.txt:619 lacks SKIP_RETURN_CODE 4 and the skip_return_code_4 label; register it like the other skipping tests and refresh the registry.",
      cls="request-for-change", status="confirmed", action="accept", hw=True, dec="",
      verdict="Catch2 3.7.1 returns 4 only when every selected case was skipped [catch_session.cpp:350-353]. add_catch_test registers the whole binary with plain add_test, so Catch2's catch_discover_tests default never applies; only the passed PROPERTIES do [t/CMakeLists.txt:212-219]. One correction to the verification: ctest cannot pass a tag filter, so 'ctest -R t_amx_numerics' keeps passing; only a direct filtered invocation reaches exit 4.",
      reply="""
You are right. Will do: register `t_amx_numerics` the way `t_chat_template` is registered, and refresh the registry.

The cause is exactly what you describe. The QK and PV cases `SKIP` when AMX is absent [t/t_amx_numerics.cpp:317-319, :330-332]. Catch2 3.7.1 returns 4 when every selected case was skipped and the process was not started with `--allow-running-no-tests` [catch_session.cpp:350-353]; our registered command never passes that flag. `add_catch_test` registers the whole binary with plain `add_test`, so Catch2's own `catch_discover_tests` default of `SKIP_RETURN_CODE 4` never applies; only the PROPERTIES we pass do [t/CMakeLists.txt:212-219]. Slice reads the skip code from the `skip_return_code_N` label alone [bin/slice:1508-1510], so both halves are needed, as doc/slice.md:296-305 says.

Proposed registration:

```
# The QK and PV cases SKIP without AMX; a run that selects only them exits
# Catch2's code 4. SKIP_RETURN_CODE + the skip_return_code_4 label report
# that as skipped (ctest and Slice) rather than failed.
add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake
  PROPERTIES SKIP_RETURN_CODE 4 LABELS "fake;skip_return_code_4")
```

Then the registry refresh from your comment at line 311, which adds `"skip_return_codes":[4]` to the `t_amx_numerics` rows [config/test-benchmarks.json:152, :492].

Verification: on a non-AMX host, `gen/t_amx_numerics "[kv_data]"; echo $?` prints 4, and `ctest -R t_amx_numerics --show-only=json-v1` lists `SKIP_RETURN_CODE 4` and the `skip_return_code_4` label. A plain `ctest -R t_amx_numerics` on that host keeps passing with exit 0, because the two pack cases run and pass; the new property only matters for a filtered invocation. On delphi-3bda the unfiltered run still passes with exit 0.
"""),
]

TODO = """
### Code and comment edits (one text per file, conflicts resolved)

- `h/tron/kernels/amx_attn_iface.hpp`: lines 14-16 (I1 text, no issue number); lines 100-105 (I3 text); the `group_heads_ok` comment at 143-145 (T11 text); one line near Note [QK orientation] pointing at the new transpose header (I10).
- `h/tron/kernels/amx_attn_transpose.hpp` (new): `transpose_scores<group_heads>` as an inline template, AVX-512 intrinsics only (I10).
- `src/tron/kernels/amx_attn.cpp`: lines 213-215 static_asserts (I14 text, Isaac's form); line 269 comment (I15 text); stages 1-4 moved out to the header (I10).
- `h/tron/models/self_attention.hpp`: line 1755 `s_pages{uninitialized}` plus one comment line (I5); lines 1795-1803 row view instead of memcpy, drop `<cstring>` (I6). Pack placement unchanged (I4, D2).
- `src/tron/CMakeLists.txt`: lines 214-218 comment (I7 text, which also carries the ctest/Slice sentence from I10).
- `README.ci.md`: lines 581-588 paragraph (I8 text) and a caption on the flags block at 563-568 (T13).
- `t/CMakeLists.txt`: line 619 registration with `SKIP_RETURN_CODE 4` and the label (I26).
- `t/t_amx_numerics.cpp`: lines 37-38 (I22); lines 117-119 (I23); `check_pv` sentinel rows and zero check (I24); alias at line 183 and shorter comment at 181-182 (I20); new transpose case above `#ifdef TRON_AMX_DISPATCH` (I10).
- `t/t_amx_dispatch_dtype.cpp`: aliases at 272 and 282 (I20); `n_kv_heads` template parameter, `kv_head` argument, K/V loop over all KV heads, value check with `kv_head` offset, comment reword, new 32-head / 2-KV-head section (I17); softmax-state block in `exercise_page` with the `kv_head` index (I19); two 16-head sections (I21); header comment lines 9-18 updated.
- `config/test-benchmarks.json`: refreshed rows for both tests on `granite_rapids_6962p`; `skip_return_codes` on the genoa96 row (I25, I26).
- `nix/cmake-tron-test-build.nix`: not in this PR; one-line PR under #3997 (D1).

### PR body edits

- `TRON_AMX_DISPATCH=OFF` row and the guard-move bullet (I16).
- Performance rule sentence, the qwen3-4b cell label and the explanatory note (I13).
- Verification table: assertion and case counts refreshed once from the final run; per-section Catch2 output and JUnit from delphi-3bda (T4); CMake-lane dispatch run and job ids (T5); object-compare row 5061623a34 vs final head and the Glimmer and llama rerun cells (T10, D6); the 'same instructions as main' claim re-checked after the transpose move (I10).
- 'Open items': the kv_mul-8 item and its follow-up issue (T9).
- Landing method stated (D3).

### Runs on delphi-3bda (follow the 3bda sharing rules; one build, one test pass, one bench refresh, one body refresh, in that order)

1. Build the final head with `cmake --preset native -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON` (the preset alone leaves the option OFF).
2. `gen/t_amx_numerics`, `gen/t_amx_dispatch_dtype`, `gen/t_llama_unit`, AMX on and with `TRON_AMX_DISABLE=1`; the four section-filtered runs and the JUnit report (T4); hostname, commit, cpuinfo flags.
3. Object compare of the six kernel instantiations between 5061623a34 and the final head, and of `qk_rowmajor_128x4<4>` against main after the transpose move (T10, I10).
4. Glimmer tp2 / prompt 1024 production-attention cell (8 users, 2 repetitions per arm) and llama-3.1-8b tp2 / prompt 1024 token identity (D6).
5. `bin/slice route`, `bin/slice bench --update t_amx_numerics t_amx_dispatch_dtype`, `bin/slice bench --check` (I25, I26).
6. Optional, for the follow-up issue's baseline: per-kernel timing of the six instantiations and the `vpextrw` census with clang 19.1.7 (T8, I9).

### CI and issues

- `gh workflow run cmake-single-platform.yml --ref jhan-amx-kvmul16 -F skip_benchmarks=true` at the final head; record run and job ids and the test-host runner (T5).
- One-line PR: `-DTRON_AMX_DISPATCH=ON` in `nix/cmake-tron-test-build.nix`, under #3997, CI owner as reviewer (D1).
- New issue: AMX attention kernel performance follow-up: vectorised pack (I9), stage-3 hoist (I12), lazy pack and lazy tile region (I4), with the Granite Rapids per-kernel timing as baseline (T8).
- New issue: serve kv_mul 8 (llama-70b family, qwen-3-32b), ordered after #5021 (T9).
- Edit #5021: add Isaac's spelling `amx_attn_h128` / `_128` (T12).
"""

PROVENANCE = """
Isaac's review was fetched with `gh api` on 2026-10-30 (review 5623855297, 26 inline comments, all on head 4c4b7b8864). Each of the 39 items (26 inline, 13 from the review body) was checked in a read-only worktree at the head (`/home/jhan/workspace/ai-runs/pr5022-isaac/tron-head`) by one agent that re-ran Isaac's "Checked by" commands and read the surrounding code, then by a second agent instructed to refute the first; 18 of 39 drafts were rewritten after refutation, and a final pass listed the contradictions between items, which this page resolves. Claims Isaac measured on his Zen 4 machine (instruction censuses, nanosecond timings) could not be reproduced here and are not disputed. No compile of the real translation units was possible on this host (no clang 19, no TBB headers), so every proposed code block is untested until built in the project toolchain. Nothing was posted to GitHub and nothing ran on delphi-3bda.
"""

# ---------- rendering ----------
CLS_COLOR = {"request-for-change": "#b45309", "request-for-response": "#1d4ed8", "informational": "#4b5563"}

def badge(cls):
    return f'<span class="badge" style="background:{CLS_COLOR[cls]}">{cls}</span>'

def hwtag(hw):
    return '<span class="tag hw">needs delphi-3bda</span>' if hw else ''

parts = []
parts.append("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Replies to Isaac, PR 5022</title>
<style>
:root{--bg:#ffffff;--fg:#1f2937;--muted:#6b7280;--line:#e5e7eb;--card:#f9fafb;--code:#f3f4f6;--accent:#1d4ed8;--warn:#b45309}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:26px;margin:0 0 6px}
h2{font-size:20px;margin:40px 0 12px;padding-top:8px;border-top:2px solid var(--line)}
h3{font-size:16px;margin:22px 0 8px}
h4{font-size:15px;margin:18px 0 6px}
p{margin:8px 0}
ul,ol{margin:6px 0 6px 22px;padding:0}
li{margin:3px 0}
code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:13px}
pre{background:var(--code);border:1px solid var(--line);border-radius:6px;padding:10px 12px;overflow:auto;font-size:12.5px;line-height:1.45}
pre code{background:none;padding:0;font-size:inherit}
.sub{color:var(--muted)}
.short{background:#eff6ff;border-left:4px solid var(--accent);padding:10px 14px;margin:14px 0}
.badge{display:inline-block;color:#fff;font-size:11px;font-weight:600;letter-spacing:.02em;padding:2px 8px;border-radius:10px;vertical-align:middle;white-space:nowrap}
.tag{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;margin-left:6px;vertical-align:middle;white-space:nowrap}
.tag.hw{background:#fef3c7;color:#92400e}
.tag.dec{background:#ede9fe;color:#5b21b6}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px 16px;margin:14px 0}
.card .head{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:6px}
.card .head .id{font-weight:700;font-size:15px}
.card .loc{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}
.card .pt{margin:6px 0}
.row{display:grid;grid-template-columns:120px 1fr;gap:6px 12px;margin:6px 0}
.row .k{color:var(--muted);font-size:13px}
.reply{background:#fff;border:1px solid var(--line);border-radius:6px;padding:10px 14px;margin-top:8px}
.reply .lbl{font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:4px}
.alt{border-style:dashed}
table{border-collapse:collapse;width:100%;margin:10px 0;font-size:14px}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--code)}
td.num{text-align:right}
.bars{margin:10px 0}
.bar{display:flex;align-items:center;gap:10px;margin:4px 0;font-size:13px}
.bar .lab{width:190px;text-align:right;color:var(--muted)}
.bar .fill{height:16px;border-radius:3px}
.bar .n{font-weight:600}
nav{font-size:13px;margin:10px 0 0}
nav a{margin-right:12px}
.dec{background:#faf5ff;border:1px solid #ddd6fe;border-radius:8px;padding:12px 16px;margin:12px 0}
.dec .t{font-weight:700}
.quote{color:var(--muted);font-style:italic;border-left:3px solid var(--line);padding-left:10px;margin:6px 0}
@media (max-width:640px){.row{grid-template-columns:1fr}.bar .lab{width:120px}}
</style></head><body><main>
""")
parts.append("<h1>Replies to Isaac's review of PR 5022</h1>")
parts.append('<p class="sub">PR 5022 &middot; AMX attention: serve kv_mul 16 (Muse Glimmer) with a group_heads template parameter &middot; review by Isaac (ishapira-positron), CHANGES_REQUESTED, 2026-10-23, at head 4c4b7b8864 &middot; drafts prepared 2026-10-30, nothing posted</p>')
parts.append('<nav><a href="#short">Short version</a><a href="#words">Words used here</a><a href="#decisions">Decisions</a><a href="#top">Review body</a><a href="#inline">Inline comments</a><a href="#todo">To-do</a><a href="#prov">How this was checked</a></nav>')
parts.append('<div class="short" id="short">' + md("**Short version.** " + SHORT.strip()) + '</div>')

# summary counts
from collections import Counter
all_cls = Counter([t["cls"] for t in TOP] + [i["cls"] for i in INLINE])
inl_act = Counter()
for i in INLINE:
    a = i["action"]
    key = "accept as written" if a.startswith("accept") and "modified" not in a and "moot" not in a else \
          "accept with a modification" if "modified" in a else \
          "defer to a follow-up issue" if a.startswith("defer") else \
          "answer only" if a.startswith("answer") else a
    inl_act[key] += 1
parts.append("<h3>Counts</h3><div class=\"bars\">")
maxn = max(all_cls.values())
for k in ["request-for-change", "request-for-response", "informational"]:
    n = all_cls[k]
    parts.append(f'<div class="bar"><div class="lab">{k}</div><div class="fill" style="width:{int(360*n/maxn)}px;background:{CLS_COLOR[k]}"></div><div class="n">{n}</div></div>')
parts.append("</div><p class=\"sub\">39 items: 26 inline comments and 13 points from the review body. Inline actions: " + ", ".join(f"{v} {k}" for k, v in sorted(inl_act.items(), key=lambda x: -x[1])) + ".</p>")

# words
parts.append('<h2 id="words">Words used here</h2><ul>')
for w, d in WORDS:
    parts.append(f"<li><strong>{html.escape(w)}</strong>: {inline(d)}</li>")
parts.append("</ul>")

# decisions
parts.append('<h2 id="decisions">Decisions that are yours before posting</h2><p>The drafts below are written for the recommended choice of each. Where the alternative changes a reply, the card says so.</p>')
for k, t, ctx, rec in DECISIONS:
    parts.append(f'<div class="dec" id="{k}"><div class="t">{k}. {html.escape(t)}</div>{md(ctx)}{md(rec)}</div>')

# top-level
parts.append('<h2 id="top">Part A. The review body, sorted into a list</h2><p>Items in the order they appear in Isaac\'s review. Marks: request-for-change, request-for-response, informational. Items marked informational get no reply unless noted.</p>')
parts.append("<table><tr><th>#</th><th>Point</th><th>Mark</th><th>Same ask as</th><th>Decision</th></tr>")
SAME = {"T1":"I7, I8","T2":"I19","T3":"I10","T4":"","T5":"","T6":"I16","T7":"I7, I8","T8":"I9, I12","T9":"I23","T10":"","T11":"I14, I23","T12":"I1","T13":"I8"}
DEC = {"T1":"D1","T2":"","T3":"","T4":"","T5":"","T6":"","T7":"","T8":"","T9":"D4","T10":"D6","T11":"D4","T12":"D5","T13":""}
for t in TOP:
    parts.append(f'<tr><td><a href="#{t["id"]}">{t["id"]}</a></td><td>{html.escape(t["title"])}</td><td>{badge(t["cls"])}</td><td>{SAME.get(t["id"],"")}</td><td>{DEC.get(t["id"],"")}</td></tr>')
parts.append("</table>")
for t in TOP:
    parts.append(f'<div class="card" id="{t["id"]}"><div class="head"><span class="id">{t["id"]}</span>{badge(t["cls"])}' + (f'<span class="tag dec">{DEC[t["id"]]}</span>' if DEC.get(t["id"]) else '') + '</div>')
    parts.append(f'<div class="pt"><strong>{html.escape(t["title"])}</strong></div>')
    parts.append(f'<div class="quote">{html.escape(t["quote"])}</div>')
    parts.append(f'<div class="row"><div class="k">Checked</div><div>{inline(t["verdict"])}</div></div>')
    parts.append('<div class="reply"><div class="lbl">' + ("Reply" if t["cls"] != "informational" else "Reply (optional)") + '</div>' + md(t["reply"]) + '</div></div>')

parts.append('<h3>One combined reply to the review body (if you post a single comment)</h3><div class="reply">' + md("""
Thanks for the review. Agreed on the architecture reading, and on the CI premise: no pull-request lane sets `TRON_AMX_DISPATCH` at this head, so the two AMX test binaries ran their placeholder cases in CI. Point by point:

- **CI lane.** The CMake comment and README.ci.md get rewritten in this PR to name the lanes that exist. The one-line `-DTRON_AMX_DISPATCH=ON` for the Nix build goes in its own PR under #3997 with the CI owner, because on a Granite Rapids runner it changes what the model tests of the required lane exercise. If it merges first, I rebase this PR on it. (Inline threads at src/tron/CMakeLists.txt:216.)
- **16-head epilogue state.** Added, in every section of `exercise_page`. (t/t_amx_dispatch_dtype.cpp:209.)
- **Transpose lanes.** `transpose_scores<group_heads>` moves to an AVX-512-only header with an ungated 4/16-head case that also runs in the pull-request lane. (src/tron/kernels/amx_attn.cpp:156.)
- **Real-AMX execution at head.** Per-section Catch2 output, JUnit report, kill-switch run, host and commit from delphi-3bda at the final head, in the Verification section.
- **Linked AMX-on build.** Manual `cmake-single-platform.yml` dispatch at the final head; it proves compile and link only, and the body will say so.
- **OFF build.** The Verification row cites jobs 117831672410 and 117835534166 and the guard move.
- **Granite Rapids timing.** No per-kernel number exists; I will attach the A/B record files and offer a per-kernel timing on delphi-3bda as the baseline of a kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack).
- **kv_mul 8.** Yes, the llama-70b family and qwen-3-32b run CPU attention at tron's defaults. I still keep 8 out of this PR, because its kernels have never run on AMX hardware and this PR's validation covers 4 and 16; the reason goes into the `group_heads_ok` comment and a follow-up issue tracks 8.
- **Benchmark provenance.** Object compare of all six instantiations between 5061623a34 and the final head, plus one Glimmer rerun cell and the llama-3.1-8b token-identity cell at the final head, because the epilogue edits you asked for are on that path.
- **Gaps 1-3.** The first `static_assert` becomes the lane bound, the `group_heads_ok` comment carries the reason for {4, 16}, the header comment carries the reason for the kept names (rename in #5021, with your spelling), and README.ci.md matches the CMake comment.

Replies with the texts are on each inline thread.
""") + '</div>')

# inline
parts.append('<h2 id="inline">Part B. Inline comments, one reply each</h2><p>Sorted by file and line. "Checked" states what was verified at head 4c4b7b8864 before the reply was written. Each reply is written to be pasted as is.</p>')
parts.append("<table><tr><th>#</th><th>Location</th><th>Mark</th><th>Isaac's claim</th><th>Action</th><th></th></tr>")
for i in INLINE:
    parts.append(f'<tr><td><a href="#{i["id"]}">{i["id"]}</a></td><td class="loc">{html.escape(i["path"])}:{i["line"]}</td><td>{badge(i["cls"])}</td><td>{html.escape(i["status"])}</td><td>{html.escape(i["action"])}</td><td>{hwtag(i["hw"])}' + (f'<span class="tag dec">{i["dec"]}</span>' if i["dec"] else '') + '</td></tr>')
parts.append("</table>")
for i in INLINE:
    parts.append(f'<div class="card" id="{i["id"]}"><div class="head"><span class="id">{i["id"]}</span><a class="loc" href="{i["url"]}">{html.escape(i["path"])}:{i["line"]}</a>{badge(i["cls"])}{hwtag(i["hw"])}' + (f'<span class="tag dec">{i["dec"]}</span>' if i["dec"] else '') + '</div>')
    parts.append(f'<div class="row"><div class="k">Isaac\'s point</div><div>{inline(i["point"])}</div></div>')
    parts.append(f'<div class="row"><div class="k">Checked</div><div>{inline(i["verdict"])} <span class="sub">(claim {html.escape(i["status"])})</span></div></div>')
    parts.append(f'<div class="row"><div class="k">Action</div><div>{html.escape(i["action"])}</div></div>')
    parts.append('<div class="reply"><div class="lbl">Reply</div>' + md(i["reply"]) + '</div>')
    if i.get("alt"):
        parts.append('<div class="reply alt"><div class="lbl">If the alternative is chosen</div>' + md(i["alt"]) + '</div>')
    parts.append('</div>')

parts.append('<h2 id="todo">Part C. Consolidated to-do (after the decisions)</h2>' + md(TODO))
parts.append('<h2 id="prov">How this was checked</h2>' + md(PROVENANCE))
parts.append("</main></body></html>")

open(OUT, "w").write("\n".join(parts))
print("wrote", OUT, len("\n".join(parts)), "bytes")
