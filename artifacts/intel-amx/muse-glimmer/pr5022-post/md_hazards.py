#!/usr/bin/env python3
"""Flag characters in the replies that GitHub markdown would treat as markup outside code. Usage: md_hazards.py <md dir> [names...]"""
import os, re, sys
md = sys.argv[1]
names = sys.argv[2:] or (['COMBINED'] + [f'I{i}' for i in range(1, 27)])
n_flag = 0
for n in names:
    t = open(os.path.join(md, n + '.md')).read()
    t = re.sub(r'^(`{3,})\w*\n.*?\n\1\s*$', lambda m: '\n' * m.group(0).count('\n'), t, flags=re.S | re.M)  # drop fenced blocks, keep line numbers
    for i, line in enumerate(t.split('\n'), 1):
        bare = re.sub(r'``.+?``|`[^`]*`', '', line)              # drop code spans
        flags = []
        if '`' in bare: flags.append('unbalanced backtick')
        if re.search(r'<[A-Za-z/!]', bare): flags.append('html-like <tag')
        if '<' in bare and 'html-like <tag' not in flags: flags.append('bare <')
        if '~' in bare: flags.append('tilde')
        if re.search(r'(?<![\w*])\*\*?(?!\*)', re.sub(r'\*\*[^*]+\*\*', '', bare)) or '*' in re.sub(r'\*\*[^*]+\*\*', '', bare): flags.append('asterisk')
        if re.search(r'(?<![A-Za-z0-9])_[A-Za-z0-9][^_]*_(?![A-Za-z0-9])', bare): flags.append('underscore emphasis')
        if re.match(r'\s*(\+ |> |# |\d+[.)] |=+\s*$|-{3,}\s*$)', bare): flags.append('block marker at line start')
        if '|' in bare: flags.append('pipe')
        if re.search(r'\\', bare): flags.append('backslash')
        if re.search(r'@[A-Za-z]', bare): flags.append('at-mention')
        if re.search(r'\$', bare): flags.append('dollar (math)')
        if flags:
            n_flag += 1; print(f'{n}:{i}: {", ".join(flags)}: {bare.strip()[:170]}')
print('flagged lines:', n_flag)
