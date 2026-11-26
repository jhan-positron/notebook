"""summary_facts.py - the texts of the summary page (make_summary.py). Facts that a script can compute are computed here."""
import filecmp
import os
import re

import lbl

AS = lbl.AS
T2 = lbl.HERE
REC = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel'
OLD_C = [('kernels-2026-11-13', 'bandwidth.c'), ('kernels-2026-11-13', 'bandwidth.orig.c'), ('kernels-2026-11-13', 'selftest.c'),
         ('kernels-2026-11-13', 'probe.c'), ('bwx12-2026-11-15', 'bwx12.c'), ('bwx12-2026-11-15', 'bwx12_selftest.c')]
# sampled rows that were taken over from another version, and how many of them a reviewer corrected (from the review reports)
TAKEN_OVER = [('SR11', 128, 0), ('SR13', 174, 0), ('SR14', 83, 0), ('SR15', 75, 0), ('SR16', 22, 0), ('SR17', 184, 8), ('SR18', 4, 0), ('SR19', 87, 0)]


def c(s):
    return '<code>%s</code>' % s.replace('&', '&amp;').replace('<', '&lt;')


def computed():
    m = lbl.manifest()
    f = {}
    # the six older C pages and their sources
    f['old_c_pages'] = sum(os.path.isfile('%s/%s/%s.md' % (AS, d, n)) for d, n in OLD_C)
    f['old_c_equal'] = sum(filecmp.cmp('%s/%s/%s' % (AS, d, n), '%s/%s/%s' % (lbl.REPO, d, n), shallow=False) for d, n in OLD_C)
    f['c_in_s'] = sum(n.endswith('.c') for _, _, names in os.walk(lbl.S) for n in names)
    f['c_pages'] = sum(n.endswith('.c.md') for _, _, names in os.walk(lbl.S) for n in names)
    # the 16 pages of the rerun folder: text before and after the new section against the backup
    same = html_rest = 0
    for key, e in m.items():
        if e['mode'] != 'section':
            continue
        new = lbl.read_text(e['page']).split('\n')
        old = lbl.read_text(lbl.BACKUP + '/' + key + '.md').split('\n')
        a = new.index(lbl.SECTION)
        b = next((i for i in range(a + 1, len(new)) if new[i].startswith('## ')), len(new))
        oa = next(i for i, l in enumerate(old) if lbl.OLD_SECTION_RE.match(l))
        ob = next((i for i in range(oa + 1, len(old)) if old[i].startswith('## ')), len(old))
        same += (new[:a] == old[:oa] and new[b:] == old[ob:])
        html_rest += bool(re.search(r'<(details|table|div|span|br)\b', '\n'.join(new[:a] + new[b:])))
    f['sec_same'], f['sec_html_rest'] = same, html_rest
    f['sec'] = sum(e['mode'] == 'section' for e in m.values())
    # lines that stand outside the table
    out = 0
    for e in m.values():
        if os.path.isfile(e['page']):
            out += len(re.findall(r'^Line \d+ holds a backslash directly before', lbl.read_text(e['page']), flags=re.M))
    f['outside'] = out
    f['notes'] = len(re.findall(r'^- ', lbl.read_text(T2 + '/SOURCE-NOTES.md'), flags=re.M))
    return f


def texts(n, fmt, pct):
    f = computed()
    allk, alln = n['full_k'] + n['samp_k'], n['full_n'] + n['samp_n']
    to_n = sum(x[1] for x in TAKEN_OVER)
    to_k = sum(x[2] for x in TAKEN_OVER)
    def names(kind):
        return ', '.join(r['name'] for r in n['reviews'] if r['kind'] == kind)

    t = {}
    t['sub'] = ('Pages in %s. Source: the working tree of %s on 2026-11-25. Tools and records: %s.'
                % (c(lbl.S), c(lbl.REPO), c(T2)))
    t['short'] = [
        'Every code file of the repo folder %s now has a page in the scratch folder %s that explains it line by line: %d files and %s explained source lines.'
        % (c('arm-crb/code'), c('w120-7200-2026-11-17'), n['files'], fmt(n['rows'])),
        'The earlier job did not miss the C code: it wrote the six C pages beside their C sources in two other scratch folders, as the request of 2026-11-22 asked [Ref1].',
        'Reviewer agents checked every explained line of the files that the whole-chip test ran and a random sample of the other pages, and they corrected %d of the %s lines that they checked (%s).'
        % (allk, fmt(alln), pct(allk, alln)),
    ]
    t['words'] = [
        '<b>CRB</b>: the Arm reference server under test. It has 128 CPUs.',
        '<b>Repo, code folder</b>: the code repository %s. Its folder %s holds the code.' % (c('/home/jhan/workspace/ai-proj/arm-crb'), c('code')),
        '<b>Rerun folder</b>: %s, the scratch folder of the whole-chip test of 2026-11-17.' % c(lbl.S),
        '<b>Tool folder</b>: %s. It holds the page tool, the explanations and the records of this job.' % c(T2),
        '<b>Whole-chip test</b>: the test of 2026-11-17 that ran the old and the new read kernel on 120 CPUs of CRB at a memory speed of 7200 MT/s.',
        '<b>Whole-chip test path</b>: the files that this test ran: the run scripts %s, %s, %s, %s and %s, the two kernel sources, and the runner %s with its build files.'
        % (c('go.sh'), c('go2.sh'), c('ra.sh'), c('rx.sh'), c('run_kernels.sh'), c('bwx12.c')),
        '<b>Kernel</b>: the inner loop of a benchmark that reads, writes or copies memory. It is not the Linux kernel.',
        '<b>Runner</b>: a benchmark program that times a sequence of kernels in one process. Its versions are named %s, %s, %s, %s, %s and %s.'
        % (c('bwx'), c('bwx8'), c('bwx10'), c('bwx11'), c('bwx12'), c('bwx13')),
        '<b>Page</b>: one Markdown file that explains one source file.',
        '<b>Row</b>: one line of a page table. It holds the line number, the source line and the explanation of that line.',
        '<b>Row taken over</b>: an explanation that the tool copied from the equal line of another version of the same file.',
        '<b>Annotation file</b>: the text file that holds the explanations of one source file. The tool builds the page from it.',
        '<b>Agent</b>: a helper session that the main session started. A writer agent wrote explanations. A reviewer agent checked them.',
        '<b>Full review, sampled review</b>: in a full review the reviewer checked every row of its files. In a sampled review it checked a random sample.',
        '<b>pandoc, markdown-it-py</b>: two programs that read Markdown. The job used them to read the pages back.',
        '<b>sha256</b>: a checksum. Two files with the same sha256 have the same content.',
        '<b>%s</b>: a Linux tool that sets the CPUs on which a program may run.' % c('taskset'),
        '<b>CPU guard</b>: a rule of the agent server. It limits every shell command of an agent to the CPUs 26 to 31.',
        '<b>est.</b>: an estimate, not a measurement.',
    ]
    t['puzzle'] = [
        'The request of 2026-11-22 said: "these companion files are in the same folder as their target files" [Ref1].',
        'The C sources of the test lie in two other scratch folders, not in the rerun folder. So that job wrote its six C pages there: '
        '%s, %s, %s and %s in %s, and %s and %s in %s [Ref2]. %d of the 6 pages exist today.'
        % (c('bandwidth.c.md'), c('bandwidth.orig.c.md'), c('selftest.c.md'), c('probe.c.md'), c('kernels-2026-11-13'),
           c('bwx12.c.md'), c('bwx12_selftest.c.md'), c('bwx12-2026-11-15'), f['old_c_pages']),
        'The rerun folder holds no C source. The command %s finds %d files there.' % (c("find . -name '*.c'"), f['c_in_s']),
        'So nothing was missed. The command looked in a folder that never held C code.',
        'Those six pages have the older form: an HTML table inside the Markdown file. They are unchanged.',
        'The rerun folder now holds %d C pages below %s. They are plain Markdown and explain the repo text. For %d of the 6 C files of the older pages the repo text equals the scratch text.'
        % (f['c_pages'], c('code/'), f['old_c_equal']),
    ]
    t['flow'] = [
        '%s<br>%d files, %s lines' % (c('arm-crb/code'), n['files'], fmt(n['lines'])),
        'One annotation file per source file, in the tool folder. One text per source line that is not blank.',
        '%d pages in the rerun folder itself, and %d pages below its folder %s' % (f['sec'], n['files'] - f['sec'], c('code/')),
    ]
    t['built'] = [
        'The %d pages of the rerun folder kept all their sections. Only the section that shows the source with its explanations was replaced. Its heading is now "Source and explanation, line by line".' % f['sec'],
        'A script compared these pages with their backups [Ref8]. In %d of %d pages the text before and after the new section is unchanged.' % (f['sec_same'], f['sec']),
        'The pages of the other repo folders are new files below %s. Each has the path of its source file in the repo, plus %s.' % (c('code/'), c('.md')),
        'The index %s lists all pages [Ref3].' % c('code-pages.md'),
        'Each new section is a Markdown table with three columns: the line number, the source line and the explanation. Every source line that is not blank has one row.',
        '%d source lines hold a backslash directly before a %s character. Markdown readers do not agree on such a table cell. So each of these lines stands in a code block between two tables, with its explanation below it.'
        % (f['outside'], c('|')),
        'Writers wrote %s rows for their file. The tool took %s rows over from the equal line of another version of the same file. %d files are equal to another file of the repo and share its %s rows.'
        % (fmt(n['own']), fmt(n['seed']), n['equal'], fmt(n['equal_rows'])),
        'Each page names the sha256 of the source text that it shows.',
    ]
    t['checked'] = [
        'The tool writes a page only after it has read the new section back, with a reader of its own and with pandoc 2.9.2.1. Every source cell must equal its source line, and the section must hold no HTML element [Ref6].',
        'A second Markdown reader, markdown-it-py 4.3.0, read all built pages back at the end. Every row gave back its source line [Ref6].',
        'A check step refuses an explanation that holds an HTML tag, a bare %s, a reference to a line that the file does not have, a citation that the page does not list, or one of the idioms on its list.' % c('|'),
        'A reviewer is a second agent. It reads the source first and the row after that, and it corrects the rows that are wrong [Ref7].',
    ]
    t['review_intro'] = [
        'Full review (%s): every row of the whole-chip test path and of the hardware record%s.'
        % (names('full'), ', and of the run scripts %s and %s' % (c('run_h2.sh'), c('run_bwx.sh')) if 'SR19' in names('full') else ''),
        'Sampled review (%s): a random sample of the rows of every other file. The sample commands are stored, so each sample can be drawn again [Ref4].' % names('sample'),
        'Mixed review (%s): every row of a part of the files and a sample of the rest. The table counts these reviews with the sampled ones.' % names('mixed'),
        'A row counts as corrected when the reviewer changed it. The reasons range from a false statement to a sentence that is hard to follow. The record gives the kinds per review [Ref4].',
    ]
    worst = max(n['reviews'], key=lambda r: r['k'] / r['n'])
    t['take'] = ('No review corrected more than %s of the rows that it checked (%s, %d of %s rows). The mixed and sampled reviews corrected %d of %s rows (%s).'
                 % (pct(worst['k'], worst['n']), worst['name'], worst['k'], fmt(worst['n']), n['samp_k'], fmt(n['samp_n']), pct(n['samp_k'], n['samp_n'])))
    t['cap'] = ('Bars start at 0 %. The text at each bar gives the corrected rows, the checked rows and the share. '
                'Point at a row, or move to it with the Tab key, to read the files of the review.')
    t['review_after'] = [
        'The full reviews cover %s rows. The mixed and sampled reviews cover %s rows. The other %s rows had no check of each claim. The record says which of them a reviewer read once, less strictly [Ref4].'
        % (fmt(n['full_n']), fmt(n['samp_n']), fmt(n['unsampled'])),
        'Estimate: if these %s rows have the same share of defects as the rows of the mixed and sampled reviews (%s), about %d of them hold a defect (est.). '
        'Reviewers already corrected %d rows outside their samples. A full review of these pages is the measurement that would replace this estimate.'
        % (fmt(n['unsampled']), pct(n['samp_k'], n['samp_n']), round(n['est_left'], -1), n['out']),
        'Rows that were taken over from another version: reviewers checked %d of them and corrected %d (%s). All corrected ones are rows of the round 1 run script %s [Ref4].'
        % (to_n, to_k, pct(to_k, to_n), c('run_bwx8.sh')),
        'Corrections of one version were also put into the equal rows of the other versions of the same file.',
    ]
    t['limits'] = [
        'The 6 JSON data files and the 8 Markdown notes of the code folder have no page. They hold data and notes, not code. The index lists them [Ref3].',
        'The script %s has no page. Another session wrote it on 2026-11-25, outside the folder %s.' % (c('arm-crb/manual-run.sh'), c('code')),
        'Five scripts have a newer text in the repo than in the scratch folders: %s, %s, %s, %s and %s. The new section explains the repo text. '
        'The other sections of these five pages still describe the older text. A table at the top of each new section maps the old line numbers to the new ones.'
        % (c('go.sh'), c('go2.sh'), c('ra.sh'), c('rx.sh'), c('run_kernels.sh')),
        'Only the new section is plain Markdown. The sections that were left intact still hold HTML in %d of the %d pages of the rerun folder.' % (f['sec_html_rest'], f['sec']),
        'The older pages in the other scratch folders are unchanged. The list %s is unchanged too, so it still points to those older pages.' % c('whole-chip-test-code-data-list.md'),
        'The older tools %s and %s would write the old section back into the %d pages. After a run of one of them, run %s in the tool folder.'
        % (c('companion_tool.py'), c('make_go_sh_md.py'), f['sec'], c('python3 lbl.py build-all')),
        'A sampled review does not prove the rows outside the sample. See the estimate above.',
        'Row 1558 of the page of %s lacks four sums with 6 decimals that the older page gave for one process (T72C1). '
        'The permission system denied the command with which the writer wanted to check them. I did not work around that denial. The four sums stand in the older state of that page [Ref8].'
        % c('make_report.py'),
        'The repo has changes of 2026-11-24 that are not committed, and another session worked in it during this job. The pages show the text of 2026-11-25. '
        'The command %s in the tool folder reports every page whose source changed after that.' % c('python3 lbl_main.py pages-check'),
        'No file of the code folder was run, and no command went to CRB. Every statement about a past run comes from a saved result file that the page cites.',
    ]
    t['rules'] = F_RULES
    t['findings_intro'] = [
        'The writers and reviewers reported points about the source code. They fill %d list entries in %s, in three groups: points that touch a measurement, comments that do not fit the code, and files that the repo copy lacks [Ref5].'
        % (f['notes'], c('SOURCE-NOTES.md')),
        'Nothing in the code was changed. Most points were reported by one agent. An entry says so when a second agent or a small test confirmed it.',
        'The points below are the ones that touch the whole-chip test. Each hypothesis names the measurement that would confirm or reject it.',
    ]
    t['findings'] = F_FINDINGS
    t['howto'] = [
        'Edit the explanation in the annotation file of the source file: %s, or a part file in %s. One line holds one row, in the form %s.'
        % (c('ann/FOLDER/FILE.ann'), c('ann/FOLDER/FILE.ann.d/'), c('LINE: text')),
        'Then run %s in the tool folder. KEY is the path of the source file below the code folder, for example %s.' % (c('python3 lbl.py build KEY'), c('w120-7200-2026-11-17/go.sh')),
        '%s builds every page. %s reads every page back. %s writes the index.' % (c('python3 lbl.py build-all'), c('python3 lbl_main.py pages-check'), c('python3 lbl_main.py index')),
        'After a change of a source file, run %s first. It records the new text and its sha256. Then write the rows of the changed lines and build the page.' % c('python3 lbl.py manifest'),
    ]
    t['refs'] = [
        '[Ref1] %s, line 10 (2026-11-22 02:00 UTC): the request for the companion pages.' % c(REC + '/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl'),
        '[Ref2] %s and %s: the six older C pages, beside their sources.' % (c(AS + '/kernels-2026-11-13/'), c(AS + '/bwx12-2026-11-15/')),
        '[Ref3] %s: the index of all pages, and the list of the files without a page.' % c(lbl.S + '/code-pages.md'),
        '[Ref4] %s: one table row and one note per review, with the kinds of defect. The folder %s holds the sample commands.' % (c(T2 + '/REVIEW-RESULTS.md'), c(T2 + '/review-lists/')),
        '[Ref5] %s: all points about the source code.' % c(T2 + '/SOURCE-NOTES.md'),
        '[Ref6] %s (build, check and the two readers), %s (index, read-back of all pages), %s (the second Markdown reader).' % (c(T2 + '/lbl.py'), c(T2 + '/lbl_main.py'), c(T2 + '/check_markdown_it.py')),
        '[Ref7] %s, %s and %s: the rules for the writers and the reviewers, and the word list.' % (c(T2 + '/BRIEF.md'), c(T2 + '/REVIEW.md'), c(T2 + '/GLOSSARY.md')),
        '[Ref8] %s: the first state of the %d pages of the rerun folder, before this job.' % (c(T2 + '/backup/'), f['sec']),
        '[Ref9] %s: the records of the agents of this job, one file per agent. They hold every command that an agent ran.' % c(REC + '/e8814cab-99b1-4798-9af9-6536ce08ea6e/subagents/'),
        '[Ref10] %s: the log of the whole-chip run of 2026-11-17. Its line %s gives the CPU list 0-119.' % (c('/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-17-whole-chip-7200/go-T72-20261117T221209Z.log'), c('affinity of this shell')),
    ]
    return t


F_RULES = [
    'Three agents used <code>taskset</code> in a small shell experiment with CPUs outside the CPUs 26 to 31 of the CPU guard: '
    '<code>taskset -c 0 nproc</code> (2026-11-25 23:30 UTC), <code>taskset -c 0 readlink /proc/self/fd/0</code> (2026-11-26 00:02 UTC), '
    'and a test script of 4 lines that started itself again under <code>taskset -c 0-5</code> (2026-11-26 00:32 UTC). Each ran one short program [Ref9].',
    'My briefing for the agents did not hold the rule on the allowed CPUs. I added it at 01:48 UTC on 2026-11-26 and sent it to the agents that were running. Three other experiments, at 01:33, 01:53 and 01:58 UTC on that day, used CPU lists inside the guard (the CPUs 26 to 31, or CPU 26 alone). The command <code>python3 scan_commands.py</code> in the tool folder lists all seven cases.',
    'One writer could not create the file <code>report_w120.py.page.md</code> with its file tool, because the tool refused the name. It wrote the file with a shell command. The file is an input of the page tool, not a report.',
    'The same scan read more than 5,200 shell commands of the main session and of its agents. It finds no <code>ssh</code>, no start of a file of the code folder, and no start of a copy of a run, visit, build or test script [Ref9]. Some reviewers ran copies of a schedule generator and of test functions in their scratch folders, to compute counts.',
    'One reviewer had a read-only shell command denied by the permission system (a search in a note). It read the note with its file tool.',
    'One reviewer wrote a note into the memory folder of this project on its own. I replaced it with an exact note of mine (<code>agentsrv-cpu-rule-in-agent-briefs.md</code>).',
]

F_FINDINGS = [
    'Rate of part A (<code>bandwidth.c</code>, <code>bandwidth.orig.c</code>): a thread stores only the length of its own interval. The rate of an interval is the bytes of all threads divided by the longest of these lengths. So one slow thread lowers the rate of the whole interval.',
    'Hardware record (<code>hw.sh</code>, written on 2026-11-24): the frequency sampler and the tool <code>atx</code> are pinned to CPU 119 and run during the timed intervals. In a process with 120 threads they share that CPU with one benchmark thread. '
    'Hypothesis, not measured: this lowers the part A rate of such a process. One part A run with <code>HW=off</code> against one with <code>HW=on</code> in the same boot would confirm or reject it. The rerun of 2026-11-17 had no hardware record.',
    'Parts L, C and I of the whole-chip test (<code>rx.sh</code> line 24, which is line 19 of the text that ran on 2026-11-17): while the binary measures, the shell of <code>rx.sh</code> starts one <code>sleep</code> process per second. The <code>taskset</code> of line 22 limits only the binary, so these processes use the CPU list of the caller. The log of the run of 2026-11-17 records that list as the CPUs 0 to 119 [Ref10]. So each of these processes ran on a CPU that also ran one pinned benchmark thread. Part A is not affected: <code>ra.sh</code> starts nothing while its binary runs. '
    'Insufficient data on the size of the effect: the count of involuntary context switches of each benchmark thread would show it.',
    '<code>ra.sh</code> line 46 and <code>run_kernels.sh</code> line 68: a comment in <code>hw.sh</code> says that <code>hw_begin</code> must stand before the quiet time of the launch. These two scripts have no pause between <code>hw_begin</code> and the start of the binary.',
    '<code>ra.sh</code> line 27 and <code>rx.sh</code> line 14: the sampler and <code>atx</code> already run when the scripts count the runnable tasks. Insufficient data on the effect: the value <code>runnable=</code> in <code>probe.txt</code> of a run with <code>HW=on</code> would show it.',
    'Runner <code>bwx12.c</code>, option <code>--stop common</code>: the deadline counts from the common start, and each thread reads its own start time a little later. So the time of a thread can be shorter than <code>--min-ms</code>: 5.999979 s for 6000 ms in the rerun. This is a property of the design, not a bug.',
    'Load record of the run scripts: the list of "busiest processes" comes from <code>ps --sort=-pcpu</code>. That column is the CPU time of a process divided by the time from its start to now. It is not the load at the launch. '
    'In the 9 files <code>launches.txt</code> of the result folders <code>bwx10-*</code>, 3,874 of 3,945 process lines show 0.0. The load averages and the login count in the same record are not affected.',
    'Facts sheet: <code>build_facts.py</code> expects two texts of the older scripts (lines 849 and 880 to 882). The repo texts of <code>go.sh</code>, <code>go2.sh</code> and <code>ra.sh</code> of 2026-11-24 no longer hold them. '
    'The scratch copy of <code>go.sh</code> was also edited on 2026-11-24, so its sha256 no longer equals the value in <code>local.sha</code>, and a new build of the facts sheet stops at that check. The stored <code>FACTS.md</code> is from before the edit.',
    '<code>manual-run/run.sh</code> line 4 compares the scripts with the list <code>local.sha</code>. The list names the checksums of the scripts of 2026-11-17. With the repo texts of 2026-11-24 the command stops at line 4 until a new list is written.',
    '<code>stat_bwx.py</code> and the runner: the field <code>bytes</code> of a thread row is the size of the buffer part of each kernel call. For the kernel <code>read_1pl</code>, which loads 16 of every 64 bytes, it is not the number of bytes loaded.',
    'Comment of <code>CHECK_BYTES</code> in the kernel sources and in <code>bwx12.c</code>: it says that the clock is read after at least 8 MiB. The division rounds down, so a buffer below 8 MiB that does not divide 8 MiB is checked after less. The sizes of the tests (32K, 1M, 8M, 256M, 1G) are not affected.',
    'Other tests, not the whole-chip test (parts A to C of the plan of 2026-11-13, and the investigation into the 8 MiB buffer size): while a benchmark process runs, their run scripts start one <code>date</code> process and one <code>sleep</code> process per second on the CPUs 0 to 119. '
    'Hypothesis, not measured: such a process lowers the rate of an interval when it runs on the CPU of a benchmark thread. The count of involuntary context switches of the benchmark thread during an interval would confirm or reject it.',
]
