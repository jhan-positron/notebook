From the named-bool check

Reviewed commit `{{HEAD}}` against merge base `{{BASE}}`. Rule applied (jhan, 2026-10-15): use a named `constexpr bool` only where a bool is passed as an argument in a function call or constructor call or template argument. The reason is, at a call site a bare `true` or `false` does not say what it means. Only lines added by this PR were checked.

{{COUNT_LINE}}

Each inline comment names the parameter the literal binds to and proposes a constant in the form this PR series already uses (`ALL_CAPS_TRUE` / `ALL_CAPS_FALSE`), or the bare literal where a named constant sits outside a call or template-argument position. Default arguments follow the precedent of PR #4901 commit d0e6f816dd: the parameter name is adjacent, so the default takes the bare literal.

Not flagged: `return true;`, assignments, comparisons, variable initializers, designated initializers, bare literals in default arguments, Catch2 macros, and computed `constexpr bool` values (`std::is_same_v`, `requires`, trait specializations).

For reference: on `main`, the parameter-name comment form `/*name=*/true` appears 454 times and no `*_TRUE` / `*_FALSE` constant exists outside `numeric_limits` traits. The rule above was applied as written.

Every finding was checked by two independent agents who were told to refute it; a finding is posted only when neither did. No code was built or run for this check.
