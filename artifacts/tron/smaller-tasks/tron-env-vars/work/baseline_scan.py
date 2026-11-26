#!/usr/bin/env python3
"""First-pass scan: environment variable names that appear as string literals
at a known read or write call in a TRON checkout.

This is a regular-expression scan. It cannot see a name that reaches the read
call through a variable, a helper function, a macro or a table. The agent
sweep covers those cases. The scan gives a reproducible lower bound and a
cross-check for the final document.

Usage: baseline_scan.py <checkout> <out.json>
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1])
out_path = Path(sys.argv[2])

files = subprocess.run(
    ["git", "-C", str(root), "ls-files"], check=True, capture_output=True, text=True
).stdout.splitlines()

NAME = r"[A-Za-z_][A-Za-z0-9_]*"
UPPER = r"[A-Z_][A-Z0-9_]*"

CPP_EXT = {".cpp", ".hpp", ".c", ".h", ".i", ".cc", ".hh"}
BINARY_EXT = {
    ".png", ".svg", ".pdf", ".parquet", ".safetensors", ".lock", ".csv",
    ".jpg", ".gif", ".ico", ".bin", ".gz", ".zip",
}


def shebang(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            first = f.readline(200).decode("utf-8", "replace")
    except OSError:
        return ""
    if not first.startswith("#!"):
        return ""
    if "python" in first:
        return "python"
    if re.search(r"\b(ba|da|z)?sh\b", first):
        return "shell"
    return ""


def kind_of(rel: str, path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name
    if ext in BINARY_EXT:
        return "skip"
    if ext == ".md":
        return "docs"
    if ext in CPP_EXT:
        return "cpp"
    if ext == ".py":
        return "python"
    if ext == ".rs":
        return "rust"
    if ext == ".hs":
        return "haskell"
    if ext == ".nix":
        return "nix"
    if ext in {".yml", ".yaml"}:
        return "yaml"
    if ext == ".cmake" or name == "CMakeLists.txt" or name == "CMakePresets.json":
        return "cmake"
    if ext in {".service", ".socket", ".timer"} or ".service" in name:
        return "systemd"
    if name in {"GNUmakefile", "Makefile", "makefile"} or ext == ".mk":
        return "make"
    if ext == ".sh":
        return "shell"
    sb = shebang(path)
    if sb:
        return sb
    return "other"


def area_of(rel: str, kind: str) -> str:
    top = rel.split("/", 1)[0]
    if kind == "docs":
        return "docs"
    if kind == "cpp":
        return "cpp-tests" if top == "t" else "cpp-core"
    if kind == "rust":
        return "cpp-core"
    if kind == "python":
        return "python"
    if kind in {"shell", "make"}:
        return "shell-make"
    return "build-ci-pkg"


PATTERNS = {
    "cpp": [
        ("read", rf"\b(?:std::|::)?(?:secure_)?getenv\s*\(\s*\"({NAME})\""),
        ("set", rf"\b(?:::)?(?:setenv|unsetenv)\s*\(\s*\"({NAME})\""),
        ("set", rf"\bputenv\s*\(\s*\"({NAME})="),
    ],
    "python": [
        ("read", rf"os\.environ\s*\[\s*[\"']({NAME})[\"']\s*\](?!\s*=[^=])"),
        ("read", rf"os\.environ\.get\s*\(\s*[\"']({NAME})[\"']"),
        ("read", rf"os\.getenv\s*\(\s*[\"']({NAME})[\"']"),
        ("read", rf"[\"']({NAME})[\"']\s+(?:not\s+)?in\s+os\.environ"),
        ("read", rf"\benviron\.get\s*\(\s*[\"']({NAME})[\"']"),
        ("set", rf"os\.environ\s*\[\s*[\"']({NAME})[\"']\s*\]\s*=[^=]"),
        ("set", rf"os\.environ\.(?:setdefault|pop)\s*\(\s*[\"']({NAME})[\"']"),
        ("set", rf"os\.putenv\s*\(\s*[\"']({NAME})[\"']"),
        ("set", rf"\benv\w*\s*\[\s*[\"']({UPPER})[\"']\s*\]\s*=[^=]"),
    ],
    "shell": [
        ("read", rf"\$\{{({UPPER})(?::?[-=?+])"),
        ("set", rf"^\s*export\s+({UPPER})="),
    ],
    "make": [
        ("read", rf"^({UPPER})\s*\?="),
        ("read", rf"\$\$\{{({UPPER})(?::?[-=?+])"),
        ("set", rf"^\s*export\s+({UPPER})\b"),
    ],
    "cmake": [
        ("read", rf"\$ENV\{{({NAME})\}}"),
        ("set", rf"\bset\s*\(\s*ENV\{{({NAME})\}}"),
        ("set", rf"ENVIRONMENT[^\n]*?\b({UPPER})="),
    ],
    "nix": [
        ("read", rf"builtins\.getEnv\s+\"({NAME})\""),
        ("set", rf"^\s*export\s+({UPPER})="),
        ("set", rf"--set(?:-default)?\s+({UPPER})\b"),
    ],
    "rust": [
        ("read", rf"env::var(?:_os)?\s*\(\s*\"({NAME})\""),
        ("read", rf"\b(?:option_)?env!\s*\(\s*\"({NAME})\""),
    ],
    "haskell": [
        ("read", rf"\b(?:lookupEnv|getEnv)\s+\"({NAME})\""),
    ],
    "yaml": [
        ("read", rf"\$\{{\{{\s*(?:env|vars|secrets)\.({NAME})\s*\}}\}}"),
        ("read", rf"\$\{{({UPPER})(?::?[-=?+])"),
    ],
    "systemd": [
        ("set", rf"^\s*Environment=\"?({UPPER})="),
        ("read", rf"\$\{{({UPPER})\}}"),
    ],
}
PATTERNS["other"] = PATTERNS["shell"]

names = defaultdict(lambda: {"read": [], "set": []})
area_names = defaultdict(lambda: {"read": set(), "set": set()})
kind_counts = defaultdict(int)
area_files = defaultdict(int)

for rel in files:
    path = root / rel
    if not path.is_file():
        continue
    kind = kind_of(rel, path)
    if kind == "skip":
        continue
    area = area_of(rel, kind)
    kind_counts[kind] += 1
    area_files[area] += 1
    if kind == "docs":
        continue
    try:
        text = path.read_text("utf-8", "replace")
    except OSError:
        continue
    for lineno, line in enumerate(text.splitlines(), 1):
        for role, pat in PATTERNS.get(kind, []):
            for m in re.finditer(pat, line):
                n = m.group(1)
                names[n][role].append(f"{rel}:{lineno}")
                area_names[area][role].add(n)

result = {
    "kind_counts": dict(kind_counts),
    "area_files": dict(area_files),
    "areas": {
        a: {
            "read": sorted(v["read"]),
            "set_only": sorted(v["set"] - v["read"]),
        }
        for a, v in area_names.items()
    },
    "names": {n: v for n, v in sorted(names.items())},
}
out_path.write_text(json.dumps(result, indent=1))

all_read = {n for n, v in names.items() if v["read"]}
all_set_only = {n for n, v in names.items() if v["set"] and not v["read"]}
print(f"files by kind: {dict(kind_counts)}")
print(f"files by area: {dict(area_files)}")
print(f"distinct names read (literal): {len(all_read)}")
print(f"distinct names set only (literal): {len(all_set_only)}")
for a, v in sorted(result["areas"].items()):
    print(f"  {a:14s} read={len(v['read']):4d} set_only={len(v['set_only']):4d}")
