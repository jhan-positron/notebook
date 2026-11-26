#!/usr/bin/env python3
"""rail_search.py KIT_FOLDER - search every readable file of the Arm welcome kit for the names of the supply rails
and for text that says which rail feeds the mesh (CMN).

It reads: every PDF (text of each page, through PyMuPDF), and every other file smaller than 5 MiB that decodes as
text. It does not open archives (.zip, .tar, .gz, .deb, .rpm) or the firmware images (.pldm, .hex, .bin).
Output: per pattern and file, the count of matching lines, then the matching lines (cut to 200 characters).
A third search is wider, because a PDF page is cut into short lines: it lists every PDF page, and every window of
7 lines of a text file, that holds a mesh word (mesh, CMN, interconnect) and a rail name of the chip
(VCPU, VSOC, VSYS) together.
"""
import os
import re
import sys

# The script runs with "python3 -I" (no user packages). PyMuPDF is a user package here, so its folder is added by hand.
sys.path.append(os.path.expanduser("~/.local/lib/python3.10/site-packages"))
import fitz  # PyMuPDF  # noqa: E402

RAIL = re.compile(r"VCPU[_-]?M|VCPU|VSOC|VSYS|V0P75|VDDQ|V1P2", re.I)
MESHPOW = re.compile(r"(mesh|\bCMN\b|interconnect).{0,120}(power|rail|supply|volt|watt)|(power|rail|supply|volt|watt).{0,120}(mesh|\bCMN\b|interconnect)", re.I)
MESHWORD = re.compile(r"\bmesh\b|\bCMN\b|interconnect", re.I)
CHIPRAIL = re.compile(r"\bVCPU(_M|M)?(_C?[01])?\b|\bVSOC(_C?[01])?\b|\bVSYS(_C?[01])?\b")
SKIP_EXT = {".zip", ".tar", ".gz", ".deb", ".rpm", ".pldm", ".hex", ".bin", ".png", ".so", ".md5", ".sha256"}


def lines_of(path):
    """(label, text) pairs: one per page of a PDF, one per line of a text file. None if not read."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        out = []
        with fitz.open(path) as doc:
            for n, page in enumerate(doc, 1):
                for ln in page.get_text().splitlines():
                    out.append(("p%d" % n, ln))
        return out
    if ext in SKIP_EXT or os.path.getsize(path) > 5 * 1024 * 1024:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return [(str(n), ln.rstrip("\n")) for n, ln in enumerate(fh, 1)]
    except (UnicodeDecodeError, OSError):
        return None


def main():
    kit = sys.argv[1].rstrip("/")
    read, skipped, hits, both = 0, [], {"rail": {}, "meshpow": {}}, {}
    for root, dirs, files in os.walk(kit):
        dirs.sort()
        for name in sorted(files):
            p = os.path.join(root, name)
            rel = os.path.relpath(p, kit)
            ls = lines_of(p)
            if ls is None:
                skipped.append(rel)
                continue
            read += 1
            if rel.lower().endswith(".pdf"):
                pages = {}
                for label, ln in ls:
                    pages.setdefault(label, []).append(ln)
                windows = [(label, " ".join(v)) for label, v in pages.items()]
            else:
                windows = [("%s-%s" % (ls[i][0], ls[min(i + 6, len(ls) - 1)][0]), " ".join(x[1] for x in ls[i:i + 7])) for i in range(0, len(ls), 4)]
            for label, text in windows:
                if MESHWORD.search(text) and CHIPRAIL.search(text):
                    both.setdefault(rel, []).append(label)
            for label, ln in ls:
                if RAIL.search(ln):
                    hits["rail"].setdefault(rel, []).append((label, ln))
                if MESHPOW.search(ln):
                    hits["meshpow"].setdefault(rel, []).append((label, ln))
    print("files read: %d, files not read: %d" % (read, len(skipped)))
    exts = {}
    for rel in skipped:
        e = os.path.splitext(rel)[1].lower() or "(none)"
        exts[e] = exts.get(e, 0) + 1
    print("not read, by ending: " + ", ".join("%s %d" % kv for kv in sorted(exts.items())))
    for key, title in (("rail", "lines that hold a rail name"), ("meshpow", "lines that hold mesh/CMN/interconnect within 120 characters of power/rail/supply/volt/watt")):
        print("\n== %s: %d files" % (title, len(hits[key])))
        for rel in sorted(hits[key]):
            print("%6d  %s" % (len(hits[key][rel]), rel))
    print("\n== PDF pages and 7-line windows of text files that hold a mesh word and a chip rail name together: %d files" % len(both))
    for rel in sorted(both):
        print("%6d  %s  at: %s" % (len(both[rel]), rel, " ".join(both[rel][:20])))
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    for key in ("rail", "meshpow"):
        for rel in sorted(hits[key]):
            print("\n-- %s: %s" % (key, rel))
            for label, ln in hits[key][rel][:limit]:
                print("   %s: %s" % (label, ln.strip()[:200]))
            if len(hits[key][rel]) > limit:
                print("   ... %d more lines" % (len(hits[key][rel]) - limit))


if __name__ == "__main__":
    main()
