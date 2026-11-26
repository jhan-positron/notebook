---
name: cpp-coding-guide
description: Follow the C++ coding guide when writing, editing, or reviewing C++ code.
---

# C++ Coding Guide

Apply these rules to code you write or modify. When reviewing code, flag violations.

## Named values

- Define fixed values as named `constexpr` variables, except for the explicit literal exceptions below.
- Prefer literal `0` for zero initialization, resets, zero comparisons, and empty or disabled values when the surrounding code makes its meaning clear.
- Numeric literals are allowed in `alignas(...)`: the syntax already explains that the value specifies alignment in bytes. Prefer `alignas(64)` over introducing a constant that merely restates the alignment. Use a named constant when it expresses a shared requirement whose uses must change together.
- Use a named constant when the value encodes a domain-specific rule or the name explains meaning that is not apparent at the use site.
- Name `constexpr` variables using uppercase letters and underscores between words.
- Append the variable's value to its name, separated by an underscore.
- For values containing punctuation or spaces, use an uppercase representation valid in a C++ identifier.
- When editing a value in source code, rename the variable and update its uses so the suffix matches the new value.
- Keep other literals, including `1`, in named declarations and refer to them by name. List any further exceptions explicitly.
- Use a named `constexpr bool` only where a bool is passed as an argument in a function call or constructor call or template argument. The reason is, at call site a bare `true` or `false` does not say what it means.

```cpp
constexpr int DAYS_PER_WEEK_7 = 7;
constexpr int MAX_RETRIES_3 = 3;

// A named bool only at a call site: a bare
// literal does not say what it means.
constexpr bool ROW_ALIGNED_TRUE = true;
void pack(const rows_t& rows, bool row_aligned = true);
pack(rows, ROW_ALIGNED_TRUE);

// A literal bool in a return, an initialization, an assignment, or a
// comparison.
bool converted = false;
if (all_rows_saved) converted = true;
return converted;
```

## Braces

- Enclose control-flow bodies in braces, including bodies of `if`, `else`, `for`, `while`, and `do` statements.
- Braces may be omitted only when the entire statement, including its body and any `else` branches, appears on one physical line.
- Always retain braces where C++ syntax requires them.

```cpp
if (retryCount < MAX_RETRIES_3) {
    retry();
}

// Also allowed: the entire statement is on one line.
if (retryCount < MAX_RETRIES_3) retry();
```

## Hot paths

A hot path is code that runs once per token, once per page or once per layer. These rules apply there. Elsewhere, prefer the simplest code.

- Declare a scratch buffer without a fill when the next writer sets every element. A default constructor can zero-fill the buffer, and the declaration line does not show that work. Use the constructor that skips initialization, and add one comment line that names the writer. Keep the default constructor when any element is read before it is written.
- In tron, pass the `uninitialized` tag only to a one-dimensional `tensor`. A `tensor` of two or more dimensions keeps its rows in a union, and its tag constructor never constructs them. Any access to a row is then undefined (Note [Uninitialized Weight Tensors] in `h/common/util.hpp`). For a buffer of several rows, declare the rows as separate one-dimensional tensors with `make_array_of`. Use that form for a small row count. With a large count it compiles slowly: tron measured about ten minutes for one tensor type with 262,144 rows. For a large count, keep the default constructor and pay one zero fill, as the Note says.
- Pass a view when the reader accepts one. Do not copy into a temporary only to change the type. A view is an object that points at memory it does not own, such as `tron::const_view` or `std::span`. Before using a view, check that the source stays alive and unchanged while it is read, that the source and the destination do not overlap, and that the address meets the alignment the view type claims.
- Test the condition first. Prepare the inputs of a branch inside that branch, so that the other branch does not pay for them. Keep another order only with a measured reason, and state that reason in a comment.

```cpp
// The default constructor zero-fills the buffer. score_page then writes
// every element, so the fill is wasted work.
tensor<HEADS_16, PAGE_TOKENS_64> scores;
score_page(keys, query, &scores[0][0]);

// Undefined: the tag constructor of a two-dimensional tensor does not
// construct the rows, and scores[0] accesses a row.
tensor<HEADS_16, PAGE_TOKENS_64> scores{uninitialized};
score_page(keys, query, &scores[0][0]);

// uninitialized: score_page writes every element before any read.
// Each row is a one-dimensional tensor, where the tag is well-defined.
auto scores = make_array_of<tensor<PAGE_TOKENS_64>, HEADS_16>(uninitialized);
score_page(keys, query, &scores[0][0]);

// A copy made only to pass the row as an expression.
tensor<HEAD_SIZE_128> scratch;
std::memcpy(&scratch[0], row_begin, HEAD_SIZE_128 * sizeof(float));
v_star.set(fma(v_star, corr, scratch));

// A view over the same row. No bytes are copied.
constexpr bool ROW_ALIGNED_TRUE = true;
constexpr bool ROW_DMA_FALSE = false;
tron::const_view<float, ROW_ALIGNED_TRUE, ROW_DMA_FALSE, tron::seq<HEAD_SIZE_128>> row{
    row_begin};
v_star.set(fma(v_star, corr, row));

// The pack runs for every page, and a partial page never reads it.
const bf16* packed = pack_query(query, slot);
if (is_dense_page(page)) apply_dense_page(page, packed);

// The pack runs only for a page that reads it.
if (is_dense_page(page)) apply_dense_page(page, pack_query(query, slot));
```

## Tests behind a build option

A build option is a switch of the build that reaches the code as a macro, such as a CMake `option(...)` that the code reads with `#ifdef`. A guard is the `#ifdef` block on that macro. The registration of a test is the line of the build file that declares the test program. A fake is a stand-in that the test defines in place of a real function. The examples use Catch2, the C++ test framework. Its `SUCCEED` macro records a pass. Its `SKIP` macro ends a test case and reports it as skipped.

These rules apply to a test file with such a guard. They also apply when you add a case or a section inside a guard that is already there. When the guard or the registration is older than your change, tell the user what the guard leaves out, and propose the change. Do not change them without the user's decision.

- Do not write a placeholder case. A placeholder case is a test case that only reports success in the build without the option, such as an `#else` branch that calls `SUCCEED`. The test program then passes in a build that compiled none of the real cases, and the report shows the same pass for both builds.
- Give the macro to the one test program when the test supplies everything else. This holds when the code under test is in headers, and the test defines its own fakes for every function that the option adds to the library. Let the registration pass the definition of the macro to that one program. Search the registrations for a test that already does this, and copy its form. In tron this is the `DEFINES` argument of `add_catch_test`.
- Before you give the macro to one test program, check the code that the definition does not reach. That code is each library that the program links, and each object file that the build compiles once and shares between test programs. It must not compile an entity that the macro changes and that this test also uses. Such an entity is a class, an instance of a template for the same types, an inline function or an inline variable.
- After the registration passes the definition, remove the guard and the placeholder case. The real cases then run in every build. Check that a case fails without the definition. If none fails, put an `#error` for the missing macro at the top of the test file.
- Keep a guard only around the cases that need something a definition cannot supply. Examples are a source file that only the option adds to the library, a compiler feature, and hardware that the test host may lack. Put every other case outside the guard. When a case needs hardware, the case tests for the hardware at run time. Without the hardware it calls `SKIP`. The report then says "skipped".
- When every case of a file must stay behind the guard, the build without the option still needs one case. A Catch2 program without a test case exits with code 2, and the test fails. Make that case call `SKIP`, and register the test so that the exit code for "every case skipped" is reported as skipped. In tron this is `SKIP_RETURN_CODE 4` with the label `skip_return_code_4`.
- Do not widen a guard to remove a warning about an unused helper in the build without the option. The warning says that this build compiles the helpers and none of the cases that use them. Ask first whether the cases can run in that build.

```cpp
// A build without the option compiles only the second case. It passes,
// so the report shows a pass for checks that did not run.
#ifdef PROJECT_FAST_PATH
TEST_CASE("the dispatch calls each fake kernel once") { check_dispatch(); }
#else
TEST_CASE("dispatch test skipped (not compiled)") {
  SUCCEED("build without PROJECT_FAST_PATH - nothing to test");
}
#endif

// The test defines the fake kernels itself, so it needs only the macro.
// Its registration passes the definition to this one program:
//   add_catch_test(NAME t_dispatch DEFINES PROJECT_FAST_PATH ...)
// No guard and no placeholder case. The case runs in every build.
TEST_CASE("the dispatch calls each fake kernel once") { check_dispatch(); }

// The transpose needs nothing from the option, so it sits outside the guard.
// The kernel case needs the kernel source file and the instruction set.
// It stays inside the guard. A build without the option does not compile it.
// With the option, it reports a skip on a host without the instruction set.
TEST_CASE("the transpose writes every row") { check_transpose(); }
#ifdef PROJECT_FAST_PATH
TEST_CASE("the kernel matches the reference") {
  if (!fast_path::available()) SKIP("this host lacks the instruction set");
  check_kernel();
}
#endif
```
