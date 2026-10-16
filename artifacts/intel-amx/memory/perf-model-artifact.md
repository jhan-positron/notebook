---
name: perf-model-artifact
description: Published artifact URL of perf-model/index.html (AMX Decode Perf Model) for jhan's in-browser comments; how to read and answer them
metadata:
  type: reference
---

perf-model/index.html is published as a Claude Artifact at
https://claude.ai/code/artifact/a851731a-db44-45bd-ab54-abcd52aef600
(published 2026-09-03, title "AMX Decode Perf Model", favicon 📐).

jhan comments and asks questions on the report through the artifact's
comment layer (they have no Microsoft Office). To answer: Artifact action
"comments" with that url reads the threads; reply/resolve only threads sent
to Claude. To update the report at the same link: strip the doctype/html/
head/body tags from perf-model/index.html into a scratchpad copy and publish
with `url` set to the address above (the source file keeps its full skeleton).
Related: [[perf-model-project]].

An earlier artifact of the same report exists from the 2026-09-03 build session
(20d126bf-5730-4715-a576-6c75d0833b3e, noted in [[perf-model-project]]). jhan comments on
a851731a (above), so that is the one to read and republish; treat 20d126bf as superseded.
The report is generated: edit exec/perf-model-20260903/gen_report.py (or narrative.json),
regenerate perf-model/index.html, then publish the stripped copy. First comment thread
(2026-09-03, THP glossary item) answered by adding the section-10 block "Page sizes and THP".

Publish gate (2026-09-03): a publish with `url` is refused until this conversation has read the live artifact: run action "read" (it saves the live HTML to tool-results/) and Read EVERY line of that saved file (385 lines, ~56k tokens, 3 Read calls) before publishing. Check first with a bash diff that the live body equals the last stripped copy, so no outside edit is lost.
