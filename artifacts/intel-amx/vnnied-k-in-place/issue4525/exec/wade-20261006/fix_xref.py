import re, sys, json
PREFIX = {'dead-symbol':'14','typo-or-wording':'15','magic-literal':'13','debug-switch':'16','comment-contradicts':'17','duplicate-logic':'18','type-and-initialization':'19','identifier-name':'20','missing-explanation':'21','redundant-code':'22','disabled-code':'23','declaration-placement':'24','silent-behavior-change':'25','silent-behavior':'25','index-count':'26','silent-fallback':'27','concurrency-race':'28','buffer-lifetime':'29','hot-path':'30','state-ownership':'31','observability-and-operability':'32','test-exists':'33','workaround-needs-tracking':'34','verify-automated':'35','value-rows':'1','test-silently-skips':'3A','tests-run':'3B','duplicate-test':'4','test-name-tag':'5','claim-wider':'6','pr-body-and-branch':'8','code-comment-carries':'9','unrelated-or-unexplained':'10'}
for fn in sys.argv[1:]:
    t = open(fn).read(); n0 = t
    for p in sorted(PREFIX, key=len, reverse=True):
        # slug possibly extended with more -words, optionally followed by " (x)" or " x" sub-letter
        t = re.sub(r'(?<![\w`/])' + re.escape(p) + r'(?:-[a-z]+)*(?:\s*\(?\b([a-zA-Z]|[A-Z]\d?)\)?)?(?=[\s,;:.)])', lambda m: f'check {PREFIX[p]}' + (f' ({m.group(1)})' if m.group(1) and len(m.group(1))<=2 else ''), t)
    t = t.replace('check check', 'check')
    left = sorted(set(re.findall(r'(?<![\w`/])[a-z]+(?:-[a-z]+){1,}(?=[\s,;:.)])', t)))
    sus = [w for w in left if any(w.startswith(p.split('-')[0]) for p in PREFIX) and w not in ('hand-written','non-blocking','read-only','test-only','debug-only','value-suffixed','type-safety','pre-merge','post-review','one-line','two-way','off-state','hot-path','follow-up','merge-base','first-parent','dead-code','magic-number','commented-out')]
    open(fn, 'w').write(t)
    print(fn, 'changed' if t != n0 else 'unchanged', 'suspect slugs:', sus[:40])
