---
name: asimov-page-wording
description: Jibin's wording rules for the Asimov pages and messages (2026-11-05): no "hop"; G8 forms are "looped" and "single-call"; on the CME pages no "chase" or "register control" (2026-11-06: "chain load", "the latency test", "round-trip baseline")
metadata:
  type: feedback
---

Jibin's wording rules for the Asimov C1-Nano / CME pages and the messages about them:

- Never write "hop". A load of a chain is "a load" ("per load", "64 loads per pass", "sparse-chain load"); a crosspoint-to-crosspoint move on the mesh is "a step" ("step counts", "an X step costs more than a Y step"); the cme-call control does "one round trip per call".
- The two G8 L1 bandwidth forms are the "looped form" (one kernel call per pass, bandwidth-l1-passes.csv) and the "single-call form" (all passes of a rep inside one assembly call, bandwidth-l1-asmpasses.csv). Not "asm form", "assembly form" or "per-pass form". Dict keys stay 'per-pass' and 'asm'.
- On asimov-cme-perf-brief.html (2026-11-06): no glossary line for chase/fresh/flushed/sparse/dense/sequential; the loop is "the latency test", the per-load number "chain load", the DUP+LASTB control is the "round-trip baseline" (Jibin chose "round-trip" then "baseline" over cost/time/only). Chain kinds are spelled out: "chain with one line per 4 KiB page", "chain over every line", "chain in address order". The full CME page (gen_perf_cme.py) got the same words on 2026-11-06: KIND map (walked many times / walked once / every line flushed first / address order), ONE_PER_PAGE, GLOSS_DROP filters the shared glossary entries; the core page keeps the shared entries unchanged.

**Why:** Jibin asked for both on 2026-11-05 through the peer session asimov-04 while the pages went to Bill and Jesse; "hop" reads as a mesh term and clashed with the chain sense.

**How to apply:** gen_run4.py's dehop() rewrites its two pages at build time (asserts none left); gen_perf.py's dehop() covers the four full/brief pages. Keep new prose, Slack drafts and memory notes to these words. See [[asimov-cme-test-state]].

2026-11-06, CME brief only (Jibin's words, applied by peer asimov-be in gen_brief.py cme_brief()): "register control" is "round-trip baseline"; "chase" is gone: per-load number "chain load", the loop "the latency test", derived row "chain load minus round-trip baseline"; sparse/dense/sequential rows read "chain with one line per 4 KiB page", "chain over every line", "chain in address order". Scoped to the brief; the full CME page keeps "register control" and "chase" until Jibin asks. gen_run3.line_chart hline may be (y, label, x) to start the label at footprint x.
2026-11-06: the same words now on the full CME page too (peer's edit in gen_perf_cme.py): "round-trip baseline", "chain load", "the latency test", chain kinds "walked many times / walked once / every line flushed first / address order", OCM shapes "one line per page / every line / one line per page at varied offsets". The core pages still say "chase" and "register control" (not asked).
