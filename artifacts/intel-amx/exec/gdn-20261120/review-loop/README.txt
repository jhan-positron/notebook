Evidence files of the review loop for GDN/gdn-amx-design.html (worker side).

regen_check.py          re-runs predict.py and gen_design.py with redirected outputs and compares with the saved files
structure_check.py      structure checks of the page (ASCII, references, figures, links, theme)
rerun_design_checks.sh  re-runs every pure-python design check from a scratch copy (it must sit next to a copy named dc/)
*.out, *.txt, *.json    saved outputs of these checks, one set per review round

Files of the plain-English pass of 2026-11-21 (rule set plain-english-experiment, run after REVIEW_COMPLETE):
gdn-amx-design.reviewed-82eab393.html   the page as the reviewer accepted it (round 2)
plain-english-writers.json              violations and fixes reported by the 8 writers
plain-english-verify.json               the 20 problems that 5 readers found in the rewrite (19 corrected, 1 kept)
plain_english_report.py                 builds GDN/gdn-amx-design.plain-english-check.html
plain-english-tools/                    regen_from.py (generate from a copy), check_page.py (length check with table cells and
                                        captions), numbers_diff.py (numbers before and after), merge.py (merge text blocks by name)
plain-english-regen-check.txt, plain-english-structure-check.txt   check outputs for the rewritten page
