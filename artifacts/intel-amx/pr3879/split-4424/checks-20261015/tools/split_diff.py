#!/usr/bin/env python3
"""Split a unified diff into per-file annotated files with new-file line numbers.

Output per file: <outdir>/<pr>/<path with / -> __>.txt
Each line: "<newline>| <marker><text>" where marker is '+', ' ' or '-' (removed lines get no number).
Also writes <outdir>/<pr>/_lines.json: {path: {"right": [line numbers present on the RIGHT side (added+context)], "added": [...]}}
"""
import json, re, sys, os
diff_path, pr, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(outdir, pr), exist_ok=True)
files = {}
cur = None
new_ln = 0
with open(diff_path, encoding='utf-8', errors='replace') as f:
    for raw in f:
        line = raw.rstrip('\n')
        if line.startswith('diff --git'):
            m = re.match(r'diff --git a/(.*?) b/(.*)$', line)
            cur = m.group(2)
            files[cur] = {"lines": [], "right": [], "added": [], "removed": 0}
            continue
        if cur is None:
            continue
        if line.startswith('+++') or line.startswith('---') or line.startswith('index ') or line.startswith('new file') or line.startswith('deleted file') or line.startswith('similarity') or line.startswith('rename') or line.startswith('old mode') or line.startswith('new mode'):
            continue
        if line.startswith('@@'):
            m = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$', line)
            new_ln = int(m.group(1))
            files[cur]["lines"].append(f"     |{line}")
            continue
        if line.startswith('+'):
            files[cur]["lines"].append(f"{new_ln:5d}| +{line[1:]}")
            files[cur]["right"].append(new_ln); files[cur]["added"].append(new_ln)
            new_ln += 1
        elif line.startswith('-'):
            files[cur]["lines"].append(f"     | -{line[1:]}")
            files[cur]["removed"] += 1
        elif line.startswith('\\'):
            files[cur]["lines"].append(f"     | {line}")
        else:
            files[cur]["lines"].append(f"{new_ln:5d}|  {line[1:] if line.startswith(' ') else line}")
            files[cur]["right"].append(new_ln)
            new_ln += 1
index = {}
for path, d in files.items():
    fn = path.replace('/', '__') + '.txt'
    with open(os.path.join(outdir, pr, fn), 'w') as o:
        o.write(f"# PR {pr} file {path}\n# format: <new-file line>| <+ added | ' ' context | - removed><text>\n")
        o.write('\n'.join(d["lines"]) + '\n')
    index[path] = {"file": os.path.join(outdir, pr, fn), "right": d["right"], "added": d["added"], "n_added": len(d["added"]), "n_removed": d["removed"]}
with open(os.path.join(outdir, pr, '_lines.json'), 'w') as o:
    json.dump(index, o, indent=1)
for path, d in index.items():
    print(f"{pr}\t+{d['n_added']}\t-{d['n_removed']}\t{path}")
