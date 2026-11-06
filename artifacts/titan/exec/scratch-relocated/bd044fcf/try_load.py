import sys, traceback
sys.path.insert(0, "/home/jhan/workspace/titan/cache-perf/asimov")
import gen_run4 as g4
for run, boot in (("007", "bootC"), ("008", "bootD"), ("010", "bootE")):
    try:
        d = g4.load_boot(g4.A + f"/results/membench-jibin-{run}/", boot)
        print(boot, "OK", len(d["MAPS"]), "maps", len(d["CMDS"]), "cmds", d["CHIP_S"], "chip s", "ctrl", d["CTRL_OK"], d["P4K"]["ns"], d["RT_NS"], "seq", d["SEQ"]["ns"], "cseq", d["CSEQ"]["ns"], "align", dict(d["ALIGN_COUNT"]), "cont", sorted(set(m["cont"] for m in d["MAPS"])), "H5", d["H5_SUPPORTED"], "fit", {k: round(v,3) for k,v in d["FIT"]["route"].items()}, "H3walk", [round(x,3) for x in d["H3_WALK"]], "H3L1", [round(x,3) for x in d["H3_L1"]])
    except Exception as e:
        print(boot, "FAILED"); traceback.print_exc()
