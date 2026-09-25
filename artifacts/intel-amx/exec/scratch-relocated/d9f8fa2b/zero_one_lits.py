# Count literal 0 and 1 tokens on the lines a diff adds, outside constexpr variable
# declarations (the guide allows literals there) and outside preprocessor lines.
import re, subprocess, collections, sys
R = '/home/jhan/workspace/ai-runs/tron-issue4525'
base = sys.argv[1]; tip = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != 'WORKTREE' else None
cmd = ['git', '-C', R, 'diff', '-U0', base] + ([tip] if tip else []) + ['--', '*.hpp', '*.cpp']
diff = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
def strip(s):
    s = re.sub(r'"(\\.|[^"\\])*"', '""', s); s = re.sub(r"'(\\.|[^'\\])*'", "''", s)
    s = re.sub(r'/\*.*?\*/', '', s); return s.split('//', 1)[0]
DECL = re.compile(r'^\s*(template\s*<[^>]*>\s*)?((inline|static)\s+)*constexpr\s+(?!auto\s+\w+\s*\()[\w:<>, ]+?\s+\w+\s*(=|\{)')
rows = []; f = None; ln = 0; in_decl = False; depth = 0
for line in diff.splitlines():
    if line.startswith('+++ '):
        f = line[6:] if line.startswith('+++ b/') else None; in_decl = False; depth = 0
    elif line.startswith('@@'):
        ln = int(re.search(r'\+(\d+)', line).group(1)); in_decl = False; depth = 0
    elif line.startswith('+') and f:
        c = strip(line[1:]); t = c.strip()
        if not in_decl and DECL.match(c):
            in_decl = True; depth = 0
        if in_decl:
            depth += c.count('{') + c.count('(') - c.count('}') - c.count(')')
            if t.endswith(';') and depth <= 0: in_decl = False
            ln += 1; continue
        if t.startswith('#'):
            ln += 1; continue
        for m in re.finditer(r'(?<![\w.])([01])(?![\w.\'xX])', c):
            around = c[max(0, m.start() - 6):m.end() + 1]
            if 'sseq<' in around: k = 'unit stride sseq<1>'
            elif re.search(r'integer_sequence<ptrdiff_t, \w+, 1>', c): k = 'unit stride in integer_sequence'
            elif re.search(r'\[\s*0\s*\]', c[max(0, m.start() - 1):m.end() + 1]): k = 'index [0]'
            elif m.group(1) == '0' and re.search(r'=\s*0\s*;', c[max(0, m.start() - 3):m.end() + 1]) and 'for' in c: k = 'loop start 0'
            elif re.search(r'(==|!=|<=|>=|<|>)\s*$', c[:m.start()]) or re.match(r'\s*(==|!=)', c[m.end():]): k = 'comparison'
            elif re.search(r'[-+]\s*$', c[:m.start()]) or re.match(r'\s*\*', c[m.end():]): k = 'arithmetic offset or unrolled index'
            else: k = 'call argument (head, slot, token, page index)'
            rows.append((k, m.group(1), f, ln, t[:110]))
        ln += 1
by = collections.defaultdict(list)
for r in rows: by[r[0]].append(r)
zeros = sum(1 for r in rows if r[1] == '0'); ones = len(rows) - zeros
print(f'0/1 literals on added code lines, outside constexpr declarations and #if lines: {len(rows)} ({zeros} zeros, {ones} ones) on {len({(r[2], r[3]) for r in rows})} lines')
for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
    files = collections.Counter(r[2].split('/')[-1] for r in v)
    print(f'  {k}: {len(v)}  ({", ".join(f"{n} {fn}" for fn, n in files.most_common())})')
if len(sys.argv) > 3:
    for r in rows:
        if sys.argv[3] in r[0]: print('   ', r[2], r[3], r[1], '|', r[4])
