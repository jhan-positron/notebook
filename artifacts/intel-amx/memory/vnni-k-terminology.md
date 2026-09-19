---
name: vnni-k-terminology
description: "jhan 2026-09-15: VNNI-K PR wording = 'shared block save' (not 'striped block store'), 'binary' (not 'arm') for the results-table column; save = the operation, store = the CPU instruction"
metadata:
  type: feedback
---

For the VNNI-K PR (branch jhan-amx-vnniK) jhan chose, on 2026-09-15:

- "shared block save" for the K store scheme of save_k, never "striped block store".
  Code Note is `Note [Shared block save]`, identifiers `k_store_shared`,
  `MAX_SHARED_WORKERS_128` (commit a76610da4f, local, jhan pushes; a73caff563 on top writes "dimension", not "dim", in the branch's comments).
- "binary" as the column header for base / this branch / this head in results
  tables, never "arm" (trial jargon). The store-remedies report still says "arms"
  in its own term table; jhan did not ask to change it.
- "save" = the operation (matches save_k / trace label "Save K");
  "store" = the CPU instruction only (full-line store, masked store, scatter).

**Why:** "striped" already means the helpers' fixed every-n-th-token kernel
split in tron (run_main_help), and in storage it means spreading data over disks;
the K save is dynamic claiming from one counter, so "shared" is the literal word.
"arm" is clinical-trial / A/B-test jargon an engineer must guess at.

**How to apply:** in any new page, PR text or comment about this branch use these
three words; keep git-history quotes (commit subjects, removed env-var names
TRON_K_VNNI_STRIPE) verbatim. Do not touch the other-meaning "stripes"
(helper kernel striping, expert loops, binary stripping). See
[[vnnied-k-in-place-project]] and [[plain-english-default]].

**"dimension" vs "dim" (refined 2026-09-16).** The rule applies only to comments
the branch ADDS. jhan rejected the dim -> dimension rewrite of pre-existing
(main) comment lines: "unnecessary, and make this big PR even bigger". On
2026-09-16 I reverted all 24 such lines (20 hunks in amx_attn_iface.hpp,
kv_cache.hpp, amx_attn.cpp, t_amx_dispatch_dtype.cpp, t_amx_numerics.cpp) to
the merge-base text; verified byte-identical, clang-format clean, no code change.
Detection script: scratchpad find_dim_renames.py (normalize -/+ hunk text, apply
dim->dimension, compare). General rule: never touch a main line only to change
a word.
