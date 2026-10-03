Agreed. The layout is called VNNI everywhere else: the file name, the `v_vnni_*` types, and the kernel comments. The Note title should say it too.

Commit 76502ce5b2 renames the Note to `Note [VNNI Packed V layout]` at all 16 places where the name appears (the header and 15 references, in 7 files) and widens the underline to match. I applied it by hand rather than through the suggestion button. The button would have renamed the header only, and 15 other comments reference the title. The PR description line that names the Note is updated too.

The Note never spelled out VNNI. I added one clause to it: "That is the VNNI layout (named after Intel's Vector Neural Network Instructions)". Comment-only change. clang-format 19.1.7 reports no change. lint-notes (the repo's checker of Note references) finds no dangling reference.

If you would rather have the literal rename only, say so and I will drop the added clause.
