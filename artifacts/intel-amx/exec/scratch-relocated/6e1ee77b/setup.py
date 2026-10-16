"""Copy the PR 4956 diagram toolchain into one record dir per PR and repoint its constants."""
import os, re, shutil, sys
SRC = "/home/jhan/workspace/intel-AMX/exec/pr4956-diagrams-20261015"
PRS = {
    "4958": dict(
        dir="/home/jhan/workspace/intel-AMX/exec/pr4958-diagrams-20261016",
        wt="/home/jhan/workspace/ai-runs/tron-split-pr3", base="26b86a279a", head="b39765ec29",
        base_branch="jhan-vnnik-2-amx", base_pr="4957", branch="jhan-vnnik-3-shared-save",
        title="Save K in 16-token blocks, shared with idle worker threads",
        keys={
            "model": ("h/tron/models/model.hpp", "diagramming-code-changes-PR4958-model.hpp.html",
                      "save_k: the shared K store window (cut, open, claim, join) and store_k_block"),
            "k_vnni": ("h/tron/tensor/k_vnni.hpp", "diagramming-code-changes-PR4958-tensor-k_vnni.hpp.html",
                       "store_block: 16 rows transposed in registers and written as whole lines"),
            "common": ("h/tron/models/common.hpp", "diagramming-code-changes-PR4958-common.hpp.html",
                       "batch::k_store_window_t: the data model of the shared K store window"),
        }),
    "4959": dict(
        dir="/home/jhan/workspace/intel-AMX/exec/pr4959-diagrams-20261016",
        wt="/home/jhan/workspace/ai-runs/tron-split-pr4", base="b39765ec29", head="6b081187e1",
        base_branch="jhan-vnnik-3-shared-save", base_pr="4958", branch="jhan-vnnik-4-tail-block",
        title="Keep short K writes row-major; enable VNNI K in the deb preset",
        keys={
            "kv_cache": ("h/tron/models/kv_cache.hpp", "diagramming-code-changes-PR4959-kv_cache.hpp.html",
                         "the K layout state per page (saved-row bits, converted-block bits), the conversion, row accessors that follow the layout, forgetting rows, page copies"),
            "k_vnni": ("h/tron/tensor/k_vnni.hpp", "diagramming-code-changes-PR4959-tensor-k_vnni.hpp.html",
                       "Note [Row-major tail block]: the row-major form of a block and the in-place conversion block_to_vnni / block_to_rows"),
            "model": ("h/tron/models/model.hpp", "diagramming-code-changes-PR4959-model.hpp.html",
                      "the deferred conversion list, the whole-block-only block save, the row-recording loop and the hardware-attention policy"),
        }),
}
FILES = ["check_legend.py", "check_page.py", "difflib_units.py", "page_common.py", "render_check.py",
         "render_one.py", "spec_builder.py", "svg_helpers.py"]
for pr, p in PRS.items():
    d = p["dir"]
    os.makedirs(os.path.join(d, "figs"), exist_ok=True)
    os.makedirs(os.path.join(d, "png"), exist_ok=True)
    os.makedirs(os.path.join(d, "facts"), exist_ok=True)
    for f in FILES:
        s = open(os.path.join(SRC, f), encoding="utf-8").read()
        s = s.replace("/home/jhan/workspace/ai-runs/tron-split-pr1", p["wt"])
        s = s.replace("exec/pr4956-diagrams-20261015", f"exec/pr{pr}-diagrams-20261016")
        s = s.replace('BASE = "76bb0bf3f4"   # main, the PR\'s merge base (2026-10-15)',
                      f'BASE = "{p["base"]}"   # the head of PR {p["base_pr"]} ({p["base_branch"]}), this PR\'s base')
        s = s.replace('HEAD = "a5697f86d3"   # PR 4956 head (2026-10-15, the merge of main)',
                      f'HEAD = "{p["head"]}"   # PR {pr} head (2026-10-15, the merge of PR {p["base_pr"]})')
        s = s.replace('HEAD = "a5697f86d3"', f'HEAD = "{p["head"]}"')
        s = s.replace('BASE = "76bb0bf3f4"', f'BASE = "{p["base"]}"')
        s = s.replace("https://github.com/positron-ai/tron/pull/4956", f"https://github.com/positron-ai/tron/pull/{pr}")
        s = s.replace('PR_TITLE = "Add the VNNI K layout and its readers"', f'PR_TITLE = "{p["title"]}"')
        s = s.replace("base\n<code>main</code> at <code>{BASE}</code> &middot; head <code>jhan-vnnik-1-layout</code>",
                      "base\n<code>" + p["base_branch"] + "</code> (the head of PR #" + p["base_pr"] +
                      ") at <code>{BASE}</code> &middot; head <code>" + p["branch"] + "</code>")
        s = s.replace("page generated 2026-10-15", "page generated 2026-10-16")
        s = s.replace("a5697f86d3", p["head"]).replace("76bb0bf3f4", p["base"])
        s = s.replace("PR 4956", f"PR {pr}").replace("#4956", f"#{pr}").replace("PR4956", f"PR{pr}")
        if f == "spec_builder.py":
            keys = "KEYS = {\n" + "".join(f'    "{k}": ("{v[0]}", "{v[1]}"),\n' for k, v in p["keys"].items()) + "}\n"
            s = re.sub(r"KEYS = \{.*?\n\}\n", keys, s, flags=re.S)
            s = s.replace("Keys: kv_cache, k_vnni, kernels.", "Keys: " + ", ".join(p["keys"]) + ".")
        if f == "page_common.py":
            pages = "PAGES = [  # the three pages, in the order the file picker ranked them\n" + "".join(
                f'    ("{v[0]}", "{v[1]}",\n     "{v[2]}"),\n' for k, v in p["keys"].items()) + "]\n"
            s = re.sub(r"PAGES = \[.*?\n\]\n", pages, s, flags=re.S)
            s = s.replace("# Rebuild: ", "# Rebuild: ")
        open(os.path.join(d, f), "w", encoding="utf-8").write(s)
    print(pr, "->", d)
