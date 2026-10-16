---
name: prompt-not-ctx
description: "jhan 2026-09-01: write 'prompt 8192', never 'ctx 8192'; ctx is our script variable, not a tron/runtron term, and it misled jhan into reading it as total context"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: af74ab66-4c6d-4be1-801a-2b6ab0d70374
  modified: 2026-09-02T00:22:48.462Z
---

Write the prompt length as "prompt 8192" (prose: "prompt length 8192 tokens"). Never label a cell
"ctx 8192". Our campaign scripts pass the value to runtron as `--prompt-length "$ctx"` and then
generate a fixed 256 tokens (`-l 256`; perf-stat rounds 2600), so total context = prompt + tokens
generated so far, from prompt+1 to prompt+256.

**Why:** jhan read "ctx 256" as total context and could not reconcile it with 256 generated tokens
(2026-09-01). Checked that day: tron uses the identifier `ctx` only for context objects (fmt,
callback, JSON), runtron has no --context flag, and the only tron precedent is the log line
"Generating N response tokens with M context" where M = prompt size + 1 padding token
(h/runtron/stream_generate.hpp:247). So "ctx = prompt" was our invention, not a convention.

**How to apply:** new documents, tables, chart labels and glossary entries say "prompt N". Pages
converted on 2026-09-01: PR3879/make-sense-amx-vs-avx.html and tron-amx-distilled.html (plus the
archived figure SVGs). Scripts under exec/ and result-file headers ("### arm=... ctx=2048 len=256")
still use ctx= as a raw-data identifier; quote them verbatim when citing raw files, but translate in
prose. Rule also recorded in intel-AMX/CLAUDE.md. Related: [[plain-english-default]],
[[amx-vs-avx-sense]].
