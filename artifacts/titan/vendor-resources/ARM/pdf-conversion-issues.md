# PDF to Markdown conversion issues in ARM/md

Written 2026-11-09 by Claude (Claude Code session on claude-agentsrv), from a comparison of
`ARM/md/Arm-C1-Nano-TRM-r0p2.md` against `arm-txt/c1-nano-trm.txt` plus spot checks of the
other four md files.

## Short version

The md files under `ARM/md` were made from the PDFs with pymupdf4llm. That converter dropped
about 4 % of the words of the C1-Nano manual, mostly prose lines that contain a ligature glyph,
and it shortened ligatures inside table cells so that "field" became "feld" and "offset" became
"ofset". Re-converting the whole PDF with the pymupdf4llm installed on this host (1.27.2.3) recovers the
dropped text and leaves only unexpanded ligature glyphs in table cells, which NFKC normalization
repairs (section 7).

## Words used here

- TRM: Technical Reference Manual, Arm's per-product hardware manual.
- pymupdf4llm: a Python package that turns a PDF into Markdown. It sits on top of PyMuPDF
  (import name `fitz`). Both convert scripts under `ARM/` use it [ARM/convert.py, ARM/convert_parallel.py].
- Ligature: one PDF glyph that prints two or three letters: ﬁ (fi), ﬂ (fl), ﬀ (ff), ﬃ (ffi), ﬄ (ffl).
  Arm's PDFs use them in body text, so "configuration" is stored as "con" + ﬁ + "guration".
- arm-txt: the folder `arm-txt/` holds a plain-text extraction of six Arm documents. The files keep
  the page layout, one form feed per page, and keep ligature glyphs unexpanded. That matches the
  output of `pdftotext -layout` (inference from the file format, the tool was not recorded).
- Word normalization: for every count below, text was NFKC-normalized (ligature glyphs expanded),
  lower-cased, punctuation and Markdown markup removed, and every run matching `f+[il]?` deleted.
  The last step makes "field", "feld" and "eld" compare equal, so the counts measure dropped text,
  not spelling damage. Word counts below are counts after this normalization.
- 8-word sequence coverage: the share of one file's distinct 8-word runs that occur in another file.
  The same text gives near 100 %. Unrelated text gives near 0 %.
- Bag of words: a count of how many times each word occurs, ignoring order and layout.
- Page bin: a group of 100 consecutive PDF pages.

## 1. What was compared

| Item | Value |
|---|---|
| PDF | `ARM/pdf/Arm-C1-Nano-TRM-r0p2-107753_0002_06_en.pdf`, Arm C1-Nano Core TRM r0p2, Issue 06, 914 pages |
| md under test | `ARM/md/Arm-C1-Nano-TRM-r0p2.md`, written 2026-06-14 17:09, 235,725 words |
| reference text | `arm-txt/c1-nano-trm.txt`, written 2026-11-02, same document ID 107753_0002_06_en, 241,116 words |
| converter | pymupdf4llm, version not recorded in any md header |
| this host | pymupdf4llm 1.27.2.3 and PyMuPDF 1.27.2.3 installed 2026-06-14 11:39, three hours before the md files were written |

The C1-Nano TRM is the only document that exists in both folders, so it is the only one where
loss can be measured directly. The other five txt files (C1-DSU TRM, C1-SME2 TRM, C1-SME2
Telemetry Specification, two CME slide decks) have no md counterpart at all.

Both files were split into pages: the txt at form feeds, the md at its "Page N of 914" footer
lines. All 914 pages are present in the md. Two page markers (248 and 623) sit inside a table
cell without spaces (section 5). A first pass therefore reported those two pages as missing. They
are not.

## 2. Prose lines that contain a ligature were dropped

This is the largest loss. The converter wrote most prose correctly, but one line in four that
contained a ligature glyph is absent from the md.

| Line type (txt lines with at least 8 words) | Lines | First 8 words absent from md | Words in absent lines |
|---|---|---|---|
| prose, no ligature in the line | 5,163 | 34 (0.7 %) | 424 |
| prose, ligature in the line | 1,609 | 449 (27.9 %) | 6,094 |
| table layout, no ligature | 4,811 | 121 (2.5 %) | 1,412 |
| table layout, ligature | 866 | 126 (14.5 %) | 1,717 |
| all | 12,449 | 730 | 9,647 (4.0 % of all txt words) |

The 0.7 % and 2.5 % rows are the method's noise level: lines that the md re-flowed differently.
The 27.9 % row is the defect.

Whole-document bag-of-words check, independent of line splitting: 9,330 of 241,116 txt word
occurrences (3.87 %) do not occur in the md. In the other direction, 3,939 of 235,725 md word
occurrences (1.67 %) do not occur in the txt. Those md-only words are table markup tokens
("0", "1", "picture", "text", "RES0"), so the md holds no text that the txt lacks.

Examples of sentences that are in the PDF and absent from the md. Each was checked with a direct
text search of the md.

- Page 2: "This document is Non-Confidential." and "We believe that this document contains no
  offensive language. To report offensive language in this document, email terms@arm.com." (only
  the fragment "document, email terms@arm.com." survived).
- Page 2: "To provide feedback on the document, fill the following survey:" (only the URL survived).
- Page 18, the first sentence of chapter 1: "The C1-Nano core is a high-efficiency, low-power, and
  area-efficient product that implements the Armv9.3-A architecture."
- Page 20: "Regardless of the cluster configuration, the C1-Nano core supports the following features:"
- Page 21: "You can choose the options that fit your implementation needs at build-time configuration."
- Page 37: "The implementer chooses the options that affect how the RTL source files are rendered."
- Every register description has a "Configurations" attribute. The heading "Configurations" occurs
  349 times in the txt and 2 times in the md. Its usual value "This register is available in all
  configurations." occurs 152 times in the txt and 0 times in the md.

The drop is spread over the whole manual. Per 100-page bin, the share of ligature prose lines
that are absent ranges from 10.9 % (pages 401 to 500) to 55.6 % (pages 901 to 914, 10 of 18 lines). It does not
depend much on which ligature: ﬀ 34.1 % (91 of 267 lines), ﬁ 26.5 % (339 of 1,279), ﬂ 26.3 %
(20 of 76), ﬃ 14.6 % (7 of 48). Lines whose first ligature sits after character 60 are dropped
more often (40.0 %) than lines with an early ligature (24.0 %).

What the PDF text layer shows for a dropped line and for a kept line on the same page: the same
font (Lato-Light), the same span flags (4), the same size (11.0 pt), horizontal direction, and
no overlap with any drawing cluster. So no span attribute distinguishes dropped lines from kept
lines, and the cause is inside the converter, not in the PDF. This was read with
`page.get_text("dict")` and `page.cluster_drawings()` on pages 2 and 18.

## 3. Ligatures inside table cells were shortened to one letter

In table cells the converter kept the line but wrote the ligature as a single "f". Every mangled
spelling in the C1-Nano md sits in a table row ("confgured": 69 of 69 lines, "feld": 195 of 195,
"ofset": 22 of 22). The same damage is in the other md files.

Whole-word counts, case-insensitive:

| md file | field / feld | offset / ofset | configured / confgured | configuration / confguration | buffer / bufer | identification / identifcation | affinity / afnity |
|---|---|---|---|---|---|---|---|
| Arm-C1-Nano-TRM-r0p2.md | 85 / 361 | 230 / 231 | 32 / 150 | 67 / 62 | 29 / 50 | 124 / 218 | 19 / 59 |
| Arm_Neoverse_CMN_S3AE_TRM_r2p5.md | 159 / 504 | 64 / 92 | 51 / 80 | 912 / 492 | 25 / 212 | 9 / 8 | 2 / 8 |
| IHI0050H_amba_chi_architecture_spec.md | 921 / 141 | 2 / 0 | 4 / 0 | 4 / 0 | 27 / 0 | 1 / 1 | 0 / 0 |
| DEN0094E_BSA_1.2.md | 26 / 45 | 30 / 0 | 9 / 0 | 46 / 7 | 43 / 0 | 6 / 3 | 0 / 0 |

Effect: a text search for "field" in the C1-Nano md finds 85 of 446 occurrences. A search for
"offset" finds half. Register bit tables are where these words live, so register lookups are the
most affected use.

No ligature glyph survives in any of the five md files (0 characters from the set ﬁﬂﬀﬃﬄ in
total), so the damage cannot be repaired by normalization after the fact.

## 4. Strikethrough fragments that are not in the PDF

The C1-Nano md contains 684 short strings wrapped in `~~`, for example `~~et~~` (216 times),
`~~Po~~` (71), `~~OO~~` (56), `~~GG~~` (54), `~~L~~` (30), `~~ee~~` (25), `~~Pri~~`, `~~oT~~`,
`~~IE~~`. The CHI specification md has 32, the other three md files have none.

They sit inside register summary tables. Example, md page 262 (AArch64 register summary), one
row: `|SCXTNUM_EL2<br>~~Po~~|3<br>~~Po~~|4<br>~~Po~~|C13<br>~~Po~~|...`.

These strings are not text in the PDF. Page 262 of the PDF has 305 text lines, all horizontal,
and none of its spans has one of these strings as its text. The page does have 1,413 vector
drawings (table rules). The txt extraction of the same page contains none of these strings
either. Converting page 262 alone with pymupdf4llm 1.27.2.3 on this host produces zero `~~`
strings. The origin inside the June run is therefore unknown. The hand-written header of the
Nano md mentions "auto-OCR text from diagrams", which fits an OCR pass over the drawings
(hypothesis, not verified).

## 5. Table rendering defects

- Page footer absorbed into the last table row. On pages 248 and 623 the row reads
  `||Copyright © 2023–2025 Arm Limited (or its afliates). All rights reserved.<br>Non-Confdential<br>Page**248**of**914**|||||||`.
  Anything that splits the md by page footer must tolerate the missing spaces. 2 of 913 footers
  are affected.
- Merged header cells duplicated. A "Description" column that spans several PDF columns becomes
  `|**Bits**|**Name**|**Description**|**Description**|**Description**|**Description**|**Description**|**Reset**|`.
  33 of the 493 bit-field table headers in the Nano md have a repeated "Description" cell. Data
  rows below such a header carry matching empty cells (`|||||`).
- Multi-line cells use `<br>` as the line separator. Tools that read the md as plain text will
  see "interrupt<br>distribution".

## 6. Items that are by design, or harmless

- Figures are not embedded. Placeholders of the form `==> picture [W x H] intentionally omitted <==`
  count 89 in the Nano md, 791 in the CMN S3(AE) TRM md, 121 in the CHI md, 10 in the BSA md,
  20 in the white paper md. Register bit-field diagrams are drawings in the PDF, so neither the
  md nor the txt has them.
- The per-page footer line "Copyright © 2023–2025 Arm Limited (or its affiliates). All rights
  reserved." occurs 916 times in the txt and 18 times in the md. This line contains the ﬃ glyph,
  so it is one more instance of section 2, but losing it costs nothing.
- Provenance. The md header comments name the tool but not its version. The Nano md has a
  hand-written header that differs from the auto-generated header of the other files. Its PDF was
  added at 16:48 and its md written at 17:09, after the other md files (14:32 to 14:34), so it was
  a separate run. Both convert scripts point at `/scratch/jhan/documents/ARM`, which does not exist
  on this host (claude-agentsrv), so the run location and version are unknown.
- Leftovers. `ARM/.trm_parts/` still holds the 73 intermediate chunk files (1.6 MB) of the
  parallel CMN TRM conversion. The whole-TRM md has 393,862 words and the 23 split-chapter md
  files sum to 394,097 words. The 235-word difference is about the size of the 23 header
  comments (11 words each, 253 words), not of a lost chapter.

## 7. Re-conversion test with pymupdf4llm 1.27.2.3 on this host

Single-page re-conversion, same PDF, same package version as installed here:

| Page | June md | Re-converted 2026-11-09 |
|---|---|---|
| 2 | 3 sentences absent (section 2) | all present |
| 18 | chapter 1 opening sentence absent | present |
| 20 | "Regardless of the cluster configuration..." absent | present |
| 216 | "This register is available in all configurations." absent | present |
| 248 | table cell has "This feld always returns"; footer inside table row | table cell keeps the glyph: "This ﬁeld always returns" (2 ﬁ glyphs on the page); footer is a normal line |
| 262 | 71 `~~` fragments in the register summary | 0 fragments |

So the current package keeps prose lines and does not produce fragments. It still does not
expand ligatures inside table cells. It keeps the original glyph instead of writing "f", which
a consumer can repair with NFKC normalization, but a plain search for "field" still misses
those cells.

Whole-document re-conversion, same PDF, same package, run 2026-11-09 on this host. It took
165 s for 914 pages. Header detection in pymupdf4llm uses document-wide font statistics, so a
whole-document run is the test that matters, not single pages.

| Metric (txt is the reference) | June md | Re-conversion 1.27.2.3 |
|---|---|---|
| txt word occurrences absent from md | 9,330 (3.87 %) | 718 (0.30 %) |
| prose lines with a ligature whose first 8 words are absent | 449 of 1,609 (27.9 %) | 14 of 1,609 (0.9 %) |
| words in absent lines, all line types | 9,647 (4.0 %) | 2,613 (1.1 %) |
| "This register is available in all configurations." (txt: 152) | 0 | 152 |
| "Configurations" heading (txt: 349) | 2 | 349 |
| "feld" / "ofset" / "confgured" | 361 / 231 / 150 | 0 / 0 / 0 |
| ligature glyphs left unexpanded | 0 | 2,079, all inside table rows |
| `~~` fragments | 684 | 18 |
| page footer absorbed into a table row | 2 | 0 |
| bit-field table headers with a duplicated "Description" cell | 33 of 493 | 0 of 519 |
| per-page copyright footer lines kept (txt: 916) | 18 | 916 |
| figure placeholders | 89 | 0 |
| md word occurrences absent from txt | 3,939 (1.67 %) | 10,308 (4.11 %) |
| file size | 1,690,846 bytes | 1,859,426 bytes |

Reading of the table:

- The dropped prose lines, the mangled spellings, the fragments, the footer-in-table rows and the
  duplicated header cells all disappear. The remaining 1.1 % of words in absent lines are table
  rows that the two extractions lay out differently, the same noise level as the no-ligature rows
  in section 2.
- The 18 remaining `~~` strings are real labels of one block diagram ("System registers",
  "Debug APB", "CORECLK", "Core interface"). The converter marks text as struck through when a
  drawn line crosses it. This is cosmetic.
- The 2,079 unexpanded glyphs are the one residue. In prose the converter expands ligatures, in
  table cells it writes the glyph as is. `unicodedata.normalize("NFKC", text)` on the md turns
  every glyph into its letters, so this is a one-line post-processing step. Without it a plain
  search for "field" still misses those cells.
- Figures are omitted without any marker. The June md at least left a placeholder per figure.
- The extra md-only words are text the txt does not have: link targets such as
  `https://developer.arm.com/documentation/ddi0487/latest` (about 320 occurrences) and bit-field
  diagram labels ("RES0" 381 times, "exlevel", "p10" to "p16"). They are additions, not errors.

Conclusion on the cause. The June defects do not reproduce with pymupdf4llm 1.27.2.3 on this
host, for single pages or for the whole document. So the June run used a different pymupdf4llm
build, or different options, on another host (both scripts point at `/scratch/jhan/documents/ARM`).
Which of the two cannot be recovered from the files, because no md header records a version.

## 8. Impact on use of ARM/md

- For the C1-Nano TRM, `arm-txt/c1-nano-trm.txt` is the more complete copy. The md is not a
  superset of it.
- Register attribute lines ("Configurations", "This register is available in all configurations")
  are effectively absent from the Nano md.
- Searches for words that contain fi, ff or ffi inside tables ("field", "offset", "buffer",
  "configured", "affinity", "first", "define") miss most hits in every md file.
- The other four md files were made by the same tool on the same day. The table damage is
  measured (section 3). Whether they also lost prose lines is a hypothesis. To measure it, extract
  each PDF under `ARM/pdf` with `pdftotext -layout` and run the comparison in section 9.
- A re-conversion of all PDFs with pymupdf4llm 1.27.2.3, followed by NFKC normalization of the
  output, removes the defects of sections 2, 3, 4 and 5 (measured for the C1-Nano TRM in
  section 7). Record the package version in each md header when that is done.

## 9. How to re-check

The comparison script behind the word and line counts in sections 2 and 7. Run it as
`python3 nano_compare.py arm-txt/c1-nano-trm.txt ARM/md/Arm-C1-Nano-TRM-r0p2.md`.

```python
#!/usr/bin/env python3
"""Compare a layout txt (one form feed per page) against a pymupdf4llm md of the same PDF."""
import sys, re, unicodedata
from collections import Counter
txtp, mdp = sys.argv[1], sys.argv[2]; N = 8; LIG = "ﬁﬂﬀﬃﬄ"
FOOT = re.compile(r"Copyright © 2023.2025 Arm Limited \(or its a\w+liates\)\. All rights reserved\.")
def norm(s):
    s = unicodedata.normalize("NFKC", s); s = FOOT.sub(" ", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S); s = re.sub(r"==> picture.*?<==", " ", s)
    s = re.sub(r"<br>", " ", s); s = s.lower(); s = re.sub(r"f+[il]?", "", s)   # field/feld/eld compare equal
    return re.sub(r"[^a-z0-9]+", " ", s).split()
t = open(txtp, encoding="utf-8", errors="replace").read(); m = open(mdp, encoding="utf-8", errors="replace").read()
TW, MW = Counter(norm(t)), Counter(norm(m))
print(f"txt words absent from md: {sum((TW-MW).values()):,} of {sum(TW.values()):,}; md absent from txt: {sum((MW-TW).values()):,} of {sum(MW.values()):,}")
mw = norm(m); MS = set(tuple(mw[i:i+N]) for i in range(len(mw)-N+1))
c = Counter()
for page in t.split("\f"):
    for line in page.splitlines():
        s = line.strip()
        if re.search(r"\.{5,}", s): continue                      # table-of-contents dot leaders
        ws = norm(s)
        if len(ws) < 8: continue
        table = bool(re.search(r"\S {3,}\S", s))                   # column gaps = table layout
        lig = any(ch in s for ch in LIG); miss = tuple(ws[:8]) not in MS
        c[(table, lig, miss)] += 1
for table in (False, True):
    for lig in (False, True):
        tot = c[(table,lig,False)] + c[(table,lig,True)]; mi = c[(table,lig,True)]
        print(f"{'table' if table else 'prose'} lines {'with' if lig else 'without'} ligature: {tot:,}, absent {mi:,} ({mi/max(tot,1):.1%})")
```

Re-conversion used for section 7 (writes one md for the whole PDF):

```python
import fitz, pymupdf4llm, unicodedata
doc = fitz.open("ARM/pdf/Arm-C1-Nano-TRM-r0p2-107753_0002_06_en.pdf")
md = pymupdf4llm.to_markdown(doc, show_progress=False)
md = unicodedata.normalize("NFKC", md)        # expands the ligature glyphs left in table cells
open("out.md", "w", encoding="utf-8").write(f"<!-- pymupdf4llm {pymupdf4llm.__version__} -->\n\n" + md)
```

Quick checks without the script:

```bash
# mangled ligature spellings in a md file
grep -oiw 'feld\|ofset\|confgured\|bufer\|afnity' ARM/md/Arm-C1-Nano-TRM-r0p2.md | sort | uniq -c
# strikethrough fragments
grep -o '~~[^~]*~~' ARM/md/Arm-C1-Nano-TRM-r0p2.md | sort | uniq -c | sort -rn | head
# a sentence known to be dropped
grep -c 'available in all configurations' ARM/md/Arm-C1-Nano-TRM-r0p2.md     # 0 in the June md
```
