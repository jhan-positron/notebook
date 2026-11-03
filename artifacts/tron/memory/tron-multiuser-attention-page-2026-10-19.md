---
name: tron-multiuser-attention-page-2026-10-19
description: HTML page answering "how does TRON parallelize multi-user attention in decode" (Ben Gamari bootcamp talk 103, slide 33); CPU cuts one page list per KV head across workers, FPGA cuts 1K-token shards across cards round-robin
metadata:
  type: project
---

Page: ~/workspace/random/from-claude/TRON-multiuser-attention-claude.html (written 2026-10-19 from tron commit e6c53ba7, main 2026-09-23). Five inline SVG figures, light theme, render-checked with the Playwright venv from session fcd18152 (see [[headless-chromium-render-check]]).

Finding: TRON has no per-user attention loop. CPU: select_relevant_pages builds one page list per minibatch and KV head (sorted by first-seeing query, so grouped by user); finish_sw_plan cuts it into kv_sections across attention workers by estimated work and measured worker speed [h/tron/models/model.hpp:2719-2790]; each worker loops page-outer, query-inner with the ranged-mask gate [self_attention.hpp:1500-1503]; run_joins merges partials. FPGA: 1,024-token shards placed round-robin across cards [full.hpp:2545-2583]; one hw_pass per (card, <=4 shards, queries sharing them) [model.hpp:2486-2700]; independent decode users never share a pass, shared-prefix users can. Minibatch level: N decode users -> 2 minibatches in the llama plugin (1 for ingested plugins), CPU attention of one overlaps FPGA matmuls of the other.

**Why:** the user logs questions from bootcamp talks and wants code-grounded answers with file:line citations, as with [[tron-concepts-page-2026-09-19]].
**How to apply:** reuse this page for follow-ups on attention scheduling; its Insufficient-data list names the Perfetto measurements (worker count, per-step timing, cross-card overlap) that were not taken.

**Update 2026-10-21:** the page gained the slide link (https://drive.google.com/file/d/1Ko2_5VUn9z-SGfhBcCCZYZIDDJKpjAIo/view?usp=sharing) and a section 4 "What a minibatch is" (label -> grains of 8 -> greedy merge, struct batch fields, cross-minibatch dependencies). Old sections 4-7 became 5-8. A Python mirror of chunk_evenly, `random/from-claude/TRON-multiuser-attention-chunk-mirror.py`, computed the worked-example table (4 decode users -> 2+2, 20-token prompt -> 8+12, 300-token prompt -> 104+104+92). Both files were pushed to the notebook repo at `artifacts/tron/random/from-claude/` with a README entry (commit "Preserve artifact: tron/random/from-claude/TRON-multiuser-attention-claude.html ...", 2026-10-21). Canonical stays in ~/workspace/random/from-claude/; edit there first, then re-copy.
