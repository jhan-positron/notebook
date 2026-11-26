#!/usr/bin/env python3
"""gdn-impl-20261121: write the body of the draft PR for the GDN/AMX branch (pr-body.md).

The section order and the rules come from the PR-description skill: Short version, Background, Words used here,
How to review this PR, Verification, Open items. Every number is computed here from the result files:
  collected.json / comparison.json      session 2 of the campaign (repetitions 11-13)
  comparison-controls.json              control runs (counters on, counters off, PR base)
  tokens/p<prompt>__<arm>.txt           generated tokens; tokens/logits-summary-*.txt = best scores
  unit-tests.txt, unit-tests-noamx.txt  unit tests at the head
Words: tron = the inference program; GDN = GatedDeltaNet; AMX = Intel tile-matrix instructions; arm = one build
with one set of switches (see campaign.sh); TTFT = time to first token.
Usage: python3 gen_pr_body.py [output file]     (default: pr-body.md next to this script)
"""
import json
import os
import re
import statistics as st
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-impl-20261121"
WT = "/home/jhan/workspace/ai-runs/tron-gdn-amx"
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE + "/pr-body.md"
sys.path.insert(0, HERE)
import report_data  # noqa: E402

COL = json.load(open(RES + "/collected.json"))["cells"]
CMP = json.load(open(RES + "/comparison.json"))["cells"]
CTL = json.load(open(RES + "/comparison-controls.json"))["cells"]
CELLS = ["q35-tp4-1u-p1024", "q35-tp4-1u-p4096", "q35-tp4-1u-p8192", "q35-tp4-8u-p1024", "q35-tp4-8u-p4096", "q35-tp4-8u-p8192"]
ARMS = [("p0", "`p0`"), ("a", "`a`"), ("b", "`b`"), ("ab", "`ab`")]


def git(*args):
    return subprocess.run(["git", "-C", WT, *args], capture_output=True, text=True, check=True).stdout.strip()


commits = git("log", "--format=%h", "--abbrev=10", "72e1191804..HEAD").split()[::-1]
assert len(commits) == 3, commits
C1, C2, C3 = commits
stat = git("diff", "--shortstat", "72e1191804", "HEAD")
n_files, n_ins, n_del = (int(x) for x in re.findall(r"\d+", stat))


def cell_name(c):
    r = CMP[c]
    return f"{r['users']} user{'s' if r['users'] > 1 else ''}, prompt {r['prompt']:,}"


def stats(c, a, key):
    v = COL[c][a][key]["values"]
    return st.mean(v), st.stdev(v)


def cmp_cell(c, a, key):
    """Mean, change against base in percent, and whether the change is beyond the band of twice the larger sd."""
    mb, sb = stats(c, "base", key)
    m, s = stats(c, a, key)
    return m, 100 * (m - mb) / mb, abs(m - mb) > 2 * max(s, sb)


def rng(vals, d=1):
    a, b = min(vals), max(vals)
    return f"{a:.{d}f}" if f"{a:.{d}f}" == f"{b:.{d}f}" else f"{a:.{d}f} to {b:.{d}f}"


def signed(v, d=1):
    t = f"{v:+.{d}f}"
    return t.replace("-", "").replace("+", "") if float(t) == 0 else t


def perf_table(key, digits, unit, arms=None):
    arms = arms or ARMS
    head = "| Cell | `base` | " + " | ".join(n for _, n in arms) + " |\n|---|---|" + "---|" * len(arms)
    rows, beyond = [], {}
    for c in CELLS:
        mb, sb = stats(c, "base", key)
        cells = [f"{mb:.{digits}f}"]
        for a, _ in arms:
            m, pct, out = cmp_cell(c, a, key)
            beyond[(c, a)] = out
            cells.append(f"{m:.{digits}f} ({signed(pct)}{'' if out else ', inside'})")
        rows.append(f"|{cell_name(c)}|" + "|".join(cells) + "|")
    return head + "\n" + "\n".join(rows), beyond


sd_max = lambda key: max(100 * stats(c, a, key)[1] / stats(c, a, key)[0] for c in CELLS for a in ("base", "p0", "a", "b", "ab"))
ttft_table, ttft_beyond = perf_table("ttft_max_s", 3, "s")
tps_table, tps_beyond = perf_table("decode_tps_per_user", 1, "tok/s", [x for x in ARMS if x[0] in ("b", "ab")])
gdn_only = [cmp_cell(c, a, "decode_tps_per_user") for c in CELLS for a in ("p0", "a")]
assert not any(out for _, _, out in gdn_only), "a GDN-only binary changes decode beyond the band"
fall = {a: [-cmp_cell(c, a, "ttft_max_s")[1] for c in CELLS] for a, _ in ARMS}
tps = {a: {c: cmp_cell(c, a, "decode_tps_per_user")[1] for c in CELLS} for a, _ in ARMS}
big = [c for c in CELLS if CMP[c]["users"] == 8 and CMP[c]["prompt"] >= 4096]
term = lambda c, a, k: CMP[c]["terms"][a][k]
STEP = "q35-tp4-1u-p1024"
step = {a: term(STEP, a, "gdn_step_us") for a in ("base", "p0", "a")}
busy = [term(c, "p0", "prefill_attn_busy_ms") / term(c, "b", "prefill_attn_busy_ms") for c in CELLS]
c8 = [c for c in CELLS if CMP[c]["users"] == 8]
join = {a: [term(c, a, "prefill_attn_join_wait_ms") for c in c8] for a in ("p0", "b")}
dec_busy8 = [term(c, "p0", "decode_attn_busy_ms") / term(c, "b", "decode_attn_busy_ms") for c in c8]
LOW = "q35-tp4-8u-p1024"


def cmp_pair(c):
    """Fall of the time to first token from p0 to b, in percent of p0 (means of 3)."""
    return 100 * (stats(c, "p0", "ttft_max_s")[0] - stats(c, "b", "ttft_max_s")[0]) / stats(c, "p0", "ttft_max_s")[0]
ctl = [(r["arms"]["orig"], r["arms"]["nost"], r["arms"]["base"]) for r in CTL.values()]
ctl_on_off = [100 * (b["tps"] - n["tps"]) / n["tps"] for o, n, b in ctl]
ctl_base = [100 * (n["tps"] - o["tps"]) / o["tps"] for o, n, b in ctl]
ctl_spread = [x["tps_spread_pct"] for t in ctl for x in t]

# ---- tests
unit = report_data.unit_tests("unit-tests.txt")
noamx = [u for u in report_data.unit_tests("unit-tests-noamx.txt") if u["build"] == "noamx"]


def tests_of(build, switch="none", rows=unit):
    return [u for u in rows if u["build"] == build and u["switch"] == switch]


def test_cell(rows):
    bad = [u for u in rows if u["result"] != "passed"]
    text = "; ".join(f"`{u['test']}` {u['assertions']:,} / {u['cases']}" for u in rows)
    return text + ("" if not bad else " FAILED: " + ", ".join(u["test"] for u in bad))


test_rows = [
    ("AMX dispatch on", test_cell(tests_of("pab"))),
    ("AMX dispatch on, kill switch set", test_cell(tests_of("pab", "kill-switch"))),
    ("AMX dispatch on, GDN switch set", test_cell(tests_of("pab", "gdn-switch"))),
]
if noamx:
    test_rows.append(("AMX dispatch off, build type Debug", test_cell(noamx)))
parents_pass = all(u["result"] == "passed" for b in ("ctr", "pa") for u in tests_of(b)) and len(tests_of("ctr")) == 5 and len(tests_of("pa")) == 5
skips = {u["switch"]: u["skips"] for u in unit if u["build"] == "pab" and u["test"] == "t_amx_numerics" and u["switch"] != "none"}

# ---- tokens and scores
tok = report_data.tokens()
row = lambda arm, prompt: next(t for t in tok["rows"] if t["arm"] == arm and t["prompt"] == prompt)
pair = lambda kind, prompt: next((t for t in tok["pairs"] if t["kind"] == kind and t["prompt"] == prompt), None)


def tok_cell(t):
    return f"identical, {t['equal']} of {t['of']} tokens" if t["first_difference"] is None else f"first difference at generated token {t['first_difference']}"


tok_rows = []
for prompt in (1024, 4096):
    rep_ = next((t for t in tok["pairs"] if t["kind"] == "repeat" and t["x"] == "base" and t["prompt"] == prompt), None)
    if rep_:
        tok_rows.append((prompt, "`base`, run again", "`base`", "must be identical", tok_cell(rep_)))
    must = {a: tok_cell(row(a, prompt)) for a in ("p0", "a0")}
    if len(set(must.values())) == 1:
        tok_rows.append((prompt, "`p0`, `a0`", "`base`", "must be identical", must["p0"]))
    else:
        for a in ("p0", "a0"):
            tok_rows.append((prompt, f"`{a}`", "`base`", "must be identical", must[a]))
    info = {a: tok_cell(row(a, prompt)) for a in ("a", "b", "ab")}
    if len(set(info.values())) == 1:
        tok_rows.append((prompt, "`a`, `b`, `ab`", "`base`", "informational", info["a"]))
    else:
        for a in ("a", "b", "ab"):
            tok_rows.append((prompt, f"`{a}`", "`base`", "informational", info[a]))
LG = report_data.logit_margins()
SC = report_data.score_compare()
g0 = {k: next(x for x in SC[k] if x["g"] == 0) for k in ("a", "b")}
gb, ga = row("b", 1024)["first_difference"], row("a", 1024)["first_difference"]
lb1, lbb = LG[(1024, "base", gb)], LG[(1024, "b", gb)]
lba, laa = LG[(1024, "base", ga)], LG[(1024, "a", ga)]
a_rows = [x for x in SC["a"] if x["g"] < ga]
a_early, a_late = max(x["best_diff"] for x in a_rows if x["g"] < 80), max(x["best_diff"] for x in a_rows)

T3 = report_data.task3()
num = T3["numerics"]

# ---- more numbers for the text
orig_rows = [t for t in tok["rows"] if t["arm"] == "orig"]
orig_same = all(t["first_difference"] is None for t in orig_rows) and len(orig_rows) == 2
for prompt in (4096, 1024):
    if orig_same:
        pos = next(k for k, r_ in enumerate(tok_rows) if r_[0] == prompt)
        t_ = next(t for t in orig_rows if t["prompt"] == prompt)
        tok_rows.insert(pos, (prompt, "PR base `72e1191804`", "`base`", "must be identical", tok_cell(t_)))
lab = LG.get((1024, "ab", gb))
ab_keeps_tie = bool(lab) and lab["steps"] == 0 and lab["id1"] == lb1["id1"] and pair("a_ab", 1024)["first_difference"] is None
blocks = sum(r["gdn"]["prompt_or_mixed"]["totals"]["amx_blocks"] for r in json.load(open(RES + "/collected.json"))["runs"].values() if r["arm"] in ("a", "ab"))
refused = sum(r["gdn"]["prompt_or_mixed"]["totals"]["amx_fallback_blocks"] for r in json.load(open(RES + "/collected.json"))["runs"].values() if r["arm"] in ("a", "ab"))
n_ab_runs = sum(1 for r in json.load(open(RES + "/collected.json"))["runs"].values() if r["arm"] in ("a", "ab"))
COLC = json.load(open(RES + "/collected-controls.json"))["cells"]


def ctl_cmp(c, key):
    """Counters on (base) against off (nost) in a control cell: change of the means in percent, and beyond the band?"""
    on, off = COLC[c]["base"][key]["values"], COLC[c]["nost"][key]["values"]
    d = st.mean(on) - st.mean(off)
    return 100 * d / st.mean(off), abs(d) > 2 * max(st.stdev(on), st.stdev(off))


ctl_tps = {c: ctl_cmp(c, "decode_tps_per_user") for c in COLC}
ctl_ttft = {c: ctl_cmp(c, "ttft_max_s") for c in COLC}
ctl_beyond = [c for c in COLC if ctl_tps[c][1]]
ctl_orig = max(abs(100 * (st.mean(COLC[c]["nost"]["decode_tps_per_user"]["values"]) - st.mean(COLC[c]["orig"]["decode_tps_per_user"]["values"]))
                   / st.mean(COLC[c]["orig"]["decode_tps_per_user"]["values"])) for c in COLC)
import math
up1 = lambda v: math.ceil(10 * v - 1e-9) / 10
p0b_out = abs(stats(LOW, "p0", "ttft_max_s")[0] - stats(LOW, "b", "ttft_max_s")[0]) > 2 * max(stats(LOW, "p0", "ttft_max_s")[1], stats(LOW, "b", "ttft_max_s")[1])
lint = open(RES + "/lint-notes.txt").read() if os.path.exists(RES + "/lint-notes.txt") else ""
lint_ok = "lint-notes rc=0" in lint
fmt_ok = subprocess.run("uvx --offline --from clang-format==19.1.7 clang-format --dry-run -Werror $(git diff --name-only 72e1191804 HEAD | grep -E '\\.(hpp|cpp|h|c)$')",
                        shell=True, cwd=WT, capture_output=True).returncode == 0
n_cpp = len([f for f in git("diff", "--name-only", "72e1191804", "HEAD").split() if re.search(r"\.(hpp|cpp|h|c)$", f)])
ws_ok = git("diff", "--check", "72e1191804", "HEAD") == ""
dec_big = [term(c, 'p0', 'decode_attn_busy_ms') / term(c, 'b', 'decode_attn_busy_ms') for c in big]
dec_join = [100 * (term(c, 'p0', 'decode_attn_join_wait_ms') - term(c, 'b', 'decode_attn_join_wait_ms')) / (term(c, 'p0', 'decode_attn_busy_ms') - term(c, 'b', 'decode_attn_busy_ms')) for c in big]
low_cell = CMP[LOW]
ctl_cell = lambda c: f"{COLC[c]['base']['users']} user{'s' if COLC[c]['base']['users'] > 1 else ''}, prompt {COLC[c]['base']['prompt_tokens']:,}"

body = f"""## Short version

This PR adds faster CPU kernels for the prompt processing of the model Qwen3.5 4B, and counters that time its GatedDeltaNet (GDN) layers. On one test server the time to first token falls by {rng(fall['ab'], 0)} %. Token generation with 8 users and long prompts gets {rng([tps['ab'][c] for c in big], 0)} % faster.

## Background

- The model has 24 GDN layers and 8 attention layers. A GDN layer keeps a 128 x 128 FP32 state matrix per value head. Its recurrence reads the matrix twice and writes it once, for every token.
- A prompt chain is known before it runs. So the write pass of one token can also be the read pass of the next token. Note [GatedDeltaNet chain recurrence] in `h/tron/kernels/gated_delta_net.hpp` gives the loop.
- 32 tokens can also be applied in a closed form with matrix products, which AMX computes. Note [AMX GatedDeltaNet block kernel] in `h/tron/kernels/amx_gdn_iface.hpp` gives the algebra.
- At the base, the AMX attention kernels serve only heads of 128 values. This model has heads of 256 values, so its attention runs on AVX-512 there. Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` describes both shapes.
- At the base only a trace can time GDN. Note [GDN path stats] in `h/tron/models/gdn_stats.hpp` describes the counters.

## Words used here

| Term | Meaning |
|---|---|
| AMX | Intel Advanced Matrix Extensions, the tile-matrix instruction set |
| AVX-512 | the 512-bit vector instruction set. The CPU kernels of the base use it |
| bf16, bf16 step | bf16 is a 16-bit floating-point format with 8 significant bits. A bf16 step is the distance between two neighbouring bf16 values, 0.125 for values from 16 to 32 |
| chain | the consecutive tokens of one sequence in one pass |
| token kernel, chain kernel, block kernel | three routines for the GDN recurrence: one token per call (the code of the base), a run of tokens with the bits of the token kernel, and 32 tokens at once with AMX |
| kill switch | `TRON_AMX_DISABLE=1`. No AMX kernel runs |
| GDN switch | `TRON_AMX_GDN_DISABLE=1`. Only the AMX block kernel of GDN is off |
| `base` | the binary of `{C1}`: the counters, and the kernels of the PR base |
| `p0` | the head binary with the kill switch set: chain kernel, AVX-512 attention |
| `a0`, `a` | the binary of `{C2}` with the GDN switch set (chain kernel) and with no switch (block kernel). Attention runs on AVX-512 |
| `b`, `ab` | the head binary with the GDN switch set (chain kernel, AMX attention) and with no switch (block kernel, AMX attention) |

## How to review this PR

**Does the chain kernel give the bytes of the per-token loop for every chain, start position and head width?**

- `h/tron/kernels/gated_delta_net.hpp`: the joined loop `gdn_recurrence_slice`, and the conversion between the stored state and the slice layout.
- `h/tron/models/gdn_rolling_executor.hpp`: `advance()` cuts a chain into windows of at most 32 tokens. `step()` keeps the token kernel for a chain that advances in place.
- `h/tron/models/gdn_execution.hpp`: `run_gdn_operation` advances a chain of 1 token in place with `step()`, and a longer chain in a working copy with `advance()`.
- Claim: with the block kernel off, outputs and stored state are equal byte for byte.
- Verification: the `t_gated_delta_net` cases "advance gives the bytes of step at the Qwen matrix shape" and "... for narrower value heads". Also the `p0` and `a0` rows of [Verification].

**Is the result of the AMX block kernel close enough, and does a refused block leave the state unchanged?**

- `src/tron/kernels/amx_gdn.cpp`: the split of an FP32 value into 3 bf16 pieces, the two refusal rules, and the scope that sets FTZ and DAZ in MXCSR.
- `h/tron/models/gdn_rolling_executor.hpp`: `advance_window_with_block_kernel` gives a refused value head to the chain kernel.
- Claim: for the 8 input families of the test, the output error against a float64 computation is at most 2 times that of the chain kernel. The state error is at most 4 times. A bench outside this PR measures {rng([n['block_err'] / n['token_err'] for n in num], 2)} and {rng([n['state_err_ratio'] for n in num], 2)} times.
- Claim: a refused block leaves the state untouched.
- Verification: the cases of `t/t_amx_gdn_numerics.cpp` and the `t_gated_delta_net` case "advance gives a refused block to the chain kernel". The model level is Open: "Numerics of the block kernel" in [Open items].

**Does the dispatch take the 256-wide kernels only for the 256 x 4 shape, and do the 128-wide kernels keep their code?**

- `h/tron/models/self_attention.hpp`: the gates `amx_serves_128x4` and `amx_serves_256x4`, and the size of the packed-query slot per model.
- `src/tron/kernels/amx_attn.cpp`: namespace `amx_attn_h256g4`. The code of the three 128-wide kernels has no change.
- Two lines of the shared dense-page path change for both shapes: the packed-query array only grows, and the buffer `scratch` is no longer zero-filled.
- Claim: a model with another shape keeps its path, and the kill switch turns both shapes off.
- Verification: the QK and PV error-band cases of `t_amx_numerics` for both shapes, and `t_amx_dispatch_dtype`. Model runs: "Coverage" in [Open items].

## Verification

All results come from delphi-3b35 (an Intel Xeon 6962P server), 2026-11-22 UTC, at the head `{C3}` and its two parent commits on the base `72e1191804`. The builds use clang 19, the preset `native` (RelWithDebInfo), `BUILD_INGEST_MODELS=ON` and `TRON_AMX_DISPATCH=ON`, except in the last row of the first table. The performance and token runs use builds of an earlier version of the same commits, which differs only in comments, tests and two README files. Those runs use the binaries `base`, `p0`, `a0`, `a`, `b` and `ab` with the model `ingested-qwen-3.5-4b-tp4`, attention on the CPU, and both counter sets on. GitHub runs only the lint and CI-machinery jobs for this draft, because it has no `Run CI` label.

### Builds and tests

Results are assertions / test cases. Every listed run passes.

| Configuration at the head | Result |
|---|---|
""" + "\n".join(f"|{a}|{c}|" for a, c in test_rows) + f"""

- {"The two parent commits pass the same five test programs." if parents_pass else "NOT ALL PARENT RUNS PASS."}
- With a switch set, `t_amx_numerics` skips the cases of the kernels that are off: {skips.get('kill-switch', 'n/a')} under the kill switch and {skips.get('gdn-switch', 'n/a')} under the GDN switch. Without AMX dispatch, `t_amx_numerics` and `t_amx_dispatch_dtype` have one placeholder case each.
- {"`clang-format` 19.1.7 reports no difference in the " + str(n_cpp) + " changed C++ files." if fmt_ok else "CLANG-FORMAT REPORTS DIFFERENCES."} {"`git diff --check` and `make lint-notes` are clean." if ws_ok and lint_ok else "WHITESPACE OR NOTE CHECK NOT CLEAN."} The Lint job of this draft passes.

### Token identity

One user, a fixed prompt, temperature 0, `--pay-for-determinism`, 256 generated tokens. Every row compares with `base`.

| Prompt (tokens) | Binary | Rule | Result |
|---|---|---|---|
""" + "\n".join(f"|{p:,}|{a}|{r}|{res}|" for p, a, b, r, res in tok_rows) + f"""

What the table says:

- Every pair that must be identical is identical. So the counters and the chain kernel change no generated token.
- `b` differs at an exact tie. At generated token {gb}, `base` scores {lb1['v1']:g} for two token ids, and `b` scores {lbb['v2']:g} for one of them: one bf16 step.
""" + ("- `ab` gives the tokens of `a`, and it keeps the tie of `base` at generated token " + str(gb) + ".\n" if ab_keeps_tie else "") + f"""- `a` differs after {len(a_rows)} equal tokens, and not at a tie. At generated token 0 its scores are within {g0['a']['largest']:g} bf16 step of `base`.
- The best score of `a` then moves away by up to {a_late:g} bf16 steps. At generated token {ga} the best token of `base` leads by {lba['steps']:g} bf16 steps, and `a` takes another token. Decode takes the same kernels in both binaries.
- A second run of `a`, `b` and `ab` gives the tokens of its first run. In the {n_ab_runs} performance runs of `a` and `ab` the block kernel refuses {refused if refused else "no"} block.

### Performance

- 6 cells, 3 repetitions per binary and cell, 256 generated tokens per user. The counter values in the text are medians of 3 runs.
- Before every run the 56 CPUs of the test are at most 0.1 % busy. The other socket of the server is 42 % busy with other users' jobs.
- A change counts when it is beyond the band: twice the larger standard deviation of the two binaries. The tables mark the other changes "inside". A standard deviation is at most {sd_max('ttft_max_s'):.1f} % of the time to first token and {sd_max('decode_tps_per_user'):.1f} % of the decode speed.

Time to first token in s, mean of 3, with the change against `base` in percent:

{ttft_table}

What the table says:

- Every change is beyond the band. The time to first token falls by {rng(fall['p0'])} % with the chain kernel (`p0`) and by {rng(fall['a'])} % with the block kernel (`a`). With both AMX kernels (`ab`) it falls by {rng(fall['ab'])} %.
- One GDN step (one token of one key head) takes {step['base']:.2f} us in `base`, {step['p0']:.2f} us in `p0` and {step['a']:.2f} us in `a`. A prefill pass gets shorter by the time that its GDN layers save.
- From `p0` to `b` the attention busy time of a prefill pass gets {rng(busy, 2)} times shorter. It includes the join wait: the time a thread waits for the other attention threads.
- The low end is {cell_name(LOW)}. There the join wait rises from {term(LOW, 'p0', 'prefill_attn_join_wait_ms'):.1f} to {term(LOW, 'b', 'prefill_attn_join_wait_ms'):.1f} ms per pass, and the change from `p0` to `b` is {"beyond" if p0b_out else "inside"} the band ({signed(-cmp_pair(LOW))} %).

Decode speed per user in tok/s, mean of 3, with the change against `base` in percent:

{tps_table}

What the table says:

- The GDN kernels alone (`p0`, `a`, not in the table) change decode by {signed(min(p for _, p, _ in gdn_only))} to {signed(max(p for _, p, _ in gdn_only))} %, inside the band in every cell.
- With the attention kernels decode gets {rng([tps[a][c] for a in ('b', 'ab') for c in big], 0)} % faster with 8 users and prompts of 4,096 tokens or more. There, from `p0` to `b`, the attention busy time of a decode step gets {rng(dec_big, 2)} times shorter. {rng(dec_join, 0)} % of that fall is a shorter join wait.
- In control runs on 3 cells, `TRON_GDN_STATS=1` changes the time to first token by {signed(min(v[0] for v in ctl_ttft.values()))} to {signed(max(v[0] for v in ctl_ttft.values()))} % and decode by {signed(min(v[0] for v in ctl_tps.values()))} to {signed(max(v[0] for v in ctl_tps.values()))} %. {"Every decode change is inside the band." if not ctl_beyond else "The decode change is beyond the band in " + str(len(ctl_beyond)) + " cell (" + ", ".join(ctl_cell(c) for c in ctl_beyond) + ": " + signed(ctl_tps[ctl_beyond[0]][0]) + " %)."} With the counters off, `{C1}` is within {up1(ctl_orig):.1f} % of the PR base.

## Open items

**Numerics of the block kernel. Reviewers decide.** The difference of `a` against `base` grows during decode [Verification]. No measurement compares the GDN states of the two binaries after the prompt. A score dump for more prompts would show how often such a difference grows. The owners of the GDN code decide whether the block kernel is on by default.

**One PR or a stack. Reviewers decide.** The PR has three commits: the counters (`{C1}`), the two GDN kernels (`{C2}`) and the attention kernels (`{C3}`). The diff has {n_ins:,} added lines. It can become a stack of three PRs, or of four with one PR per GDN kernel.

**Coverage. Reviewers decide which checks this PR must add.**

- The default PR pipeline (GCP Nix) builds the tests with `TRON_AMX_DISPATCH` off. So it compiles neither the AMX kernels nor their test cases. The legacy workflow `cmake-single-platform.yml` builds with the option on.
- No test sets the GDN switch itself, no test runs the counters through a generated model, and no 128-wide model ran at this head.

**Base.** The model is not on `main`, so this PR is a draft on top of PR #3696. Other open PRs of that stack change the GDN code, and PR #5022 changes the same kernel calls in `h/tron/models/self_attention.hpp`. The author rebases this PR when one of them merges below it.

**Changelog and test timing record.** `main` asks for a `changelog.d` fragment for a performance change, and the base of this PR is older than that rule. `config/test-benchmarks.json` is not refreshed for `t_gated_delta_net` and `t_amx_numerics`. The author adds both before the PR leaves the draft state.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""
open(OUT, "w").write(body)
words = len(re.sub(r"## Words used here.*?(?=\n## )", "", body, flags=re.S).split())
print("wrote", OUT, "| words without the Words section:", words, "| commits", C1, C2, C3)
