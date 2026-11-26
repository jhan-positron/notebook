#!/usr/bin/env python3
"""scan_commands.py - scan every shell command of this job (main session and its agents) for four things:

    1. a start of a .py or .sh file of the code folder (by its repo path, or by a relative name after cd into that folder)
    2. a login or a copy to another machine (ssh, scp, sftp, rsync)
    3. a program started under taskset (the CPU list is printed)
    4. a start of a file that has the name of a run, visit, build or test script of the code folder, in any folder (a copy)

The commands are read from the session records. Each command text is split into words as the shell does (module shlex).
Only the command word of each part of a pipeline or list counts, and the script that an interpreter (python3, bash, sh) gets.
Text inside a here-document is not a command and is left out, except for item 3: there the lines of scripts that an agent
wrote in a here-document are scanned too, because such a script may call taskset.
A command text that shlex cannot split (a quote without a partner) is counted and listed as "not split".
"""
import glob
import json
import os
import re
import shlex
import sys

REC = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel'
SID = 'e8814cab-99b1-4798-9af9-6536ce08ea6e'
CODE_RE = re.compile(r'ai-proj/arm-crb/code|^\$CODE\b|^\$\{CODE\}|^\$C/|^\$REPO\b')
NAMES = re.compile(r'^(run_bwx\d*|run_h2|run_partA|run_kernels|run_cread|run_sudo|run_chip|run_mesh|run_single|visit\d*|visit_h2|session2|fetch|remote|'
                   r'go2?|ra|rx|rc2?|rgc?|r0|prep|hw|test_schedule\d*|test_runner\d+|test_h2|test_hwwatch|test_kernels\d+|build\d*)\.(sh|py)$')
TASKSET = re.compile(r'(?:^|[;&(\n|]|\bthen\b|\bdo\b|\$\()[ \t]*(?:[A-Za-z_]\w*=\S*[ \t]+)*(?:exec[ \t]+)?'
                     r'taskset[ \t]+(-[a-z]*c[a-z]*|--cpu-list)[ \t]+("?[^\s"`\']+"?)[ \t]+([^\s;|&]+)')
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?.*?\n\1\b", flags=re.S)
OPS = {';', '&&', '||', '|', '&', '(', ')', '|&', ';;'}
WORDS_BEFORE = {'then', 'do', 'else', 'elif', 'if', 'while', 'until', '!', '{', 'time', 'exec', 'command', 'env', 'nice', 'nohup', 'builtin'}
INTERP = {'python3', 'python', 'bash', 'sh'}


def commands():
    files = sorted(glob.glob('%s/%s/subagents/agent-*.jsonl' % (REC, SID))) + ['%s/%s.jsonl' % (REC, SID)]
    for p in files:
        if not os.path.isfile(p):
            continue
        who = os.path.basename(p).replace('agent-', '').replace('.jsonl', '')[:20]
        for line in open(p, encoding='utf-8', errors='replace'):
            if '"Bash"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            m = d.get('message') or {}
            c = m.get('content')
            if m.get('role') != 'assistant' or not isinstance(c, list):
                continue
            for x in c:
                if isinstance(x, dict) and x.get('type') == 'tool_use' and x.get('name') == 'Bash':
                    yield d.get('timestamp', '')[:19], who, (x.get('input') or {}).get('command', '')


def parts(body):
    """The simple commands of a command text: lists of words. None when shlex cannot split the text."""
    lex = shlex.shlex(body.replace('\n', ' ; '), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return None
    out, cur = [], []
    for t in toks:
        if t in OPS:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        out.append(cur)
    return out


def target(words):
    """(command word, script) of one simple command: assignments and wrapper words are skipped."""
    i = 0
    while i < len(words):
        w = words[i]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w) or w in WORDS_BEFORE:
            i += 1
        elif w == 'timeout' and i + 1 < len(words):
            i += 2
        else:
            break
    if i >= len(words):
        return None, None
    cmd = words[i]
    script = None
    if os.path.basename(cmd) in INTERP:
        j = i + 1
        while j < len(words) and words[j].startswith('-'):
            if words[j] in ('-c', '-m'):          # inline code or a module: no script file
                return cmd, None
            j += 1
        if j < len(words):
            script = words[j]
    return cmd, script


def main():
    n = unsplit = 0
    starts, net, ts, copies, bad = [], [], [], [], []
    for when, who, cmd in commands():
        n += 1
        body = HEREDOC.sub(' ', cmd)
        ps = parts(body)
        if ps is None:
            unsplit += 1
            bad.append((when, who, body[:100].replace('\n', ' ')))
            ps = []
        cwd_code = False
        for words in ps:
            c, script = target(words)
            if c is None:
                continue
            if c == 'cd' and len(words) > 1:
                cwd_code = bool(CODE_RE.search(words[1]))
                continue
            cand = script if script is not None else c
            if cand.endswith(('.py', '.sh')):
                if CODE_RE.search(cand) or (cwd_code and not cand.startswith(('/', '$'))):
                    starts.append((when, who, ' '.join(words)[:160]))
                elif NAMES.match(os.path.basename(cand)):
                    copies.append((when, who, ' '.join(words)[:160]))
            if os.path.basename(c) in ('ssh', 'scp', 'sftp', 'rsync'):
                net.append((when, who, ' '.join(words)[:160]))
        for r in TASKSET.finditer(cmd):       # also inside the scripts that the command writes
            if 'p' in r.group(1) and not re.match(r'^[\d,-]+$', r.group(2)):
                continue                      # taskset -cp PID only prints the CPU list of a process
            ts.append((when, who, r.group(2).strip('"'), r.group(3)[:40]))
    print('%d shell commands scanned, %d of them not split into words' % (n, unsplit))
    for h in sorted(bad):
        print('   not split: %s %s %s' % h)
    print('1. starts of a file of the code folder: %d' % len(starts))
    for h in sorted(starts):
        print('   %s %s %s' % h)
    print('2. ssh, scp, sftp or rsync as a command: %d' % len(net))
    for h in sorted(net):
        print('   %s %s %s' % h)
    print('3. programs started under taskset: %d' % len(ts))
    for h in sorted(ts):
        print('   %s %s cpus=%s program=%s' % h)
    print('4. starts of a file with the name of a run, visit, build or test script, outside the code folder (a copy): %d' % len(copies))
    for h in sorted(copies):
        print('   %s %s %s' % h)
    return 0


if __name__ == '__main__':
    sys.exit(main())
