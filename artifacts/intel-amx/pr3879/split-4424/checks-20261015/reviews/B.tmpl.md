From simplify-cpp-comments (Check mode)

Reviewed commit `{{HEAD}}` against merge base `{{BASE}}` with the simplify-cpp-comments skill in Check mode: list every comment that a rule would cut, shorten or move, with the rule number and the proposed text. No code was edited. Only comments added or changed by this PR were checked (Rule 0).

The rules, in short:

- Rule 1: the name carries it (a function whose name and body say what the comment says gets no comment).
- Rule 2: do not restate identifiers.
- Rule 3: the one-line test (keep the one fact the code does not say, as one line).
- Rule 4: every comment line maps to a code line (a line that maps to nothing moves to the caller or the owning Note, or is cut).
- Rule 5: a call-site comment says only why the call sits here.
- Rule 6: no comment on a language idiom.

{{COUNT_LINE}}

`Note [..]` blocks were not proposed for cutting; inside a Note only a sentence that restates an identifier was flagged.

Every finding was checked by three independent agents with different lenses (the rule as written, the code at this commit, diff scope and line anchoring), each told to refute it; a finding is posted only when at least two did not. Proposed text was reflowed by hand to the 88-column limit. No code was built or run for this check.
