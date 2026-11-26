export const meta = {
  name: 'gdn-design-plain-english-verify',
  description: 'Verify the plain-English rewrite of the GDN design page: no fact changed or lost, rules met by reading, layout intact (read-only)',
  phases: [
    { title: 'Verify', detail: 'four readers compare old and new text section by section, one checks the browser layout' },
  ],
}

const SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-GDN/6abaa6d4-a2e5-4e74-bd4c-106db969141b/scratchpad'
const PE = SP + '/pe'

const COMMON = [
  'A design page was rewritten to a strict plain-English rule set. An external reviewer had accepted the content of the page before the rewrite. So the rewrite may change wording and structure only. You check one part of it. You do not edit anything.',
  '',
  'The rule set: /home/jhan/.claude/skills/plain-english-experiment/SKILL.md. Read it in full first. It is an experimental version of the plain-English rules that you may know. Where the two differ, the experimental rules win (at most 25 words per sentence, 21 to 25 only for one simple claim, no clause inside a clause, no semicolon, a parenthesis of at most 8 words, at most 3 sentences per paragraph or bullet, lists for sequences and for several aspects, no label at the start of a bullet, short simple sentences are not split).',
  '',
  'Files:',
  '- Old text (accepted by the reviewer): ' + PE + '/base/page-text.txt (653 lines). Old page: ' + PE + '/base/out/page.html.',
  '- New text (the rewrite): ' + PE + '/merged/page-text.txt (1,132 lines). New page: ' + PE + '/merged/out/page.html. In both text files a figure appears as [SVG...] lines, a table row as one line with " | " between cells, and a bullet as a line that starts with "- ".',
  '- Generator sources, old and new: ' + PE + '/base/gen/ and ' + PE + '/merged/gen/ (gen_design.py and design_numbers.py hold the text; use diff -u to see what changed).',
  '- The length check, already run on the new page with zero lines printed: python3 ' + PE + '/tools/check_page.py ' + PE + '/merged/out/page.html. It counts words and sentences. It cannot see meaning, labels, a clause inside a clause, idioms or terms. Those are your job.',
  '- The number comparison: python3 ' + PE + '/tools/numbers_diff.py ' + PE + '/base/out/page.html ' + PE + '/merged/out/page.html. It prints 23 tokens. 21 of them are the same number counted with or without a following comma. Two names occur once more ("Part 0" and "AVX-512").',
  '',
  'Hard rules: read-only. Do not modify, create or delete any file under /home/jhan/workspace or under ' + PE + '/base, ' + PE + '/merged or ' + PE + '/agents. Scratch files go only under ' + PE + '/verify/<your key>/. Do not ssh anywhere. Do not use the network. This shell may use 6 CPUs.',
  '',
  'What to report (only real problems):',
  '- A fact, number, unit, condition, cause or degree of certainty that differs between old and new text. Examples: a hypothesis that now reads as a fact, a condition that got lost when a sentence was split, "est." or "measured" dropped or added wrongly, "at most" turned into "about".',
  '- A fact of the old text that is missing in the new text, or a new claim that the old text does not make. Definitions of terms that the rewrite added count as new claims only when they are wrong or unsupported: check them.',
  '- A reference mark [RefN] that moved away from the sentence that carries its claim, or that is missing.',
  '- A rule violation that the length check cannot see: a label at the start of a bullet (bold or plain, such as "Clock." or "Benefit:"), a bold run-in of 6 words or fewer, a clause inside another clause, an idiom or metaphor, a sentence that holds a test, an observation and a meaning together, a term that is used before it is defined and is not in the "Words used here" list, a term defined twice, a number without a unit, a short simple sentence that was split without need, filler text, a list whose order matters but is not numbered.',
  '- A place where the new structure hides the point: a nested list that separates a claim from its reason, a sub-heading that does not match the bullets under it.',
  'For each problem give: the place (section and the first words of the bullet or cell), the old sentence, the new text, what is wrong, and the exact corrected wording (it must itself obey the rules). Zero problems is a valid result. Say what you compared and what you could not check.',
  '',
].join('\n')

const TASKS = [
  { key: 'a', prompt: 'Your key: a. Your part: from the top of the page to the end of section 3 (title, meta line, Short version, the summary table, the whole "Words used here" list, sections 1, 2 and 3 with their figure captions and tables). Go through the old text of this part sentence by sentence and find each sentence\'s content in the new text. Check the Short version with special care: it must hold at most three sentences, each within the limits, a newcomer must be able to follow it, and it must not claim more or less than the old one (old: 24 of 32 layers are GDN layers, GDN is a layer that keeps a memory matrix of fixed size, tron runs no AMX code for this model today, three changes are proposed, the table gives what each is predicted to do to the time to first token, nothing is built, every gain is an estimate from the baseline measured on delphi-3b35). Check every entry of the "Words used here" list: same meaning as before, no term lost.' },
  { key: 'b', prompt: 'Your key: b. Your part: all of section 4 (Method with its sub-headings and formula block, the factor table with every basis bullet, the clock note, figures 9 and 10 with captions, the per-cell table, "How to read the prediction", "What would prove the prediction wrong", the note "Seen in the same data"). This part holds the prediction model and most numbers of the page. Go through the old text sentence by sentence and find each sentence\'s content in the new text. Pay special attention to conditions and certainty: "The model assumes", "Assumption of the model", "Hypothesis", "is not measured", "Insufficient data", "est.", low case, working value, high case.' },
  { key: 'c', prompt: 'Your key: c. Your part: all of section 5 (5.1 to 5.7: the table of 5.1, figure 11, section 5.2, section 5.3 with its two tables and their notes and figures 12 and 13, section 5.4 on numerics, section 5.5, the code structure table of 5.6, section 5.7). Go through the old text sentence by sentence and find each sentence\'s content in the new text. Pay special attention to section 5.4: the split rule, the powers of two (2^-103, 2^-110, 2^-126, 2^-133, 2^-149), the values 3.3895314e38 and 3.3961775e38, which statements are exact and which hold "in the checks", the fallback, the contract and the two consequences to accept.' },
  { key: 'd', prompt: 'Your key: d. Your part: section 6 (the plan table, the block "Which runs tasks 2, 5 and 6 compare" with its two tables and notes, the open points) and section 7 (the 23 source entries). For section 7 check that every file path, line range and code name of the old entries is still there, that the 23 entries keep their order, and that each definition that the rewrite added to an entry is correct (check code terms against the tron source copy at /home/jhan/workspace/ai-runs/tron-qwen35-4b). Then do one pass over the whole new text for consistency of terms between the parts that different writers rewrote: the same thing must have the same name everywhere (for example base build, base run, column-half path, block path, full-page time, other attention work, join wait, attention wait, memory stall, tile run, turn, working value, low case), and a sub-heading in one section must not use a term in another sense than the word list.' },
  { key: 'e', prompt: 'Your key: e. You check the layout of the new page in a real browser. The headless Chromium is /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell with the flags --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer --hide-scrollbars --window-size=W,H --timeout=20000 --screenshot=<png> <file url>. A file URL with a #fragment gives a blank screenshot here. An earlier checker covered the whole page with tiles through wrapper pages and helper scripts: they are in ' + SP + '/round2-final/browser/ and ' + SP + '/round2-verify/browser/ (shot.sh, dump.sh, cols.js and others). Copy what you need into your scratch folder and point it at the new page ' + PE + '/merged/out/page.html. The rewrite added: 22 sub-headings (h4 elements, with a new CSS rule), nested lists in bullets, lists inside table cells (factor table, code structure table, plan table), lists inside figure captions, lists inside entries of the folded "Words used here" block and of the source list. Check at desktop width (1280 px) and at phone width (390 px): the h4 sub-headings are visible as headings and are smaller than the h3 headings, nested lists are indented and readable, a list inside a table cell or a caption does not overflow or collide with other content, the folded word list opens correctly (render a copy with the details element open), the page does not scroll sideways as a whole, no table column is unreachable, no raw tag text is visible, and the 13 figures are unchanged against the old page ' + PE + '/base/out/page.html (compare the svg elements as text). Report each layout defect with the screenshot path, the position and the smallest CSS or markup correction.' },
]

const SCHEMA = {
  type: 'object',
  properties: {
    problems: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          kind: { type: 'string', enum: ['meaning changed', 'fact lost', 'fact added', 'reference', 'rule', 'structure', 'layout'] },
          place: { type: 'string' },
          old_text: { type: 'string' },
          new_text: { type: 'string' },
          problem: { type: 'string' },
          correction: { type: 'string' },
        },
        required: ['id', 'kind', 'place', 'old_text', 'new_text', 'problem', 'correction'],
      },
    },
    compared: { type: 'string' },
    not_checked: { type: 'string' },
  },
  required: ['problems', 'compared', 'not_checked'],
}

phase('Verify')
const results = await parallel(TASKS.map(t => () =>
  agent(COMMON + t.prompt, { label: 'verify:' + t.key, phase: 'Verify', schema: SCHEMA }).then(r => ({ key: t.key, result: r }))
))
return results.filter(Boolean)
