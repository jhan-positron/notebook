"""Build a page spec from units_<key>.json, facts/<key>.json and the figure
modules in figs/, then write the page. Usage: python3 spec_builder.py <key>
Keys: kv_cache, k_vnni, kernels."""
import importlib
import json
import os
import sys

G = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, G)
sys.path.insert(0, os.path.join(G, "figs"))
import page_common  # noqa: E402

OUT_DIR = "/home/jhan/workspace/intel-AMX/PR3879/new-PRs/split-4424"
KEYS = {
    "kv_cache": ("h/tron/models/kv_cache.hpp", "diagramming-code-changes-PR4956-kv_cache.hpp.html"),
    "k_vnni": ("h/tron/tensor/k_vnni.hpp", "diagramming-code-changes-PR4956-tensor-k_vnni.hpp.html"),
    "kernels": ("h/tron/kernels/k_vnni.hpp", "diagramming-code-changes-PR4956-kernels-k_vnni.hpp.html"),
}


def fig_of(key, uid):
    """The figure function(s) of unit uid and its BASE sentence:
    figs/d_<key>_<uid>.py exposes fig() or figs(), and BASE = "Updates B2: ..."."""
    mod = importlib.import_module(f"d_{key}_{uid}")
    base = getattr(mod, "BASE", None)
    if hasattr(mod, "figs"):
        # figs() returns a list of figure HTML strings; unit_html wants a
        # callable that returns one string
        return (lambda m=mod: "".join(m.figs())), base
    return mod.fig, base


def load(key):
    file, out = KEYS[key]
    units = json.load(open(os.path.join(G, f"units_{key}.json")))
    base = importlib.import_module(f"base_{key}")
    spec = dict(file=file, gen=f"spec_builder.py {key}", units=[], trivial=units["trivial"],
                base=[], glossary=units["glossary"], short=units["short"],
                base_intro=units["base_intro"], changes_intro=units["changes_intro"],
                trivial_intro=units.get("trivial_intro", ""), trivial_bullets=units.get("trivial_bullets", []),
                method=units.get("method", []))
    for b in units["base"]:
        name = b["id"].split("-")[-1]
        fn = getattr(base, name, None)
        if fn is None:   # a base figure kept in its own module: figs/base_<key>_<name>.py
            fn = getattr(importlib.import_module(f"base_{key}_{name}"), name)
        spec["base"].append(dict(b, fig=fn))
    for u in units["units"]:
        uu = dict(u)
        uu["ranges"] = [tuple(r) for r in u["ranges"]]
        uu["fig"], base_sentence = fig_of(key, u["id"])
        if base_sentence:
            uu["base"] = base_sentence
        spec["units"].append(uu)
    for t in spec["trivial"]:
        t["ranges"] = [tuple(r) for r in t["ranges"]]
    return spec, os.path.join(OUT_DIR, out)


if __name__ == "__main__":
    key = sys.argv[1]
    spec, out = load(key)
    page_common.write(spec, out)
