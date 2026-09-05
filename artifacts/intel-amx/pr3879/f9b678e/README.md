# Evidence archive for PR3879/f9b678e.html

The page unpacks commit f9b678e5d0f0c5b971bfaa5dd457d2c7112eb237 of
positron-ai/tron PR #3879 ("K mirror arena: make its RAM visible"), line by
line, against the PR head 1d158249e2 (2026-08-30).

- `facts.json` — output of the fact-gathering round: three agents (kv_cache.hpp;
  the counter/gauge/manifest chain; the tests), each returning per-line
  explanations with file:line evidence at head, plus an obsolescence check
  (`git diff f9b678e5d0..HEAD` per file).
- `verdicts.json` — output of the adversarial verification round: four section
  refuters plus one page-mechanics checker re-checked the drafted page.
  119 verdicts: 109 confirmed, 10 partial, 0 refuted. Every partial was folded
  into the page; the list of resulting edits is in the page's section 9.

Key negative results worth keeping: no line of the commit was modified by the
two later commits (e217f518e0 only shifted the t/CMakeLists.txt block by +3
lines; 1d158249e2 only rewrote an unrelated comment at kv_cache.hpp:1433-1439),
and the header comment above `k_mirror_arena_live_bytes` over-claims that the
footprint log line "reads" the counter (the log keeps its own static total).
