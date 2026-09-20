# Change note: claude-handoff-generation-prompt.md, data-preservation amendment

Draft written 2026-09-19. The notebook copy of the prompt is untouched. Files
in this folder:

- `claude-handoff-generation-prompt.md`: the recommended draft (629 lines).
- `changes.diff`: unified diff against `baseline.claude-handoff-generation-prompt.md`
  (the notebook copy at commit 39c71bf, 410 lines). 5 hunks, 227 lines added,
  8 removed.
- `VERIFY.md`: the 46 verifier findings on the first condensed draft, the 18
  findings of the final check, the 6 points of the Codex review, and what was
  done with each.
- `full.*`: the longer draft the first multi-agent workflow produced (988
  lines, 585 added, 9 removed). Kept for reference. Not recommended: it
  embeds run-specific numbers and adds features the failure does not need.

## Short version

The 2026-09-18 handoff run preserved the page `mirror-vs-VNNI-K.html` and its
generator but left the page's input file and the raw result texts behind 24
of its 52 tests on NFS. The cause was the wording of Step 4b rule 4, which
the run read as excluding the data files inside a result tree. This draft
replaces that location test with class and size tests, adds a lineage rule that pulls a page's data in with the page,
and settles where Workflow scripts from the Claude session store go.

## Words used here

- the prompt: `claude-handoff-generation-prompt.md`, pasted into a Claude
  Code session to write handoff files and mirror workspace files into the
  notebook repo (github.com/jhan-positron/notebook).
- Step 4b: the prompt's "Artifact preservation" section, with four
  qualifying rules ("ALL must hold"), a registry rule, a refresh loop and a
  new-artifacts step.
- canonical folder: `~/workspace/intel-AMX` on the shared NFS home, the
  authoritative copy of the project's files, not a git repository. The
  README calls it `WS`.
- mirror: the copy of a canonical file inside `artifacts/<topic>/` in the
  repo.
- the page: `VNNIed-K-in-place/status/mirror-vs-VNNI-K.html`, 52 runtron
  tests and 16 CI-harness tests, generated 2026-09-14 by `gen_compare.py`.
- rows.json: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json`, the
  generator's only input (545679 bytes, 239 rows).
- generator, input, sources: the script that writes a page, the file(s) it
  reads, and the raw result files the input's numbers were extracted from.
- lineage: generator, input, the script that built the input, sources, and
  the exact regenerate command, taken together.
- session store: `~/.claude/projects/`, where Claude Code keeps transcripts
  and Workflow scripts. Not a workspace, not a repository.
- gate: the Step 5.3 approval gate, where a run lists what it will commit
  and waits for approval.
- status doc: `VNNIed-K-in-place/status/mirror-vs-VNNI-K-data-preservation.md`
  (2026-09-19), the analysis this draft answers.

## What went wrong

- The 2026-09-14 handoff listed rows.json in its Artifacts section, under
  "Results, .../exec/results/vnnik-20260914/"
  [handoffs/claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md:99].
  Step 4 did its job.
- The 2026-09-18 preservation run mirrored the page and `gen_compare.py`
  but not rows.json [artifacts/intel-amx/README.md:799-800]. The same run
  did mirror nine files (text, html and one shell script) from other result
  trees, so the
  exclusion was a judgment on the data files, not a path filter.
- Step 4b rule 4 said "Not bulk or regenerable data (benchmark result
  trees, turbostat captures, raw logs stay on their storage)". The run read
  rows.json and the raw texts as result-tree data
  [baseline.claude-handoff-generation-prompt.md:336-337].
- The README repeats the exclusion as a policy phrase: "bulk result trees
  stay on the canonical storage" [artifacts/intel-amx/README.md:113-114].
- Rule 3's litmus test asks whether recreating a file "would cost
  hours-to-days". A measurement cannot be recreated at any cost, so the
  test does not fit data [baseline.claude-handoff-generation-prompt.md:334-335].
- The Workflow script that built rows.json lives only in the session store
  and was never listed in the handoff, so rule 1 never saw it.
- Result: 28 of the 52 tests keep raw data in the notebook, 20 keep only
  derived numbers (per-repetition values or means) in other preserved
  pages, handoffs and `codex-perf-audit.json`, and 4 keep nothing [status
  doc, section 4]. rows.json exists in one place [status doc, section 5].

## Changes

| # | Where in the prompt | Old (abridged) | New (abridged) | Why | Closes |
|---|---|---|---|---|---|
| 1 | Config, `SCOPE: auto` | skip a session with no new activity ("no commit churn") | one exception: the Step 4b lineage backfill runs for such a session | the 2026-09-14 session has no new activity, so without this the backfill would never run | status doc section 6, process |
| 2 | Step 4, Artifacts item 4 | nothing about Workflow scripts or page inputs | list Workflow scripts; nest five lineage labels (`generator:`, `input:`, `input built by:`, `sources:`, `regenerate:` with `<OUT>`, or `unavailable (<reason>)` when the generator has no output argument or reads outside its inputs) under every report page | Step 4b needs a label linking page to data; a file listed under a results directory is not one. The `<OUT>` rule records the one-argument trap | section 2 (trap), section 6 tier 1 |
| 3 | Step 4b rule 3 | litmus test: "would recreating this cost hours-to-days?" | adds measurement data that a preserved page or a handoff Results table is computed from; litmus test gains "or be impossible", with one sentence why | measurements cannot be re-run into the same numbers; pageless campaign texts (for example `fused-sweep-v2.txt`) must still qualify | section 5 |
| 4 | Step 4b rule 4 | "benchmark result trees, turbostat captures, raw logs stay on their storage" | judge by class and size, never by location; class list based on the status doc's "deliberately not proposed" set plus turbostat captures, binaries and CI client logs whose `perf*.json` holds the samples (`functional.xml` is not named; the gate decides it under the override); one override for a file the page, its input or the Results table takes a measured number from (a line citation is evidence, not a requirement), with identity and configuration lines excluded; 5 MiB single-file threshold with gate approval; batch count and MiB at the gate; "regenerable" defined for data files only | the location test is the cause; the override settles the t4 `power*.log` case, which holds per-request lines in server-log format | sections 4, 6 |
| 5 | Step 4b, new bullet "Computed-from files" | none | when a report page is proposed or registered, propose its generator, input, input builder and cited sources (three kinds named); left-behind reasons (`no value used`, `provenance`, `size`, `duplicate`); layout path; one gate line per page, one left-behind reason per file; a definition of canonical roots (a topic may have several, each mapped to its own repo prefix); four-sentence history with a pointer to the status doc | this is the rule that pulls the 2.0 MiB in with the page | section 6, tiers 1 to 3 |
| 6 | Step 4b, new bullet "Session-store files" | none | copy the script into the canonical folder of the script that reads its output (else of the scripts it drove, else `<canonical root>/exec/workflows/`, created if missing), on approval; mirror from there; register that path; keep the store path as `origin:`; retention stated as Insufficient data; supersedes the 2026-09-18 practice and relocates its two entries at the next run | the store path is unguessable and possibly cleaned after 30 days | section 6 tier 1; brief item 6 |
| 7 | Step 4b, Registry bullet | "That README is the source of truth for refresh." | plus: the README records WHAT is preserved, the rules live in the prompt; the "bulk result trees" phrases are descriptions, not rules; page entries carry the labels, with per-kind marking for a partly preserved directory and the full inventory in a companion `<page>.lineage.md` file; batch headers list what was left behind and why | future runs read the README and would otherwise keep applying the old phrase | section 3 (policy phrase) |
| 8 | Step 4b, Refresh bullet | "Different -> refresh the repo copy" for every artifact | measurement files are not refreshed silently; on `measurement changed:` the page, generator and lineage files form one gate item; yes refreshes the set, no freezes the whole set so the mirror stays one consistent version | a re-run into the same result directory would overwrite an immutable record, and a declined input refresh must not leave a new page pointing at old data | gap found by the failure-replay-first drafter, not in the status doc |
| 9 | Step 4b, New artifacts bullet | propose Artifacts entries at the gate | plus a lineage walk for proposed pages and for registered pages with a generator but no labels (`lineage unknown:`); runs despite no new activity; where to read labels; unreachable host and missing file cases; labels written to README and handoff on approval without touching header dates; a regeneration check once at first preservation and after a lineage refresh; FROZEN handoff case; batch commit message | this makes the next `SCOPE: auto` run propose the files behind the 2026-09-14 pages | section 6 (the capture) |
| 10 | Step 5.3 gate | "preserved / refreshed / canonical-missing alerts" | plus the new line kinds, each batch's count and MiB, and the clone's `.git` size | the gate is where the user approves paths | section 6, process |
| 12 | Step 5.2 update rule | an UPDATE refreshes the header dates and may rename the file | exception: a lineage backfill edits only the page's Artifacts lines and rides in the `Preserve artifact:` commit | a run reading Step 5 alone would otherwise refresh the idle handoff's dates | consistency with change 9 |
| 11 | Step 5.4 push | commit and push | after a preserve or refresh push, compare the blob id of every touched file on origin/main with the local copy and report `on origin/main: N of N files, contents match` | the status doc's last process step; a name-only check would pass a README-only push that left a changed mirror unstaged | section 6, process |

## Conflicts settled

1. README policy phrase versus the new rule. The prompt wins. The old
   README headers and entries stay unchanged, the phrase is not repeated in
   new headers, and the prompt says so [claude-handoff-generation-prompt.md, Registry bullet].
2. Where a session-store Workflow script goes. The 2026-09-18 batch
   registered the store path itself as canonical
   [artifacts/intel-amx/README.md:722-725]. The status doc asked to copy the
   script into the canonical folder and mirror it beside those two under
   `exec/workflows/`. The draft copies into the folder of the script that
   reads the Workflow's output (`exec/vnnik-20260914/` for the 2026-09-14
   script) and mirrors at the layout path. When no folder qualifies or more
   than one does, the target is `<canonical root>/exec/workflows/`. Both
   2026-09-18 scripts are that case: one drove no canonical script, the
   other drove scripts in two folders (checked in their handoffs on
   2026-09-19). Their mirrors therefore stay at
   `artifacts/intel-amx/exec/workflows/`, and only their canonical paths
   change.
3. Direction "strictly canonical -> repo" versus the relocation copy. The
   copy is the one write into a canonical folder the prompt allows, only on
   approval, and only for session-store files. When the store has already
   deleted the file, the copy comes from the repo mirror, which is the
   restore the canonical-missing rule asks for.
4. Status doc tier 3 versus the new rule. The status doc's tier 3 count of
   189 files includes 47 CI client logs (`perf*.log`), although its text
   names only `perf*.json`, `meta.json` and `proof.txt` (counted by the
   first workflow's replay verifier on 2026-09-19 from `capture_list.json`).
   The prompt now names the class: a `perf*.log` stays as `provenance` when
   the sibling `perf*.json` holds the per-request samples, unless the input
   cites it by line for a value the page shows. It appears at the gate as
   left behind, where it can be approved.
5. No-churn skip versus backfill. The backfill is an explicit exception in
   Config and in the New artifacts bullet, and it edits only the page's
   Artifacts lines.
6. One-time instructions in a standing prompt. The Codex review asked to
   move the relocation of the two 2026-09-18 entries into this note. A
   `SCOPE: auto` run reads only the prompt, so the instruction stays there,
   with a sentence telling the next editor to delete it once done.

## Defaults chosen for you to confirm

- 5 MiB (5242880 bytes) as the single-file threshold. Nothing in the
  status doc's 215-file, 2.0 MiB capture exceeds it. The largest file is
  rows.json at 0.52 MiB. The 9.5 MiB of `rinzler.log` files are excluded by
  class before size matters.
- The relocation target order: folder of the script that reads the
  Workflow's output, then the folder of the scripts it drove, then
  `<canonical root>/exec/workflows/`.
- Authored pages (no generator) get the lineage labels from now on, but
  registered authored pages are not backfilled automatically. The raw
  sources behind the 20 derived-only tests are the same t4, g1 and p0perf
  result trees that the rows.json walk already proposes, so the overlap is
  large. Say which authored pages you want walked, if any.

## What this draft does not do

- It does not edit `codex-handoff-generation-prompt.md`. Its rule 4 carries
  the same exclusion [codex-handoff-generation-prompt.md:356-357].
- It does not perform the capture. The next `SCOPE: auto` run proposes it
  through the `lineage unknown:` line.
- It does not edit the README policy lines 44, 113-114, 202 or 442-444.
- It does not preserve the status doc itself. It qualifies under rule 3
  once a handoff's Artifacts section lists it.
- It does not resolve the two directory spellings that both exist on
  origin/main: `artifacts/intel-amx/VNNIed-K-in-place/` (24 files, Codex
  batch) and `artifacts/intel-amx/vnnied-k-in-place/` (33 files, Claude
  batch) (checked with `git ls-tree origin/main` on 2026-09-19).
- It does not run the regenerate command on every pass. It runs it once
  at a page's first preservation and again after a lineage refresh.

## Follow-ups

1. Review this draft, then copy it over the notebook file and commit, for
   example as "Update claude-handoff-generation-prompt: preserve the data a
   report page is computed from, relocate Workflow scripts (2026-09-19)".
2. Apply the twin of changes 1 and 3 to 12 to
   `codex-handoff-generation-prompt.md`.
3. Run `SCOPE: auto` with the new prompt. Expected gate lines: `lineage
   unknown:` for `mirror-vs-VNNI-K.html`, `Monday-morning-report.html` and
   `tron-amx-distilled.html` (its README entry says "regenerated by
   `generators/gen_distilled.py`" [artifacts/intel-amx/README.md:93]), one
   `computed-from:` line per page with its path list, one `relocate:` line
   for `pull-mirror-vs-vnni-data-wf_9b0f456d-293.js`, and two more
   `relocate:` lines for the 2026-09-18 entries. Expect `regenerate:
   unavailable` for two of the three pages: `gen_distilled.py` writes the
   canonical page unconditionally and takes no output argument
   [intel-AMX/exec/gen_distilled.py:1420], and `gen_report.py` reads live
   git history and files under `/var/tmp`
   [intel-AMX/exec/vnnik-20260914/gen_report.py:59,75-77].
4. Set `cleanupPeriodDays` in `~/.claude/settings.json` (the 2026-09-11
   memory note records an offer of 3650 days, not applied). This lowers the
   session-store risk independently of the prompt.
5. Preserve the status doc through a handoff Artifacts entry.
6. Decide the fate of the two directory spellings named above.
7. If `capture_list.json` from the 2026-09-19 status-doc session is reused
   for the capture, note that it lists 226 paths against the status doc's
   215 files: it adds the 12 optional `g1-20260908/runtron-*-rep*` logs and
   omits `PR3879/more-testing/round-1/status.md` (reconciled by the first
   workflow's critic fixer on 2026-09-19).
8. Record lineage when a page is generated, not only when a handoff is
   written (Codex review suggestion). A generator, or the session that runs
   it, could write the five labels to `<page>.lineage.md` beside the
   canonical page. The handoff would then copy them. This is outside the
   handoff prompt and belongs in the generators or in the project's
   CLAUDE.md.

## How this was produced

A Claude Workflow of 25 agents ran first: three drafters (surgical-minimal,
lineage-and-verification, failure-replay-first), three judges (rubric scores
summed over the three judges: 227, 224 and 198 points of 300; the
failure-replay-first draft won), one synthesizer, three rounds of four
adversarial verifiers (replay of the 2026-09-14 run, consistency, prose,
coverage) each followed by a fixer, then a completeness critic and a final
fixer. Each fix round added text, and the result grew to 988 lines. That
output is kept as `full.*`. The recommended draft was then written by hand
from the same findings, keeping every rule the replay needs and dropping
run-specific numbers and features the failure does not require. A second
workflow of four verifiers checked that condensed draft and returned 46
findings (7 high, 17 medium, 22 low); 42 were applied, 2 applied in part and
2 rejected, as listed in `VERIFY.md`. A final two-lens check of the rebuilt
draft returned 18 findings (4 high, 5 medium, 9 low), all wording defects in
the new text or in this note; all 18 were applied by hand, and the result was
checked mechanically (diff regenerated, line widths, semicolons, counts) but
not by another agent round. The list is in `VERIFY.md`.

On 2026-09-20 a Codex review of the 601-line draft
(`~/tmp/codex-review-claude-handoff-prompt-2026-09-19.md`) returned one high
and four medium findings plus one suggestion. All six were adopted after
checking their claims against `gen_distilled.py`, `gen_report.py`, the
`tron-perf-fluctuation` registry and a blob-id comparison on an existing
mirror. The edits (28 lines net) were made by hand and checked mechanically.
The decisions are listed in `VERIFY.md` and in a response appended to the
review file.
