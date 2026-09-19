---
name: plain-english
description: Use when writing or rewriting prose - chat answers, HTML reports, commit messages, PR descriptions, documents, code comments - or when the user asks to check, review, or fix text (define terms, one claim per sentence, units on numbers, Short version first, no idioms, bullets for multi-point paragraphs, short sentences). Also use when the user says "plain English", "unpack this", or "explain this in plain English".
---

# Plain English for engineers

Write so that an engineer who has never seen the project can follow the text on first read.

Two modes:

- **Write**: produce new prose (report, commit message, document, answer) that follows the rules below.
- **Check**: given existing text, list every rule violation with the exact phrase and a corrected version, then output the full corrected text.

If the user did not say which mode, infer it: text supplied to you means Check; a request to produce text means Write.

## The rules

### Rule 1 - Define a term at first use

Add one clause in parentheses, or a "Words used here" list at the top, whenever ANY of these holds:

- The term is a name from the code or the project: a program, branch, function, file, label, machine, or build variant.
- The term is an abbreviation or an acronym.
- The term is a statistic or a metric name: a percentile, a norm, an error measure.
- A general dictionary does not give the meaning used here.

When in doubt, define it. Undefined shorthand is a defect, not a style choice.

Before writing, check the project's CLAUDE.md for a per-project term list; reuse those definitions verbatim.

Definition forms, in order of preference:

1. Inline clause: "rinzler (the FPGA reset helper) cleared the stuck queue."
2. "Words used here" list at the top, when more than three terms need definition or a term recurs in every paragraph.

A term defined once in a document does not need redefinition later in the same document. A chat reply is one document; a new reply starts fresh.

### Rule 2 - One claim per sentence

State the test, then the observation, then the meaning, each as its own sentence.

- Good: "We ran X twice. The outputs were identical. So later differences come from what we changed."
- Bad: "Since running X twice gave identical outputs, later differences must come from what we changed."

Splitting test: if a sentence contains "because", "since", "which means", "so that", or a semicolon, try to split it.

### Rule 3 - Numbers carry units and a plain meaning

Every number gets a unit and, when the reader cannot judge it alone, a clause saying what it means.

- Good: "0.125 (one bf16 notch at that size)"
- Good: "300 us (about 3% of one iteration)"
- Bad: "0.125"
- Bad: "the delta was 300"

Label estimates "est." with units. Never present an estimate where a measurement exists.

### Rule 4 - Citations follow the sentence, in brackets

A citation or a file:line reference comes after a plain sentence that already carries the claim. It never replaces the sentence.

- Good: "The guard re-checks the lease before each run [exec/lib-guard.sh:112]."
- Bad: "See exec/lib-guard.sh:112."

### Rule 5 - Every report or long answer starts with a "Short version"

At most three sentences. A newcomer must be able to follow them without reading the rest. Apply this to anything longer than about one screen: reports, HTML pages, long chat answers, design notes.

Short chat replies (a few sentences), commit subject lines, and code comments are exempt.

### Rule 6 - No idioms, metaphors, wordplay, or uncommon words

Clever phrasing costs the reader comprehension.

- Good: "the fix removed the 300 us stall"
- Bad: "the fix clawed back the stall", "the stall evaporated", "the bug bit us", "under the hood", "low-hanging fruit", "moving parts", "a wash", "noise floor" (unless defined)

Test: would a non-native English speaker with an engineering degree need to guess? If yes, replace with the literal verb.

### Rule 7 - Use bullet points and blank lines to separate points

When one paragraph carries several separate points, break it into bullet points. Otherwise separate sentence groups with a blank line.

### Rule 8 - Prefer short sentences

Break a sentence with several subordinate clauses into short sentences. If two clauses must stay together, join them with ", and" or ", or". Do not use a semicolon.

## Code comments

Rules 2 and 6 apply in full.

Rule 1 applies only to terms imported from outside the code: an instruction set name, a math term, a notion from a paper. A name visible in the surrounding code needs no definition.

- Good: `// AMX tile (16 rows x 64 bytes) holds one bf16 block`
- Good: `// Kahan summation (carries the rounding error into the next add)`
- Bad: `// use the tile` (what is a tile?) in a file where "tile" is not a code identifier

## Check-mode output format

1. A "Short version" line: how many violations, by rule number.
2. A table with columns: Rule, Original phrase, Fix.
3. The full corrected text.

Report zero violations plainly when there are none. Do not invent violations to fill the table.

## Self-check before returning (both modes)

Walk the text once per item:

- [ ] Every code name, acronym, and metric is defined at first use, or listed under "Words used here".
- [ ] No sentence carries two claims.
- [ ] Every number has a unit and, where needed, a meaning clause. Estimates are marked "est.".
- [ ] Every citation follows a sentence; none stands alone.
- [ ] Text longer than one screen opens with a "Short version" of at most three sentences.
- [ ] No idioms, metaphors, or uncommon words remain.
- [ ] No paragraph carries several separate points without bullets or a blank line.
- [ ] No sentence has more than one subordinate clause.
