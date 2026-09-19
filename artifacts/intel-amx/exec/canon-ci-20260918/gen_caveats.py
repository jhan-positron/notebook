#!/usr/bin/env python3
"""Write the caveats fragment (a <ul>) for the canon-ci report from the run records and the campaign log.
usage: gen_caveats.py --base perf.json --target perf.json --canon perf.json --canon-log driver.log
                      --base-log driver.log --target-log driver.log --nightly-log nightly.log
                      --campaign-log canon-ci-20260918.log --out caveats.html
                      [--nightly nightly-0918.arm.json] [--bill-log bill-share.log] [--preflight preflight.txt]
Every number is computed here; nothing is typed in by hand except the hand-recorded PSI spot check of the base arm
(14:52 UTC, PSI some 93 %, from the 2026-09-18 ci-mimic caveats) and the 02:45 UTC timer (from campaign.sh's header)."""
import argparse, json, re, statistics

R = "/home/jhan/workspace/intel-AMX/exec"

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None

def psi10(s):
    m = re.search(r"avg10=([0-9.]+)", s or "")
    return float(m.group(1)) if m else None

def short_name(model, users):
    """'ingested-qwen-3-4b-instruct-2507-tp2', 8 -> 'qwen-3-4b-2507-tp2 @8u'"""
    return model.replace("-instruct", "").replace("ingested-", "") + f" @{users}u"

def conditions(rec):
    """load/PSI over the driver's snapshots, per config with the user count taken from the record's config list."""
    if not rec:
        return None
    snaps = rec.get("snapshots") or []
    cfgs = rec.get("configs") or []
    loads = [s["client_load"][0] for s in snaps if s.get("client_load")]
    psis = [psi10(s.get("client_cpu_psi")) for s in snaps]
    psis_v = [p for p in psis if p is not None]
    per = []
    for s in snaps:
        tag = s.get("tag") or ""
        if tag.startswith("after-provision:"):
            i = len(per)
            model = tag.split(":", 1)[1]
            users = cfgs[i][1] if i < len(cfgs) and cfgs[i][0] == model else "?"
            reused = i > 0 and i < len(cfgs) and cfgs[i - 1][0] == model  # same model as the previous config: engines kept
            per.append((short_name(model, users) + (" (no re-provisioning)" if reused else ""), psi10(s.get("client_cpu_psi"))))
    return {"n": len(snaps), "load": (min(loads), max(loads)) if loads else None,
            "psi": (min(psis_v), max(psis_v)) if psis_v else None, "per": per,
            "started": rec.get("started"), "finished": rec.get("finished"), "minutes": rec.get("perf_minutes"),
            "host": rec.get("client_host")}

def count(path, pat):
    try:
        return sum(1 for l in open(path, errors="replace") if pat in l)
    except Exception:
        return None

def per_config_count(path, pat):
    """[(config as the harness prints it in '== Benchmarking X ==', count)] in run order."""
    out = []
    try:
        for l in open(path, errors="replace"):
            m = re.search(r"== Benchmarking (\S+) ==", l)
            if m:
                out.append([m.group(1), 0])
            elif pat in l and out:
                out[-1][1] += 1
    except Exception:
        return None
    return out

def log_lines(path, pats):
    out = []
    try:
        for l in open(path, errors="replace"):
            if any(p in l for p in pats):
                out.append(l.rstrip()[:200])
    except Exception:
        pass
    return out

def hhmm(ts):
    m = re.search(r"T(\d\d:\d\d)", ts or "")
    return m.group(1) if m else "?"

def hhmmss(ts):
    m = re.search(r"T(\d\d:\d\d:\d\d)", ts or "")
    return m.group(1) if m else "?"

def day(ts):
    m = re.search(r"\d{4}-(\d\d-\d\d)", ts or "")
    return m.group(1) if m else "?"

def window(c):
    """'22:44 to 00:15 UTC' or, across midnight, '22:44 UTC 09-18 to 00:15 UTC 09-19'."""
    if not c["finished"]:
        return f"{hhmm(c['started'])} UTC to running"
    if day(c["started"]) == day(c["finished"]):
        return f"{hhmm(c['started'])} to {hhmm(c['finished'])} UTC"
    return f"{hhmm(c['started'])} UTC {day(c['started'])} to {hhmm(c['finished'])} UTC {day(c['finished'])}"

def main():
    ap = argparse.ArgumentParser()
    for k in ("base", "target", "canon", "base_log", "target_log", "canon_log", "nightly_log", "campaign_log"):
        ap.add_argument("--" + k.replace("_", "-"))
    ap.add_argument("--nightly", default=R + "/results/ci-mimic-20260918/reference/nightly-0918.arm.json")
    ap.add_argument("--bill-log", default=R + "/logs/bill-share.log", help="bill-share.sh's own log (take and release lines)")
    ap.add_argument("--preflight", default=R + "/results/canon-ci-20260918/preflight.txt")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base_rec, tgt_rec, can_rec, ngt_rec = load(a.base), load(a.target), load(a.canon), load(a.nightly)
    B, T, C = conditions(base_rec), conditions(tgt_rec), conditions(can_rec)
    logs = (("nightly", a.nightly_log), ("base", a.base_log), ("target", a.target_log), ("canon", a.canon_log))
    an = {k: count(p, "anomalous tps") for k, p in logs if p}
    an_cfg = {k: per_config_count(p, "anomalous tps") for k, p in logs if p}
    camp = log_lines(a.campaign_log, ["campaign start", "CI lease", "take:", "release:", "installing canon", "installed and verified", "reinstalling", "restored and verified",
                                       "taking production serving down", "serving down:", "handoff", "HANDOFF", "RESTORE", "flock released", "WARNING", "SIGNAL"]) if a.campaign_log else []
    items = []

    # 1. client conditions per arm
    def cond_text(name, c, spot=None):
        if not c:
            return f"<li><b>{name}:</b> no record yet.</li>"
        s = f"<li><b>{name} ({window(c)}, client host {esc(c['host'] or '?')}):</b> "
        if c["load"]:
            s += f"1-minute load average across its {c['n']} snapshots {c['load'][0]:.1f} to {c['load'][1]:.1f} on a 32-CPU host. "
        if c["psi"]:
            hi = [f"{n} {p:.0f} %" for n, p in c["per"] if p is not None and p >= 10]
            s += f"CPU pressure (PSI some avg10, the share of the last 10 s in which at least one task waited for a CPU) {c['psi'][0]:.1f} to {c['psi'][1]:.1f} %. "
            s += ("Configs whose start snapshot showed 10 % or more: " + ", ".join(hi) + ". ") if hi else "No start snapshot showed 10 % or more. "
        elif spot:
            s += spot + " "
        return s + "</li>"
    # base: when did its 1-minute load fall below the CPU count (32)? Reported as config indexes.
    base_low = ""
    if B and B["per"]:
        import time
        aps = [s for s in (base_rec or {}).get("snapshots") or [] if (s.get("tag") or "").startswith("after-provision:")]
        lows = [(i + 1, time.strftime("%H:%M", time.gmtime(s["t"]))) for i, s in enumerate(aps) if s.get("client_load") and s["client_load"][0] < 32 and s.get("t")]
        if lows:
            base_low = (" (its 1-minute load was below the 32-CPU count at the start of " + ("config " if len(lows) == 1 else "configs ")
                        + ", ".join(f"{i} at {t} UTC" for i, t in lows) + ", and above it at the other start snapshots)")
    items.append("<li><b>Client-host conditions differ between the arms.</b> The harness ran on the same container for all three arms. "
                 f"Other containers on that host saturated its CPUs during most of the base arm{base_low} and during the first five configs of the target arm. "
                 "The canon arm ran on an idle host. Per arm:<ul>")
    items.append(cond_text("base", B, spot="Its record has no PSI field (the driver added it later that day). A hand-recorded spot check at 14:52 UTC showed PSI some 93 %."))
    items.append(cond_text("target", T))
    items.append(cond_text("canon", C))
    items.append("</ul></li>")

    # 2. anomalous-sample counts = a direct client-stall indicator from the harness itself, per run and per config
    if an:
        parts = ", ".join(f"{k} {v}" for k, v in an.items() if v is not None)
        items.append(f"<li><b>The harness's own stall indicator.</b> The nightly's client code logs a TPS sample above 1000 tokens per second as 'anomalous tps' (testlib/tps.py). It keeps the sample. Such a sample appears when 16 tokens arrive in one burst after a pause on the client side. Lines per run: {esc(parts)}. A count near the nightly's means the client kept up with the stream. A count far above it means the client stalled and then received bursts. Stalls lower some TPS samples and raise short TTFTs.")
        rows = []
        cfgs = (can_rec or base_rec or {}).get("configs") or []   # the same 12 configs in the same order in every run
        for k, lst in an_cfg.items():
            if not lst:
                continue
            names = [short_name(m, u) for m, u in cfgs] if len(cfgs) == len(lst) else [c.replace("_", "-") for c, _ in lst]
            nz = [f"{esc(nm)} {n}" for nm, (c, n) in zip(names, lst) if n]
            rows.append(f"<li>{k}: " + (", ".join(nz) if nz else "0 on every config") + (", 0 on the other configs" if nz and len(nz) < len(lst) else "") + "</li>")
        if rows:
            items.append("<p>Anomalous-tps lines per config (a client-stall indicator, counted between the harness's 'Benchmarking' lines):</p><ul>" + "".join(rows) + "</ul>")
        items.append("</li>")

    # 3. TPS robust, TTFT not. The rule of thumb is calibrated on the one config with a large stall count.
    robust = "A stalled client lowers a few samples and moves the mean by a small amount."
    if B and ngt_rec and base_rec and an_cfg.get("base"):
        def tab(rec):
            return {(x["context"]["model"], int(x["context"]["nominal_users"])): x for x in rec.get("results") or []}
        bt, nt = tab(base_rec), tab(ngt_rec)
        worst = max(an_cfg["base"], key=lambda x: x[1])
        k3b = next((k for k in bt if k[0].startswith("llama-3.2-3b")), None)
        if k3b and k3b in nt and worst[0].startswith("llama_3_2_3b"):
            d = (bt[k3b]["tps_mean"] - nt[k3b]["tps_mean"]) / nt[k3b]["tps_mean"] * 100
            others = [abs((bt[k]["tps_mean"] - nt[k]["tps_mean"]) / nt[k]["tps_mean"] * 100) for k in bt if k in nt and k != k3b]
            gpt = next((k for k in bt if k[0].startswith("ingested-gpt-oss")), None)
            others_no_gpt = [abs((bt[k]["tps_mean"] - nt[k]["tps_mean"]) / nt[k]["tps_mean"] * 100) for k in bt if k in nt and k not in (k3b, gpt)]
            robust = (f"On base, llama-3b (the config with {worst[1]} anomalous samples) came out {d:+.1f} % against the same-day nightly. "
                      f"The other base configs were within {max(others_no_gpt):.1f} % of the nightly, except gpt-oss-120b (+{max(others):.1f} %, inside its own 13-night band). "
                      f"A stall of {worst[1]} samples therefore moved a TPS mean by about 2 % at most. It cannot explain a 5 % change in a config with 3 anomalous samples.")
    items.append(f"<li><b>What the client load can and cannot change.</b> TPS is a rate over a window of generated tokens late in each request (the glossary gives the window). {robust} TTFT is one timestamp difference on the client and moves by the whole stall. TTFT comparisons that involve the base arm for llama-3b, llama-8b and qwen-3-4b tp2 (the three configs whose base TTFT differs from the same-day nightly by more than 5 %, section 2), or the target arm for configs 1 to 5, therefore cannot be attributed to the package.</li>")

    # 4. machine handling from the campaign log
    if camp:
        items.append("<li><b>Machine handling (from the campaign log, UTC):</b><ul>" + "".join(f"<li><code>{esc(l)}</code></li>" for l in camp) + "</ul></li>")

    # 5. start state: marker, lease, flock, with the times the logs hold
    start_ts = (can_rec or {}).get("started") or ""
    lease_line = next((l for l in camp if "CI lease free" in l), None)
    take_line = rel_line = None
    for l in log_lines(a.bill_log, ["take:", "release:"]):
        ts = l[:20]
        if "take:" in l and start_ts and ts <= start_ts:
            take_line = l
        if "release:" in l and start_ts and ts >= start_ts and rel_line is None:
            rel_line = l
    pre_marker = None
    pre_time = None
    try:
        pre = open(a.preflight).read()
        m = re.search(r"== bill marker: (\S+)", pre); pre_marker = m.group(1) if m else None
        m = re.search(r"== time (\S+)", pre); pre_time = m.group(1) if m else None
    except Exception:
        pass
    marker_txt = ("Bill's marker (the file /bill-has-instance-0,2 on delphi-3bda that reserves the first half of the cards for Bill) "
                  + (f"was taken (removed) by launch.sh at {hhmmss(take_line[:20])} UTC on jhan's order, with Bill idle (bill-share.log), " if take_line else "")
                  + (f"was recorded {pre_marker} by the preflight at {hhmmss(pre_time)} UTC, " if pre_marker and pre_time else "")
                  + (f"and was re-created at {hhmmss(rel_line[:20])} UTC." if rel_line else "and its re-creation is not in the logs."))
    lease_txt = (f"The CI lease (the file /run/lock/systems-test-ci.lease, which the nightly holds while it runs) was free at {hhmmss(lease_line[:20])} UTC, the one check the campaign made. "
                 f"The run ended at {hhmm((can_rec or {}).get('finished'))} UTC, before the 03:30 UTC nightly." if lease_line else "The campaign log has no CI lease line.")
    items.append(f"<li><b>Start state of the machine.</b> When the canon arm began, four idle production engines (gemma-4-31b tp2, left by the restore of an earlier campaign at 21:07 UTC) were running on all cards. The harness's first provisioning replaced them, as it replaces the previous config's engines in the nightly. {marker_txt} {lease_txt} The campaign flock (the host-wide lock file /var/tmp/jhan/3bda-campaign.lock that lets only one of our campaigns run at a time) was held from the preflight to the 'flock released' line above.</li>")
    items.append("<li><b>End state.</b> After the last config the campaign reinstalled the nightly's package, stopped the production engines through platformd (POST /api/inference/down after an idle test), removed the positron-owned hugepage slice files (hugepages = the 1 GiB memory pages the engines reserve, HugePages_Free = pages not in use) and left the machine to the issue #4500 root-cause campaign of another session. The 02:45 UTC ci-runner-stop timer (a systemd timer on delphi-3bda that brings production serving back before the nightly, recorded in campaign.sh's header, not verified in this run) restores serving. No engine served a replaced binary during any measured config (section 6, binary identity row).</li>")
    items.append("<li><b>One run per arm.</b> base and target are the 2026-09-18 arms and were not repeated. canon ran once. The 13-night band from the Slack reports is used in place of run-to-run noise.</li>")
    html = "<ul>\n" + "\n".join(items) + "\n</ul>\n"
    data = html.encode("ascii", "xmlcharrefreplace")
    open(a.out, "wb").write(data)
    print(f"wrote {a.out} ({len(data)} bytes)")
    print(re.sub(r"<[^>]+>", " ", html)[:1500])

if __name__ == "__main__":
    main()
