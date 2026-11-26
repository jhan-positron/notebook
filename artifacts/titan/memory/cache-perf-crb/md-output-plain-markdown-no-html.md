---
name: md-output-plain-markdown-no-html
description: "When the user asks for a .md file, write plain Markdown (pipe table, no HTML tags); user remark of 2026-11-24 on go.sh.md"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 9b54dcc5-d417-461d-9dcc-1710acea784e
  modified: 2026-11-25T00:28:51.213Z
---

On 2026-11-24 the user ran `/explain-bash line by line explain .../go.sh and generate to .../go.sh.md`. I wrote the side-by-side part as an HTML `<table>` with `<pre>` cells and the word list as a `<details>` block, inside the `.md` file. The user's reply: "Are you sure you used markdown format? It looks like html", with a paste of the raw `<tr><td ...><pre style=...>` lines. I then rewrote the page as plain Markdown.

**Why:** the user asked for a `.md` file and read it as raw text. The pasted lines were cut at about 210 columns, so the view was a terminal without line wrap (the viewer is my inference). In that view HTML markup hides the content.

**How to apply:** for a `.md` output, use Markdown only: a pipe table (`| Line | Source | Explanation |`) for a side-by-side layout, a plain list for "Words used here", no `<details>`, `<br>`, `<pre>` or `<table>`. Inside a table cell write each `|` as `\|` (also inside a code span) and say so in the page. A table cell cannot hold a list or a line break, so write each explanation as one line of sentences. Say in the reply which limits remain (a row is one text line, so long rows are cut in a raw view without wrap). Check the result with pandoc (`-f gfm`): no `RawBlock` or `RawInline`, and the code cells equal the source.

Scope: the remark was about `go.sh.md` only. The user has not said whether the other 32 code companions of [[crb-whole-chip-code-data-list-2026-11-21]] (HTML tables from `companion_tool.py`) should change. Applying this to every `.md` file is my interpretation.
