---
name: simplify-cpp-comments
description: Cut the comments of a C++ change down to what a reader needs. Use when reviewing or editing C++ comments, when the user says a comment is unnecessary, restates the code, or is too long for the code it sits on, or asks "is this comment necessary", "map the comment to the code", or "simplify the comments".
---

# Simplify C++ comments

Goal: every comment line that stays earns its place. A reader who knows C++ and the surrounding names learns one fact per comment line that the code does not already say.

Two modes:

- **Edit**: given a diff, a file, or a function, return the trimmed comments as exact edits (old text, new text) plus a table of what was cut and why.
- **Check**: given a diff, list every comment that a rule below would cut or shorten, with the rule number and the proposed text. Do not change code.

If the user did not say which mode, a request to "simplify" or "remove" means Edit; a question ("is this necessary?") means Check.

## Rules

### Rule 0 - Do diff only

Apply this skill on changed comments only, new or changed. Do not touch existing comment.

### Rule 1 - The name carries it

A function whose name and body say the same thing as its comment gets no comment. Typical: a one-expression accessor or predicate (`eagle_view_active() { return storage_view_offset_.i != 0; }`).

Test: cover the comment and read the signature and the body. If nothing is missing, delete the comment.

### Rule 2 - Do not restate identifiers

A comment does not repeat what names and types already say. "Only the blocks named by k_vnni_blocks hold the VNNI layout" restates `k_vnni_blocks`. Cut the sentence. A pointer to a Note is kept only when the Note holds a fact the names do not.

### Rule 3 - The one-line test

Write the function's contract in one line. Then:

- If that line adds nothing to the signature and the body, delete the comment (Rule 1).
- If it adds one fact (a precondition, a lifetime rule, a unit, what an empty result means), keep that one fact as one line.
- If it needs more than one line, the function may be doing too much; say so.

Prefer an attribute or a type over a comment when one exists (`TRON(this_lifetimebound)`, `[[nodiscard]]`, a `requires` clause, an assert).

### Rule 4 - Every comment line maps to a code line

For a comment longer than two lines above a short body, map each comment line to the code line it explains. A line that maps to nothing is either:

- caller context (why the function can be called in a given state): it moves to the caller or to the Note that owns that story, or is cut;
- a restatement (Rule 2): cut;
- a one-line contract (Rule 3): keep as the first line.

Put the surviving line next to the operand it explains when the body has several operands (one short comment above each operand beats one block above the function).

### Rule 5 - A call-site comment says only why here

At a call, the comment states the placement reason: why the call sits at this point, what must have happened before it, what would break if it moved. What the callee does belongs to the callee's comment. A sentence that restates the callee's comment or a Note is cut.

### Rule 6 - No comments on language idioms, and no idiom without a reason

Do not comment `(void)x;`, `T{}`, `~T{}`, `[[maybe_unused]]`, `.template`, or similar spellings. If a reviewer asks what such a spelling does, answer in the review, not in the code. Before keeping a warning-silencing idiom (`(void)x;`, `[[maybe_unused]]`), remove it and compile with the project's warning flags: a parameter referenced anywhere in the function body, and a variable referenced inside a discarded `if constexpr` branch, already count as used. Keep the idiom only when the compile shows the warning.

## Procedure (Edit mode)

1. List every comment the diff adds or changes, with file:line.
2. Classify each: contract (Rule 3), placement (Rule 5), anchored fact (Rule 4), restatement (Rule 2), name-carried (Rule 1), idiom note (Rule 6).
3. Apply the rule. Produce exact old/new text within the project's column limit and comment style. Reflow by hand: clang-format splits a comment line that is over the limit, and it never joins short lines.
4. For each surviving comment of more than two lines, do the Rule 4 mapping and show it.
5. Run the project's format check on the edited files.
6. Output: the edits, then a table with columns Rule, Original comment (first words), Action (cut / shortened to / moved to), Reason.

## Self-check before returning

- [ ] Did not check existing comments
- [ ] No comment restates a name, a type, or a Note.
- [ ] Every surviving comment longer than two lines has a line-to-code mapping.
- [ ] Every call-site comment states only placement.
- [ ] No language idiom carries a comment.
- [ ] Every edit's old text occurs exactly once in the file.
- [ ] The format check passed on the edited files.
