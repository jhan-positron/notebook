#!/usr/bin/env python3
"""gen_tron_flatfreq.py — generate the exact intel-speed-select commands that
put a TRON deployment's tron_cores + peer_cores (and their HT siblings) at top
flat frequency, with every other core allowed to run slow (boot 2700 MHz clip).

Derived from the delphi-3bda findings of 2026-07-02
(debug_3bda/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md):
  - Fast set -> CLOS0 (2700-4400) with SST-TF left ENABLED gives 4100 MHz flat
    on the loaded tron cores at the 80-core shape (+200 vs the TF-disable
    recipe); the clipped rest leaves extra package-power headroom.
  - CLOS0 and CLOS3 configs are explicitly (re)pinned because
    `turbo-freq enable --auto` wipes all CLOS configs and `core-power enable`
    resets CLOS2/CLOS3 — boot values cannot be assumed mid-uptime.

Usage:
  gen_tron_flatfreq.py <resource-map.yaml> [--section granite_rapids_6962p]
      [--isst PATH] [--also-boost dev,rinzler,platform] [--revert]
      [--emit out.sh]

Prints the command sequence to stdout (or writes an executable script with
--emit). --revert prints the restore-to-boot-default block instead.
This tool only GENERATES commands; it never executes isst itself.
"""
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required (apt: python3-yaml)")

ROLE_KEYS = {
    "tron": "tron_cores",
    "peer": "peer_cores",
    "dev": "dev_cores",
    "rinzler": "rinzler_cores",
    "platform": "platform_cores",
}


def find_section(node, name):
    """Depth-first search for a dict key == name (schema-agnostic parent)."""
    if isinstance(node, dict):
        if name in node and isinstance(node[name], dict):
            return node[name]
        for v in node.values():
            hit = find_section(v, name)
            if hit is not None:
                return hit
    elif isinstance(node, list):
        for v in node:
            hit = find_section(v, name)
            if hit is not None:
                return hit
    return None


def expand_cpulist(spec):
    """'27-36' | '24,168' | list of such -> set of ints."""
    cpus = set()
    if spec is None:
        return cpus
    items = spec if isinstance(spec, list) else [spec]
    for item in items:
        for tok in str(item).replace(" ", "").split(","):
            if not tok:
                continue
            if "-" in tok:
                a, b = tok.split("-", 1)
                cpus.update(range(int(a), int(b) + 1))
            else:
                cpus.add(int(tok))
    return cpus


def sibling_map(ncpu):
    """Return sibling(cpu). Prefer live sysfs topology when it matches ncpu;
    fall back to the documented GNR layout: sibling(N) = (N + ncpu/2) % ncpu."""
    base = ncpu // 2
    fallback = lambda c: (c + base) % ncpu
    try:
        online = sum(1 for d in os.listdir("/sys/devices/system/cpu")
                     if d.startswith("cpu") and d[3:].isdigit())
        if online != ncpu:
            return fallback, "static +%d (sysfs has %d CPUs, yaml expects %d)" % (base, online, ncpu)
        sib = {}
        for c in range(ncpu):
            with open(f"/sys/devices/system/cpu/cpu{c}/topology/thread_siblings_list") as f:
                ids = expand_cpulist(f.read().strip())
            others = sorted(ids - {c})
            sib[c] = others[0] if others else c
        return (lambda c: sib[c]), "live sysfs thread_siblings_list"
    except OSError:
        return fallback, "static +%d (no sysfs topology available here)" % base


def compress(cpus):
    """sorted set -> list of 'a-b'/'a' range strings."""
    out, run = [], []
    for c in sorted(cpus):
        if run and c == run[-1] + 1:
            run.append(c)
        else:
            if run:
                out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else f"{run[0]}")
            run = [c]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else f"{run[0]}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("yaml_path")
    ap.add_argument("--section", default="granite_rapids_6962p")
    ap.add_argument("--isst", default="/opt/intel-speed-select/intel-speed-select",
                    help="isst binary (NOPASSWD sudo path on delphi-3bda)")
    ap.add_argument("--also-boost", default="",
                    help="comma list of extra roles to boost: dev,rinzler,platform")
    ap.add_argument("--revert", action="store_true",
                    help="emit the restore-to-boot-default block instead")
    ap.add_argument("--emit", metavar="OUT.SH", help="write an executable script")
    args = ap.parse_args()

    with open(args.yaml_path) as f:
        tree = yaml.safe_load(f)
    sec = find_section(tree, args.section)
    if sec is None:
        sys.exit(f"section '{args.section}' not found in {args.yaml_path}")

    phys = int(sec.get("physical_cores", 0))
    if phys <= 0:
        sys.exit("section lacks physical_cores")
    ncpu = phys * 2  # SMT2 (HT sibling per core); 6962P: 288
    ndomains = 6     # GNR-AP: 3 power domains per package, 2 packages
    anchors = [i * (phys // ndomains) for i in range(ndomains)]

    boost_roles = ["tron", "peer"] + [r.strip() for r in args.also_boost.split(",") if r.strip()]
    for r in boost_roles:
        if r not in ROLE_KEYS:
            sys.exit(f"unknown role '{r}' (known: {', '.join(ROLE_KEYS)})")

    roles = {r: expand_cpulist(sec.get(ROLE_KEYS[r])) for r in ROLE_KEYS}
    boost_listed = set().union(*(roles[r] for r in boost_roles))
    bad = [c for c in boost_listed if c >= ncpu]
    if bad:
        sys.exit(f"CPU ids out of range for {ncpu}-CPU topology: {sorted(bad)[:8]}")

    sib, sib_src = sibling_map(ncpu)
    boost = set(boost_listed) | {sib(c) for c in boost_listed}
    slow = set(range(ncpu)) - boost

    hdr = [
        f"# generated by gen_tron_flatfreq.py from {os.path.basename(args.yaml_path)}",
        f"# section: {args.section} ({phys} cores / {ncpu} CPUs; sibling map: {sib_src})",
        f"# boost roles: {'+'.join(boost_roles)} -> {len(boost_listed)} listed CPUs "
        f"+ siblings = {len(boost)} CPUs",
        f"# boost set: {','.join(compress(boost))}",
        f"# slow set ({len(slow)} CPUs, boot 2700 MHz clip): {','.join(compress(slow))}",
        f'ISST="sudo -n {args.isst}"',
    ]

    lines = []
    if args.revert:
        lines.append("# ---- restore boot-default PCT state ----")
        for a in anchors:
            lines.append(f"$ISST --cpu {a} turbo-freq enable")
            lines.append(f"$ISST --cpu {a} core-power disable")
            lines.append(f"$ISST --cpu {a} core-power config --clos 0 --weight 0 --min 2700 --max 4400")
            lines.append(f"$ISST --cpu {a} core-power config --clos 1 --weight 0 --min 0 --max 25500")
            lines.append(f"$ISST --cpu {a} core-power config --clos 2 --weight 0 --min 0 --max 25500")
            lines.append(f"$ISST --cpu {a} core-power config --clos 3 --weight 0 --min 800 --max 2700")
        boot_clos0 = set()
        for p in range(2):  # 8 fused PCT core-pairs per package + HT siblings
            for c in (0, 1, 18, 19, 36, 37, 54, 55):
                boot_clos0.add(p * (phys // 2) + c)
        boot_clos0 |= {sib(c) for c in set(boot_clos0)}
        for seg in compress(boot_clos0):
            lines.append(f"$ISST --cpu {seg} core-power assoc --clos 0")
        for seg in compress(set(range(ncpu)) - boot_clos0):
            lines.append(f"$ISST --cpu {seg} core-power assoc --clos 3")
    else:
        lines.append("# ---- 1. SST-TF stays ENABLED (boot default; the TF HP bucket is what")
        lines.append("#         grants 4100 instead of the 3900 TRL bucket at the 80-core shape) ----")
        for a in anchors:
            lines.append(f"$ISST --cpu {a} turbo-freq enable")
        lines.append("# ---- 2. pin CLOS0 (fast window) and CLOS3 (slow clip) configs; boot values")
        lines.append("#         cannot be assumed: --auto wipes all CLOS configs, core-power enable")
        lines.append("#         resets CLOS2/3 (verified 2026-07-02) ----")
        for a in anchors:
            lines.append(f"$ISST --cpu {a} core-power config --clos 0 --weight 0 --min 2700 --max 4400")
            lines.append(f"$ISST --cpu {a} core-power config --clos 3 --weight 0 --min 800 --max 2700")
        lines.append("# ---- 3. associations: slow first, then the boost set ----")
        for seg in compress(slow):
            lines.append(f"$ISST --cpu {seg} core-power assoc --clos 3")
        for seg in compress(boost):
            lines.append(f"$ISST --cpu {seg} core-power assoc --clos 0")
        lines.append("# ---- 4. verify ----")
        for a in anchors:
            lines.append(f"$ISST --cpu {a} perf-profile info 2>&1 | grep -m1 speed-select-turbo-freq:  # want enabled")
        probes_fast = compress(boost)[0].split("-")[0], compress(boost)[-1].split("-")[-1]
        probes_slow = compress(slow)[0].split("-")[0], compress(slow)[-1].split("-")[-1]
        for c in probes_fast:
            lines.append(f"$ISST --cpu {c} core-power get-assoc 2>&1 | grep clos:  # want clos:0 (boost)")
        for c in probes_slow:
            lines.append(f"$ISST --cpu {c} core-power get-assoc 2>&1 | grep clos:  # want clos:3 (slow)")
        lines.append(f"$ISST --cpu 0 core-power get-config --clos 3 2>&1 | grep clos-max  # want 2700")
        lines.append("# expected under TRON-shaped load: loaded tron/peer cores (+HT siblings)")
        lines.append("# flat at 4100 MHz (SSE); slow cores <= 2700; validate with:")
        lines.append("#   sudo turbostat --quiet --show Package,Core,CPU,Busy%,Bzy_MHz -i 5 -n 2")
        lines.append("# NOTE: does not survive reboot (BIOS reprograms the PCT partition).")

    text = "\n".join(hdr + lines) + "\n"
    if args.emit:
        with open(args.emit, "w") as f:
            f.write("#!/bin/bash\nset -e\n" + text)
        os.chmod(args.emit, 0o755)
        print(f"wrote {args.emit} ({len(lines)} commands)")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
