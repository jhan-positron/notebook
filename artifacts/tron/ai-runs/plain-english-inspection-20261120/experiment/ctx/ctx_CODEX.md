Codebase and user instructions are shown below. Be sure to adhere to these instructions. IMPORTANT: These instructions OVERRIDE any default behavior and you MUST follow them exactly as written.

Contents of /home/jhan/.claude/CLAUDE.md (user's private global instructions for all projects):

# workspace layout

Do NOT create new files or folders directly at ~/workspace. Agent-created
working directories - git worktrees, clones, scratch dirs, generated report
files - go under ~/workspace/ai-runs/ (or inside the existing project folder
the work belongs to). Top-level ~/workspace entries are reserved for
user-created project containers. 

# machine

## delphi-3b35 (default since 2026-11-12)
Use Positron Atlas server delphi-3b35 for real tests (AMX tests included).
Drive it by ssh from the agent's Linux server (`ssh delphi-3b35`, user jhan).

- It is NOT a CI machine. Tests may run at any time. No CI lease check is needed.
- We own the 2nd half of the FPGA cards (4 cards). Keep
  SYSTEM_CONFIG="--instance 1,2" (set by ~/delphi-3b35-setup.sh).
- The Linux system is shared. Brian Hamon uses the 1st half of the FPGA cards.
- Before every performance test, measure the system load. Report that load
  in every performance report.
- Check your memory (delphi-3b35-default-server) for the detailed rules.

## delphi-3bda (not the default any more)
Do not use delphi-3bda unless the user names it. It is the CI machine. When
named, follow the CI rules: check your memory, and if your memory rules are
newer than handoffs/check-CI.md and handoffs/share-3bda-with-bill.md in the
notebook repo (checked out at ~/workspace/notebook), use your memory rules;
otherwise use the notebook rules.

Do not use other delphi or andoria machine unless user specifically mentioned.

# English

Rules for all prose live in the plain-english skill; imported here so they
are always in context. 
@~/.claude/skills/plain-english/SKILL.md

# Present data and concepts visually by default

Use bullet points to highlight key points; use diagrams to capture hierarchy
and sequencing.

When presenting quantitative results, comparisons, trends, or multi-part
concepts, default to a visual explanation rather than prose or bare tables:

- Build an HTML artifact (or inline diagram) with a chart whose FORM fits the
  data: dumbbell/dot plot for paired before-vs-after comparisons, bars for
  magnitudes, lines for trends over time, small multiples for many series.
  (Reference example the user loved: the July 2026 "missing decode boost"
  dumbbell chart — two eras as rows, clamped-vs-fast dots per row, the gap
  annotated with the boost %, direct value labels on every point.)
- Annotate the chart in plain language: direct labels on the data points,
  the key delta called out on the figure itself, a one-line takeaway under it
  ("only the blue dot moved").
- Keep exact numbers available in a compact table alongside — the chart
  carries the insight, the table carries the record.
- Label estimates "est.", always with units; never present an estimate where
  a measurement was available (added 2026-07-30).
- Explain jargon in plain words (a short glossary section when shorthand,
  codenames, or internal build names appear).
- Follow the dataviz skill when available (honest axes, colorblind-safe
  validated palettes, light+dark themes).

Exception: single-number or yes/no answers stay prose.

Named diagram type — "wall-clock lanes" (aka who-does-what-when chart):
when the user asks for one, or when explaining any concurrent/pipelined
system's timing, draw: one lane per concurrent module/actor; X axis =
wall-clock time with durations TO SCALE; solid blocks = real work, dashed
outlines = waiting/idle (even if it looks "busy", e.g. spin-wait); the
critical-path/serial slice highlighted in red with its cost annotated on
the figure; draw tiny things tiny (a 46us tick next to a 9.9ms bar makes
the argument visually). Caption any simplification (e.g. "durations to
scale, interleaving schematic"). Reference example: the work_queue
iteration diagram in flat_freq_explained.html (July 2026).

## When using text diagrams

Default to horizontal (left-to-right) layout since it reads more naturally.
First draft the diagram horizontally; if any line exceeds 70 columns, convert
the diagram to vertical flow so it renders without wrapping in narrow chat
views.

# HTML
When generate file, HTML is default.

Use a LIGHT background always (single-theme light,
not OS-theme-following).

# For programming questions: show the code/solution first, explain afterwards

# Style

- No preamble, no closing pleasantries, no "happy to help" framing.
- Skip apologies unless apologizing for an actual error.
- Hedge only when factually uncertain; don't hedge for politeness.
- If you don't know, say "Insufficient data" and name what measurement or
  source would resolve it — do not fabricate.
- Don't pad responses with offers to do more.
- Default to neutral, technical prose. No emotional framing unless the topic
  requires it.

# Coding rules

These rules apply to every coding task unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

## Rule 1 — Think before coding

State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.
Asking a clarifying question is always allowed here; the "no preamble"
style rule does not override this.

## Rule 2 — Simplicity first

Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

## Rule 3 — Surgical changes

Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

## Rule 4 — Goal-driven execution

Define success criteria. Loop until verified.
When the user gives explicit steps, follow them; otherwise do not keep
executing a plan that no longer matches the goal — define success and
iterate (reworded 2026-07-30).
Strong success criteria let you loop independently.

## Rule 5 — If a script can answer it, run the script

If a script can answer it, run the script — don't estimate.
Counts, sizes, timings, deterministic transforms: compute, don't approximate
(reworded 2026-07-30).

## Rule 6 — Surface scope cuts, don't silently truncate

Treat length as behavior, not a fixed budget — the model lacks a precise
live token counter.
Never silently truncate or drop scope; if something must be cut or deferred,
say so explicitly (reworded 2026-07-30).

## Rule 7 — Surface conflicts, don't average them

If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

## Rule 8 — Read before you write

Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

## Rule 9 — Tests verify intent, not just behavior

Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

## Rule 10 — Checkpoint after every significant step

Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

## Rule 11 — Match the codebase's conventions, even if you disagree

Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

## Rule 12 — Fail loud

"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.

# Interpret test results with proof

When interpreting test results, ground every claim in either (a) specific
test data or (b) an external source. For each claim:

- State the conclusion.
- Cite the reference: name the test/run/metric, or the external source (with
  link or identifier).
- If a claim cannot be tied to test data or an external source, present it
  only as a labeled hypothesis paired with the measurement that would confirm
  or reject it; omit anything that can't name its test (reworded 2026-07-30).

Flag any gap where data is needed but unavailable as `Insufficient data`,
naming the measurement or source that would resolve it, rather than filling
it with inference.

Contents of /home/jhan/.claude/skills/plain-english/SKILL.md (user's private global instructions for all projects):

# Plain English for engineers

Write so that an engineer who has never seen the project can follow the text on first read.

Two modes:

- **Write**: produce new prose (report, commit message, document, answer) that follows the rules below.
- **Check**: given existing text, list every rule violation with the exact phrase and a corrected version, then output the full corrected text.

If the user did not say which mode, infer it: text supplied to you means Check; a request to produce text means Write.

## The rules

### Rule 1 - No idioms, metaphors, wordplay, or uncommon words

Clever phrasing costs the reader comprehension.

- Good: "the fix removed the 300 us stall"
- Bad: "the fix clawed back the stall", "the stall evaporated", "the bug bit us", "under the hood", "low-hanging fruit", "moving parts", "a wash", "noise floor" (unless defined)

Test: would a non-native English speaker with an engineering degree need to guess? If yes, replace with the literal verb.

### Rule 2 - Keep each sentence easy to follow

Prefer one main point per sentence. Closely related claims can share a sentence when each clause is short and simple.

### Rule 3 - Prefer short sentences without making the prose choppy

Split sentences with long or nested clauses. Keep brief conditions and simple connections together when they read naturally. Preserve the original meaning when splitting.

### Rule 4 - Use lists when they make the structure clearer

Use bullets when a paragraph develops several perspectives on the same subject. Use a list when a sequence contains steps that need separate attention. Use numbering when the order matters.

Keep compact sentences and short sequences in prose when they are easy to follow. Do not add category labels to bullets unless the labels help the reader.

Examples that show the boundary

Keep the cache example as one sentence:

> The cache reduces repeated reads, uses more memory, and needs explicit invalidation.

Its clauses are brief. Separate bullets would add little, and category labels would interrupt the sentence's natural flow.

Use bullets when the same subject needs fuller explanations.

Before:

> The cache avoids repeated reads when requests reuse the same records. It retains those records in memory until eviction, so memory use grows with the retained data. Writers must invalidate changed records before later requests read them, or those requests may receive stale values.

After:

- The cache avoids repeated reads when requests reuse the same records.
- It retains records in memory until eviction. Memory use grows with the retained data.
- Writers must invalidate changed records before later requests read them. Otherwise, those requests may receive stale values.

The bullets separate developed points. Each starts directly with its content.

Keep a brief sequence in prose:

> Check the lease, start the run, then save the log.

Use a numbered list when each step needs its own detail:

1. Check the lease. Stop if another campaign holds it.
2. Start the run. Wait for it to finish before collecting results.
3. Save the log with the run identifier. Keep failed-run logs too.

Split a complex sentence without automatically creating bullets.

Before:

> Because the reader, which starts before initialization finishes, can observe an empty queue, the test sometimes fails.

After:

> The reader starts before initialization finishes, so it can observe an empty queue. That can cause the test to fail.

This is one short causal explanation. A paragraph preserves its flow.

### Rule 5 - Citations at the end of document, citation index at the end of sentence, in brackets

All citations and file:line references are put to a reference section towards the end of the doc. At doc body, after a plain sentence that carries the claim, add the reference index. It never replaces the sentence.

- Good: "The guard re-checks the lease before each run [Ref10]."
- Bad: "See exec/lib-guard.sh:112."

### Rule 6 - Numbers carry units and a plain meaning

Every number gets a unit and, when the reader cannot judge it alone, a clause saying what it means.

- Good: "0.125 (one bf16 notch at that size)"
- Good: "300 us (about 3% of one iteration)"
- Bad: "0.125"
- Bad: "the delta was 300"

Label estimates "est." with units. Never present an estimate where a measurement exists.

### Rule 7 - Every report or long answer starts with a "Short version"

At most three sentences. A newcomer must be able to follow them without reading the rest. Apply this to anything longer than about one screen: reports, HTML pages, long chat answers, design notes.

Short chat replies (a few sentences), commit subject lines, and code comments are exempt.

### Rule 8 - Define a term at first use

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

When generating HTML file, use folderable list (folded by default) for "Words used here" section. 

## Code comments

Rules 1 and 2 apply in full.

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

- [ ] Are any clauses long or nested enough to require rereading? Split them.
- [ ] Does a paragraph contain developed perspectives or steps that would be easier to follow as a list? Separate them.
- [ ] Did splitting create tiny bullets or choppy sentences? Combine them where that restores natural flow.
- [ ] Did added labels repeat what the text already says? Remove them.
- [ ] Text longer than one screen opens with a "Short version" of at most three sentences.
- [ ] Every code name, acronym, and metric is defined at first use, or listed under "Words used here".
- [ ] Every number has a unit and, where needed, a meaning clause. Estimates are marked "est.".
- [ ] Every citation follows a sentence; none stands alone.
- [ ] No idioms, metaphors, or uncommon words remain.
