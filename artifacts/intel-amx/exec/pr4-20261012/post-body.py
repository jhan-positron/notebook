"""post-body.py: pr-body.md -> pr-body-post.md (the text posted as the PR description) + words-comment.md (the first comment).
Why: GitHub limits a pull-request description to 65,536 characters and the full body (PR4-handoff.md section 6 form) is 84 KB.
Two cuts, no fact lost: (1) the "Words used here" table moves to the first comment of the PR, the section keeps a pointer;
(2) the per-pair bullets of the Measurements subsections ("- TPS of X against Y:" / "- TTFT of ..." / "- Standard deviations ...")
are dropped: every value in them is in the pair and arm tables of "### Runtron cells". A pending whole-machine campaign is
written in its pending form (--w-pending). Re-run after every regeneration of pr-body.md. Usage: python3 post-body.py [--w-pending] [--words-url URL]"""
import pathlib, re, sys
D = pathlib.Path(__file__).resolve().parent
body = (D / 'pr-body.md').read_text()
url = sys.argv[sys.argv.index('--words-url') + 1] if '--words-url' in sys.argv else None
# (1) the glossary table
a = body.index('## Words used here'); b = body.index('## The changes')
words = body[a:b]
assert words.count('\n|') >= 20, 'glossary table expected'
intro = ("Words used here: the glossary of the description of this PR. It is a comment because GitHub limits a description to 65,536 "
         "characters. The description's section of the same name points here.\n\n")
(D / 'words-comment.md').write_text(intro + words[len('## Words used here'):].lstrip('\n'))
where = f"[the first comment of this PR]({url})" if url else "the first comment of this PR"
pointer = ("## Words used here\n\nThe glossary of this description, one row per term, is " + where +
           " (GitHub limits a description to 65,536 characters). It defines the code names, the measurement terms and the machine terms used below. "
           "A term is also defined in a clause at its first use where the sentence needs it.\n\n")
body = body[:a] + pointer + body[b:]
# (2) the per-pair bullets of the Measurements subsections
m0 = body.index('## Measurements'); m1 = body.index('### Token identity')
meas = body[m0:m1]
out, skip = [], False
for l in meas.splitlines(keepends=True):
    if re.match(r'- (TPS|TTFT) of `|- Standard deviations and HW-attention losses:', l): skip = True; continue
    if skip and l.startswith('  - '): continue
    skip = False; out.append(l)
meas2 = re.sub(r'\n{3,}', '\n\n', ''.join(out))
body = body[:m0] + meas2 + body[m1:]
# (3) the pending campaign
if '--w-pending' in sys.argv:
    a = body.index('- Passes: base, target, target, base ({{W_PASSES}})'); b = body.index('{{W_MEM_TEXT}}') + len('{{W_MEM_TEXT}}')
    body = body[:a] + (
"- Passes: base, target, target, base, 10 rounds of one request per user each. TPS is captured over generated tokens 896 to 1024. The paired t pools the rounds of both pass pairs.\n"
"- Dates: pending. The campaign is scheduled on the test machine after the nightly CI of 2026-10-13, at 13:00 UTC at the earliest.\n"
"- Memory: VmHWM and VmRSS of every rinzler process, summed over the engines, read after every provisioning and every benchmark.\n\n"
"Status at posting: pending. A cell is resolved when its target differs from its base beyond noise: the paired t is at least 2.26 in magnitude and the difference is at least 1 % (for TTFT also at least 1 ms). This section is updated when the campaign completes: the TPS, TTFT and memory table of the three configurations, the comparison with the PR #4424 campaign of 2026-10-09 on the same configurations, and the memory text.") + body[b:]
left = re.findall(r'\{\{[A-Z_0-9]+\}\}', body); assert not left, left
(D / 'pr-body-post.md').write_text(body)
print(f'pr-body-post.md: {len(body)} chars ({len(body.encode())} bytes); words-comment.md: {len((D / "words-comment.md").read_text())} chars')
