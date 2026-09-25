import re, subprocess, sys, collections
R = '/home/jhan/workspace/ai-runs/tron-issue4525'
base, tip = sys.argv[1], sys.argv[2]
diff = subprocess.run(['git', '-C', R, 'diff', '-U0', base, tip, '--', '*.hpp', '*.cpp', '*.h'],
                      capture_output=True, text=True, check=True).stdout
def strip_code(s):
    # drop string/char literals and // comments (block comments rare on these lines)
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s)
    s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
    s = s.split('//', 1)[0]
    return s
rows = []
f = None; ln = 0
for line in diff.splitlines():
    if line.startswith('+++ '):
        f = line[6:] if line.startswith('+++ b/') else None
    elif line.startswith('@@'):
        m = re.search(r'\+(\d+)(?:,(\d+))?', line); ln = int(m.group(1))
    elif line.startswith('+') and f:
        code = strip_code(line[1:])
        if re.search(r'\b(true|false)\b', code):
            rows.append((f, ln, line[1:].strip()))
        ln += 1
def cls(t):
    if re.search(r'\b(const_)?view\s*<[^>]*\b(true|false)\b', t) or re.match(r'^(true|false),', t): return 'view/const_view flag (aligned, dma)'
    if re.search(r'constexpr\b[^=]*=\s*(true|false)\s*;', t): return 'constexpr declaration initializer (allowed)'
    if re.search(r'\breturn\s+(true|false)\b', t): return 'return true/false'
    if re.search(r'\b(REQUIRE|CHECK|STATIC_REQUIRE|static_assert)\b', t): return 'test assertion / static_assert'
    return 'other'
by = collections.defaultdict(list)
for r in rows: by[cls(r[2])].append(r)
print('PR-added code lines with true/false (base %s .. tip %s): %d' % (base, tip, len(rows)))
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    print(f'\n## {k}: {len(v)}')
    for f_, l_, t in v: print(f'  {f_}:{l_}: {t[:150]}')
