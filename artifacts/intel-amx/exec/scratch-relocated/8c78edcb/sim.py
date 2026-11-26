# Test only: builds a page from the saved nights plus two invented nights with the PR.
import copy, json, sys, datetime as dt
sys.path.insert(0, sys.argv[1]); sys.dont_write_bytecode = True
import watch, report
nights = json.load(open(sys.argv[1] + "/data/nights.json"))
for n in nights.values(): n["has_pr"] = False
pr = {"state": "MERGED", "mergedAt": "2026-11-25T19:02:11Z", "oid": "0123456789abcdef", "merged_ts": dt.datetime(2026,11,25,19,2,11,tzinfo=dt.timezone.utc).timestamp()}
G = watch.GLIMMER
for dut in watch.MACHINES:
    last = max((n for n in nights.values() if n["dut"] == dut), key=lambda n: n["started"])
    for i, (gain, tt) in enumerate(((1.046, 0.966), (1.049, 0.968))):
        n = copy.deepcopy(last); n["uuid"] = "sim-%s-%d" % (dut, i); n["started"] = last["started"] + 86400 * (i + 1)
        n["tron_version"] = "v2026.11.%d-deadbeef" % (26 + i); n["has_pr"] = True
        if dut == "delphi-3bda":
            n["series"][G]["tps"] *= gain; n["series"][G]["ttft"] = round(n["series"][G]["ttft"] * tt)
        k = "mixtral_8x7b_instruct_v0_1_tp2_tps @ 8"; n["series"][k]["tps"] *= 0.975
        if i == 1 and dut == "andoria-b1a3":
            k2 = "ingested_qwen_3_4b_instruct_2507_tp2_tps @ 8"; del n["series"][k2]; n["failed"][k2] = "FAILED (RuntimeError: invented for the test)"
        nights[n["uuid"]] = n
res = watch.analyse(nights)
status = {"generated": "TEST PAGE", "pr": pr, "error": None, "machines": res,
          "arrived": {"delphi-3bda": {"old": "73ab1891", "new": "deadbeef", "commits": ["AMX attention: serve kv_mul 16 (#5022)", "Another change <b>with markup</b> (#5999)"]}},
          "summary": [], "false_alarms": watch.false_alarms(res, nights)[0], "nights": sorted(nights.values(), key=lambda n: n["started"])}
snap = report.glimmer_snapshot(status)
day1 = dict(snap, date="2026-11-26", title="2026-11-26: Day 1 with PR 5022", days=1, head=snap["head"][:9], rows=[r[:9] for r in snap["rows"]])
base = list(json.load(open(sys.argv[1] + "/data/table-log.json")).values())
status["table_log"] = [snap, day1] + base
open(sys.argv[2], "w").write(report.render(status))
print(report.snapshot_markdown(snap))
print("\n".join(watch.summary_lines(res, pr, nights, None)))
