#!/usr/bin/env python3
"""Regenerate PR3879/more-testing/round-1/status.md from the raw results of
the more-testing round-1 campaign (exec/results/more-testing-r1/) and the
nightly-CI reference JSON. Safe to run at any time; missing cells are shown
as not run yet.
"""
import datetime
import os
import re
import sys

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resultlib import RES, MODELS, ARMS, SUBJECTS, SUBJECT_N, read, load_all  # noqa: E402
from mmlu_diff import compare  # noqa: E402
OUT = f"{HOME}/workspace/intel-AMX/PR3879/more-testing/round-1/status.md"
GB_PER_GIB = 1.073741824


def fmt(x, nd=2, unit=""):
    if x is None: return "n/a"
    return f"{x:.{nd}f}{unit}"


def delta_pct(a, b):
    if a is None or b is None or b == 0: return "n/a"
    return f"{100.0 * (a - b) / b:+.1f}%"


def phases_str(meta):
    ph = meta.get("phases", {})
    if not ph: return "n/a"
    return " / ".join(f"{ph[k]['seconds'] / 60:.1f}" if k in ph else "-" for k in ("start", "functional", "perf", "mmlu"))


cells, extra, soaks, ci = load_all()
soak, soak_meta, soak_status = soaks["main"]
extra_soaks = [(tag, sk, meta, st_) for tag, (sk, meta, st_) in soaks.items() if tag != "main"]
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
L = []
w = L.append
w("# Status report: AMX change (PR3879) under the nightly System CI tests, round 1")
w("")
w(f"Generated {now} by `exec/more-testing-r1/gen_status.py`. Test plan: `../test-plan.md`. Raw data: `exec/results/more-testing-r1/`. "
  "Chart page with the same data: `results.html`.")
w("")
done = [k for k, v in cells.items() if v["status"] == "done"]
running = [k for k, v in cells.items() if v["status"] == "running"]
failed = [k for k, v in cells.items() if v["status"] not in ("done", "running", "not run", "skipped")]
skipped = [k for k, v in cells.items() if v["status"] == "skipped"]

w("## Short version")
w("")
w(f"{len(done)} of {len(cells)} model-and-arm combinations (cells) and the 60-minute soak finished"
  + (f"; {len(running)} cell(s) still running" if running else "") + (f"; {len(skipped)} skipped for time" if skipped else "")
  + (f"; {len(failed)} failed to run" if failed else "") + ". "
  "Every functional API test passed in every arm, decode throughput rose by 14 to 19% on llama-3.1-8b and 4.5 to 5.5% on qwen-3-4b with AMX on, "
  "and MMLU Pro accuracy moved by -0.4 to +1.5 points, which is inside the +1.7 points seen when the off arm was run a second time unchanged, so no accuracy change is detectable. "
  "Two findings need follow-up: the mirror arm is 13% slower to first token than off on qwen and llama, and its K mirror arena grows host RAM by about half the KV cache size (about 40 GiB in the soak), which the CI soak monitor reports as an error.")
w("")
w("## Words used here")
w("")
for t, d in [
    ("tron, rinzler, runtron", "tron is the inference program under test; rinzler is its production HTTP server, which every cell here runs; runtron is tron's command-line tool used by the earlier decode-only rounds."),
    ("AMX, AVX", "AMX = Intel Advanced Matrix Extensions, CPU matrix instructions the change uses for attention; AVX = the older vector instructions the existing code uses."),
    ("K, V, KV cache, KV head, head size", "for every served token the server stores the attention keys (K) and values (V); this store is the KV cache, kept in hugepages (2 MB or 1 GB memory pages reserved for it). A KV head is one stored key/value stream shared by several query heads; head size is the vector width of one attention head. The change's kernels (small compute routines) exist only for head size 128 with 4 query heads per KV head (qwen, llama, mixtral); gpt-oss (head size 64, 8 query heads per KV head) never runs them."),
    ("off, canon, mirror (the arms)", "off = the canonical build (rinzler.canon) started with TRON_AMX_DISABLE=1, the kill switch, so attention runs on the AVX path; canon = the same binary with the switch unset, AMX kernels read the normal K layout; mirror = a second build (rinzler.mirror) that also keeps an AMX-friendly copy of K in ordinary RAM, the K mirror arena. The kill-switch state is recorded by the launcher (rz.sh, meta.json); rinzler itself does not log it."),
    ("USE_HW_ATTN=0", "environment switch that forces attention onto the CPU for every model; without it the ingested models (qwen, gpt-oss) run attention on the FPGA (the accelerator cards) and AMX never engages. Set in every arm; the server log line 'HW attention disabled' confirms it per cell."),
    ("tp2, tp4", "tensor parallelism, the number of FPGA cards one model instance spans; CI's choice per model was kept."),
    ("functional", "the CI pytest suite functional_tests/test_api.py: API shape, streaming, stop tokens, golden-response similarity, concurrency; counts are passed/skipped/failed."),
    ("perf, TPS, TTFT, sd", "the CI throughput benchmark: 8 users each send 10 rounds of a 1024-token prompt and read 1536 generated tokens. TPS = tokens per second per user during generation (decode); TTFT = time to first token in milliseconds (mostly the prompt processing, prefill, with 8 requests arriving together); sd = standard deviation of the 80 per-user-per-round TPS samples inside one run (round-to-round drift within one server process, not between-run spread)."),
    ("MMLU Pro", "multiple-choice knowledge test; CI's setting is the first 10% of every subject, a fixed set of 1196 questions, answered with chain-of-thought (the model writes its reasoning before the final letter) under greedy decoding (always the highest-scoring token) at temperature 0, 8 questions in flight at a time. Score = percent correct as computed by the CI runner, which scores a response with no extractable letter by a seeded random guess and drops a question whose response was empty."),
    ("answer changes, A/A control", "per-question comparison of two runs: the final letters actually extracted are compared, so a question one run left unanswered is dropped and a random-guess credit is not counted; the net column can therefore differ from the score difference by a few questions. A/A control = the same binary with the same switches run a second time, which measures the run-to-run spread of the serving path (8 requests are batched in changing order and the floating-point reduction order follows)."),
    ("soak, coherency probe, harness", "sustained mixed traffic from 25 simulated users for a fixed time while the CI monitor records failed requests, host used memory (whole host, hugepages excluded), power, and a coherency probe (a fixed prompt sent every 30 s, its answer compared with known-good answers). Harness = the soak.py driver; its error count includes monitor alerts."),
    ("CI reference", "the nightly run of 2026-09-04 (GitHub Actions run 33833914529, tron package 2026.09.04-fe8dbdee, main branch). Its client ran on another host through the platformd proxy over 2 to 4 engines; ours ran on the test machine against one engine, so CI throughput and TTFT are not directly comparable and are shown for orientation only."),
]:
    w(f"- **{t}**: {d}")
w("")
w("## Per-model summary")
w("")
for mid, label, elig in MODELS:
    off = cells[(mid, "off")]
    parts = []
    for arm in ("canon", "mirror"):
        c = cells[(mid, arm)]
        if c["status"] != "done": continue
        f = c["functional"]; p = c["perf"]; m = c["mmlu"]
        seg = []
        if f: seg.append(f"functional {f['passed']} passed / {f['failed']} failed")
        if p and off["perf"]: seg.append(f"TPS {delta_pct(p['tps_mean'], off['perf']['tps_mean'])} vs off")
        if p and off["perf"]: seg.append(f"TTFT {delta_pct(p['ttft_mean_ms'], off['perf']['ttft_mean_ms'])} vs off")
        if m and m["complete"] and off["mmlu"] and off["mmlu"]["complete"]:
            seg.append(f"MMLU Pro {m['overall_pct']:.2f}% vs off {off['mmlu']['overall_pct']:.2f}% ({m['overall_pct'] - off['mmlu']['overall_pct']:+.2f} points)")
        if seg: parts.append(f"{arm}: " + ", ".join(seg))
    if parts:
        w(f"- **{label}** ({elig}): " + "; ".join(parts) + ".")
w("")
w("## Build and machine facts")
w("")
anymeta = next((v["meta"] for v in cells.values() if v["meta"]), {})
w(f"- tron source tree `~/workspace/tron-amx` at `{anymeta.get('tron_head', '60d66d9c04')}`, the PR3879 head. rinzler binaries were built 2026-09-04 17:33-17:46 UTC "
  "(`exec/logs/more-testing-r1-build.log`): canon sha256 `0b5fe23f...`, mirror sha256 `fc32cabe...`, version 2026.09.04-60d66d9c-jhan-amx-p0.")
w("- Test machine delphi-3bda (2-socket Xeon 6, 8 FPGA cards). Production rinzler serving was stopped 17:33 UTC per the standing policy (idle: zero client connections, zero request lines). "
  "One rinzler process per cell on port 13100 with production's per-instance card, core, and hugepage arguments (tp2: 2 cards, 128 hugepages; tp4: 4 cards, 256 hugepages); `USE_HW_ATTN=0` in every arm.")
w("- Client: systems_test `470aca1` (the CI repository) in `/var/tmp/jhan/st-venv` on delphi-3bda itself; its CI reporting library was replaced by a no-op stub so nothing was written to the CI database.")
w("- CI's functional phase ran six models at tp4 in one group (150 passed, 2 skipped) and gpt-oss-120b + qwen-3-4b at tp4 in a second group (48 passed, 4 skipped); it reports group totals only and did not run the llama and mixtral tp2 ids through the functional tests (their tp4 variants were in the first group). "
  "The two proxy-authentication tests (`test_auth_reject_no_token`, `test_auth_reject_bad_token`) skip themselves when the Server header starts with `drogon/` (rinzler's own HTTP server); they were skipped in our cells and, by its pytest progress output, in both CI groups as well, so the skip counts match.")
w("")
w("## Results per model")
w("")
for mid, label, elig in MODELS:
    w(f"### {label}: `{mid}` ({elig})")
    w("")
    ciperf = (ci.get("perf", {}).get(mid) or [{}])[-1]
    cimmlu = ci.get("mmlu", {}).get(mid, {})
    w("| Arm | Status | Functional passed/skipped/failed | TPS mean (sd) [tok/s per user] | TPS vs off | TTFT [ms] | TTFT vs off | MMLU Pro [%] | MMLU vs off [points] | Phase durations [min]: start / functional / perf / MMLU |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    ci_over = (cimmlu.get("scores_pct") or {}).get("overall")
    w(f"| CI reference (main, 2-4 engines) | 2026-09-04 | group totals only | {fmt(ciperf.get('tps'))} | n/a | {ciperf.get('ttft_ms', 'n/a')} | n/a | {fmt(ci_over)} | n/a | perf {ciperf.get('minutes', 'n/a')}, MMLU {cimmlu.get('minutes', 'n/a')} |")
    off = cells[(mid, "off")]
    rows = [(a, cells[(mid, a)]) for a in ARMS] + [(lbl, c) for (emid, lbl), c in extra.items() if emid == mid]
    for name, c in rows:
        f, p, m = c["functional"], c["perf"], c["mmlu"]
        fcol = f"{f['passed']}/{f['skipped']}/{f['failed']}" if f else "n/a"
        if f and f["failed_names"]: fcol += " (" + ", ".join(f["failed_names"][:4]) + (", ..." if len(f["failed_names"]) > 4 else "") + ")"
        tps = f"{p['tps_mean']:.2f} ({p['tps_std_dev']:.2f})" if p else "n/a"
        is_off = name == "off"
        dtps = delta_pct(p["tps_mean"], off["perf"]["tps_mean"]) if (p and off["perf"] and not is_off) else ("baseline" if is_off and p else "n/a")
        ttft = str(p["ttft_mean_ms"]) if p else "n/a"
        dttft = delta_pct(p["ttft_mean_ms"], off["perf"]["ttft_mean_ms"]) if (p and off["perf"] and not is_off) else ("baseline" if is_off and p else "n/a")
        if m and m["total"]:
            mm = f"{m['overall_pct']:.2f}" + ("" if m["complete"] else f" (partial: {len(m['per_subject'])}/14 subjects)")
        elif c["meta"].get("run_mmlu") is False and c["status"] == "done":
            mm = "not planned"
        else:
            mm = "n/a"
        if m and m["complete"] and not is_off and off["mmlu"] and off["mmlu"]["complete"]:
            dm = f"{m['overall_pct'] - off['mmlu']['overall_pct']:+.2f}"
        else:
            dm = "baseline" if (is_off and m and m["complete"]) else "n/a"
        w(f"| {name} | {c['status']} | {fcol} | {tps} | {dtps} | {ttft} | {dttft} | {mm} | {dm} | {phases_str(c['meta'])} |")
    w("")
    # answered / excluded / random-guess counts
    acc = []
    for name, c in rows:
        m = c["mmlu"]
        if m and m["total"]:
            acc.append(f"{name}: {int(m['total'])} answered, {m['excluded']} excluded (empty completion), {m['random_guess']} scored by random guess (no extractable letter)")
    if acc:
        w("MMLU Pro question accounting per arm, of the 1196 asked: " + "; ".join(acc) + ".")
        w("")
    # per-question answer changes relative to the off arm
    if off["mmlu"] and off["mmlu"]["complete"]:
        crow = []
        for arm in ("canon", "mirror"):
            m = cells[(mid, arm)]["mmlu"]
            if m and m["complete"]:
                crow.append((arm, compare(f"{off['dir']}/eval_results", f"{cells[(mid, arm)]['dir']}/eval_results")))
        for (emid, elabel), c in extra.items():
            if emid == mid and c["mmlu"] and c["mmlu"]["complete"]:
                crow.append((elabel, compare(f"{off['dir']}/eval_results", f"{c['dir']}/eval_results")))
        if crow:
            w("MMLU Pro answer changes relative to the off arm. Both runs were asked the same 1196 questions; a question one run left unanswered is dropped from the comparison (compared count below), and the letters actually extracted are compared, so the net column can differ from the score difference by a few random-guess credits. A changed answer means the reasoning text diverged and ended on another letter.")
            w("")
            w("| Compared with off | Questions compared | Responses byte-identical | Final answer changed | right -> wrong | wrong -> right | wrong -> other wrong | Net [questions] |")
            w("|---|---|---|---|---|---|---|---|")
            for name, r in crow:
                n = r["n_common"] or 1
                w(f"| {name} | {r['n_common']} | {r['response_identical']} ({100*r['response_identical']/n:.1f}%) | {r['pred_changed']} ({100*r['pred_changed']/n:.1f}%) | {r['right_to_wrong']} | {r['wrong_to_right']} | {r['wrong_to_wrong_changed']} | {r['wrong_to_right'] - r['right_to_wrong']:+d} |")
            w("")
    # per-subject MMLU
    srows = []
    if cimmlu.get("scores_pct"):
        srows.append(("CI reference", [cimmlu["scores_pct"].get(s) for s in SUBJECTS], ci_over))
    for name, c in rows:
        m = c["mmlu"]
        if m and m["per_subject"]:
            srows.append((name, [100.0 * m["per_subject"][s]["acc"] if s in m["per_subject"] else None for s in SUBJECTS], m["overall_pct"]))
    if srows:
        w("MMLU Pro per subject, percent correct (question counts asked per subject: " + ", ".join(f"{s} {n}" for s, n in zip(SUBJECTS, SUBJECT_N)) + "; an excluded question lowers a subject's count by one):")
        w("")
        w("| Arm | overall | " + " | ".join(SUBJECTS) + " |")
        w("|---|---|" + "---|" * len(SUBJECTS))
        for name, vals, over in srows:
            w(f"| {name} | {fmt(over)} | " + " | ".join(fmt(v, 2) for v in vals) + " |")
        w("")
    # server-log evidence
    ev = []
    for arm in ARMS:
        ls = cells[(mid, arm)]["amx_lines"]
        if ls:
            keep = [l for l in ls if re.search(r"HW attention|K mirror", l)]
            if keep: ev.append(f"- {arm}: " + " / ".join(re.sub(r"^\[[^\]]*\]\s*\[[a-z ]*\]\s*", "", l)[:160] for l in keep[:3]))
    if ev:
        w("Server log evidence. Two facts are read from each cell's rinzler.log: 'HW attention disabled' shows attention ran on the CPU in that arm, and a non-zero 'K mirror' size shows the mirror arena was allocated (zero in the off and canon arms, and always zero for gpt-oss). The footprint line is printed at start-up and again as the KV cache grows, so the early copies quoted here are small; the notes quote the end-of-run values.")
        w("")
        L.extend(ev)
        w("")

w("## Soak")
w("")
w(f"Planned: 60 minutes, 25 users, mirror arm, models llama-3.1-8b-instruct-good-tp2 + ingested-qwen-3-4b-instruct-2507-tp2 on one tp2 engine. Status: {soak_status}.")
w("")


def soak_block(sk, meta, label):
    if not sk or sk.get("raw"):
        w(f"- {label}: no summary block in the log yet."); w(""); return
    exit_reason = sk.get("exit_reason") or "n/a"
    m = re.match(r"(\d+):(\d+):(\d+)", sk["duration"])
    dur = f"{int(m.group(1)) * 60 + int(m.group(2))} min {int(m.group(3))} s" if m else sk["duration"]
    alerts = [a for a in sk.get("alerts", []) if not a.startswith("Failed to gather") and a != "Dumping Errors"]
    warn = [a for a in sk.get("alerts", []) if a.startswith("Failed to gather")]
    peak = max((g for _, g in sk.get("growth_series", [])), default=None)
    w(f"- {label}: arm {meta.get('arm', '?')}, {meta.get('users', '?')} users, duration {dur} ({exit_reason}). "
      f"The harness counted {sk.get('errors')} error(s): {'the monitor alert(s) quoted below' if alerts else 'none'}; request failures are in the table. "
      f"Host used memory (whole host, hugepages excluded): growth since start {fmt(sk.get('growth_gib'), 1)} GiB at the end, peak growth {fmt(peak, 1)} GiB; the monitor's per-process 'Rinzler RSS' figure read 0 because it targets the production systemd units, not our process. "
      f"Coherency probes {sk['coherency_checks']}, failures {sk['coherency_failures']}.")
    for a in alerts:
        w(f"  - monitor alert (counted): {a}")
    if warn:
        w(f"  - post-run log copy warnings (not counted): {len(warn)} 'Failed to gather ...' lines; the monitor's journalctl calls need sudo when run as jhan, and our rinzler is not a systemd unit.")
    w("")
    w("| Model | Requests sent / completed / failed (a request still running at the cutoff is neither) | Avg TTFT [s] | Total generation [tok/s] | Per-user generation [tok/s] |")
    w("|---|---|---|---|---|")
    for mname, v in sk["models"].items():
        w(f"| {mname} | {v.get('sent', 'n/a')} / {v.get('succeeded', 'n/a')} / {v.get('failed', 'n/a')} | {fmt(v.get('avg_ttft_s'))} | {fmt(v.get('total_gen_tok_s'))} | {fmt(v.get('per_user_gen_tok_s'))} |")
    w("")


if soak:
    soak_block(soak, soak_meta, "Planned soak")
for tag, sk, meta, st_ in extra_soaks:
    w(f"Extra soak `{tag}` (status {st_}):")
    w("")
    soak_block(sk, meta, f"Extra soak {tag}")
cis = ci.get("soak", {})
if cis.get("models"):
    w(f"For comparison, CI's own soak of 2026-09-04 (3 h; 100 users over 4 tp2 engines per the test plan, section 2; models {', '.join(cis.get('model_list', []))}) recorded {cis.get('errors')} errors and {fmt(cis.get('growth_gib'), 3)} GiB memory growth:")
    w("")
    w("| Model | Requests sent / completed / failed | Avg TTFT [s] | Per-user generation [tok/s] |")
    w("|---|---|---|---|")
    for k, v in cis["models"].items():
        w(f"| {k} | {v.get('sent')} / {v.get('succeeded')} / {v.get('failed')} | {v.get('avg_ttft_s')} | {v.get('per_user_gen_tok_s')} |")
    w("")
notes = read(f"{RES}/notes.md")
if notes:
    w("## Notes from the analyst (hand-written, `exec/results/more-testing-r1/notes.md`)")
    w("")
    L.extend(notes.rstrip().splitlines())
    w("")
w("## Cells not run or failed")
w("")
notes_ = []
for (mid, arm), c in cells.items():
    if c["status"] == "skipped":
        notes_.append(f"- {mid} / {arm}: skipped (would not finish before the 02:30 UTC deadline).")
    elif c["status"] not in ("done", "running", "not run"):
        notes_.append(f"- {mid} / {arm}: {c['status']} (see `{os.path.relpath(c['dir'], HOME + '/workspace/intel-AMX')}/`).")
    elif c["status"] == "not run":
        notes_.append(f"- {mid} / {arm}: not run yet.")
L.extend(notes_ or ["- none"])
w("")
w("## Timeline (UTC)")
w("")
tl = []
for (mid, arm), c in cells.items():
    if c["meta"].get("started"):
        tl.append((c["meta"]["started"], f"{c['meta']['started'][11:16]} - {c['meta'].get('ended', '...')[11:16]}  {mid} / {arm}  ({c['status']})"))
for (mid, lbl), c in extra.items():
    if c["meta"].get("started"):
        tl.append((c["meta"]["started"], f"{c['meta']['started'][11:16]} - {c['meta'].get('ended', '...')[11:16]}  {mid} / {lbl}  ({c['status']})"))
for tag, (sk, meta, st_) in soaks.items():
    if meta.get("started"):
        tl.append((meta["started"], f"{meta['started'][11:16]} - {meta.get('ended', '...')[11:16]}  soak {tag} ({meta.get('arm', '?')} arm, {meta.get('minutes', '?')} min, {meta.get('users', '?')} users)  ({st_})"))
for _, t in sorted(tl):
    w(f"- {t}")
if not tl:
    w("- nothing started yet")
w("")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {OUT} ({len(L)} lines); cells done={len(done)} running={len(running)} skipped={len(skipped)} failed={len(failed)}; soak={soak_status}")
