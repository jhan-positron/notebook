**Short version:** Revise before adopting. The draft correctly adds report inputs and measurement sources to preservation. It still permits inconsistent report/data versions and lacks a check that the approved file contents reached the remote repository.

Review dated 2026-09-20 UTC. This reviews the recommended [601-line prompt](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md), [CHANGES.md](/home/jhan/tmp/handoff-prompt-2026-09-19/CHANGES.md), and [VERIFY.md](/home/jhan/tmp/handoff-prompt-2026-09-19/VERIFY.md). The longer `full.*` draft is reference material, not the proposed implementation. The failure being addressed is documented in the [data-preservation analysis](/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/mirror-vs-VNNI-K-data-preservation.md).

Terms used below: **canonical** means the original workspace copy. **Notebook** means the Git repository holding preserved copies. **Lineage** means the files and commands used to produce a report. **Freeze** means keeping a previously preserved file unchanged. A **Workflow** is Claude's script coordinating agent steps.

**What I would keep**

- Preserve a report with its generator, prepared inputs, input-building script, and measurement sources. Do not exclude a file merely because it lives in a results directory. [Draft:368](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:368)
- Move needed Workflow scripts out of the session store. Record the original location. Backfill missing lineage even when the session has no new activity. [Draft:438](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:438), [draft:514](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:514)
- Show exact proposed paths and explicit omissions before publication. Keep the shorter draft as the starting point.

**Changes needed**

1. **High — Preserve a consistent report and data version when a refresh is declined.**

   The ordinary refresh rule replaces a changed report or generator. The new freeze rule applies only to inputs and sources. If a rerun changes both a report and its input, declining the input refresh still permits the new report to replace the old report. The stored report then describes measurements absent from its stored input. Later runs check only the frozen input's existence. This follows directly from the two rules. [Draft:488](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:488), [draft:502](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:502)

   **Change:** Review each affected report and its dependencies together. If an input refresh is declined, retain the matching report and generator versions too. Alternatively, preserve the new set separately. Recheck lineage when a report, generator, or input changes, including entries that already have labels. The detailed discovery rule currently emphasizes entries without labels. [Draft:514](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:514)

   **Acceptance:** A fixture that changes a report and its input, then declines the input change, must leave a reproducible old set or a separately preserved new set. It must never leave a new report pointing to old data.

2. **Medium — Allow an honest unavailable regeneration command, and verify runnable commands once.**

   The draft requires an exact command with an explicit output path. It allows `none` only when there is no generator or the generator is a Workflow. [Draft:321](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:321)

   A named backfill target cannot use that contract directly. The generator for `tron-amx-distilled.html` ignores output arguments. It reads from the canonical workspace and writes the canonical page unconditionally. Appending `<OUT>` would not redirect its output. [CHANGES:171](/home/jhan/tmp/handoff-prompt-2026-09-19/CHANGES.md:171), [gen_distilled.py:12](/home/jhan/workspace/intel-AMX/exec/gen_distilled.py:12), [gen_distilled.py:1419](/home/jhan/workspace/intel-AMX/exec/gen_distilled.py:1419)

   An explicit output argument also does not establish independent recovery. The Monday report generator accepts that argument but reads canonical logs, live source-repository history, and temporary files. [gen_report.py:20](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_report.py:20), [gen_report.py:70](/home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_report.py:70)

   **Change:** Permit `regenerate: unavailable (reason)` and `regenerate: unverified (reason)`. Record needed generator repairs separately. Before marking a command verified, run it using preserved inputs and a scratch output, with canonical inputs unavailable. Record its working directory and required runtime. This can be an adoption check and a check after dependency changes. It need not run on every unchanged handoff pass.

   **Acceptance:** The distilled page receives an accurate unavailable status until a safe command or wrapper is demonstrated. A verified command rebuilds the intended report from the notebook's preserved files.

3. **Medium — Verify remote contents, not just remote filenames.**

   The proposed post-push check uses `git ls-tree --name-only`. That proves a path exists in the fetched `origin/main` reference, which represents the remote main branch. It does not prove that the approved replacement contents reached that branch. [Draft:595](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:595)

   **Test evidence:** An isolated temporary Git fixture started with an input containing `{"measurement": 10}`. Its local replacement contained `{"measurement": 20}`. A README-only refresh commit was pushed while the changed input remained unstaged. The proposed check passed with `tracked on origin/main: 1 of 1 files`. The remote input still contained the old value. These are synthetic fixture values, not benchmark measurements.

   **Change:** Record the expected Git blob ID (the identifier of stored file contents) for each approved destination. Compare it with the fetched remote file's blob ID after pushing. Compute the expected ID after adding the required HTML rendering comment. Include changed registry and handoff files in publication verification.

   **Acceptance:** The missed-refresh fixture must fail verification. Publishing every approved file with matching contents must pass.

4. **Medium — Let a required measurement source override its file class without requiring an input-file line citation.**

   The draft supports handwritten reports with `input: none`. It also qualifies measurements used by a handoff's Results table. However, the exception to excluded log classes requires a line citation from “the page's input.” A directly authored report or handoff has no such input. Its sole measurement source can therefore remain excluded even when the author identifies it correctly. [Draft:312](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:312), [draft:360](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:360), [draft:380](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:380)

   **Change:** Base this exception on demonstrated use by the report, its input, or the handoff Results table. Treat line citations as evidence, not an eligibility requirement. Require a preserved replacement before excluding a needed file as a duplicate. Keep the size decision explicit when a necessary source exceeds the threshold.

   **Acceptance:** A handwritten report whose only measurement source is an otherwise excluded log must propose that source, or show an explicit size/missing-data limitation. The absence of a generator must not silently remove its evidence.

5. **Medium — Keep source-root mappings for topics spanning several machines or directories.**

   The proposed layout assumes one canonical root per topic. Existing notebook topics do not all satisfy that assumption. The performance-fluctuation registry includes Windows paths, workspace paths, and scratch paths. It already maps the latter two to different destination prefixes. [Draft:423](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:423), [registry:50](/home/jhan/workspace/notebook/artifacts/tron-perf-fluctuation/README.md:50), [registry:107](/home/jhan/workspace/notebook/artifacts/tron-perf-fluctuation/README.md:107)

   **Change:** Resolve each source through its registered host/root-to-destination mapping. Keep existing mappings. For a new source root, show an explicit proposed destination. Do not derive a destination containing `..` from an unrelated root.

   **Acceptance:** Workspace and scratch dependencies of the same report retain distinct valid notebook paths. Already-preserved files are reused at their registered paths.

**Artifact generation should record the evidence while it is available**

The draft reconstructs lineage during a later handoff by inspecting generators, citations, and transcripts. That is useful for historical repair. For new artifacts, record the five labels when the report is generated. The handoff should consume that record. This reduces dependence on session history, including the session-store files identified as at risk. [Draft:438](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:438), [draft:522](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:522)

```mermaid
flowchart LR
  A[Record inputs] --> B[Generate report]
  B --> C[Preserve matching files]
  C --> D[Verify recovery]
```

Keep an exact file inventory with the report or registry. Include source paths, destination paths, content identifiers, and omission reasons. When a compact file replaces several logs, record that substitution there. The draft permits directory summaries and leaves the full list at the approval gate and in the commit. A persistent inventory makes the recovery check possible without reopening the approval conversation. [Draft:479](/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md:479)

Keep this small. A companion data file or an exact registry list is sufficient. Move one-time migration instructions and historical explanations into the change note instead of adding more exceptions to the standing prompt.

**Verification performed for this review**

- The notebook's current Claude prompt is byte-identical to the supplied baseline. The local notebook `HEAD` and `origin/main` references both identify commit `39c71bf6135dfe8b25f096293d91a17a15cc55ee`. This review did not fetch the remote branch.
- I copied `gen_compare.py` and `mirror-vs-vnni-rows.json` into scratch space. Running `python3 gen_compare.py rows.json review-output.html` succeeded. It generated 151079 bytes with 52 command-line benchmark rows and 16 continuous-integration test rows. The output matched the canonical page after masking its generation timestamp. It also matched the notebook page after removing the notebook's rendering-link comment.
- The isolated Git fixture described in finding 3 demonstrated the filename-only verification failure. It was removed after the test.
- The prepared input is absent at its proposed path in the local `origin/main` tree. **Insufficient data:** this review does not establish complete recovery of all raw measurements. Resolve that with an exact capture inventory, checks of compact-log substitutions, and derivation of the report's measurements from the preserved sources.

The scratch regeneration proves that this page can be reproduced from its prepared input. It does not prove that all underlying measurements have been preserved. Adoption should require both checks, with any unavailable sources reported explicitly. No handoff prompt, registry, canonical artifact, or remote repository was changed by this review.


---

## Response (Claude, 2026-09-20)

Short version: all five numbered findings and the inventory suggestion were adopted into the draft at `/home/jhan/tmp/handoff-prompt-2026-09-19/claude-handoff-generation-prompt.md`, which grew from 601 to 629 lines. The four factual claims the findings rest on were re-checked before editing and all hold. The notebook copy of the prompt is still unchanged.

- Finding 1 (high): on `measurement changed:` the page, its generator and its lineage files are now one gate item. Yes refreshes the whole set. No freezes the whole set, page and generator included, so the mirror stays one consistent version.
- Finding 2 (medium): `regenerate:` may now read `unavailable (<reason>)` when the generator has no output-path argument or reads files outside its `input:` and `sources:`. A regeneration check runs once, at first preservation and after a lineage refresh, with `<OUT>` in scratch and only preserved copies as input, and records `regenerate verified <date>` or `regenerate unverified (<reason>)`. `tron-amx-distilled.html` and `Monday-morning-report.html` will both get `unavailable` under this rule, for the reasons your review gives.
- Finding 3 (medium): the post-push check now compares blob ids (`git ls-tree -r origin/main <path>` against `git hash-object <local path>`) for every file the commit touched, mirrors, README and handoffs included. The prompt states why a name-only check is not enough.
- Finding 4 (medium): the class override now keys on "a file that the page, its input, or the handoff's Results table takes a measured number from". A line citation is evidence, not a requirement, and the `sources:` label is enough for an authored page.
- Finding 5 (medium): "canonical root" is now defined as a folder the topic README maps to a repo prefix, a topic may have several, the registered mapping is used, a new root is proposed at the gate, and no derived path may contain `..`.
- Inventory suggestion: the full source inventory (canonical path, repo path or left-behind reason, byte size, and the compact text that replaces a duplicate) goes in a companion `<page mirror path>.lineage.md` beside the page's mirror. Recording lineage at generation time is outside this prompt and is listed as follow-up 8 in CHANGES.md.
- Process note (one-time instructions belong in the change note): the relocation of the two 2026-09-18 entries stays in the prompt, because a `SCOPE: auto` run reads only the prompt. A sentence now tells the next editor to delete it once done.

Not changed: the History paragraph in the Computed-from bullet stays (four short sentences with a pointer to the analysis), matching the prompt's convention of dated rationales.
