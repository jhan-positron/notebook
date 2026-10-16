# Assemble the v2 skill files from the compressed workflow output (wf3-result.json) and the v1 text.
import json, re, os
R = json.load(open('wf3-result.json')); style = R['style']
numbers = json.load(open('items2/numbers.json'))
checks = {c['label']: c for c in R['checks']}
v1 = open('skill-snapshot-v1/SKILL.md').read(); v1proc = open('skill-snapshot-v1/references/procedures.md').read()
os.makedirs('out/references', exist_ok=True)
SHORT = {'dead-symbol-no-consumer-or-definition':'dead symbol','typo-or-wording-in-added-text':'typo','debug-switch-or-output-left-on':'debug switch','comment-contradicts-adjacent-code':'comment versus code','duplicate-logic-use-existing-helper':'duplicate logic','type-and-initialization-choice':'type and initialization','identifier-name-states-role':'identifier name','missing-explanation-at-declaration':'missing explanation','redundant-code-simplify':'redundant code','disabled-code-left-in':'disabled code','declaration-placement-and-file-organization':'declaration placement','silent-behavior-change-or-unexamined-threshold':'silent behavior change','index-count-or-wait-set-mismatch':'index or wait set','silent-fallback-where-assert-belongs':'silent fallback','concurrency-race-or-lock-placement':'lock placement','buffer-lifetime-or-alignment':'buffer lifetime','hot-path-avoidable-work':'hot path','state-ownership-and-key-granularity':'state ownership','observability-and-operability-of-new-path':'observability','test-exists-and-reaches-changed-path':'test reaches the path','workaround-needs-tracking':'workaround tracking','verify-automated-findings':'bot findings','value-rows-need-consumer-or-provenance':'value rows','test-silently-skips-or-cannot-fail':'test cannot fail','tests-run-at-head-before-approve':'run at head','duplicate-test-coverage':'duplicate coverage','test-name-tag-output-conventions':'test name','claim-wider-than-code':'claim wider than code','pr-body-and-branch-state':'body and branch state','code-comment-carries-no-lasting-fact':'unusable passages','unrelated-or-unexplained-hunk':'unrelated hunk','magic-literal-or-constant-name':'magic literal'}
NUMTXT = {**{k: str(v) for k, v in numbers.items()}, 'test-silently-skips-or-cannot-fail': '3A', 'tests-run-at-head-before-approve': '3B'}
def xref(t):
    # replace label slugs with "check N (short)"
    for lab in sorted(SHORT, key=len, reverse=True):
        t = re.sub(r'`?' + re.escape(lab) + r'`?(?: \([a-z]\))?', f'check {NUMTXT[lab]} ({SHORT[lab]})', t)
    return t
def head(lab, c):
    name = re.sub(r'^### [0-9A-B]+\. ', '', c['heading']).strip()
    return f'### {NUMTXT[lab]}. {name}'
def qline(lab, c):
    q = re.sub(r'^[0-9A-B]+\. ', '', c['question_line'].strip()); return f'{NUMTXT[lab]}. {q}'
def v1_check(n):
    m = re.search(r'^### %d\. .*?(?=^### \d+\.|^## |\Z)' % n, v1, re.S | re.M); return m.group(0).rstrip() + '\n'
def v1_proc(n):
    m = re.search(r'^## Check %d: .*?(?=^## Check |\Z)' % n, v1proc, re.S | re.M); return m.group(0).rstrip() + '\n'
def v1_q(n):
    m = re.search(r'^%d\. (.*)$' % n, v1, re.M); return m.group(0)
KEEP_V1 = {'test-silently-skips-or-cannot-fail': 3, 'duplicate-test-coverage': 4, 'code-comment-carries-no-lasting-fact': 9, 'unrelated-or-unexplained-hunk': 10}
ORDER = [
 ('Checks on code: hygiene', ['dead-symbol-no-consumer-or-definition','typo-or-wording-in-added-text','magic-literal-or-constant-name','debug-switch-or-output-left-on','comment-contradicts-adjacent-code','duplicate-logic-use-existing-helper','type-and-initialization-choice','identifier-name-states-role','missing-explanation-at-declaration','redundant-code-simplify','disabled-code-left-in','declaration-placement-and-file-organization','silent-behavior-change-or-unexamined-threshold']),
 ('Checks on code: lifetime, concurrency, cost and observability', ['index-count-or-wait-set-mismatch','silent-fallback-where-assert-belongs','concurrency-race-or-lock-placement','buffer-lifetime-or-alignment','hot-path-avoidable-work','state-ownership-and-key-granularity','observability-and-operability-of-new-path']),
 ('Checks on tests', ['value-rows-need-consumer-or-provenance','__2','test-silently-skips-or-cannot-fail','tests-run-at-head-before-approve','duplicate-test-coverage','test-name-tag-output-conventions','test-exists-and-reaches-changed-path','workaround-needs-tracking']),
 ('Checks on claims and the PR body', ['claim-wider-than-code','__7','pr-body-and-branch-state','code-comment-carries-no-lasting-fact']),
 ('Checks on scope, history, ownership and automated findings', ['unrelated-or-unexplained-hunk','__11','__12','verify-automated-findings']),
]
INTRO = {
 'Checks on code: hygiene': 'Where most of his comments land (144 of the 238 classified review comments). Each check asks of an added line: who uses it, does the text beside it match it, and does the project already have it.',
 'Checks on code: lifetime, concurrency, cost and observability': 'The checks for the FPGA attention, DMA and scheduler code he reviews most (38 comments). They trace who still reads a buffer, which set a wait covers, what a lock guards, and what a new path costs per token.',
 'Checks on tests': 'Checks 1 to 5 keep their 2026-10-05 text; the widenings from the whole record are appended under each. Test files draw 11 percent of his inline comments.',
 'Checks on claims and the PR body': 'Checks 6 to 9. Wade read the body against the code only on PRs 4557 and 4596; before that his body comments were "stale after the review rounds" (5371062950) and mislabeled options (5106398334).',
 'Checks on scope, history, ownership and automated findings': 'Checks 10 to 12 keep their text with the cross-references the critic added. Check 35 covers the one process habit the record shows on 14 PRs: he verifies a bot finding before endorsing it.',
}
body, questions, procs = [], [], []
for section, labs in ORDER:
    body.append(f'\n## {section}\n\n{INTRO[section]}\n')
    for lab in labs:
        if lab.startswith('__'):
            n = int(lab[2:]); body.append(v1_check(n)); questions.append(v1_q(n)); procs.append(v1_proc(n)); continue
        c = checks[lab]; sm = xref(c['skill_md'].strip())
        if lab in KEEP_V1:
            n = KEEP_V1[lab]; t = v1_check(n)
            t = re.sub(r'^### \d+\. .*$', head(lab, c), t, count=1, flags=re.M)
            t = t.rstrip() + '\n\nWidening from the whole record (2026-10-06):\n\n' + sm + '\n'
            body.append(t); procs.append(v1_proc(n).rstrip() + '\n\nWidening (2026-10-06):\n\n' + xref(c['procedure_md'].strip()) + '\n')
        elif c['disposition'] == 'widen_existing':
            body.append(head(lab, c) + '\n\n' + sm + '\n')
            n = numbers[lab]; procs.append(v1_proc(n).rstrip() + '\n\nWidening (2026-10-06):\n\n' + xref(c['procedure_md'].strip()) + '\n')
        else:
            body.append(head(lab, c) + '\n\n' + sm + '\n'); procs.append(xref(c['procedure_md'].strip()) + '\n')
        questions.append(qline(lab, c))
# fix the 3A/3B question line for v1 check 3 (replaced by the two new lines already)
# cross-check sentences for v1 checks 10, 11, 12
B = '\n'.join(body)
B = B.replace('a cleanup the title or "What changes" lists as bundled.', 'a cleanup the title or "What changes" lists as bundled; a hunk that leaves a symbol, include or parameter with no consumer (check 14 owns it; check 10 asks only whether the hunk belongs); a #define flip (check 16), a commented-out statement (check 23) or a commented-out wait (check 25): those checks own the hunk.')
B = B.replace('Never raise above hygiene.', 'Never raise above hygiene. A review-round commit later than the body\'s last edit also triggers check 8; report the stale body there and the cluster here. Precedent: one squash request in 334 reviews (5420005787) and two rebase asks; PR 4596 was approved at 26 non-merge commits.')
B = B.replace('Do not make every low-level change require new approval, and do not contact reviewers; the finding is the unposted question.', 'Do not make every low-level change require new approval, and do not contact reviewers; the finding is the unposted question. Precedent: n = 1 (4188336279), whose stated reasons are the commit\'s origin (a fold rather than the owner\'s PR) and the line "nothing can catch a regression here"; the placement half alone matches 57 of the 115 PRs in his record where he asked nothing, so both halves are required.')
open('out/body.md', 'w').write(B)
open('out/questions.md', 'w').write('\n'.join(questions) + '\n')
P = '\n\n'.join(procs)
P = P.replace('BASE=$(git -C WT merge-base $HEAD origin/main)', 'BASEOID=$(gh pr view N --repo positron-ai/tron --json baseRefOid -q .baseRefOid)   # the PR\'s base branch, never origin/main\nBASE=$(git -C WT merge-base $HEAD $BASEOID)   # for a merged PR (merge-base returns HEAD) use the first parent of the merge commit, or gh api .base.sha')
open('out/procs.md', 'w').write(P)
open('out/style.md', 'w').write(style['style_md'].strip() + '\n')
open('out/references/wade-style.md', 'w').write(style['full_reference_md'].strip() + '\n')
print('body', len(B), 'questions', len(questions), 'procs', len(P), 'style', len(style['style_md']), 'style-ref', len(style['full_reference_md']))
