---
name: plain-english-experiment
description: Experimental version of the plain-english skill, for side-by-side trials. Use it only when the user names it - "plain-english-experiment", "/plain-english-experiment", or "the experimental plain English rules" - for writing, rewriting or checking prose. When invoked, its rules replace the rules of the plain-english skill for that task. It differs in four ways - a sentence has at most 25 words; a short sentence with short, simple clauses stays whole; long paragraphs, developed points and steps become lists; bullets carry no labels. For a plain "plain English" request that does not say "experiment", use the plain-english skill instead.
---

# Plain English for engineers (experimental version)

This skill is an experiment. It is a reworded version of the plain-english skill.

- Follow the rules below for the whole task.
- The rules of the plain-english skill may also be in your context. Where the two differ, the rules below win.

Write so that an engineer who has never seen the project can follow the text on first read.

Two modes:

- **Write**: produce new prose (report, commit message, document, answer) that follows the rules below.
- **Check**: given existing text, list every rule violation with the exact phrase and a corrected version. Then output the full corrected text.

If the user did not say which mode, infer it. Text supplied to you means Check. A request to produce text means Write.

## The rules

### Rule 1 - No idioms, metaphors, wordplay, or uncommon words

Clever phrasing costs the reader comprehension.

- Good: "the fix removed the 300 us stall"
- Bad: "the fix clawed back the stall", "the stall evaporated", "the bug bit us", "under the hood", "low-hanging fruit", "moving parts", "a wash", "noise floor" (unless defined)

Test: would a non-native English speaker with an engineering degree need to guess? If yes, replace with the literal verb.

### Rule 2 - One claim per sentence

State the test, then the observation, then the meaning, each as its own sentence.

- Good: "We ran X twice. The outputs were identical. So later differences come from what we changed."
- Bad: "Since running X twice gave identical outputs, later differences must come from what we changed."

Splitting test: if a sentence contains "because", "since", "which means", "so that", or a semicolon, try to split it.

Short, simple clauses about one subject may share a sentence. Do not split them.

- Keep: "The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation."

### Rule 3 - A sentence has at most 25 words

Count the words. Words inside parentheses count too.

- Over 25 words: always fix the sentence.
- 21 to 25 words: fix it, unless it makes one simple claim.
- 20 words or fewer: leave it alone when its clauses are short and simple.
- At any length: no clause sits inside another clause, and no semicolon.

Apply the first fix that fits:

1. The sentence holds a list of items, values or actions. Make it a list (Rule 4).
2. The sentence joins two claims. Split it at the join: ", and", ", but", ", so", "because", ", which", or a colon.
3. The sentence holds a parenthesis of more than 8 words. Move that text into its own sentence.
4. None of the above fits. Cut words, or split the sentence at its second verb.

Start a second sentence with "So", "But", "Then" or "This". That keeps the link. A split must not change a condition, a cause, or how certain the claim is.

- Bad, 27 words: "Parts A, B and C are complete on CRB (the Arm server under test), and Part D (the steps that need administrator rights) was not run."
- Good: "Parts A, B and C are complete on CRB (the Arm test server). Part D was not run. It holds the steps that need administrator rights."
- Bad, a clause inside a clause: "Because the reader, which starts before initialization finishes, can observe an empty queue, the test sometimes fails."
- Good: "The reader starts before initialization finishes, so it can observe an empty queue. That can cause the test to fail."

### Rule 4 - Use a list for long paragraphs, developed points and steps

Use a list in these cases.

- A sentence over the limit of Rule 3 holds a list or a sequence.
- Three or more sentences in a row each cover a different aspect of one thing.
- A sequence has steps that each need a sentence of their own.

Keep prose in these cases.

- One short sentence names several aspects: "The cache reduces repeated reads, it uses more memory, and it needs explicit invalidation."
- One short sentence names a few steps: "Check the lease, start the run, then save the log."
- A fact, its reason and its meaning are one point. They stay a paragraph.

Form:

- Start each bullet directly with its content. Do not add a label such as "Benefit:" or "Cost:".
- Use a numbered list when the order matters.
- A paragraph has at most three sentences. A bullet has at most three sentences.
- A longer paragraph becomes a list, or two paragraphs.

Example of a list inside a long sentence:

- Bad: "The total is 230 to 310 GB/s above 30 lines, 459 to 480 GB/s at 12 to 28 lines, and 544 to 549 GB/s at 8 to 12 lines."
- Good:

  The total depends on the depth:

  - above 30 lines: 230 to 310 GB/s
  - 12 to 28 lines: 459 to 480 GB/s
  - 8 to 12 lines: 544 to 549 GB/s

Example of several aspects of one thing:

- Bad: "The cache avoids repeated reads when requests reuse the same records. It retains those records in memory until eviction, so memory use grows with the retained data. Writers must invalidate changed records before later requests read them, or those requests may receive stale values."
- Good:

  - The cache avoids repeated reads when requests reuse the same records.
  - It retains records in memory until eviction. Memory use grows with the retained data.
  - Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

Example of a sequence:

- Bad: "I will fill in the run ids, then edit the description, then post the replies as one review, and then ask for a new review of the whole change."
- Good:

  1. Fill in the run ids.
  2. Edit the description.
  3. Post the replies as one review.
  4. Ask for a new review of the whole change.

### Rule 5 - Citations at the end of document, citation index at the end of sentence, in brackets

- Put all citations and file:line references in a reference section towards the end of the document.
- In the body, write a plain sentence that carries the claim. Then add the reference index.
- The index never replaces the sentence.

- Good: "The guard re-checks the lease before each run [Ref10]."
- Bad: "See exec/lib-guard.sh:112."

### Rule 6 - Numbers carry units and a plain meaning

Every number gets a unit. When the reader cannot judge the number alone, add a clause that says what it means.

- Good: "0.125 (one bf16 notch at that size)"
- Good: "300 us (about 3% of one iteration)"
- Bad: "0.125"
- Bad: "the delta was 300"

Keep the meaning clause to at most 8 words. A longer meaning becomes its own sentence.

Label estimates "est." with units. Never present an estimate where a measurement exists.

### Rule 7 - Every report or long answer starts with a "Short version"

- At most three sentences. Each one obeys the limits of Rule 3.
- A newcomer must be able to follow them without reading the rest.
- Apply this to anything longer than about one screen: reports, HTML pages, long chat answers, design notes.

Short chat replies (a few sentences), commit subject lines, and code comments are exempt.

### Rule 8 - Define a term at first use

Add one clause in parentheses, or a "Words used here" list at the top, whenever ANY of these holds:

- The term is a name from the code or project: a program, branch, function, file, label, machine, or build variant.
- The term is an abbreviation or an acronym.
- The term is a statistic or a metric name: a percentile, a norm, an error measure.
- A general dictionary does not give the meaning used here.

When in doubt, define it. Undefined shorthand is a defect, not a style choice.

Before writing, check the project's CLAUDE.md for a per-project term list. Reuse those definitions verbatim.

Definition forms, in order of preference:

1. Inline clause of at most 8 words: "rinzler (the FPGA reset helper) cleared the stuck queue."
2. A sentence of its own before the first use, when the definition needs more than 8 words.
3. "Words used here" list at the top. Use it when more than three terms need definition, or a term recurs in every paragraph.

Define a term once in a document. Do not repeat the clause at later uses.

A chat reply is one document. A new reply starts fresh.

When generating HTML file, use folderable list (folded by default) for "Words used here" section.

## Code comments

Rules 1, 2 and 3 apply in full.

Rule 8 applies only to terms imported from outside the code. Examples: an instruction set name, a math term, a notion from a paper. A name visible in the surrounding code needs no definition.

- Good: `// AMX tile (16 rows x 64 bytes) holds one bf16 block`
- Good: `// Kahan summation (carries the rounding error into the next add)`
- Bad: `// use the tile` (what is a tile?) in a file where "tile" is not a code identifier

## Check-mode output format

1. A "Short version" line: how many violations, by rule number.
2. A table with columns: Rule, Original phrase, Fix.
   - For Rule 3, the Original phrase is the first six words of the sentence, then its word count.
   - For Rule 4, the Original phrase is the first six words of the paragraph, then its sentence count.
3. The full corrected text.

Report zero violations plainly when there are none. Do not invent violations to fill the table.

## Self-check before returning (both modes)

Walk the text once per item. Count. Do not judge by eye.

- [ ] No sentence has more than 25 words.
- [ ] No sentence of 21 to 25 words joins claims or holds a list.
- [ ] No clause sits inside another clause.
- [ ] No paragraph and no bullet has more than three sentences.
- [ ] No parenthesis has more than 8 words.
- [ ] No short, simple sentence was split. No bullet starts with an added label.
- [ ] No sentence carries a test, an observation and a meaning together.
- [ ] Text longer than one screen opens with a "Short version" of at most three sentences.
- [ ] Every code name, acronym, and metric is defined at first use, or listed under "Words used here".
- [ ] Every number has a unit and, where needed, a meaning clause. Estimates are marked "est.".
- [ ] Every citation follows a sentence. None stands alone.
- [ ] No idioms, metaphors, or uncommon words remain.

When the output is a file and you can run commands, run `scripts/check_lengths.py FILE` from this skill's folder with python3. Fix every line it prints. Run it again until it prints nothing.
