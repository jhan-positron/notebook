#!/usr/bin/env python3
"""v2 (2026-09-17, for Hannah): generate PR3879/new-PRs/PR1/nightly-amx-check-20260916.html
from evidence.json. No machine comparison; action section after the Short version. ASCII only."""
import json, datetime, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[1] / "PR3879/new-PRs/PR1/nightly-amx-check-20260916.html"
E = json.load(open(HERE / "evidence.json"))
R = E["runs"]
BLUE, ORANGE, INK, INK2, GRID, RED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e1e0d9", "#d03b3b"

def T(s):
    d = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    return (d - datetime.datetime(2026, 9, 15)).total_seconds() / 3600

def fig1():
    W, L, Rm = 980, 210, 24
    span = 38.0
    def x(h): return L + (W - L - Rm) * h / span
    lanes = ["tron main branch", "apt package build\n(publish-deb.yml)", "nightly CI on delphi-3bda\n(System CI, 03:39 UTC)"]
    top, lh = 58, 74
    n = len(lanes)
    s = [f'<svg viewBox="0 0 {W} {top + lh*n + 40}" width="100%" style="max-width:{W}px;min-width:760px;display:block;background:#fcfcfb" role="img" aria-label="wall-clock lanes: merge of PR 3879, apt package builds and the nightly runs on 2026-09-15 and 2026-09-16, UTC">']
    s.append(f'<text x="{L}" y="22" font-size="15" font-weight="600" fill="{INK}">Who ran what, when (UTC, durations to scale)</text>')
    for h in range(0, 39, 6):
        xx = x(h)
        s.append(f'<line x1="{xx:.1f}" y1="{top-14}" x2="{xx:.1f}" y2="{top+lh*n-10}" stroke="{GRID}" stroke-width="1"/>')
        day = "09-15" if h < 24 else "09-16"
        s.append(f'<text x="{xx:.1f}" y="{top+lh*n+8}" font-size="11" fill="#898781" text-anchor="middle">{day} {h%24:02d}:00</text>')
    for i, name in enumerate(lanes):
        y = top + lh * i
        for k, line in enumerate(name.split("\n")):
            s.append(f'<text x="8" y="{y+22+k*15}" font-size="12.5" font-weight="{600 if k==0 else 400}" fill="{INK if k==0 else INK2}">{line}</text>')
        s.append(f'<line x1="{L}" y1="{y+lh-8}" x2="{W-Rm}" y2="{y+lh-8}" stroke="{GRID}" stroke-width="1"/>')
    def block(lane, a, b, label, fill, sub=None, anchor="start"):
        y = top + lh * lane + 8
        xa, xb = x(T(a)), x(T(b))
        xl = xa if anchor == "start" else xb
        s.append(f'<rect x="{xa:.1f}" y="{y}" width="{max(xb-xa,3):.1f}" height="22" rx="3" fill="{fill}"/>')
        s.append(f'<text x="{xl:.1f}" y="{y+36}" font-size="11.5" fill="{INK}" text-anchor="{anchor}">{label}</text>')
        if sub: s.append(f'<text x="{xl:.1f}" y="{y+50}" font-size="11" fill="{INK2}" text-anchor="{anchor}">{sub}</text>')
    def mark(lane, a, label, color, anchor="start"):
        y = top + lh * lane + 8
        xx = x(T(a))
        s.append(f'<line x1="{xx:.1f}" y1="{y-2}" x2="{xx:.1f}" y2="{y+24}" stroke="{color}" stroke-width="2.5"/>')
        if label: s.append(f'<text x="{xx + (6 if anchor=="start" else -6):.1f}" y="{y+36}" font-size="11.5" fill="{INK}" text-anchor="{anchor}">{label}</text>')
    m = E["merge"]
    mark(0, m["merge_commit_time"], "22:20 PR 3879 merge commit 3fd5edaa66 lands on main", RED, anchor="end")
    mark(0, m["f46e48ba_time"], "23:25 f46e48ba (next package source)", INK2, anchor="start")
    d15, d16 = E["deb_builds"]["0915"], E["deb_builds"]["0916"]
    block(1, d15["start"], d15["end"], "01:37 to 02:01  package from e0a11a6c2e built (pre-merge source)", "#c3c2b7", "published to apt only at 16:26, after the nightly had installed the 09-14 package")
    mark(1, d15["published"], "", "#c3c2b7")
    block(1, d16["start"], d16["end"], "", BLUE)
    xe = W - Rm
    s.append(f'<text x="{xe:.1f}" y="{top+lh*1+8+36}" font-size="11.5" fill="{INK}" text-anchor="end">01:35 to 02:00  package 2026.09.16-f46e48ba</text>')
    s.append(f'<text x="{xe:.1f}" y="{top+lh*1+8+50}" font-size="11" fill="{INK2}" text-anchor="end">PR source in; deb preset, so AMX option OFF</text>')
    a, b = R["3bda_0915"], R["3bda_0916"]
    block(2, a["start"], a["end"], f'03:39 to 13:17  ran tron {a["tron"]}', ORANGE, "package built 2026-09-14: no PR 3879 source at all")
    block(2, b["start"], b["end"], f'03:39 to 13:17  ran tron {b["tron"]}', BLUE, "PR 3879 source present, AMX code absent", anchor="end")
    xm = x(T(m["merge_commit_time"]))
    s.append(f'<line x1="{xm:.1f}" y1="{top-14}" x2="{xm:.1f}" y2="{top+lh*n-10}" stroke="{RED}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    s.append('</svg>')
    return "\n".join(s)

def num(v, d=2): return f"{v:,.{d}f}" if isinstance(v, float) else (f"{v:,}" if isinstance(v, int) else str(v))

def main():
    bc = E["binary_checks"]; J = E["journal"]; m = E["merge"]
    rows = "\n".join(
        f'<tr><td>{b["binary"]}</td><td>{b["source"]}</td><td>{b["option"]}</td><td class="num">{num(b["size"])}</td><td>{b["mtime"]}</td><td class="num">{b["amx_instructions"]}</td><td class="num">{b["disable_string"]}</td><td class="num">{b["amx_attn_symbols"]}</td><td>{"<span class=no>no AMX code</span>" if b["amx_instructions"]==0 else "<span class=ok>AMX code present</span>"}</td></tr>'
        for b in bc)
    html = f"""<title>Nightly AMX check</title>
<style>
:root {{ color-scheme: light; }}
body {{ background:#f9f9f7; color:{INK}; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size:15px; line-height:1.5; margin:0; padding-block: 24px 48px; padding-inline: 16px; }}
main {{ max-width: 980px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0 0 4px; text-wrap: balance; }} h2 {{ font-size: 18px; margin: 32px 0 8px; }} h3 {{ font-size: 15px; margin: 20px 0 6px; }}
.sub {{ color:{INK2}; font-size: 13.5px; margin-bottom: 18px; }}
.short {{ background:#fcfcfb; border:1px solid {GRID}; border-radius:8px; padding:14px 18px; }}
table {{ border-collapse: collapse; font-size: 13.5px; }} .tw {{ overflow-x:auto; }}
th, td {{ border-bottom: 1px solid {GRID}; padding: 5px 10px; text-align: left; vertical-align: top; }} th {{ color:{INK2}; font-weight:600; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.fig {{ background:#fcfcfb; border:1px solid {GRID}; border-radius:8px; padding:10px 12px 6px; margin: 10px 0; overflow-x:auto; }}
.take {{ font-size: 13.5px; color:{INK2}; margin: 4px 0 0 4px; }}
code {{ font-size: 12.5px; background:#f0efec; padding:1px 4px; border-radius:3px; }}
pre {{ font-size: 12.5px; background:#f0efec; padding:10px 12px; border-radius:6px; overflow-x:auto; margin: 6px 0 10px; }}
dl {{ margin:0; }} dt {{ font-weight:600; margin-top:6px; }} dd {{ margin: 0; color:{INK2}; }}
ol.steps {{ padding-left: 22px; }} ol.steps > li {{ margin: 0 0 12px; }} ol.steps b {{ display:block; }}
.flow {{ display:grid; grid-template-columns: 1fr; gap: 14px; margin: 10px 0; }}
.lane {{ background:#fcfcfb; border:1px solid {GRID}; border-radius:8px; padding:10px 12px; }}
.lane h4 {{ margin:0 0 8px; font-size:13.5px; color:{INK2}; text-transform: uppercase; letter-spacing: .04em; }}
.steps {{ display:flex; flex-wrap:wrap; gap:8px; align-items:stretch; }}
.step {{ flex: 1 1 150px; border:1px solid {GRID}; border-radius:6px; padding:6px 9px; font-size:12.5px; background:#f9f9f7; min-width:0; }}
.step b {{ display:block; font-size:12.5px; }}
.step.amx-on {{ border-color:{BLUE}; }} .step.amx-off {{ border-color:{ORANGE}; }}
.ok {{ color:#0ca30c; font-weight:600; }} .no {{ color:{RED}; font-weight:600; }}
</style>
<main>
<h1>Was AMX in the last two nightly CI binaries? No. What has to change so the nightly uses it (2026-09-15 and 2026-09-16)</h1>
<div class="sub">Question (jhan, 2026-09-16): PR 3879 merged on 2026-09-15 and the nightly System CI showed no throughput change. Was AMX compiled into the binary the nightly ran, and if so did it run? Evidence gathered 2026-09-17 00:10 to 01:50 UTC and checked by an adversarial verification pass (section 6). Generator: exec/nightly-amx-check-20260916/gen_page.py.</div>

<div class="short"><p><b>Short version.</b> No: the apt package that the nightly installs is built without the AMX option, so last night's binary (the first one that contains the PR 3879 source) has no AMX code in it, and AMX could not run. The night before ran a package built before the merge, so it had no AMX source at all. The fix is one line in the package build (turn the CMake option TRON_AMX_DISPATCH on in the "deb" preset); after that, the line to watch in the nightly is llama-3.1-8b-instruct-good tp2, because the qwen-3-4b and gpt-oss engines run attention on the FPGA and will barely move.</p></div>

<h2>1. What has to change for the nightly to use AMX, and how</h2>
<ol class="steps">
<li><b>Turn the option on where the package is built (one line).</b> The nightly installs tron from the apt package (the .deb file). That package is produced by "make deb", which configures CMake with the preset named "deb" (a preset is a named set of CMake options) [GNUmakefile:508]. Add the AMX option to that preset's cache variables in CMakePresets.json (lines 68-81 on main today):
<pre>       "BUILD_INGEST_MODELS": "ON",
-      "ENABLE_FUSE_STATS": "ON"
+      "ENABLE_FUSE_STATS": "ON",
+      "TRON_AMX_DISPATCH": "ON"</pre>
The alternative is <code>-DTRON_AMX_DISPATCH=ON</code> on the cmake line of the gen-deb rule in the GNUmakefile. The preset is the better place: a developer's "make deb" then produces the same package as CI. Why this is enough: the option adds the one kernel file kernels/amx_attn.cpp with its own instruction-set flags (-mamx-tile -mamx-bf16 and the AVX-512 set) and defines TRON_AMX_DISPATCH for the rest of the tree [src/tron/CMakeLists.txt:193-198]. The package builder compiles with Clang 19.1.7 (build log of run 35044660449), the same compiler the PR test lane used when it compiled this file, so no toolchain change is needed. No other build file (CMakeLists, presets, GNUmakefile, packaging) sets or gates the option; its source consumers are the #ifdef sites in h/tron/models/self_attention.hpp and the kernel and interface files, and the unit tests that use it are excluded by ENABLE_TESTS OFF. The combination is not new: our 2026-09-16 build of the merge commit (tron-p3879 on delphi-3bda) used the deb preset's values (BUILD_NATIVE OFF, AVX512 ON, production and ingested models, FUSE stats ON; only ENABLE_TESTS differs) plus the option, and compiled all 173 model variants with Clang 19. Two precautions: build once before merging, outside "nix develop", with <code>cmake --preset deb -DTRON_AMX_DISPATCH=ON &amp;&amp; cmake --build gen-deb</code> (no pull-request lane compiles the deb preset, so the first CI compile of the change is the 01:17 UTC package run itself), and check that run's log the next morning for the amx_attn.cpp.o line, because a failed package build makes the nightly silently keep the previous package.</li>
<li><b>Nothing else in the nightly has to change.</b> The systems_test workflow runs a plain <code>apt-get install -y tron</code> on the machine [system_ci_granite_rapids_72_rinzler_OCI.yaml:47-50]; the machine's apt pin (priority 900 on the unstable release) makes that resolve to the nightly package from the unstable channel today. No environment variable is needed: when the option is compiled in, the AMX path is on by default, and TRON_AMX_DISABLE=1 is the kill switch [h/tron/kernels/amx_attn_iface.hpp:47-48]. The service units read environment files that platformd and operators write (/etc/rinzler/instance-*.env, /opt/positron/user/config.env); a TRON_AMX_DISABLE=1 line there would switch AMX off without any trace in the package checks of step 5, so step 5 includes a grep for it.</li>
<li><b>Machines without AMX stay safe with the same package.</b> The other nightly machine (andoria-b1a3, an AMD host) runs the same apt-get command [system_ci_genoa96_rinzler.yaml:46-50], so it receives a package built by the same deb preset. The kernels test the CPU at run time (CPUID feature bits, the XCR0 register, and a kernel permission request) and fall back to the existing AVX path when AMX is absent; this fallback was verified on 2026-09-11 with runtron built from the PR head on andoria-06, an AMD EPYC Genoa host of the same family as andoria-b1a3 [andoria-AMD-machine-test.md].</li>
<li><b>Timing.</b> publish-deb.yml is scheduled at 01:17 UTC; last week's runs started between 01:31 and 01:40 UTC and build the head of main at that moment. The delphi-3bda nightly is scheduled at 03:30 UTC (the AMD machine at 03:00) and installed the package at about 03:39 UTC (03:10) in the last runs. A change pushed to main before about 01:00 UTC is therefore in that night's run, provided the publish step finishes in time: on 2026-09-15 the package was built in 24 minutes but its publish job ran only at 16:26 UTC, so that night kept the previous package (Figure 1); the job list does not record why it waited. The run log's "Setting up tron (version)" line and the rinzler journal's "Version:" line tell which package a night ran, so check them before reading the first night's numbers.</li>
<li><b>Check the package before reading the numbers.</b> In the publish-deb build log, look for <code>Building CXX object src/tron/CMakeFiles/tron.dir/kernels/amx_attn.cpp.o</code> (absent today). On delphi-3bda, after the install:
<pre>strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE          # expect 1 (today 0)
objdump -d --no-show-raw-insn /opt/positron/bin/rinzler \\
  | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)'  # expect about 86 (today 0)
sudo grep -l TRON_AMX_DISABLE /etc/rinzler/instance-*.env /opt/positron/user/config.env  # expect no output</pre>
The package binary is stripped, so <code>nm</code> shows no symbols and cannot be used; the first two checks work on a stripped binary (section 3b shows them on our builds as controls). The 86 is our control build's count (32 tdpbf16ps, 40 tileloadd, 12 tilestored, 1 ldtilecfg, 1 tilerelease) with the same compiler version and build type; a different Clang patch level or link-time optimisation could shift it by a few. The third line confirms nobody has switched AMX off through the service environment.</li>
<li><b>Check that the AMX gate opens at run time.</b> Nothing the package emits today records AMX use: no log line, no counter, no FUSE stat. The gate probes the CPU once per process, at the first software-attention call of an eligible model (the header comment says "process start", but the code runs it lazily [src/tron/kernels/amx_attn.cpp:84; h/tron/models/self_attention.hpp:1255]), and asks Linux for tile-state permission with the system call arch_prctl(0x1023, 18). Two ways to see it: (a) restart the unit that serves llama-3.1-8b-good or mixtral (<code>systemctl restart rinzler@N</code>), wait until it has loaded, attach <code>sudo strace -f -e trace=arch_prctl -p &lt;pid&gt;</code>, then send one request to that model. The expected line is <code>arch_prctl(0x1023 /* ARCH_??? */, 0x12) = 0</code> (strace 5.16 does not know the request name): a return value of 0 means permission granted and the gate open, -1 means the AVX path is in use, and no line means the probe did not run (no eligible model, or attached too late: the result is cached for the process lifetime). Attach after start-up, not by starting rinzler under strace (that breaks the setuid FUSE helper), and do it in a separate session, because strace stops every thread at every system call while attached; Ctrl-C detaches. (b) The direct evidence that a kernel ran a page would be a one-time info log line in amx_attn.cpp; that small follow-up does not exist yet.</li>
<li><b>Where the change will show, and where it will not.</b> The AMX kernels replace CPU (software) attention only. In the nightly, the qwen-3-4b (tp2, tp4) and gpt-oss-120b engines run attention on the FPGA cards from query position 127 on (journal: "HW attention enabled for model ... engagement=127"); the CPU scores only positions 0 to 126 plus up to 3 tail tokens per query, and only the first 64 tokens form the complete page the AMX kernel needs, so AMX can cover at most one page per query per layer there: those lines should move close to 0% (code reading, not measured under FPGA attention). qwen-3-4b itself passes the kernel's shape test and gained +4.5% in our measurement with CPU attention forced, which the nightly does not do. The CPU-attention models that pass the shape test (4 query heads per KV head, head size 128, bf16 activations) are llama-3.1-8b-instruct-good tp2 and mixtral-8x7b tp2. Our 2026-09-05 measurement with the CI harness (8 users on one rinzler process, prompt 1024, 1536 generated tokens, 10 rounds; binary = the PR head 60d66d9c04 of 2026-09-04, before the split, with USE_HW_ATTN=0 in every cell, which for llama equals the nightly default) gave llama-3.1-8b-good tp2 +13.9% TPS with AMX against the same binary with the kill switch, and mixtral -0.2% (no gain) [more-testing round 1]. The merged main code and the nightly's own layout for llama (4 tp2 engines behind the proxy, 8 users, about 2 per engine) were not re-measured; treat +14% as an estimate (est.). The perf test's goal for llama-3.1-8b-good tp2 is a mean of 144 TPS with every user above 140 TPS [testlib/tps.py; the same values in scripts/system_ci.py get_goal]; the last two nights reported means of 139.78 and 139.98 TPS with slowest users at 136.46 and 132.70 (run logs), so a gain of that size (mean about 159 TPS, slowest user about 151 to 155, est.) would take the line from failing to passing. Every other CPU-attention model in the perf list fails the shape test (llama-3.2-3b 3 heads per KV head, llama-3.3-70b 8, qwen-2.5-32b 5, gemma-2-9b head 256); gpt-oss-120b (head 64, from its model config) fails it and runs FPGA attention anyway.</li>
<li><b>Separate item, not needed for the nightly.</b> The default pull-request lane (gcp-nix.yml, since the 2026-09-11 cutover; its tron build flags live in nix/cmake-tron-test-build.nix) does not set the option either. The AMX unit tests (t_amx_numerics, t_amx_dispatch_dtype) are built and run there, but without the option each contains only a placeholder case that passes, so no AMX code is exercised in default CI. The legacy lane that has the flag runs only on manual dispatch, or as publish-deb's test job on a v* tag push or a feature-branch publish, never on the nightly schedule. Proposal for a dedicated test job: Hannah-AMX-CI.html and issue 3997.</li>
</ol>

<h2>Words used here</h2>
<dl>
<dt>tron, rinzler, runtron</dt><dd>tron is the inference program under test. rinzler is its production server binary (the nightly runs rinzler from /opt/positron/bin). runtron is the command-line tool we use in our own campaigns.</dd>
<dt>AMX, TRON_AMX_DISPATCH, the AMX option</dt><dd>AMX = Intel Advanced Matrix Extensions, CPU instructions that multiply small matrices in one step. PR 3879 adds AMX attention kernels behind the CMake option TRON_AMX_DISPATCH (default OFF). When the option is OFF the kernel file kernels/amx_attn.cpp is not compiled at all [src/tron/CMakeLists.txt:193-198 at f46e48ba].</dd>
<dt>the nightly, System CI, systems_test, DUT</dt><dd>The GitHub Actions workflow "System CI (Rinzler 72-core Intel system OCI version)" in the repo positron-ai/systems_test. It runs every night at 03:39 UTC against delphi-3bda (the DUT, device under test), installs tron from the apt package server, then runs functional, performance, MMLU and soak tests. A sister workflow "System CI (Rinzler 96-core system)" does the same against andoria-b1a3, an AMD host.</dd>
<dt>PR test CI: cmake-single-platform.yml, gcp-nix.yml</dt><dd>cmake-single-platform.yml ("CMake and CTest") is the tron repo's legacy pull-request pipeline: it configures and builds tron from source with the AMX option on, runs unit tests and a benchmark, and never produces the installable package. Since the switch to the GCP Nix lane on 2026-09-11 (PR 4339) it runs only when started by hand or as a gate inside publish-deb.yml for tag pushes and feature branches; the default pull-request and merge-queue lane is now gcp-nix.yml, which does not set the AMX option either. cmake-single-platform.yml is the file with the -DTRON_AMX_DISPATCH=ON line (line 333 in the PR diff, line 355 on main today).</dd>
<dt>apt package, deb, publish-deb.yml, the deb preset</dt><dd>The installable package tron_&lt;version&gt;_amd64.deb. It is built once a day at 01:17 UTC by the tron workflow publish-deb.yml, which runs "make deb"; that target configures CMake with the preset named "deb" [GNUmakefile:508]. A preset is a named set of CMake options [CMakePresets.json:68-81].</dd>
<dt>package version 2026.09.16-f46e48ba</dt><dd>build date, then the first 8 hex digits of the tron main commit the package was built from. rinzler prints the same string at start ("Version: 2026.09.16-f46e48ba hash: f46e48bab498...").</dd>
<dt>TPS</dt><dd>decode tokens per second per user in the nightly's performance test, averaged over 8 users and 10 rounds (prompt 1024 tokens, 1536 generated tokens).</dd>
<dt>FPGA attention, software attention, engagement point</dt><dd>For "ingested" models (qwen-3-4b, gpt-oss) tron runs attention on the FPGA cards from query position 127 on (the engagement point); positions before that and the hand-written models (llama, mixtral, qwen-2.5) run attention on the CPU (software attention). The AMX kernels replace only software attention.</dd>
<dt>nm, strings, objdump</dt><dd>Three binary-inspection tools: nm lists the function names in a binary (useless on a stripped binary), strings lists the text constants, objdump -d disassembles the machine code. We look for the text constant "TRON_AMX_DISABLE" (read by the kernel file with getenv) and for AMX machine instructions (tdpbf16ps, tileloadd, tilestored, ldtilecfg, tilerelease).</dd>
<dt>journal</dt><dd>The systemd log of the rinzler service units rinzler@0..3 on delphi-3bda, read with sudo journalctl.</dd>
</dl>

<h2>2. Timeline: which source each nightly ran</h2>
<p>PR 3879 was merged on Tuesday 2026-09-15 at 22:54 UTC; its merge commit 3fd5edaa66 was created by the merge queue at 22:20 UTC [gh pr view 3879: mergedAt {m["merged_at"]}]. The nightly of 2026-09-15 started at 03:39 UTC, 19 hours before the merge, and installed the package 2026.09.14-875cd228. Commit 875cd228 is an earlier main commit, 21 merges before the PR 3879 merge, so that binary contained none of the PR source [git merge-base --is-ancestor 3fd5edaa66 875cd228: no]. The nightly of 2026-09-16 installed 2026.09.16-f46e48ba; commit f46e48ba (the merge commit of PR 4422, created 23:25 UTC on 2026-09-15) does contain the PR [git merge-base --is-ancestor 3fd5edaa66 f46e48ba: yes]. So the 2026-09-16 run was the first nightly whose source contained PR 3879, and the 2026-09-15 run predates the merge.</p>
<h3>Figure 1: merge, package builds and nightly runs</h3>
<div class="fig">{fig1()}</div>
<p class="take">Durations to scale. Package build and nightly start times are the GitHub Actions job timestamps; the merge time is the merge commit's committer date (the merge queue created the commit at 22:20 UTC and GitHub marked the PR merged at 22:54 UTC). The 2026-09-15 package (source e0a11a6c2e, also pre-merge) was built in 24 minutes but its publish step ran only at 16:26 UTC, after that day's nightly had already installed the previous package (the apt history on delphi-3bda shows "Install: tron:amd64 (2026.09.14-875cd228)" at 03:39:16 UTC on 2026-09-15). Both nightly runs were first attempts, and dpkg logged no tron install between 2026-09-15 03:39 and 2026-09-16 03:39 UTC.</p>

<h2>3. Was AMX compiled into last night's binary? No</h2>
<h3>3a. Why: the package build path never turns the option on</h3>
<div class="flow">
<div class="lane"><h4>Path A: PR test CI (the yaml with the flag)</h4><div class="steps">
<div class="step amx-on"><b>cmake-single-platform.yml, job "build"</b>cmake --preset native ... -DTRON_AMX_DISPATCH=ON [three-line command at lines 331-333 of the PR's file, the flag on line 333; line 355 on main]</div>
<div class="step amx-on"><b>compiles kernels/amx_attn.cpp.o</b>seen in the two pull-request runs of this lane on the PR branch (34375107972 on 2026-09-09, 34621722240 on 2026-09-11: "[504/822] Building CXX object src/tron/CMakeFiles/tron.dir/kernels/amx_attn.cpp.o")</div>
<div class="step"><b>unit tests + benchmark</b>on the pull-request runner; the built tree is bundled as a CI artifact only</div>
<div class="step"><b>never installed anywhere</b>this pipeline does not produce the apt package. Since 2026-09-11 it also no longer runs on pull requests or the merge queue by default: the GCP Nix lane took over and does not set the option, and the merge-queue checks for PR 3879 itself were "GCP Nix", "Nix build validation" and "Debian smoke"</div>
</div></div>
<div class="lane"><h4>Path B: the package the nightly installs</h4><div class="steps">
<div class="step"><b>publish-deb.yml, cron 01:17 UTC</b>job "build" runs "make ... deb" [publish-deb.yml, "Build .deb" step]; its optional "test" job would call the legacy CMake lane for tag pushes and feature branches, and was skipped on this scheduled run</div>
<div class="step amx-off"><b>GNUmakefile target gen-deb</b>cmake --preset deb -DENABLE_FUSE_STATS=... -DTRON_INGEST_PLUGIN_BUNDLE="" [GNUmakefile:508]</div>
<div class="step amx-off"><b>preset "deb" has no TRON_AMX_DISPATCH</b>cache variables: RelWithDebInfo, ENABLE_TESTS OFF, BUILD_NATIVE OFF, BUILD_PRODUCTION_MODELS ON, BUILD_INGEST_MODELS ON, ENABLE_FUSE_STATS ON [CMakePresets.json:68-81]; the option defaults OFF [CMakeLists.txt:48]</div>
<div class="step amx-off"><b>amx_attn.cpp not compiled</b>the build log of the 2026-09-16 package (run 35044660449, 397 ninja steps; the downloaded log shows 378 of them, 19 lines inside the model-ingest segment are missing) shows kernels/rope.cpp.o as the only kernels/ object and never mentions amx_attn; its "Preset CMake variables" block lists no TRON_AMX_DISPATCH. The binary check in 3b closes the gap left by the missing lines</div>
<div class="step"><b>tron_2026.09.16-f46e48ba_amd64.deb</b>published to apt.positron.internal/unstable at 02:00 UTC</div>
<div class="step"><b>nightly: apt-get install -y tron</b>over ssh on delphi-3bda at 03:39 UTC [system_ci_granite_rapids_72_rinzler_OCI.yaml:47-50]; the machine's own apt pin (tron from release o=unstable, priority 900) selects the unstable channel</div>
</div></div>
</div>
<p class="take">The yaml with the flag (path A) did compile AMX on the PR's own runs, but the product package (path B) does not, and the nightly only ever sees path B. Today no default lane compiles AMX: path A runs only on manual dispatch, and the default GCP Nix lane lacks the flag.</p>

<h3>3b. Proof on the installed binaries, with controls</h3>
<p>We ran the same three checks on the package binaries that served both nights (last night's from the installed file, the night before's extracted from the package still in the apt cache on delphi-3bda) and on three of our own builds on delphi-3bda. Two checks are decisive for a shipped binary: the machine-instruction count (objdump) and the text constant "TRON_AMX_DISABLE" (strings), because both survive symbol stripping. The function-name check (nm) works only on unstripped builds; the package binary is stripped ("no symbols"), so that column is not evidence for it. The controls show that the checks do detect AMX code when it is present, and stay at zero for a build that has no AMX source.</p>
<div class="tw"><table>
<tr><th>binary</th><th>built from</th><th>AMX option</th><th class="num">size, bytes</th><th>built</th><th class="num">AMX instructions (objdump)</th><th class="num">"TRON_AMX_DISABLE" text (strings)</th><th class="num">amx_attn functions (nm)</th><th>reading</th></tr>
{rows}
</table></div>
<p class="take">Commands: <code>objdump -d --no-show-raw-insn BIN | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)'</code>, <code>strings BIN | grep -c -x TRON_AMX_DISABLE</code>, <code>nm -C --defined-only BIN | grep -c amx_attn</code>. A second, independent disassembly count of the 2026-09-16 package binary (44,285,369 instructions decoded) found 8,784 AVX-512 BF16 instructions and 0 AMX tile instructions of any kind. The strings check is meaningful on this stripped binary because 35 other TRON_* environment-variable names do survive in it. The only "amx" text in the package binary is a CPU-feature name table ("amx-bf16", "amx-tile", "amx-int8", ...) from the Rust standard library's std_detect module, not tron code. tron is a static library linked into rinzler [src/tron/CMakeLists.txt:160], so rinzler is the right file to inspect. dpkg confirms the installed package is tron 2026.09.16-f46e48ba; the installed file's sha256 equals that of the rinzler inside the cached package file, and its modification time (2026-09-16 01:56 UTC, preserved from the package build) matches the build run (01:35 to 02:00 UTC). ldd shows only system libraries plus libfuse3 and a 4 KB libversion.so, so all tron code is inside the rinzler executable; the package ships no runtron. The 2026-09-15 binary (202,100,384 bytes, also stripped) shows 2,868 AVX-512 BF16 dot instructions and the text USE_HW_ATTN (both positive controls) but 0 AMX instructions and no TRON_AMX_DISABLE text.</p>

<h2>4. Did AMX run at runtime? No, it could not</h2>
<ul>
<li><b>The binary that served the nightly is the package binary.</b> All 78 rinzler start banners in the journal during the 2026-09-16 nightly window (03:30 to 13:30 UTC; {num(sum(J["0916"]["units_lines"]))} journal lines over the four units) read "Version: 2026.09.16-f46e48ba hash: f46e48bab498c0c07825f3e3d38d6ffa42d4af9b", for both engine layouts the nightly uses (4 engines for tp2, 2 for tp4), and every journal line's executable field is /opt/positron/bin/rinzler (the file the service unit starts; no runtron or other tron executable appears, and the host runs no containers). During the 2026-09-15 window all 79 banners read "Version: 2026.09.14-875cd228".</li>
<li><b>No AMX code in either binary means no AMX at runtime on either night.</b> Both package binaries were inspected (section 3b): the installed 2026-09-16 file, and the 2026-09-15 file extracted from the package still in the apt cache. For 2026-09-15 the source agrees: commit 875cd228 dates from 2026-09-13, precedes the merge, and its tree contains no AMX file at all (git ls-tree). rinzler_proxy and platformd only route requests.</li>
<li><b>PR 3879 changes nothing that runs with the option off.</b> Outside the #ifdef TRON_AMX_DISPATCH guards the PR adds three #include lines, one named constant with the same value as the literal it replaced, and two accessors that only guarded code calls (diff of eb2de0265a to 3fd5edaa66, non-test files). So the 2026-09-16 binary carries no PR 3879 behaviour of any kind.</li>
<li><b>The journal cannot show AMX use either way.</b> Zero journal lines mention "amx" in either window, but the tron source at f46e48ba has no log statement that mentions AMX (checked src/tron/kernels/amx_attn.cpp, h/tron/kernels/amx_attn_iface.hpp, h/tron/models/self_attention.hpp). So a log search is not a test; the binary inspection is. Step 6 of section 1 says how to observe engagement once the option is compiled in.</li>
<li><b>No AMX-related environment in the service units.</b> /etc/rinzler/instance-*.env, as regenerated by platformd on 2026-09-16 (08:42 UTC for instances 2 and 3, 10:12 UTC for 0 and 1), set neither USE_HW_ATTN nor TRON_AMX_DISABLE; earlier generations of these files are not kept. With the option compiled out, TRON_AMX_DISABLE would have no effect anyway.</li>
</ul>

<h2>5. Attention mode of the nightly's models (why the qwen lines will not move)</h2>
<ul>
<li>In both nightly windows the qwen engines log "HW attention enabled for model 'ingested-qwen-3-4b-instruct-2507-tp2': max_layers=36 engagement=127" ({J["0916"]["hw_attn_qwen_tp2"]} lines per night, one per tp2 engine; tp4 {J["0916"]["hw_attn_qwen_tp4"]} lines; gpt-oss-120b {J["0916"]["hw_attn_gptoss_tp4"]} lines), and no attention fallback is logged during the 3-minute qwen perf test. The line ends "(model default)": ingested plugins force hardware attention unless USE_HW_ATTN=0 is set.</li>
<li>llama-3.2-3b, llama-3.1-8b-good, llama-3.3-70b, mixtral-8x7b and qwen-2.5-32b log "HW attention disabled ... default off for this model": CPU attention, where the AMX kernels apply if the model shape passes the gate.</li>
<li>Our 2026-09-13 campaign in the nightly's own engine layout reproduced the nightly qwen TPS within 5% with FPGA attention, and showed the AMX gain only with CPU attention [Sunday-CI-layout-results.html].</li>
<li>One nuance: in the later MMLU Pro phase the qwen tp4 engines logged about 800 FPGA-memory-exhaustion warnings per night, each degrading one 1024-token shard to CPU attention, so that phase does exercise CPU attention on qwen; the perf test does not.</li>
</ul>

<h2>6. Verification</h2>
<div id="verification">
<p>An adversarial verification workflow ran on 2026-09-17 00:44 to 01:08 UTC (17 agents, 376 tool calls, run wf_39c58401-d26) over the findings of version 1 of this page: for each finding one verifier re-derived every number, id and quote from the primary sources with its own commands, and a second verifier tried to break the conclusion with alternative explanations (another binary serving, another delivery path, a detection method that could miss AMX code, a date or log-format mistake). A final agent looked for gaps.</p>
<ul>
<li><b>All 16 verdicts confirmed the main conclusion</b> (the nightly binaries contain no AMX code and AMX did not run); 13 upheld the finding as written.</li>
<li><b>Corrections applied:</b> the linked workflow file is the legacy CMake lane, no longer the default pull-request or merge-queue lane since 2026-09-11 (section 3a, Words); the function-name check (nm) is void on the stripped package binary (section 3b); the f46e48ba time is a committer date, not the PR's merge time; the 2026-09-15 package was built in 24 minutes and published at 16:26 UTC; the service environment files were regenerated during the run; the 2026-09-15 binary was measured from the apt cache instead of inferred from git history; mixtral and qwen-2.5-32b also run CPU attention.</li>
<li><b>Version 2 (2026-09-17, for Hannah):</b> the machine-attribution material of version 1 was removed and section 1 (what to change, and how) was added. Its new statements were checked against primary sources: the compiler identification line of the package build log (Clang 19.1.7 in both the package build and the PR test lane build), the preset text on main, the CMake gate at src/tron/CMakeLists.txt:193-198, the llama-3.1-8b-good tp2 values in the two run logs, and the 2026-09-05 measurement record. Section 1 itself was verified by a second, smaller adversarial pass (see the note at the end of this section).</li>
<li><b>Left as stated, with the evidence chain named:</b> FPGA attention during the perf test rests on the load-time "enabled" line, the absence of fallback warnings in that window, and our 2026-09-13 same-layout measurement.</li>
</ul>
<p class="take" id="v2-verify">Section 1 verification (run wf_5285df32-e6a, 4 agents, 176 tool calls, 2026-09-17 02:03 to 02:22 UTC; two claim groups, each checked by a re-deriving verifier and a verifier trying to break the recommendation): 0 of 4 verdicts refuted; the fixes applied were wording precision: the probe runs at the first eligible dispatch, not at process start; the strace line as strace 5.16 prints it and what its return value means; scheduled versus observed run times; the deb preset resolves the package through the machine's apt pin; qwen-3-4b passes the shape test but runs FPGA attention; the round-1 binary and settings; the unit tests run as placeholders in the default lane; the 144 TPS goal comes with a 140 TPS slowest-user floor; a pre-merge local build of the deb preset and an environment-file grep were added as precautions.</p>
<p class="take">Verifier journal: ~/.claude/projects/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/65083b84-d7db-4aa7-82ef-613b1002c56b/subagents/workflows/wf_39c58401-d26/journal.jsonl.</p>
</div>

<h2>7. Sources</h2>
<div class="tw"><table>
<tr><th>item</th><th>where</th></tr>
<tr><td>nightly run logs (gh run view --log)</td><td>systems_test runs 34925789174 (2026-09-15) and 35052594106 (2026-09-16), DUT delphi-3bda</td></tr>
<tr><td>package build log</td><td>tron publish-deb.yml run 35044660449 (head f46e48ba, 2026-09-16 01:35 to 02:00 UTC); "The CXX compiler identification is Clang 19.1.7"</td></tr>
<tr><td>PR test CI build logs</td><td>tron cmake-single-platform.yml runs 34621722240 (544ca05c7a) and 34375107972 (26a0338c3b), job "build"</td></tr>
<tr><td>build configuration</td><td>tron at f46e48ba and main 0a39578313: CMakeLists.txt:48, CMakePresets.json:68-81, GNUmakefile:506-510, src/tron/CMakeLists.txt:182-198, .github/workflows/publish-deb.yml, .github/workflows/cmake-single-platform.yml:349-355</td></tr>
<tr><td>installed package and binary</td><td>delphi-3bda: dpkg -l tron; /var/log/apt/history.log; /opt/positron/bin/rinzler (objdump, strings, nm, sha256sum, ldd)</td></tr>
<tr><td>2026-09-15 package binary</td><td>delphi-3bda: dpkg-deb --fsys-tarfile /var/cache/apt/archives/tron_2026.09.14-875cd228_amd64.deb | tar -xO ./opt/positron/bin/rinzler (streamed, nothing written on the host), then objdump and strings</td></tr>
<tr><td>control binaries</td><td>delphi-3bda: /var/tmp/jhan/tron-p3879/gen/runtron, /var/tmp/jhan/tron-p0perf13/gen/rinzler, /var/tmp/jhan/tron-pre3879/gen/runtron (CMakeCache.txt checked for TRON_AMX_DISPATCH)</td></tr>
<tr><td>journal</td><td>delphi-3bda: sudo journalctl -u rinzler@0..3 --since "2026-09-1N 03:30:00 UTC" --until "2026-09-1N 13:30:00 UTC"</td></tr>
<tr><td>merge facts</td><td>gh pr view 3879 (mergedAt {m["merged_at"]}); git log --first-parent origin/main; git merge-base --is-ancestor</td></tr>
<tr><td>AMX gain measurements</td><td>PR3879/more-testing/round-1 (2026-09-05, CI harness, 8 users, one engine): llama-3.1-8b-good tp2 +13.9%, mixtral -0.2%; Sunday-CI-layout-results.html (2026-09-13, nightly layout, qwen only)</td></tr>
<tr><td>AMD fallback</td><td>andoria-AMD-machine-test.md (2026-09-11, andoria-06)</td></tr>
</table></div>
</main>
"""
    OUT.write_text(html)
    bad = [c for c in html if ord(c) > 126]
    print("wrote", OUT, len(html), "bytes; non-ascii chars:", len(bad))
    if bad: sys.exit(1)

if __name__ == "__main__":
    main()
